# ADR-007: Riverboard パターンによる DAG ノード設計の刷新

## ステータス
承認済み (2026-03-10)

## コンテキスト

v0.13.x までの DAG ノードは Contract ベースの設計を採用していた：

```python
# v0.13.x: Contract + model_copy + tuple
@node
def check_host(ctx: AlertContext) -> tuple[AlertContext, Outcome]:
    hostname = lookup(ctx.incident_id)
    return ctx.model_copy(update={"hostname": hostname}), Outcome.success("found")
```

**問題点:**

| 問題 | 影響 |
|------|------|
| `model_copy()` の冗長性 | 毎回 Contract を複製する儀式的コード |
| `tuple` 返り値 | `(context, outcome)` のアンパック忘れでバグ |
| `requires/optional/provides` の YAML 二重管理 | ノードコードと YAML の同期が必要 |
| 静的解析不能 | フィールド依存を実行時にしか検証できない |

### 目標

1. ノード実装の簡潔化
2. フィールド依存の静的検証
3. AST ベースのゼロ設定依存抽出

## 決定

### 1. Board パターン（ミュータブル共有状態）

Contract の代わりに、`BoardBase` をノード間で共有する：

```python
# v0.14.0: Board パターン
@node
def check_host(board) -> Outcome:
    board.hostname = lookup(board.incident_id)
    return Outcome.success("found")
```

**BoardBase** は任意のフィールドを動的に受け付ける mutable オブジェクト：

```python
class BoardBase:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            object.__setattr__(self, key, value)
```

**設計判断:**
- Pydantic ではなく素の Python オブジェクト（バリデーション不要、高速）
- `_snapshot()` で任意のタイミングでスナップショット取得可能
- テスト時に sync 不要で直接使用可能

### 2. WorkflowResult（ExitContract の置換）

Board mode の `dag_runner` は `WorkflowResult` を返す：

```python
@dataclass(frozen=True)
class WorkflowResult:
    exit_state: str
    exit_code: int
    board: BoardBase
    execution_path: tuple[str, ...] = ()
    iterations: int = 0
    trace: Any | None = None
```

ExitContract と異なり、frozen dataclass であり Pydantic 非依存。

### 3. `board` パラメータ名の強制（E015）

Board mode ノードの第一引数は必ず `board` でなければならない：

```python
# ✅ 正しい
@node
def check(board) -> Outcome: ...

# ❌ E015 エラー
@node
def check(ctx) -> Outcome: ...
```

**理由:** AST 解析で `board.xxx` の読み書きを追跡するため、引数名の統一が必要。

**Linear mode との判別:** `@node(output=...)` または `@node(inputs=...)` が指定されていれば Linear mode として E015 チェックをスキップ。

### 4. AST アナライザ（sync as コンパイラ）

`railway sync transition` を「ドメイン特化コンパイラ」として拡張：

```
YAML パース → グラフ検証 → ノードファイル AST 解析
    → reads/writes 抽出 → 経路依存検証
    → Board 型自動生成 → 遷移コード生成
```

**AST 解析の出力（NodeAnalysis）:**

| フィールド | 説明 |
|-----------|------|
| `reads_required` | 条件分岐外で読み取るフィールド |
| `reads_optional` | 条件分岐内でのみ読み取るフィールド |
| `branch_writes` | Outcome 分岐ごとの書き込みフィールド |
| `all_writes` | 全書き込みフィールド |
| `violations` | パターン違反（E012〜E015） |

### 5. 経路ごとの依存検証

遷移グラフの各辺で、遷移先ノードの `reads_required` が遷移元の `writes` でカバーされているか検証：

| コード | 種別 | 説明 |
|--------|------|------|
| E010 | エラー | 必須フィールドが遷移辺上で不足 |
| E012 | エラー | board を関数引数として渡している |
| E013 | エラー | board を別の変数に代入している |
| E014 | エラー | getattr/setattr で動的アクセス |
| E015 | エラー | 第一引数名が `board` でない |
| E016 | エラー | dunder名（`__xxx__`）をエントリポイント名/ノード名に使用 |
| E017 | エラー | 予約名（`exit` 等）をエントリポイント名/ノード名に使用 |
| W001 | 警告 | writes したフィールドを後続ノードが reads しない |
| I001 | 情報 | 合流地点で optional フィールドが一部経路からのみ提供 |

### 6. Entry Fields の定義

開始ノードの **reads**（writes ではなく）が entry_fields となる：

```python
@node
def start(board) -> Outcome:
    # board.incident_id を読む → entry_fields に含まれる
    severity = classify(board.incident_id)
    board.severity = severity
    return Outcome.success("check")
```

これにより、ワークフロー実行時に呼び出し元が提供すべきフィールドが自動導出される。

### 7. Board 型自動生成

AST 解析結果から型付き Board クラスを自動生成：

```python
# _railway/generated/{entry}_board.py（自動生成）
class AlertWorkflowBoard(BoardBase):
    """alert_workflow の Board 型（自動生成）。"""

    # entry_point で提供
    incident_id: Any

    # check_host が writes
    hostname: Any = None

    # escalate が writes
    escalated: Any = None
```

### 8. Trace モード

Board のスナップショット差分を追跡するデバッグ機能：

```bash
railway run my_workflow --trace
```

```
[trace] start:
  mutations: severity
[trace] check_host:
  mutations: hostname
[trace] escalate:
  mutations: escalated, notified_at
```

## 理由

### Contract パターンとの比較

| 観点 | Contract (v0.13) | Board (v0.14) |
|------|-----------------|---------------|
| データ更新 | `model_copy(update={...})` | `board.x = value` |
| 返り値 | `tuple[Context, Outcome]` | `Outcome` のみ |
| 依存宣言 | `@node(requires=[], provides=[])` | **自動（AST 解析）** |
| 型安全性 | Pydantic 実行時検証 | sync 時静的検証 |
| テスト | Contract インスタンス作成 | `BoardBase()` で即テスト |
| パフォーマンス | model_copy のオーバーヘッド | 直接代入 |

### なぜ mutable か

**Railway Oriented Programming の本質は「エラーの分岐制御」であり、「イミュータブルなデータ」ではない。**

- ノード間のデータ引き継ぎは **board の直接変更** で十分
- イミュータブル性は **WorkflowResult**（最終結果）で担保
- 中間状態の immutability は実質的な恩恵がなく、コード複雑性のみ増大

### なぜ AST 解析か

- **ゼロ設定:** ノードコードから依存を自動抽出
- **静的:** 実行前にフィールド依存エラーを検出
- **正確:** `board.xxx` パターンのみ追跡（E012〜E014 で非トレーサブルなパターンを禁止）

## 影響

### 後方互換性

| 機能 | v0.13 | v0.14 |
|------|-------|-------|
| Contract mode dag_runner | サポート | **引き続きサポート** |
| Board mode dag_runner | なし | 新規追加 |
| `@node(requires=..., provides=...)` | サポート | **削除** |
| `typed_pipeline` | サポート | 引き続きサポート（Linear mode） |
| ExitContract | dag_runner 返り値 | Contract mode のみ |
| WorkflowResult | なし | Board mode 返り値 |

**Contract mode は廃止されない。** Board mode は新しいデフォルトとして推奨。

### マイグレーション

```bash
railway update  # v0.13 → v0.14 マイグレーション
```

検出パターン:
- `model_copy` の使用 → Board パターンへの書き換えを提案
- `@node(requires=[], provides=[])` → 削除を提案
- `tuple[Context, Outcome]` 返り値 → `Outcome` のみに変更を提案
- ExitContract サブクラス → Board mode 終端ノードへの変換を提案

### 実装への影響

**追加:**
- `railway/core/board.py` — `BoardBase`, `WorkflowResult`
- `railway/core/dag/board_analyzer.py` — AST 解析
- `railway/core/dag/path_validator.py` — 経路依存検証
- `railway/core/dag/board_codegen.py` — Board 型生成
- `railway/core/dag/trace.py` — Trace 型
- `railway/core/dag/sync_cache.py` — 差分解析キャッシュ
- `railway/core/dag/sync_scope.py` — sync スコープ計算

**変更:**
- `railway/core/decorators.py` — E015 チェック追加、requires/optional/provides 削除
- `railway/core/dag/runner.py` — Board mode 追加
- `railway/cli/sync.py` — AST 解析パイプライン統合
- `railway/cli/new.py` — Board mode テンプレート
- `railway/cli/run.py` — `--trace` フラグ

## 代替案

### 代替案A: TypedDict ベース

```python
class AlertBoard(TypedDict, total=False):
    incident_id: str
    hostname: str | None
```

**却下理由:** TypedDict は静的型チェック向けで、動的フィールド追加に不向き。

### 代替案B: Pydantic Model（frozen=False）

```python
class AlertBoard(BaseModel):
    model_config = ConfigDict(frozen=False)
    incident_id: str
```

**却下理由:** Pydantic のバリデーションオーバーヘッドが不要。Board は内部状態であり、外部入力のバリデーションは不要。

### 代替案C: requires/provides の YAML 記述維持

**却下理由:** AST 解析で自動抽出できるため、手動記述は冗長。

## 参考資料

- ADR-004: Exit ノードの設計と例外処理
- ADR-005: ExitContract による dag_runner API 簡素化
- ADR-006: フィールドベース依存関係
- Phase 4 Issue 一覧: `.local/issues/Phase4/`
