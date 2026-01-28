"""Tests for dag_runner exit node execution (v0.13.0 ExitContract 強制).

v0.13.0 破壊的変更:
- 終端ノードは ExitContract サブクラスを返す必要がある
- dict, None 等を返すと ExitNodeTypeError
"""

import pytest
from railway import ExitContract
from railway.core.dag.runner import dag_runner, async_dag_runner
from railway.core.dag.outcome import Outcome
from railway.core.dag.errors import ExitNodeTypeError


class TestDagRunnerExitNode:
    """dag_runner の終端ノード実行テスト。"""

    def test_executes_exit_node_function(self) -> None:
        """終端ノード関数が実行される。"""
        execution_log: list[str] = []

        class DoneResult(ExitContract):
            summary: str
            original_count: int
            exit_state: str = "success.done"

        def start():
            execution_log.append("start")
            return {"count": 1}, Outcome.success("done")

        start._node_name = "start"

        def exit_success_done(ctx) -> DoneResult:
            """終端ノードは ExitContract を返す。"""
            execution_log.append("exit.success.done")
            return DoneResult(summary="completed", original_count=ctx["count"])

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "start::success::done": exit_success_done,
        }

        result = dag_runner(
            start=start,
            transitions=transitions,
        )

        assert "start" in execution_log
        assert "exit.success.done" in execution_log
        assert isinstance(result, DoneResult)
        assert result.summary == "completed"
        assert result.original_count == 1
        assert result.is_success is True

    def test_exit_node_returns_final_context(self) -> None:
        """終端ノードの返り値が最終結果になる。"""

        class DoneResult(ExitContract):
            status: str
            original: dict
            exit_state: str = "success.done"

        def start():
            return {"initial": True}, Outcome.success("done")

        start._node_name = "start"

        def exit_success_done(ctx) -> DoneResult:
            return DoneResult(status="completed", original=ctx)

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "start::success::done": exit_success_done,
        }

        result = dag_runner(
            start=start,
            transitions=transitions,
        )

        assert result.status == "completed"
        assert result.original["initial"] is True

    def test_success_exit_node_is_success(self) -> None:
        """success.* 終端ノードは is_success=True。"""

        class DoneResult(ExitContract):
            exit_state: str = "success.done"

        def start():
            return {}, Outcome.success("done")

        start._node_name = "start"

        def exit_success_done(ctx) -> DoneResult:
            return DoneResult()

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "start::success::done": exit_success_done,
        }

        result = dag_runner(
            start=start,
            transitions=transitions,
        )

        assert result.exit_state == "success.done"
        assert result.exit_code == 0
        assert result.is_success is True

    def test_failure_exit_node_is_failure(self) -> None:
        """failure.* 終端ノードは is_failure=True。"""

        class ErrorResult(ExitContract):
            exit_state: str = "failure.error"

        def start():
            return {}, Outcome.failure("error")

        start._node_name = "start"

        def exit_failure_error(ctx) -> ErrorResult:
            return ErrorResult()

        exit_failure_error._node_name = "exit.failure.error"

        transitions = {
            "start::failure::error": exit_failure_error,
        }

        result = dag_runner(
            start=start,
            transitions=transitions,
        )

        assert result.exit_state == "failure.error"
        assert result.exit_code == 1
        assert result.is_success is False

    def test_on_step_called_for_exit_node(self) -> None:
        """on_step コールバックが終端ノードでも呼ばれる。"""
        step_log: list[tuple[str, str]] = []

        class DoneResult(ExitContract):
            exit_state: str = "success.done"

        def start():
            return {}, Outcome.success("done")

        start._node_name = "start"

        def exit_success_done(ctx) -> DoneResult:
            return DoneResult()

        exit_success_done._node_name = "exit.success.done"

        def on_step(node_name: str, state: str, ctx) -> None:
            step_log.append((node_name, state))

        transitions = {
            "start::success::done": exit_success_done,
        }

        dag_runner(
            start=start,
            transitions=transitions,
            on_step=on_step,
        )

        assert ("start", "start::success::done") in step_log
        # 終端ノードも on_step で呼ばれる
        assert any("exit.success.done" in node for node, state in step_log)

    def test_execution_path_includes_exit_node(self) -> None:
        """execution_path に終端ノードが含まれる。"""

        class DoneResult(ExitContract):
            exit_state: str = "success.done"

        def start():
            return {}, Outcome.success("done")

        start._node_name = "start"

        def exit_success_done(ctx) -> DoneResult:
            return DoneResult()

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "start::success::done": exit_success_done,
        }

        result = dag_runner(
            start=start,
            transitions=transitions,
        )

        assert "start" in result.execution_path
        assert "exit.success.done" in result.execution_path

    def test_exit_node_returning_dict_raises_error(self) -> None:
        """v0.13.0: 終端ノードが dict を返すと ExitNodeTypeError。"""

        def start():
            return {}, Outcome.success("done")

        start._node_name = "start"

        def exit_success_done(ctx):
            return {"summary": "completed"}  # ExitContract ではない

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "start::success::done": exit_success_done,
        }

        with pytest.raises(ExitNodeTypeError) as exc_info:
            dag_runner(
                start=start,
                transitions=transitions,
            )

        assert "exit.success.done" in str(exc_info.value)
        assert "dict" in str(exc_info.value)

    def test_custom_exit_contract_subclass(self) -> None:
        """ExitContract サブクラスを返す終端ノード。"""

        class DoneResult(ExitContract):
            summary: str
            exit_state: str = "success.done"

        def start():
            return {}, Outcome.success("done")

        start._node_name = "start"

        def exit_success_done(ctx) -> DoneResult:
            return DoneResult(summary="all tasks completed")

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "start::success::done": exit_success_done,
        }

        result = dag_runner(
            start=start,
            transitions=transitions,
        )

        assert isinstance(result, DoneResult)
        assert result.summary == "all tasks completed"
        assert result.exit_code == 0
        assert result.is_success is True


class TestDagRunnerExitNodeAsync:
    """async_dag_runner の終端ノード実行テスト。"""

    @pytest.mark.asyncio
    async def test_async_executes_exit_node(self) -> None:
        """非同期版でも終端ノードが実行される。"""

        class DoneResult(ExitContract):
            summary: str
            exit_state: str = "success.done"

        async def start():
            return {"count": 1}, Outcome.success("done")

        start._node_name = "start"

        async def exit_success_done(ctx) -> DoneResult:
            return DoneResult(summary="completed")

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "start::success::done": exit_success_done,
        }

        result = await async_dag_runner(
            start=start,
            transitions=transitions,
        )

        assert result.summary == "completed"
        assert result.is_success is True

    @pytest.mark.asyncio
    async def test_async_sync_exit_node(self) -> None:
        """非同期 runner で同期終端ノードも実行可能。"""

        class DoneResult(ExitContract):
            summary: str
            exit_state: str = "success.done"

        async def start():
            return {"count": 1}, Outcome.success("done")

        start._node_name = "start"

        def exit_success_done(ctx) -> DoneResult:  # 同期関数
            return DoneResult(summary="completed")

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "start::success::done": exit_success_done,
        }

        result = await async_dag_runner(
            start=start,
            transitions=transitions,
        )

        assert result.summary == "completed"
