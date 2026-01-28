# ADR-005: ExitContract による dag_runner API 簡素化

## ステータス
提案中 (2026-01-28)

## コンテキスト

ADR-004 で終端ノードの設計を決定し、v0.12.0 で実装した。しかし、以下の冗長な抽象化が残っている：

```python
# v0.12.0 の状態
class DagRunnerResult:
    exit_code: str  # "exit::green::done"
    context: Any
    iterations: int
    execution_path: tuple[str, ...]

EXIT_CODES = {
    "exit.success.done": 0,
    "exit.failure.timeout": 1,
}

result = dag_runner(
    start=start,
    transitions=TRANSITIONS,
    exit_codes=EXIT_CODES,  # ← 冗長
)
```

**問題点:**

| 問題 | 説明 |
|------|------|
| 二重管理 | `EXIT_CODES` と終端ノード関数の両方を定義 |
| 型安全性の欠如 | `exit_code` が文字列、`context` が `Any` |
| 冗長な抽象化 | `Exit.GREEN`, `Exit.code()`, `DagRunnerResult`, `ExitOutcome` |

## 決定

### 1. ExitContract 基底クラス導入

終端ノードが返す型を `ExitContract` で統一する。

```python
from railway import ExitContract

class DoneResult(ExitContract):
    """処理完了時の結果。"""
    data: dict[str, Any]
    processed_count: int
    exit_state: str = "success.done"  # exit_code は自動導出（0）

class TimeoutResult(ExitContract):
    """タイムアウト時の結果。"""
    reason: str
    exit_state: str = "failure.timeout"  # exit_code は自動導出（1）
```

**ExitContract の設計:**

```python
class ExitContract(Contract):
    """終端ノードが返す Contract の基底クラス。"""
    exit_state: str                      # 必須: "success.done", "failure.timeout" など
    exit_code: int | None = None         # 省略時は exit_state から自動導出
    execution_path: tuple[str, ...] = () # dag_runner が設定
    iterations: int = 0                  # dag_runner が設定

    @model_validator(mode="after")
    def _derive_exit_code(self) -> "ExitContract":
        """exit_code が None なら exit_state から自動導出。"""
        if self.exit_code is None:
            derived = 0 if self.exit_state.startswith("success") else 1
            object.__setattr__(self, "exit_code", derived)
        return self

    @property
    def is_success(self) -> bool:
        return self.exit_code == 0
```

**exit_code 自動導出ルール:**

| exit_state パターン | exit_code |
|---------------------|-----------|
| `success.*` | 0 |
| `failure.*` | 1 |
| `warning.*` | 1（カスタム可） |
| その他 | 1 |

### 2. dag_runner の返り値を ExitContract に

```python
# Before (v0.12.0)
def dag_runner(..., exit_codes: dict[str, int]) -> DagRunnerResult:
    ...

# After (v0.12.2)
def dag_runner(...) -> ExitContract:
    ...
```

**終端ノードの実装:**

```python
@node(name="exit.success.done")
def done(ctx: WorkflowContext) -> DoneResult:
    """終端ノードは ExitContract を返す。"""
    return DoneResult(
        data=ctx.data,
        processed_count=ctx.count,
    )
```

**dag_runner の動作:**

1. 終端ノードを検出（`exit.` または `_exit_` プレフィックス）
2. 終端ノードを実行
3. 結果が `ExitContract` なら `execution_path` と `iterations` を追加して返す
4. 結果が `ExitContract` でなければ `DefaultExitContract` でラップ（後方互換）

### 3. 削除する抽象化

| 削除対象 | 理由 |
|----------|------|
| `Exit` クラス | `ExitContract` サブクラスで代替 |
| `Exit.GREEN`, `Exit.RED`, `Exit.YELLOW` | 不要 |
| `Exit.code()` | 不要 |
| `DagRunnerResult` | `ExitContract` で代替 |
| `exit_codes` パラメータ | `ExitContract.exit_code` で定義 |
| `EXIT_CODES` 生成（codegen） | 不要 |
| `ExitOutcome` | 未使用 |
| `NodeDefinition.exit_code` | `ExitContract` で定義 |

## 理由

### 型安全性の向上

```python
# Before: Any 型
result: DagRunnerResult = dag_runner(...)
data = result.context  # Any 型、IDE 補完なし

# After: 具体的な型
result: DoneResult = dag_runner(...)
data = result.data  # dict[str, Any] 型、IDE 補完あり
count = result.processed_count  # int 型
```

### API の簡素化

```python
# Before: 3つの概念を管理
EXIT_CODES = {"exit.success.done": 0, ...}
TRANSITIONS = {"node::success::done": Exit.code("green", "done")}
result = dag_runner(..., exit_codes=EXIT_CODES)

# After: 1つの概念
TRANSITIONS = {"node::success::done": done}  # done は ExitContract を返す関数
result = dag_runner(...)
```

### 一貫性

- 通常ノード: `Contract` を返す
- 終端ノード: `ExitContract`（`Contract` のサブクラス）を返す
- すべてのノードが `Contract` ベースの型を返す

## 影響

### 破壊的変更

| 変更 | マイグレーション |
|------|------------------|
| `dag_runner()` 返り値 | `DagRunnerResult` → `ExitContract` |
| `run()` 返り値（codegen） | `DagRunnerResult` → `ExitContract` |
| `exit_codes` パラメータ | 削除 |
| `Exit` クラス | 削除 |

### 後方互換性

- 終端ノードが `ExitContract` 以外を返す場合、`DefaultExitContract` でラップ
- `exit_state` は終端ノード名から自動導出

```python
# 後方互換: Context のみ返す終端ノード
@node(name="exit.success.done")
def done(ctx: WorkflowContext) -> dict:
    return {"status": "ok"}

# dag_runner は DefaultExitContract でラップして返す
result = dag_runner(...)
assert isinstance(result, DefaultExitContract)
assert result.context == {"status": "ok"}
assert result.exit_state == "success.done"
```

### 実装への影響

**追加:**
- `ExitContract` 基底クラス（`railway/core/exit_contract.py`）
- `DefaultExitContract` フォールバッククラス
- `_is_exit_node()` 純粋関数
- `_derive_exit_state()` 純粋関数

**削除:**
- `Exit` クラス
- `DagRunnerResult` クラス
- `exit_codes` パラメータ
- `EXIT_CODES` 生成（codegen）
- `ExitOutcome` クラス
- `NodeDefinition.exit_code` 属性

## 代替案

### 代替案A: DagRunnerResult に型パラメータ追加

```python
class DagRunnerResult(Generic[T]):
    context: T
    ...

result: DagRunnerResult[DoneResult] = dag_runner(...)
```

**却下理由:**
- `DagRunnerResult` と `ExitContract` の二重構造が残る
- `exit_code` 文字列と数値の変換が必要

### 代替案B: exit_code を ExitContract に含めない

```python
class ExitContract(Contract):
    exit_state: str
    # exit_code なし
```

**却下理由:**
- シェルスクリプトとの連携で数値終了コードが必要
- `exit_state` から毎回計算するのは非効率

## 参考資料

- ADR-004: Exit ノードの設計と例外処理
- Issue #34: executor の YamlTransform 適用
- Issue #35: ExitContract 基底クラス追加
- Issue #36: dag_runner・codegen の ExitContract 対応
- Issue #37: 不要コード削除
- Issue #38: リリース準備
