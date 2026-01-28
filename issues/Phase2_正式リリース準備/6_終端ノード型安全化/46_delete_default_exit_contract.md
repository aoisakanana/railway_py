# Issue #46: DefaultExitContract 削除（強制）

**優先度**: P1
**依存**: #45
**ブロック**: #47 (TUTORIAL.md 更新)
**バージョン**: v0.13.0（破壊的変更）

---

## 概要

`DefaultExitContract` を削除し、終端ノードが必ず `ExitContract` サブクラスを返すことを強制する。

## 背景

- #44: スケルトン生成により、開発者は正しい形式のコードを得られる
- #45: 警告により、既存コードの問題を事前に検知できる

これらの準備が整った上で、最終的に `DefaultExitContract` を削除し、型安全性を強制する。

**移行パス**:
```
v0.12.3 (#44, #45)
    - スケルトン生成で正しい形式を提供
    - 警告で問題を通知
    ↓ 開発者が修正
v0.13.0 (#46)
    - DefaultExitContract 削除
    - 不正な返り値は TypeError
```

---

## TDD 実装フロー

### Phase 1: Red（失敗するテストを先に作成）

#### 1-1. カスタム例外のテスト

```python
# tests/unit/core/dag/test_exit_node_errors.py

import pytest
from railway.core.dag.errors import (
    ExitNodeTypeError,
    LegacyExitFormatError,
)


class TestExitNodeTypeError:
    """終端ノード型エラーのテスト。"""

    def test_includes_node_name(self) -> None:
        error = ExitNodeTypeError(
            node_name="exit.success.done",
            actual_type="dict",
        )
        assert "exit.success.done" in str(error)

    def test_includes_actual_type(self) -> None:
        error = ExitNodeTypeError(
            node_name="exit.success.done",
            actual_type="dict",
        )
        assert "dict" in str(error)

    def test_includes_hint(self) -> None:
        error = ExitNodeTypeError(
            node_name="exit.success.done",
            actual_type="dict",
        )
        assert "railway sync transition" in str(error)

    def test_is_type_error(self) -> None:
        """TypeError のサブクラスである。"""
        error = ExitNodeTypeError(
            node_name="exit.success.done",
            actual_type="dict",
        )
        assert isinstance(error, TypeError)


class TestLegacyExitFormatError:
    """レガシー exit 形式エラーのテスト。"""

    def test_includes_legacy_format(self) -> None:
        error = LegacyExitFormatError(legacy_format="exit::green::done")
        assert "exit::green::done" in str(error)

    def test_includes_hint(self) -> None:
        error = LegacyExitFormatError(legacy_format="exit::green::done")
        assert "railway update" in str(error)

    def test_is_value_error(self) -> None:
        """ValueError のサブクラスである。"""
        error = LegacyExitFormatError(legacy_format="exit::green::done")
        assert isinstance(error, ValueError)
```

#### 1-2. dag_runner のテスト

```python
# tests/unit/core/dag/test_runner_exit_contract_enforcement.py

import pytest
from railway import ExitContract, Contract, node
from railway.core.dag import dag_runner, async_dag_runner, Outcome
from railway.core.dag.errors import ExitNodeTypeError, LegacyExitFormatError


class ValidExitResult(ExitContract):
    """テスト用の正しい ExitContract。"""
    exit_state: str = "success.done"
    message: str = "completed"


class CustomExitResult(ExitContract):
    """カスタムフィールドを持つ ExitContract。"""
    exit_state: str = "success.done"
    processed_count: int
    summary: str


class StartContext(Contract):
    """開始ノードのコンテキスト。"""
    value: str = "initial"


# --- フィクスチャ用の関数 ---

def make_start_node():
    """開始ノードを生成するファクトリ。"""
    @node(name="start")
    def start() -> tuple[StartContext, Outcome]:
        return StartContext(), Outcome.success("done")
    return start


class TestExitNodeMustReturnExitContract:
    """終端ノードは ExitContract を返す必要がある。"""

    def test_exit_node_returning_dict_raises_type_error(self) -> None:
        """終端ノードが dict を返すと ExitNodeTypeError。"""
        @node(name="exit.success.done")
        def exit_returns_dict(ctx: StartContext) -> dict:
            return {"status": "ok"}

        start = make_start_node()
        transitions = {"start::success::done": exit_returns_dict}

        with pytest.raises(ExitNodeTypeError) as exc_info:
            dag_runner(start=start, transitions=transitions)

        error = exc_info.value
        assert "exit.success.done" in str(error)
        assert "dict" in str(error)

    def test_exit_node_returning_none_raises_type_error(self) -> None:
        """終端ノードが None を返すと ExitNodeTypeError。"""
        @node(name="exit.success.done")
        def exit_returns_none(ctx: StartContext) -> None:
            return None

        start = make_start_node()
        transitions = {"start::success::done": exit_returns_none}

        with pytest.raises(ExitNodeTypeError) as exc_info:
            dag_runner(start=start, transitions=transitions)

        assert "NoneType" in str(exc_info.value)

    def test_exit_node_returning_exit_contract_succeeds(self) -> None:
        """終端ノードが ExitContract を返すと成功。"""
        @node(name="exit.success.done")
        def exit_returns_contract(ctx: StartContext) -> ValidExitResult:
            return ValidExitResult()

        start = make_start_node()
        transitions = {"start::success::done": exit_returns_contract}

        result = dag_runner(start=start, transitions=transitions)

        assert isinstance(result, ExitContract)
        assert result.is_success

    def test_exit_node_returning_custom_exit_contract_succeeds(self) -> None:
        """終端ノードがカスタム ExitContract サブクラスを返すと成功。

        Note:
            開発者は ExitContract を継承した独自のクラスを定義し、
            カスタムフィールドを追加できる。
        """
        @node(name="exit.success.done")
        def exit_returns_custom(ctx: StartContext) -> CustomExitResult:
            return CustomExitResult(
                processed_count=42,
                summary="All items processed",
            )

        start = make_start_node()
        transitions = {"start::success::done": exit_returns_custom}

        result = dag_runner(start=start, transitions=transitions)

        assert isinstance(result, CustomExitResult)
        assert result.processed_count == 42
        assert result.summary == "All items processed"
        assert result.exit_state == "success.done"
        assert result.exit_code == 0
        assert result.is_success


class TestExitNodeWithFailureState:
    """failure 状態の終端ノードのテスト。"""

    def test_failure_exit_node_returns_exit_code_1(self) -> None:
        """failure 状態の終端ノードは exit_code=1 を返す。"""
        class FailureTimeoutResult(ExitContract):
            exit_state: str = "failure.timeout"
            reason: str

        @node(name="exit.failure.timeout")
        def exit_timeout(ctx: StartContext) -> FailureTimeoutResult:
            return FailureTimeoutResult(reason="Request timed out")

        start = make_start_node()
        transitions = {"start::success::done": exit_timeout}

        result = dag_runner(start=start, transitions=transitions)

        assert isinstance(result, FailureTimeoutResult)
        assert result.exit_state == "failure.timeout"
        assert result.exit_code == 1
        assert result.is_success is False
        assert result.is_failure is True
        assert result.reason == "Request timed out"


class TestLegacyExitFormatIsRejected:
    """レガシー exit 形式は拒否される。"""

    def test_legacy_exit_format_raises_error(self) -> None:
        """レガシー形式 'exit::green::done' は LegacyExitFormatError。"""
        start = make_start_node()
        transitions = {"start::success::done": "exit::green::done"}

        with pytest.raises(LegacyExitFormatError) as exc_info:
            dag_runner(start=start, transitions=transitions)

        assert "exit::green::done" in str(exc_info.value)
        assert "railway update" in str(exc_info.value)


@pytest.mark.asyncio
class TestExitNodeMustReturnExitContractAsync:
    """非同期終端ノードも ExitContract を返す必要がある。"""

    async def test_async_exit_node_returning_dict_raises_type_error(self) -> None:
        """非同期終端ノードが dict を返すと ExitNodeTypeError。"""
        @node(name="exit.success.done")
        async def exit_returns_dict(ctx: StartContext) -> dict:
            return {"status": "ok"}

        @node(name="start")
        async def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.success("done")

        transitions = {"start::success::done": exit_returns_dict}

        with pytest.raises(ExitNodeTypeError):
            await async_dag_runner(start=start, transitions=transitions)

    async def test_async_exit_node_returning_exit_contract_succeeds(self) -> None:
        """非同期終端ノードが ExitContract を返すと成功。"""
        @node(name="exit.success.done")
        async def exit_returns_contract(ctx: StartContext) -> ValidExitResult:
            return ValidExitResult()

        @node(name="start")
        async def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.success("done")

        transitions = {"start::success::done": exit_returns_contract}

        result = await async_dag_runner(start=start, transitions=transitions)

        assert isinstance(result, ExitContract)
        assert result.is_success
```

### Phase 2: Green（最小実装）

#### 2-1. カスタム例外定義

```python
# railway/core/dag/errors.py

"""DAG ランナー関連のエラー定義。"""
from __future__ import annotations


class ExitNodeTypeError(TypeError):
    """終端ノードが ExitContract を返さなかった場合のエラー。

    Attributes:
        node_name: 終端ノード名
        actual_type: 実際に返された型名
    """

    def __init__(self, node_name: str, actual_type: str) -> None:
        self.node_name = node_name
        self.actual_type = actual_type
        message = (
            f"終端ノード '{node_name}' は ExitContract を返す必要があります。"
            f" 戻り値の型: {actual_type}"
            f"\n\nヒント: `railway sync transition` を実行してスケルトンを生成してください。"
        )
        super().__init__(message)


class LegacyExitFormatError(ValueError):
    """レガシー exit 形式が使用された場合のエラー。

    Attributes:
        legacy_format: 使用されたレガシー形式
    """

    def __init__(self, legacy_format: str) -> None:
        self.legacy_format = legacy_format
        message = (
            f"レガシー exit 形式 '{legacy_format}' は v0.13.0 で廃止されました。"
            " 終端ノード関数を使用してください。"
            "\n\nヒント: `railway update` を実行してマイグレーションしてください。"
        )
        super().__init__(message)
```

#### 2-2. runner.py の修正

```python
# railway/core/dag/runner.py

from railway.core.dag.errors import ExitNodeTypeError, LegacyExitFormatError

# Before (v0.12.x):
# if isinstance(result, ExitContract):
#     return result.model_copy(...)
# else:
#     return DefaultExitContract(context=result, ...)

# After (v0.13.0):
def _execute_exit_node(
    exit_node: Callable,
    context: Any,
    node_name: str,
    execution_path: list[str],
    iteration: int,
) -> ExitContract:
    """終端ノードを実行し、ExitContract を返す（純粋関数的）。

    Args:
        exit_node: 終端ノード関数
        context: 直前のコンテキスト
        node_name: ノード名
        execution_path: 実行パス
        iteration: イテレーション数

    Returns:
        ExitContract: 終了結果

    Raises:
        ExitNodeTypeError: ExitContract 以外が返された場合
    """
    result = exit_node(context)

    if isinstance(result, ExitContract):
        return result.model_copy(update={
            "execution_path": tuple(execution_path),
            "iterations": iteration,
        })

    raise ExitNodeTypeError(
        node_name=node_name,
        actual_type=type(result).__name__,
    )


def _resolve_next_step(
    next_step: Callable | str,
    transition_key: str,
) -> Callable:
    """次のステップを解決する。

    Args:
        next_step: 次のステップ（関数またはレガシー文字列）
        transition_key: 遷移キー

    Returns:
        次のノード関数

    Raises:
        LegacyExitFormatError: レガシー形式が使用された場合
    """
    if isinstance(next_step, str) and next_step.startswith("exit::"):
        raise LegacyExitFormatError(legacy_format=next_step)
    return next_step
```

#### 2-3. DefaultExitContract の削除

```python
# railway/core/exit_contract.py から削除:

# class DefaultExitContract(ExitContract):
#     """デフォルト終端 Contract（後方互換・ハンドラなし用）。
#
#     Note:
#         v0.13.0 で削除。終端ノードは必ず ExitContract サブクラスを返す必要がある。
#     """
#     context: Any = None
```

#### 2-4. エクスポートから削除

```python
# railway/__init__.py
# "DefaultExitContract" を __all__ から削除

# railway/core/dag/__init__.py
# "DefaultExitContract" を __all__ から削除
```

### Phase 3: Refactor

- エラーメッセージの改善
- マイグレーションガイドの更新
- ADR-005 更新

---

## 修正ファイル

| ファイル | 変更内容 |
|----------|----------|
| `railway/core/dag/errors.py` | 新規ファイル（カスタム例外） |
| `railway/core/exit_contract.py` | `DefaultExitContract` クラス削除 |
| `railway/core/dag/runner.py` | `DefaultExitContract` 使用箇所を `ExitNodeTypeError` に変更 |
| `railway/__init__.py` | エクスポートから削除 |
| `tests/unit/core/dag/test_exit_node_errors.py` | 新規テストファイル |
| `tests/unit/core/dag/test_runner_exit_contract_enforcement.py` | 新規テストファイル |
| `tests/unit/core/test_exit_contract.py` | `DefaultExitContract` テスト削除 |

---

## エラーメッセージ例

### ExitNodeTypeError

```
ExitNodeTypeError: 終端ノード 'exit.success.done' は ExitContract を返す必要があります。
戻り値の型: dict

ヒント: `railway sync transition` を実行してスケルトンを生成してください。
```

### LegacyExitFormatError

```
LegacyExitFormatError: レガシー exit 形式 'exit::green::done' は v0.13.0 で廃止されました。
終端ノード関数を使用してください。

ヒント: `railway update` を実行してマイグレーションしてください。
```

---

## 受け入れ条件

### 機能
- [ ] `DefaultExitContract` クラスが削除されている
- [ ] 終端ノードが `ExitContract` 以外を返すと `ExitNodeTypeError` が発生
- [ ] 終端ノードが `ExitContract` サブクラス（カスタムクラス含む）を返すと成功
- [ ] エラーメッセージにノード名と実際の戻り値型が含まれる
- [ ] エラーメッセージに解決方法のヒントが含まれる
- [ ] sync/async 両方で同じ動作
- [ ] レガシー exit 形式は `LegacyExitFormatError`
- [ ] カスタム例外は標準例外のサブクラス（`TypeError`, `ValueError`）

### TDD・関数型
- [ ] Red → Green → Refactor フェーズに従って実装
- [ ] 新規テスト追加
- [ ] 既存の `DefaultExitContract` テスト削除
- [ ] 純粋関数的なヘルパー関数に分離
- [ ] 全テスト通過

### ドキュメント
- [ ] ADR-005 更新（DefaultExitContract 廃止を記載）
- [ ] マイグレーションガイド更新
- [ ] CHANGELOG に破壊的変更を記載

---

## 破壊的変更

**影響**:
- 終端ノードが `ExitContract` サブクラスを返さないコードは動作しなくなる
- レガシー exit 形式 (`"exit::green::done"`) は動作しなくなる

**マイグレーション**:
1. `railway sync transition` でスケルトン生成（#44）
2. 警告に従ってコード修正（#45）
3. `railway update` でレガシー形式を新形式に変換

---

*型安全性の最終強制*
