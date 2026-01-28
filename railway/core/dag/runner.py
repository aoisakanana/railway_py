"""
DAG workflow runner.

Executes workflows defined by transition tables,
routing between nodes based on their returned states.

Note: This runner ONLY supports Contract context and string keys.
      dict context is NOT supported.

v0.13.0: 型安全性強制
- 終端ノードは ExitContract サブクラスを返す必要がある
- dict, None 等を返すと ExitNodeTypeError
- レガシー形式 "exit::green::done" は LegacyExitFormatError
- DefaultExitContract は削除
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable

from loguru import logger

from railway.core.dag.errors import ExitNodeTypeError, LegacyExitFormatError
from railway.core.dag.outcome import Outcome
from railway.core.exit_contract import ExitContract


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


def _execute_exit_node(
    exit_node: Callable,
    context: Any,
    node_name: str,
    execution_path: list[str],
    iteration: int,
) -> ExitContract:
    """終端ノードを実行し、ExitContract を返す。

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
        return result.model_copy(
            update={
                "execution_path": tuple(execution_path),
                "iterations": iteration,
            }
        )

    raise ExitNodeTypeError(
        node_name=node_name,
        actual_type=type(result).__name__,
    )


async def _execute_exit_node_async(
    exit_node: Callable,
    context: Any,
    node_name: str,
    execution_path: list[str],
    iteration: int,
) -> ExitContract:
    """終端ノードを非同期実行し、ExitContract を返す。

    Args:
        exit_node: 終端ノード関数（sync or async）
        context: 直前のコンテキスト
        node_name: ノード名
        execution_path: 実行パス
        iteration: イテレーション数

    Returns:
        ExitContract: 終了結果

    Raises:
        ExitNodeTypeError: ExitContract 以外が返された場合
    """
    if asyncio.iscoroutinefunction(exit_node):
        result = await exit_node(context)
    else:
        result = exit_node(context)

    if isinstance(result, ExitContract):
        return result.model_copy(
            update={
                "execution_path": tuple(execution_path),
                "iterations": iteration,
            }
        )

    raise ExitNodeTypeError(
        node_name=node_name,
        actual_type=type(result).__name__,
    )


def _check_legacy_exit_format(next_step: Any, state_string: str) -> None:
    """レガシー exit 形式をチェックし、使用されていればエラーを発生。

    Args:
        next_step: 次のステップ
        state_string: 状態文字列（エラーメッセージ用）

    Raises:
        LegacyExitFormatError: レガシー形式が使用された場合
    """
    if isinstance(next_step, str) and next_step.startswith("exit::"):
        raise LegacyExitFormatError(legacy_format=next_step)


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
        ExitNodeTypeError: If exit node returns non-ExitContract (v0.13.0+)
        LegacyExitFormatError: If legacy "exit::..." format is used (v0.13.0+)

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
                raise UndefinedStateError(
                    f"未定義の状態です: {state_string} (ノード: {node_name})"
                )

        # Check for legacy exit format (v0.13.0: raise error)
        _check_legacy_exit_format(next_step, state_string)

        # Execute next node
        iteration += 1
        next_node_name = _get_node_name(next_step)

        # Check if it's an exit node
        if _is_exit_node(next_node_name):
            execution_path.append(next_node_name)
            logger.debug(f"DAGワークフロー終了（終端ノード）: {next_node_name}")

            result = _execute_exit_node(
                exit_node=next_step,
                context=context,
                node_name=next_node_name,
                execution_path=execution_path,
                iteration=iteration,
            )

            if on_step:
                on_step(next_node_name, f"exit::{result.exit_state}", result)

            return result

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
        ExitNodeTypeError: If exit node returns non-ExitContract (v0.13.0+)
        LegacyExitFormatError: If legacy "exit::..." format is used (v0.13.0+)
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
                raise UndefinedStateError(
                    f"未定義の状態です: {state_string} (ノード: {node_name})"
                )
            raise UndefinedStateError(
                f"未定義の状態です: {state_string} (ノード: {node_name})"
            )

        # Check for legacy exit format (v0.13.0: raise error)
        _check_legacy_exit_format(next_step, state_string)

        iteration += 1
        next_node_name = _get_node_name(next_step)

        # Check if it's an exit node
        if _is_exit_node(next_node_name):
            execution_path.append(next_node_name)

            result = await _execute_exit_node_async(
                exit_node=next_step,
                context=context,
                node_name=next_node_name,
                execution_path=execution_path,
                iteration=iteration,
            )

            if on_step:
                on_step(next_node_name, f"exit::{result.exit_state}", result)

            return result

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
