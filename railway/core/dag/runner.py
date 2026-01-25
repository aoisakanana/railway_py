"""
DAG workflow runner.

Executes workflows defined by transition tables,
routing between nodes based on their returned states.

Note: This runner ONLY supports Contract context and string keys.
      dict context is NOT supported.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable

from loguru import logger

from railway.core.dag.outcome import Outcome


class Exit:
    """
    終了コード定数。

    遷移テーブルの値として使用します。

    Example:
        transitions = {
            "node::success::done": Exit.GREEN,
            "node::failure::error": Exit.RED,
        }
    """

    GREEN = "exit::green::done"  # 正常終了（成功）
    YELLOW = "exit::yellow::warning"  # 警告終了（成功扱い）
    RED = "exit::red::error"  # 異常終了（失敗）

    @staticmethod
    def code(color: str, detail: str = "done") -> str:
        """カスタム終了コードを生成。

        Args:
            color: 終了コードの色（green, yellow, red など）
            detail: 詳細情報（デフォルト: "done"）

        Returns:
            終了コード文字列（例: "exit::green::done"）
        """
        return f"exit::{color}::{detail}"


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
        exit_code: The exit code string (e.g., "exit::green::done")
        context: Final context from the last node (Contract only)
        iterations: Number of nodes executed
        execution_path: Tuple of node names in execution order
    """

    exit_code: str
    context: Any  # Contract type
    iterations: int
    execution_path: tuple[str, ...]

    @property
    def is_success(self) -> bool:
        """Check if the workflow completed successfully (green or yellow)."""
        return "::green::" in self.exit_code or "::yellow::" in self.exit_code


def _get_node_name(func: Callable) -> str:
    """Get node name from function.

    Supports:
    - Functions with @node decorator (has _node_name attribute)
    - Regular functions (uses __name__)
    - Lambda functions with __name__ = "<lambda>"

    Args:
        func: The function to get the name from

    Returns:
        The node name string
    """
    # Check for @node decorator metadata
    if hasattr(func, "_node_name"):
        return func._node_name

    # For wrapped functions, try to get original name
    if hasattr(func, "__wrapped__"):
        return _get_node_name(func.__wrapped__)

    return getattr(func, "__name__", "unknown")


def dag_runner(
    start: Callable[[], tuple[Any, Outcome]],
    transitions: dict[str, Callable | str],
    max_iterations: int = 100,
    strict: bool = True,
    on_step: Callable[[str, str, Any], None] | None = None,
) -> DagRunnerResult:
    """
    Execute a DAG workflow.

    The runner executes nodes in sequence, using the transition table
    to determine the next node based on each node's returned state.

    Nodes return Outcome, and the runner generates state strings automatically:
    - Outcome.success("done") → "node_name::success::done"
    - Outcome.failure("error") → "node_name::failure::error"

    Args:
        start: Initial node function (returns (context, Outcome))
        transitions: Mapping of state strings to next nodes or exit codes
        max_iterations: Maximum number of node executions
        strict: Raise error on undefined states
        on_step: Optional callback for each step (node_name, state_string, context)

    Returns:
        DagRunnerResult with exit code and final context

    Raises:
        MaxIterationsError: If max iterations exceeded
        UndefinedStateError: If strict and undefined state encountered

    Example:
        transitions = {
            "fetch::success::done": process,
            "fetch::failure::http": Exit.RED,
            "process::success::done": Exit.GREEN,
        }
        result = dag_runner(start=fetch, transitions=transitions)
    """
    logger.debug(f"DAGワークフロー開始: max_iterations={max_iterations}")

    execution_path: list[str] = []
    iteration = 0

    # Execute start node
    context, outcome = start()
    node_name = _get_node_name(start)
    state_string = outcome.to_state_string(node_name)

    execution_path.append(node_name)
    iteration += 1

    logger.debug(f"[{iteration}] {node_name} -> {state_string}")

    if on_step:
        on_step(node_name, state_string, context)

    # Execution loop
    while iteration < max_iterations:
        # Look up next step
        next_step = transitions.get(state_string)

        if next_step is None:
            if strict:
                raise UndefinedStateError(
                    f"未定義の状態です: {state_string} (ノード: {node_name})"
                )
            else:
                logger.warning(f"未定義の状態: {state_string}")
                # Return result with current state (no exit code)
                return DagRunnerResult(
                    exit_code="",
                    context=context,
                    iterations=iteration,
                    execution_path=tuple(execution_path),
                )

        # Check if it's an exit (string starting with "exit::")
        if isinstance(next_step, str) and next_step.startswith("exit::"):
            logger.debug(f"DAGワークフロー終了: {next_step}")
            return DagRunnerResult(
                exit_code=next_step,
                context=context,
                iterations=iteration,
                execution_path=tuple(execution_path),
            )

        # Execute next node
        iteration += 1
        context, outcome = next_step(context)
        node_name = _get_node_name(next_step)
        state_string = outcome.to_state_string(node_name)

        execution_path.append(node_name)

        logger.debug(f"[{iteration}] {node_name} -> {state_string}")

        if on_step:
            on_step(node_name, state_string, context)

    # Max iterations reached
    raise MaxIterationsError(
        f"最大イテレーション数 ({max_iterations}) に達しました。"
        f"実行パス: {' -> '.join(execution_path[-10:])}"
    )


async def async_dag_runner(
    start: Callable[[], tuple[Any, Outcome]],
    transitions: dict[str, Callable | str],
    max_iterations: int = 100,
    strict: bool = True,
    on_step: Callable[[str, str, Any], None] | None = None,
) -> DagRunnerResult:
    """
    Execute a DAG workflow with async support.

    Same as dag_runner but awaits async nodes.

    Args:
        start: Initial node function (sync or async)
        transitions: Mapping of state strings to next nodes or exit codes
        max_iterations: Maximum number of node executions
        strict: Raise error on undefined states
        on_step: Optional callback for each step

    Returns:
        DagRunnerResult with exit code and final context

    Raises:
        MaxIterationsError: If max iterations exceeded
        UndefinedStateError: If strict and undefined state encountered
    """
    logger.debug(f"非同期DAGワークフロー開始: max_iterations={max_iterations}")

    execution_path: list[str] = []
    iteration = 0

    # Execute start node
    if asyncio.iscoroutinefunction(start):
        context, outcome = await start()
    else:
        context, outcome = start()

    node_name = _get_node_name(start)
    state_string = outcome.to_state_string(node_name)
    execution_path.append(node_name)
    iteration += 1

    if on_step:
        on_step(node_name, state_string, context)

    # Execution loop
    while iteration < max_iterations:
        next_step = transitions.get(state_string)

        if next_step is None:
            if strict:
                raise UndefinedStateError(f"未定義の状態です: {state_string}")
            return DagRunnerResult(
                exit_code="",
                context=context,
                iterations=iteration,
                execution_path=tuple(execution_path),
            )

        # Check if it's an exit
        if isinstance(next_step, str) and next_step.startswith("exit::"):
            return DagRunnerResult(
                exit_code=next_step,
                context=context,
                iterations=iteration,
                execution_path=tuple(execution_path),
            )

        iteration += 1

        if asyncio.iscoroutinefunction(next_step):
            context, outcome = await next_step(context)
        else:
            context, outcome = next_step(context)

        node_name = _get_node_name(next_step)
        state_string = outcome.to_state_string(node_name)
        execution_path.append(node_name)

        if on_step:
            on_step(node_name, state_string, context)

    raise MaxIterationsError(f"最大イテレーション数 ({max_iterations}) に達しました")
