# Issue #10: DAGランナー実装

**Phase:** 2c
**優先度:** 高
**依存関係:** #04, #07
**見積もり:** 1.5日

---

## 概要

生成された遷移テーブルを使用してDAGワークフローを実行するランナーを実装する。
ノードは状態を返し、ランナーが遷移先を決定する。

---

## 設計原則

### ノードはステートレス

```python
# ノードは (結果, 状態) のタプルを返す
@node
def fetch_alert(incident_id: str) -> tuple[WorkflowContext, Top2State]:
    ctx = WorkflowContext(incident_id=incident_id)
    return ctx, Top2State.FETCH_ALERT_SUCCESS_DONE
```

### ランナーが遷移を制御

```python
# ランナーは遷移テーブルを参照して次のステップを決定
result = dag_runner(
    start=lambda: fetch_alert(incident_id),
    transitions=TRANSITION_TABLE,
    max_iterations=20,
)
```

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/core/dag/test_runner.py
"""Tests for DAG runner."""
import pytest
from enum import Enum
from typing import Callable, Any


class TestDagRunner:
    """Test dag_runner function."""

    def test_simple_workflow(self):
        """Should execute a simple linear workflow."""
        from railway.core.dag.runner import dag_runner
        from railway.core.dag.state import NodeOutcome, ExitOutcome

        # Define states
        class State(NodeOutcome):
            A_SUCCESS = "a::success::done"
            B_SUCCESS = "b::success::done"

        class Exit(ExitOutcome):
            DONE = "exit::green::done"

        # Define context
        context = {"value": 0}

        # Define nodes
        def node_a() -> tuple[dict, State]:
            context["value"] = 1
            return context, State.A_SUCCESS

        def node_b(ctx: dict) -> tuple[dict, State]:
            ctx["value"] = 2
            return ctx, State.B_SUCCESS

        # Define transitions
        transitions = {
            State.A_SUCCESS: node_b,
            State.B_SUCCESS: Exit.DONE,
        }

        result = dag_runner(
            start=node_a,
            transitions=transitions,
        )

        assert result.exit_code == Exit.DONE
        assert result.context["value"] == 2
        assert result.iterations == 2

    def test_branching_workflow(self):
        """Should handle conditional branching."""
        from railway.core.dag.runner import dag_runner
        from railway.core.dag.state import NodeOutcome, ExitOutcome

        class State(NodeOutcome):
            CHECK_TRUE = "check::success::true"
            CHECK_FALSE = "check::success::false"
            PATH_A = "path_a::success::done"
            PATH_B = "path_b::success::done"

        class Exit(ExitOutcome):
            DONE_A = "exit::green::done_a"
            DONE_B = "exit::green::done_b"

        call_log = []

        def check(condition: bool) -> tuple[dict, State]:
            call_log.append("check")
            if condition:
                return {"path": "a"}, State.CHECK_TRUE
            else:
                return {"path": "b"}, State.CHECK_FALSE

        def path_a(ctx: dict) -> tuple[dict, State]:
            call_log.append("path_a")
            return ctx, State.PATH_A

        def path_b(ctx: dict) -> tuple[dict, State]:
            call_log.append("path_b")
            return ctx, State.PATH_B

        transitions = {
            State.CHECK_TRUE: path_a,
            State.CHECK_FALSE: path_b,
            State.PATH_A: Exit.DONE_A,
            State.PATH_B: Exit.DONE_B,
        }

        # Test true branch
        result = dag_runner(
            start=lambda: check(True),
            transitions=transitions,
        )

        assert result.exit_code == Exit.DONE_A
        assert call_log == ["check", "path_a"]

    def test_max_iterations_limit(self):
        """Should stop when max iterations reached."""
        from railway.core.dag.runner import dag_runner, MaxIterationsError
        from railway.core.dag.state import NodeOutcome

        class State(NodeOutcome):
            LOOP = "loop::success::continue"

        def loop_node(ctx: dict) -> tuple[dict, State]:
            ctx["count"] = ctx.get("count", 0) + 1
            return ctx, State.LOOP

        # Infinite loop
        transitions = {
            State.LOOP: loop_node,
        }

        with pytest.raises(MaxIterationsError):
            dag_runner(
                start=lambda: loop_node({}),
                transitions=transitions,
                max_iterations=5,
            )

    def test_undefined_state_error(self):
        """Should error on undefined state."""
        from railway.core.dag.runner import dag_runner, UndefinedStateError
        from railway.core.dag.state import NodeOutcome

        class State(NodeOutcome):
            KNOWN = "node::success::known"
            UNKNOWN = "node::failure::unknown"

        def node() -> tuple[dict, State]:
            return {}, State.UNKNOWN  # Not in transitions

        transitions = {
            State.KNOWN: lambda x: x,
            # UNKNOWN not defined
        }

        with pytest.raises(UndefinedStateError):
            dag_runner(
                start=node,
                transitions=transitions,
                strict=True,
            )

    def test_passes_context_between_nodes(self):
        """Should pass context from one node to the next."""
        from railway.core.dag.runner import dag_runner
        from railway.core.dag.state import NodeOutcome, ExitOutcome

        class State(NodeOutcome):
            A = "a::success::done"
            B = "b::success::done"

        class Exit(ExitOutcome):
            DONE = "exit::green::done"

        def node_a() -> tuple[dict, State]:
            return {"from_a": True}, State.A

        def node_b(ctx: dict) -> tuple[dict, State]:
            assert ctx["from_a"] is True
            ctx["from_b"] = True
            return ctx, State.B

        transitions = {
            State.A: node_b,
            State.B: Exit.DONE,
        }

        result = dag_runner(start=node_a, transitions=transitions)

        assert result.context["from_a"] is True
        assert result.context["from_b"] is True


class TestDagRunnerResult:
    """Test DagRunnerResult data type."""

    def test_result_properties(self):
        """Should have expected properties."""
        from railway.core.dag.runner import DagRunnerResult
        from railway.core.dag.state import ExitOutcome

        class Exit(ExitOutcome):
            DONE = "exit::green::done"

        result = DagRunnerResult(
            exit_code=Exit.DONE,
            context={"key": "value"},
            iterations=3,
            execution_path=["node_a", "node_b", "node_c"],
        )

        assert result.exit_code == Exit.DONE
        assert result.context["key"] == "value"
        assert result.iterations == 3
        assert len(result.execution_path) == 3

    def test_result_is_success(self):
        """Should determine success based on exit code."""
        from railway.core.dag.runner import DagRunnerResult
        from railway.core.dag.state import ExitOutcome

        class Exit(ExitOutcome):
            GREEN = "exit::green::done"
            RED = "exit::red::error"

        success_result = DagRunnerResult(
            exit_code=Exit.GREEN,
            context={},
            iterations=1,
            execution_path=[],
        )
        assert success_result.is_success is True

        failure_result = DagRunnerResult(
            exit_code=Exit.RED,
            context={},
            iterations=1,
            execution_path=[],
        )
        assert failure_result.is_success is False


class TestDagRunnerAsync:
    """Test async dag_runner."""

    @pytest.mark.asyncio
    async def test_async_workflow(self):
        """Should execute async nodes."""
        from railway.core.dag.runner import async_dag_runner
        from railway.core.dag.state import NodeOutcome, ExitOutcome

        class State(NodeOutcome):
            A = "a::success::done"

        class Exit(ExitOutcome):
            DONE = "exit::green::done"

        async def async_node() -> tuple[dict, State]:
            return {"async": True}, State.A

        transitions = {
            State.A: Exit.DONE,
        }

        result = await async_dag_runner(
            start=async_node,
            transitions=transitions,
        )

        assert result.is_success
        assert result.context["async"] is True
```

```bash
pytest tests/unit/core/dag/test_runner.py -v
# Expected: FAILED (ImportError)
```

### Step 2: Green（最小限の実装）

```python
# railway/core/dag/runner.py
"""
DAG workflow runner.

Executes workflows defined by transition tables,
routing between nodes based on their returned states.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, TypeVar, Generic

from loguru import logger

from railway.core.dag.state import NodeOutcome, ExitOutcome


class MaxIterationsError(Exception):
    """Raised when max iterations limit is reached."""
    pass


class UndefinedStateError(Exception):
    """Raised when a node returns an undefined state."""
    pass


@dataclass(frozen=True)
class DagRunnerResult:
    """
    Result of DAG workflow execution.

    Attributes:
        exit_code: The exit outcome that terminated the workflow
        context: Final context from the last node
        iterations: Number of nodes executed
        execution_path: List of node names in execution order
    """
    exit_code: ExitOutcome
    context: Any
    iterations: int
    execution_path: tuple[str, ...]

    @property
    def is_success(self) -> bool:
        """Check if the workflow completed successfully."""
        return self.exit_code.is_success


def dag_runner(
    start: Callable[[], tuple[Any, NodeOutcome]],
    transitions: dict[NodeOutcome, Callable | ExitOutcome],
    max_iterations: int = 100,
    strict: bool = True,
    on_step: Callable[[str, NodeOutcome, Any], None] | None = None,
) -> DagRunnerResult:
    """
    Execute a DAG workflow.

    The runner executes nodes in sequence, using the transition table
    to determine the next node based on each node's returned state.

    Args:
        start: Initial node function (returns (context, state))
        transitions: Mapping of states to next nodes or exits
        max_iterations: Maximum number of node executions
        strict: Raise error on undefined states
        on_step: Optional callback for each step (node_name, state, context)

    Returns:
        DagRunnerResult with exit code and final context

    Raises:
        MaxIterationsError: If max iterations exceeded
        UndefinedStateError: If strict and undefined state encountered
    """
    logger.debug(f"DAGワークフロー開始: max_iterations={max_iterations}")

    execution_path: list[str] = []
    iteration = 0

    # Execute start node
    context, state = start()
    node_name = state.node_name
    execution_path.append(node_name)
    iteration += 1

    logger.debug(f"[{iteration}] {node_name} -> {state}")

    if on_step:
        on_step(node_name, state, context)

    # Execution loop
    while iteration < max_iterations:
        # Look up next step
        next_step = transitions.get(state)

        if next_step is None:
            if strict:
                raise UndefinedStateError(
                    f"未定義の状態です: {state} "
                    f"(ノード: {node_name})"
                )
            else:
                logger.warning(f"未定義の状態: {state}")
                break

        # Check if it's an exit
        if isinstance(next_step, ExitOutcome):
            logger.debug(f"DAGワークフロー終了: {next_step}")
            return DagRunnerResult(
                exit_code=next_step,
                context=context,
                iterations=iteration,
                execution_path=tuple(execution_path),
            )

        # Execute next node
        iteration += 1
        context, state = next_step(context)
        node_name = state.node_name
        execution_path.append(node_name)

        logger.debug(f"[{iteration}] {node_name} -> {state}")

        if on_step:
            on_step(node_name, state, context)

    # Max iterations reached
    raise MaxIterationsError(
        f"最大イテレーション数 ({max_iterations}) に達しました。"
        f"実行パス: {' -> '.join(execution_path[-10:])}"
    )


async def async_dag_runner(
    start: Callable[[], tuple[Any, NodeOutcome]],
    transitions: dict[NodeOutcome, Callable | ExitOutcome],
    max_iterations: int = 100,
    strict: bool = True,
    on_step: Callable[[str, NodeOutcome, Any], None] | None = None,
) -> DagRunnerResult:
    """
    Execute a DAG workflow with async support.

    Same as dag_runner but awaits async nodes.
    """
    import asyncio
    import inspect

    logger.debug(f"非同期DAGワークフロー開始: max_iterations={max_iterations}")

    execution_path: list[str] = []
    iteration = 0

    # Execute start node
    if asyncio.iscoroutinefunction(start):
        context, state = await start()
    else:
        context, state = start()

    node_name = state.node_name
    execution_path.append(node_name)
    iteration += 1

    if on_step:
        on_step(node_name, state, context)

    # Execution loop
    while iteration < max_iterations:
        next_step = transitions.get(state)

        if next_step is None:
            if strict:
                raise UndefinedStateError(f"未定義の状態です: {state}")
            break

        if isinstance(next_step, ExitOutcome):
            return DagRunnerResult(
                exit_code=next_step,
                context=context,
                iterations=iteration,
                execution_path=tuple(execution_path),
            )

        iteration += 1

        if asyncio.iscoroutinefunction(next_step):
            context, state = await next_step(context)
        else:
            context, state = next_step(context)

        node_name = state.node_name
        execution_path.append(node_name)

        if on_step:
            on_step(node_name, state, context)

    raise MaxIterationsError(f"最大イテレーション数 ({max_iterations}) に達しました")
```

```bash
pytest tests/unit/core/dag/test_runner.py -v
# Expected: PASSED
```

### Step 3: Refactor

- 実行トレース機能の強化
- メトリクス収集の追加
- コンテキストのイミュータブル化オプション

---

## 完了条件

- [ ] `dag_runner()` が線形ワークフローを実行
- [ ] 条件分岐が正しく動作
- [ ] `max_iterations` で無限ループを防止
- [ ] 未定義状態でエラー（strictモード）
- [ ] コンテキストがノード間で渡される
- [ ] `DagRunnerResult` が実行結果を保持
- [ ] `async_dag_runner()` が非同期ノードをサポート
- [ ] `on_step` コールバックが動作
- [ ] テストカバレッジ90%以上

---

## 次のIssue

- #11: ステップコールバック
