# Issue #15: @node デコレータ自動マッピング & Outcome クラス

**Phase:** 2c
**優先度:** 高
**依存関係:** #07（状態Enum基底クラス）
**見積もり:** 1日

> **Note:** dag_runner（#10）が本Issueに依存します（Outcome.to_state_string() を使用するため）。
> 本Issueの統合テスト（TestOutcomeWithDagRunner）は #10 完了後に実行可能になります。

---

## 概要

ノード関数の戻り値を簡潔かつ型安全に記述するため、以下を実装する：

1. **Outcome クラス** - `success`/`failure` を表現する軽量な型
2. **dag_runner の自動状態解決** - 関数名から状態文字列を自動生成

これにより、State Enum のimportや指定が**完全に不要**になり、ノード実装が最もシンプルになる。

---

## 設計原則

### Before（現在の冗長な実装）

```python
from _railway.generated.my_workflow_transitions import MyWorkflowState

@node
def fetch_alert(ctx: InputContext) -> tuple[OutputContext, MyWorkflowState]:
    if success:
        return OutputContext(...), MyWorkflowState.FETCH_ALERT_SUCCESS_DONE
    else:
        return OutputContext(...), MyWorkflowState.FETCH_ALERT_FAILURE_HTTP
```

**問題点:**
- State Enum 名が冗長（`FETCH_ALERT_SUCCESS_DONE`）
- 生成コードのimportが必要
- DRY 原則違反（関数名がEnum値に重複）

### After（理想の実装）

```python
from railway import node, Outcome

@node  # state_enum 指定は不要！
def fetch_alert(ctx: InputContext) -> tuple[OutputContext, Outcome]:
    if success:
        return OutputContext(...), Outcome.success("done")
    else:
        return OutputContext(...), Outcome.failure("http")
```

**改善点:**
- `Outcome.success("done")` を返すだけ
- dag_runner が自動的に `"fetch_alert::success::done"` を生成
- 生成コードのimport不要
- ノード実装が最もシンプル

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/core/dag/test_outcome.py
"""Tests for Outcome class and @node decorator mapping."""
import pytest
from enum import Enum


class TestOutcome:
    """Test Outcome class."""

    def test_success_outcome(self):
        """Should create success outcome."""
        from railway.core.dag.outcome import Outcome

        outcome = Outcome.success("done")

        assert outcome.is_success is True
        assert outcome.is_failure is False
        assert outcome.outcome_type == "success"
        assert outcome.detail == "done"

    def test_failure_outcome(self):
        """Should create failure outcome."""
        from railway.core.dag.outcome import Outcome

        outcome = Outcome.failure("http")

        assert outcome.is_success is False
        assert outcome.is_failure is True
        assert outcome.outcome_type == "failure"
        assert outcome.detail == "http"

    def test_outcome_to_state_string(self):
        """Should convert to state string format."""
        from railway.core.dag.outcome import Outcome

        outcome = Outcome.success("done")

        assert outcome.to_state_string("fetch_alert") == "fetch_alert::success::done"

    def test_outcome_is_immutable(self):
        """Outcome should be immutable."""
        from railway.core.dag.outcome import Outcome

        outcome = Outcome.success("done")

        with pytest.raises(AttributeError):
            outcome.detail = "modified"

    def test_outcome_equality(self):
        """Outcomes with same values should be equal."""
        from railway.core.dag.outcome import Outcome

        o1 = Outcome.success("done")
        o2 = Outcome.success("done")
        o3 = Outcome.failure("done")

        assert o1 == o2
        assert o1 != o3


class TestOutcomeMapping:
    """Test Outcome to State Enum mapping (internal use only).

    Note: map_to_state() is used internally by code generation validation.
          Users do not need to call this directly.
    """

    def test_map_outcome_to_state_enum(self):
        """Should map Outcome to State Enum value (internal)."""
        from railway.core.dag.outcome import Outcome, map_to_state
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            FETCH_SUCCESS_DONE = "fetch::success::done"
            FETCH_FAILURE_HTTP = "fetch::failure::http"

        outcome = Outcome.success("done")
        state = map_to_state(outcome, "fetch", MyState)

        assert state == MyState.FETCH_SUCCESS_DONE

    def test_map_failure_outcome(self):
        """Should map failure Outcome to State Enum (internal)."""
        from railway.core.dag.outcome import Outcome, map_to_state
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            FETCH_SUCCESS_DONE = "fetch::success::done"
            FETCH_FAILURE_HTTP = "fetch::failure::http"

        outcome = Outcome.failure("http")
        state = map_to_state(outcome, "fetch", MyState)

        assert state == MyState.FETCH_FAILURE_HTTP

    def test_map_unknown_outcome_raises(self):
        """Should raise error for unknown outcome (internal)."""
        from railway.core.dag.outcome import Outcome, map_to_state, OutcomeMappingError
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            FETCH_SUCCESS_DONE = "fetch::success::done"

        outcome = Outcome.failure("unknown")

        with pytest.raises(OutcomeMappingError):
            map_to_state(outcome, "fetch", MyState)


class TestNodeDecorator:
    """Test @node decorator (simple, no state_enum needed)."""

    def test_node_decorator_passes_outcome_through(self):
        """@node should pass Outcome through unchanged (dag_runner handles conversion)."""
        from railway import Contract
        from railway.core.decorators import node
        from railway.core.dag.outcome import Outcome

        class TestContext(Contract):
            value: int

        @node  # シンプル！state_enum 不要
        def process(ctx: TestContext) -> tuple[TestContext, Outcome]:
            return ctx, Outcome.success("done")

        result_ctx, result_outcome = process(TestContext(value=1))

        # @node は Outcome をそのまま返す（変換は dag_runner が行う）
        assert isinstance(result_outcome, Outcome)
        assert result_outcome.is_success
        assert result_outcome.detail == "done"

    def test_node_decorator_preserves_function_name(self):
        """@node should preserve function name for dag_runner state resolution."""
        from railway import Contract
        from railway.core.decorators import node
        from railway.core.dag.outcome import Outcome

        class Ctx(Contract):
            value: int

        @node
        def my_custom_node(ctx: Ctx) -> tuple[Ctx, Outcome]:
            return ctx, Outcome.success("ok")

        # 関数名が保持されていることを確認（dag_runner が状態文字列生成に使用）
        assert my_custom_node.__name__ == "my_custom_node"

    def test_node_decorator_preserves_context_type(self):
        """@node should preserve Contract type in return."""
        from railway import Contract
        from railway.core.decorators import node
        from railway.core.dag.outcome import Outcome

        class InputCtx(Contract):
            input_value: str

        class OutputCtx(Contract):
            output_value: str

        @node
        def transform(ctx: InputCtx) -> tuple[OutputCtx, Outcome]:
            return OutputCtx(output_value=ctx.input_value.upper()), Outcome.success("done")

        result_ctx, result_outcome = transform(InputCtx(input_value="hello"))

        assert isinstance(result_ctx, OutputCtx)
        assert result_ctx.output_value == "HELLO"
        assert isinstance(result_outcome, Outcome)

    def test_node_decorator_failure_outcome(self):
        """@node should handle failure outcomes."""
        from railway import Contract
        from railway.core.decorators import node
        from railway.core.dag.outcome import Outcome

        class Ctx(Contract):
            value: int

        @node
        def may_fail(ctx: Ctx) -> tuple[Ctx, Outcome]:
            if ctx.value < 0:
                return ctx, Outcome.failure("negative")
            return ctx, Outcome.success("done")

        _, failure_outcome = may_fail(Ctx(value=-1))
        assert failure_outcome.is_failure
        assert failure_outcome.detail == "negative"

        _, success_outcome = may_fail(Ctx(value=1))
        assert success_outcome.is_success


class TestOutcomeWithDagRunner:
    """Integration test: Outcome with dag_runner."""

    def test_dag_runner_with_outcome_nodes(self):
        """dag_runner should work with Outcome-returning nodes (string keys)."""
        from railway import Contract
        from railway.core.decorators import node
        from railway.core.dag.outcome import Outcome
        from railway.core.dag.runner import dag_runner, Exit

        class Ctx(Contract):
            value: int

        @node  # シンプル！state_enum 不要
        def start() -> tuple[Ctx, Outcome]:
            return Ctx(value=1), Outcome.success("done")

        @node
        def process(ctx: Ctx) -> tuple[Ctx, Outcome]:
            return Ctx(value=ctx.value + 1), Outcome.success("complete")

        # 遷移テーブルは文字列キーのみ（シンプル！）
        transitions = {
            "start::success::done": process,
            "process::success::complete": Exit.GREEN,
        }

        result = dag_runner(start=start, transitions=transitions)

        assert result.is_success
        assert result.context.value == 2

    def test_dag_runner_with_failure_path(self):
        """dag_runner should handle failure outcomes."""
        from railway import Contract
        from railway.core.decorators import node
        from railway.core.dag.outcome import Outcome
        from railway.core.dag.runner import dag_runner, Exit

        class Ctx(Contract):
            should_fail: bool

        @node
        def check(ctx: Ctx) -> tuple[Ctx, Outcome]:
            if ctx.should_fail:
                return ctx, Outcome.failure("validation")
            return ctx, Outcome.success("done")

        transitions = {
            "check::success::done": Exit.GREEN,
            "check::failure::validation": Exit.RED,
        }

        # 成功パス
        success_result = dag_runner(
            start=lambda: check(Ctx(should_fail=False)),
            transitions=transitions,
        )
        assert success_result.is_success

        # 失敗パス
        failure_result = dag_runner(
            start=lambda: check(Ctx(should_fail=True)),
            transitions=transitions,
        )
        assert not failure_result.is_success
```

```bash
pytest tests/unit/core/dag/test_outcome.py -v
# Expected: FAILED (ImportError)
```

### Step 2: Green（最小限の実装）

```python
# railway/core/dag/outcome.py
"""
Outcome class for simplified node return values.

Provides a clean API for expressing success/failure outcomes
without directly referencing the generated State Enum.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from railway.core.dag.state import NodeOutcome


class OutcomeMappingError(Exception):
    """Raised when Outcome cannot be mapped to State Enum."""
    pass


@dataclass(frozen=True, slots=True)
class Outcome:
    """
    Represents the outcome of a node execution.

    Use Outcome.success() or Outcome.failure() to create instances.
    The @node decorator will map these to the appropriate State Enum.

    Example:
        @node(state_enum=MyState)
        def fetch_data() -> tuple[Context, Outcome]:
            if data_found:
                return ctx, Outcome.success("found")
            else:
                return ctx, Outcome.failure("not_found")
    """

    outcome_type: str  # "success" or "failure"
    detail: str

    @classmethod
    def success(cls, detail: str = "done") -> Outcome:
        """Create a success outcome.

        Args:
            detail: Specific success detail (e.g., "done", "found", "cached")

        Returns:
            Outcome instance representing success
        """
        return cls(outcome_type="success", detail=detail)

    @classmethod
    def failure(cls, detail: str = "error") -> Outcome:
        """Create a failure outcome.

        Args:
            detail: Specific failure detail (e.g., "http", "timeout", "validation")

        Returns:
            Outcome instance representing failure
        """
        return cls(outcome_type="failure", detail=detail)

    @property
    def is_success(self) -> bool:
        """Check if this is a success outcome."""
        return self.outcome_type == "success"

    @property
    def is_failure(self) -> bool:
        """Check if this is a failure outcome."""
        return self.outcome_type == "failure"

    def to_state_string(self, node_name: str) -> str:
        """Convert to state string format.

        Args:
            node_name: Name of the node

        Returns:
            State string in format: {node_name}::{outcome_type}::{detail}
        """
        return f"{node_name}::{self.outcome_type}::{self.detail}"


StateEnumT = TypeVar("StateEnumT", bound="NodeOutcome")


def map_to_state(
    outcome: Outcome,
    node_name: str,
    state_enum: type[StateEnumT],
) -> StateEnumT:
    """
    Map an Outcome to a State Enum value.

    Args:
        outcome: Outcome to map
        node_name: Name of the node (used to construct state string)
        state_enum: Target State Enum class

    Returns:
        Matching State Enum value

    Raises:
        OutcomeMappingError: If no matching state found
    """
    target_value = outcome.to_state_string(node_name)

    for member in state_enum:
        if member.value == target_value:
            return member

    available = [m.value for m in state_enum]
    raise OutcomeMappingError(
        f"Outcomeに対応する状態が見つかりません: '{target_value}'\n"
        f"利用可能な状態: {available}"
    )


def is_outcome(value: object) -> bool:
    """Check if value is an Outcome instance."""
    return isinstance(value, Outcome)
```

```python
# railway/core/decorators.py への追加
# @node デコレータをシンプルに（state_enum 不要）

from functools import wraps
from typing import Callable, TypeVar, ParamSpec


P = ParamSpec("P")
R = TypeVar("R")


def node(func: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator for DAG node functions.

    Simply marks a function as a node and preserves metadata.
    Outcome to state string conversion is handled by dag_runner.

    Usage:
        @node
        def my_node(ctx: InputCtx) -> tuple[OutputCtx, Outcome]:
            return OutputCtx(...), Outcome.success("done")

        # dag_runner が自動的に "my_node::success::done" を生成
    """
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return func(*args, **kwargs)

    # Store node name for dag_runner state resolution
    wrapper._node_name = func.__name__
    wrapper._is_railway_node = True

    return wrapper
```

**Note:** `state_enum` パラメータは削除しました。状態文字列の生成は `dag_runner` が担当します。

```bash
pytest tests/unit/core/dag/test_outcome.py -v
# Expected: PASSED
```

### Step 3: Refactor

- エラーメッセージの改善
- 型ヒントの強化（Generic対応）
- パフォーマンス最適化（キャッシュ）

---

## 完了条件

- [ ] `Outcome` クラスが `success`/`failure` ファクトリメソッドを持つ
- [ ] `Outcome` がイミュータブル（`frozen=True`）
- [ ] `Outcome.to_state_string(node_name)` が状態文字列を生成
- [ ] `@node` がノード名を保持（`_node_name` 属性）
- [ ] `dag_runner` が Outcome から状態文字列を自動生成
- [ ] `dag_runner` との統合テストが通過
- [ ] テストカバレッジ90%以上

---

## dict 非対応について

**重要:** このIssueでは dict コンテキストは非対応とする。

コンテキストは `Contract` のみをサポート：

```python
# ✅ 唯一のサポート形式（シンプル！）
@node
def my_node(ctx: MyContract) -> tuple[MyContract, Outcome]:
    return MyContract(...), Outcome.success("done")

# ❌ 非対応（dict は使用不可）
@node
def my_node(ctx: dict) -> tuple[dict, Outcome]:  # 型エラー
    ...
```

---

## API エクスポート

```python
# railway/__init__.py への追加
from railway.core.dag.outcome import Outcome
from railway.core.dag.runner import Exit

__all__ = [
    # ... existing exports
    "Outcome",
    "Exit",
]
```

これにより、ユーザーは以下のようにシンプルにインポートできます：

```python
from railway import node, Outcome, Exit

@node
def my_node(ctx: MyContract) -> tuple[MyContract, Outcome]:
    return MyContract(...), Outcome.success("done")

transitions = {
    "my_node::success::done": Exit.GREEN,
}
```

---

## 次のIssue

- #10: DAGランナー実装（本Issueに依存、Outcome.to_state_string() を使用）

---

## 関連ドキュメント

- 設計分析: `.claude_output/design_analysis_20250125.md`
- Issue #10: DAGランナー実装
- Issue #07: 状態Enum基底クラス
