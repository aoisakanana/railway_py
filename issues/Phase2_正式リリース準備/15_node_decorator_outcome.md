# Issue #15: @node デコレータ自動マッピング & Outcome クラス

**Phase:** 2c
**優先度:** 高
**依存関係:** #07, #10
**見積もり:** 1日

---

## 概要

ノード関数の戻り値を簡潔かつ型安全に記述するため、以下を実装する：

1. **Outcome クラス** - `success`/`failure` を表現する軽量な型
2. **@node デコレータ拡張** - Outcome から State Enum への自動マッピング

これにより、冗長な State Enum 値の記述が不要になり、ノード実装がシンプルになる。

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
- ノード名が Enum 値に含まれるため DRY 原則違反
- import が増える

### After（理想の実装）

```python
from railway import node, Outcome

@node(state_enum=MyWorkflowState)  # オプション: 省略時は自動推論
def fetch_alert(ctx: InputContext) -> tuple[OutputContext, Outcome]:
    if success:
        return OutputContext(...), Outcome.success("done")
    else:
        return OutputContext(...), Outcome.failure("http")
```

**改善点:**
- `Outcome.success("done")` → 自動的に `MyWorkflowState.FETCH_ALERT_SUCCESS_DONE` に変換
- ノード名は関数名から自動取得
- 型安全性は維持

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
    """Test Outcome to State Enum mapping."""

    def test_map_outcome_to_state_enum(self):
        """Should map Outcome to State Enum value."""
        from railway.core.dag.outcome import Outcome, map_to_state
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            FETCH_SUCCESS_DONE = "fetch::success::done"
            FETCH_FAILURE_HTTP = "fetch::failure::http"

        outcome = Outcome.success("done")
        state = map_to_state(outcome, "fetch", MyState)

        assert state == MyState.FETCH_SUCCESS_DONE

    def test_map_failure_outcome(self):
        """Should map failure Outcome to State Enum."""
        from railway.core.dag.outcome import Outcome, map_to_state
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            FETCH_SUCCESS_DONE = "fetch::success::done"
            FETCH_FAILURE_HTTP = "fetch::failure::http"

        outcome = Outcome.failure("http")
        state = map_to_state(outcome, "fetch", MyState)

        assert state == MyState.FETCH_FAILURE_HTTP

    def test_map_unknown_outcome_raises(self):
        """Should raise error for unknown outcome."""
        from railway.core.dag.outcome import Outcome, map_to_state, OutcomeMappingError
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            FETCH_SUCCESS_DONE = "fetch::success::done"

        outcome = Outcome.failure("unknown")

        with pytest.raises(OutcomeMappingError):
            map_to_state(outcome, "fetch", MyState)


class TestNodeDecoratorWithStateEnum:
    """Test @node decorator with state_enum parameter."""

    def test_node_decorator_maps_outcome(self):
        """@node should automatically map Outcome to State Enum."""
        from railway import Contract
        from railway.core.decorators import node
        from railway.core.dag.outcome import Outcome
        from railway.core.dag.state import NodeOutcome

        class TestContext(Contract):
            value: int

        class TestState(NodeOutcome):
            PROCESS_SUCCESS_DONE = "process::success::done"

        @node(state_enum=TestState)
        def process(ctx: TestContext) -> tuple[TestContext, Outcome]:
            return ctx, Outcome.success("done")

        # Execute the decorated function
        result_ctx, result_state = process(TestContext(value=1))

        assert isinstance(result_state, TestState)
        assert result_state == TestState.PROCESS_SUCCESS_DONE

    def test_node_decorator_infers_node_name(self):
        """@node should infer node name from function name."""
        from railway import Contract
        from railway.core.decorators import node
        from railway.core.dag.outcome import Outcome
        from railway.core.dag.state import NodeOutcome

        class Ctx(Contract):
            value: int

        class State(NodeOutcome):
            MY_CUSTOM_NODE_SUCCESS_OK = "my_custom_node::success::ok"

        @node(state_enum=State)
        def my_custom_node(ctx: Ctx) -> tuple[Ctx, Outcome]:
            return ctx, Outcome.success("ok")

        _, state = my_custom_node(Ctx(value=1))
        assert state == State.MY_CUSTOM_NODE_SUCCESS_OK

    def test_node_decorator_preserves_context_type(self):
        """@node should preserve Contract type in return."""
        from railway import Contract
        from railway.core.decorators import node
        from railway.core.dag.outcome import Outcome
        from railway.core.dag.state import NodeOutcome

        class InputCtx(Contract):
            input_value: str

        class OutputCtx(Contract):
            output_value: str

        class State(NodeOutcome):
            TRANSFORM_SUCCESS_DONE = "transform::success::done"

        @node(state_enum=State)
        def transform(ctx: InputCtx) -> tuple[OutputCtx, Outcome]:
            return OutputCtx(output_value=ctx.input_value.upper()), Outcome.success("done")

        result_ctx, _ = transform(InputCtx(input_value="hello"))

        assert isinstance(result_ctx, OutputCtx)
        assert result_ctx.output_value == "HELLO"

    def test_node_decorator_without_state_enum(self):
        """@node without state_enum should pass Outcome through unchanged."""
        from railway import Contract
        from railway.core.decorators import node
        from railway.core.dag.outcome import Outcome

        class Ctx(Contract):
            value: int

        @node  # No state_enum
        def simple(ctx: Ctx) -> tuple[Ctx, Outcome]:
            return ctx, Outcome.success("done")

        result_ctx, result_outcome = simple(Ctx(value=1))

        assert isinstance(result_outcome, Outcome)
        assert result_outcome.is_success


class TestNodeDecoratorWithExistingStateEnum:
    """Test @node decorator when returning State Enum directly."""

    def test_node_accepts_state_enum_directly(self):
        """@node should accept State Enum as return value."""
        from railway import Contract
        from railway.core.decorators import node
        from railway.core.dag.state import NodeOutcome

        class Ctx(Contract):
            value: int

        class State(NodeOutcome):
            DIRECT_SUCCESS_DONE = "direct::success::done"

        @node(state_enum=State)
        def direct(ctx: Ctx) -> tuple[Ctx, State]:
            return ctx, State.DIRECT_SUCCESS_DONE

        _, state = direct(Ctx(value=1))

        assert state == State.DIRECT_SUCCESS_DONE


class TestOutcomeWithDagRunner:
    """Integration test: Outcome with dag_runner."""

    def test_dag_runner_with_outcome_nodes(self):
        """dag_runner should work with Outcome-returning nodes."""
        from railway import Contract
        from railway.core.decorators import node
        from railway.core.dag.outcome import Outcome
        from railway.core.dag.state import NodeOutcome, ExitOutcome
        from railway.core.dag.runner import dag_runner

        class Ctx(Contract):
            value: int

        class State(NodeOutcome):
            START_SUCCESS_DONE = "start::success::done"
            PROCESS_SUCCESS_COMPLETE = "process::success::complete"

        class Exit(ExitOutcome):
            DONE = "exit::green::done"

        @node(state_enum=State)
        def start() -> tuple[Ctx, Outcome]:
            return Ctx(value=1), Outcome.success("done")

        @node(state_enum=State)
        def process(ctx: Ctx) -> tuple[Ctx, Outcome]:
            return Ctx(value=ctx.value + 1), Outcome.success("complete")

        transitions = {
            State.START_SUCCESS_DONE: process,
            State.PROCESS_SUCCESS_COMPLETE: Exit.DONE,
        }

        result = dag_runner(start=start, transitions=transitions)

        assert result.is_success
        assert result.context.value == 2
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
# 既存の @node デコレータを拡張

from functools import wraps
from typing import Any, Callable, TypeVar, ParamSpec, overload
from railway.core.dag.outcome import Outcome, map_to_state, is_outcome


P = ParamSpec("P")
R = TypeVar("R")


def node(
    func: Callable[P, R] | None = None,
    *,
    state_enum: type | None = None,
) -> Callable[P, R] | Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator for DAG node functions.

    When state_enum is provided, automatically maps Outcome to State Enum.

    Args:
        func: The function to decorate (when used without parentheses)
        state_enum: Optional State Enum class for automatic mapping

    Usage:
        # Without state mapping (pass-through)
        @node
        def my_node(ctx) -> tuple[Context, Outcome]:
            return ctx, Outcome.success("done")

        # With state mapping
        @node(state_enum=MyState)
        def my_node(ctx) -> tuple[Context, Outcome]:
            return ctx, Outcome.success("done")  # Auto-mapped to MyState
    """
    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        node_name = fn.__name__

        @wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            result = fn(*args, **kwargs)

            # If no state_enum, return as-is
            if state_enum is None:
                return result

            # Extract context and outcome from tuple
            if isinstance(result, tuple) and len(result) == 2:
                context, outcome_or_state = result

                # If already a State Enum, return as-is
                if isinstance(outcome_or_state, state_enum):
                    return result

                # If Outcome, map to State Enum
                if is_outcome(outcome_or_state):
                    mapped_state = map_to_state(
                        outcome_or_state,
                        node_name,
                        state_enum,
                    )
                    return (context, mapped_state)

            return result

        # Store metadata for introspection
        wrapper._node_name = node_name
        wrapper._state_enum = state_enum

        return wrapper

    # Handle both @node and @node(state_enum=...) syntax
    if func is not None:
        return decorator(func)
    return decorator
```

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
- [ ] `map_to_state()` が Outcome を State Enum に変換
- [ ] `@node(state_enum=...)` が自動マッピングを実行
- [ ] `@node` がノード名を関数名から推論
- [ ] State Enum を直接返す場合も動作
- [ ] `dag_runner` との統合テストが通過
- [ ] テストカバレッジ90%以上

---

## dict 非対応について

**重要:** このIssueでは dict コンテキストは非対応とする。

コンテキストは `Contract` のみをサポート：

```python
# ✅ 推奨（唯一のサポート形式）
@node(state_enum=MyState)
def my_node(ctx: MyContract) -> tuple[MyContract, Outcome]:
    return MyContract(...), Outcome.success("done")

# ❌ 非対応（dict は使用不可）
@node(state_enum=MyState)
def my_node(ctx: dict) -> tuple[dict, Outcome]:  # 型エラー
    ...
```

---

## API エクスポート

```python
# railway/__init__.py への追加
from railway.core.dag.outcome import Outcome

__all__ = [
    # ... existing exports
    "Outcome",
]
```

---

## 次のIssue

- #11: ステップコールバック（#10 完了後に着手）

---

## 関連ドキュメント

- 設計分析: `.claude_output/design_analysis_20250125.md`
- Issue #10: DAGランナー実装
- Issue #07: 状態Enum基底クラス
