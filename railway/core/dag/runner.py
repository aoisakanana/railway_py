"""
DAG workflow runner.

Executes workflows defined by transition tables,
routing between nodes based on their returned states.

Note: This runner ONLY supports Contract context and string keys.
      dict context is NOT supported.

v0.12.2: ExitContract ベースに変更
- dag_runner() は ExitContract を返す
- Exit クラス、DagRunnerResult クラスは削除
- exit_codes パラメータは削除
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable

from loguru import logger

from railway.core.dag.outcome import Outcome
from railway.core.exit_contract import DefaultExitContract, ExitContract


class MaxIterationsError(Exception):
    """Raised when max iterations limit is reached."""

    pass


class UndefinedStateError(Exception):
    """Raised when a node returns an undefined state."""

    pass


# =============================================================================
# 純粋関数: 終端ノード判定・状態導出
# =============================================================================


def _is_exit_node(node_name: str) -> bool:
    """終端ノードかどうかを判定する。

    判定条件:
    - "exit." で始まる（新形式: exit.success.done）
    - "_exit_" で始まる（codegen 生成形式: _exit_success_done）

    Args:
        node_name: ノード名

    Returns:
        終端ノードなら True
    """
    return node_name.startswith("exit.") or node_name.startswith("_exit_")


def _derive_exit_state(node_name: str) -> str:
    """終端ノード名から exit_state を導出する。

    変換ルール:
    - "exit.success.done" → "success.done"
    - "_exit_failure_timeout" → "failure.timeout"

    Args:
        node_name: 終端ノード名

    Returns:
        exit_state 文字列
    """
    # "exit." プレフィックスを除去
    if node_name.startswith("exit."):
        return node_name[5:]
    # "_exit_" プレフィックスを除去し、"_" を "." に変換
    if node_name.startswith("_exit_"):
        return node_name[6:].replace("_", ".")
    return node_name


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
) -> ExitContract:
    """Execute a DAG workflow.

    The runner executes nodes in sequence, using the transition table
    to determine the next node based on each node's returned state.

    Nodes return Outcome, and the runner generates state strings automatically:
    - Outcome.success("done") → "node_name::success::done"
    - Outcome.failure("error") → "node_name::failure::error"

    Args:
        start: Initial node function (returns (context, Outcome))
        transitions: Mapping of state strings to next nodes
        max_iterations: Maximum number of node executions
        strict: Raise error on undefined states
        on_step: Optional callback for each step (node_name, state_string, context)

    Returns:
        ExitContract from the exit node

    Raises:
        MaxIterationsError: If max iterations exceeded
        UndefinedStateError: If strict and undefined state encountered

    Example:
        transitions = {
            "fetch::success::done": process,
            "process::success::done": exit_done,
        }
        result = dag_runner(start=fetch, transitions=transitions)
        print(result.is_success)  # True/False
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
                # Return DefaultExitContract with failure state
                return DefaultExitContract(
                    exit_state="failure.undefined",
                    context=context,
                    execution_path=tuple(execution_path),
                    iterations=iteration,
                )

        # Check if it's an exit (legacy string format "exit::...")
        if isinstance(next_step, str) and next_step.startswith("exit::"):
            logger.debug(f"DAGワークフロー終了 (レガシー形式): {next_step}")
            # Convert legacy format to exit_state
            # "exit::green::done" → "success.done"
            # "exit::red::error" → "failure.error"
            parts = next_step.split("::")
            color = parts[1] if len(parts) > 1 else "green"
            detail = parts[2] if len(parts) > 2 else "done"
            category = "success" if color in ("green", "yellow") else "failure"
            exit_state = f"{category}.{detail}"

            return DefaultExitContract(
                exit_state=exit_state,
                context=context,
                execution_path=tuple(execution_path),
                iterations=iteration,
            )

        # Execute next node
        iteration += 1
        next_node_name = _get_node_name(next_step)

        # Check if it's an exit node
        if _is_exit_node(next_node_name):
            # Exit node returns Context or ExitContract (no Outcome)
            result = next_step(context)
            execution_path.append(next_node_name)

            logger.debug(f"DAGワークフロー終了（終端ノード）: {next_node_name}")

            if on_step:
                exit_state = (
                    result.exit_state
                    if isinstance(result, ExitContract)
                    else _derive_exit_state(next_node_name)
                )
                on_step(next_node_name, f"exit::{exit_state}", result)

            # Return ExitContract with execution metadata
            if isinstance(result, ExitContract):
                return result.model_copy(
                    update={
                        "execution_path": tuple(execution_path),
                        "iterations": iteration,
                    }
                )
            else:
                # Backward compatibility: wrap non-ExitContract in DefaultExitContract
                exit_state = _derive_exit_state(next_node_name)
                return DefaultExitContract(
                    exit_state=exit_state,
                    context=result,
                    execution_path=tuple(execution_path),
                    iterations=iteration,
                )

        # Regular node returns (context, Outcome)
        context, outcome = next_step(context)
        node_name = next_node_name
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
) -> ExitContract:
    """Execute a DAG workflow with async support.

    Same as dag_runner but awaits async nodes.

    Args:
        start: Initial node function (sync or async)
        transitions: Mapping of state strings to next nodes
        max_iterations: Maximum number of node executions
        strict: Raise error on undefined states
        on_step: Optional callback for each step

    Returns:
        ExitContract from the exit node

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
            return DefaultExitContract(
                exit_state="failure.undefined",
                context=context,
                execution_path=tuple(execution_path),
                iterations=iteration,
            )

        # Check if it's an exit (legacy string format "exit::...")
        if isinstance(next_step, str) and next_step.startswith("exit::"):
            # Convert legacy format to exit_state
            parts = next_step.split("::")
            color = parts[1] if len(parts) > 1 else "green"
            detail = parts[2] if len(parts) > 2 else "done"
            category = "success" if color in ("green", "yellow") else "failure"
            exit_state = f"{category}.{detail}"

            return DefaultExitContract(
                exit_state=exit_state,
                context=context,
                execution_path=tuple(execution_path),
                iterations=iteration,
            )

        iteration += 1
        next_node_name = _get_node_name(next_step)

        # Check if it's an exit node
        if _is_exit_node(next_node_name):
            # Exit node returns Context or ExitContract (no Outcome)
            if asyncio.iscoroutinefunction(next_step):
                result = await next_step(context)
            else:
                result = next_step(context)

            execution_path.append(next_node_name)

            if on_step:
                exit_state = (
                    result.exit_state
                    if isinstance(result, ExitContract)
                    else _derive_exit_state(next_node_name)
                )
                on_step(next_node_name, f"exit::{exit_state}", result)

            # Return ExitContract with execution metadata
            if isinstance(result, ExitContract):
                return result.model_copy(
                    update={
                        "execution_path": tuple(execution_path),
                        "iterations": iteration,
                    }
                )
            else:
                # Backward compatibility: wrap non-ExitContract in DefaultExitContract
                exit_state = _derive_exit_state(next_node_name)
                return DefaultExitContract(
                    exit_state=exit_state,
                    context=result,
                    execution_path=tuple(execution_path),
                    iterations=iteration,
                )

        # Regular node returns (context, Outcome)
        if asyncio.iscoroutinefunction(next_step):
            context, outcome = await next_step(context)
        else:
            context, outcome = next_step(context)

        node_name = next_node_name
        state_string = outcome.to_state_string(node_name)
        execution_path.append(node_name)

        if on_step:
            on_step(node_name, state_string, context)

    raise MaxIterationsError(f"最大イテレーション数 ({max_iterations}) に達しました")
