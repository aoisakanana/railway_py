"""Tests for dag_runner exit node execution."""

import pytest
from railway.core.dag.runner import dag_runner, async_dag_runner, DagRunnerResult
from railway.core.dag.outcome import Outcome


class TestDagRunnerExitNode:
    """dag_runner の終端ノード実行テスト。"""

    def test_executes_exit_node_function(self) -> None:
        """終端ノード関数が実行される。"""
        execution_log: list[str] = []

        def start():
            execution_log.append("start")
            return {"count": 1}, Outcome.success("done")

        start._node_name = "start"

        def exit_success_done(ctx):
            """終端ノードは Context のみを返す。"""
            execution_log.append("exit.success.done")
            return {"summary": "completed", "original_count": ctx["count"]}

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "start::success::done": exit_success_done,
        }
        exit_codes = {
            "exit.success.done": 0,
        }

        result = dag_runner(
            start=start,
            transitions=transitions,
            exit_codes=exit_codes,
        )

        assert "start" in execution_log
        assert "exit.success.done" in execution_log
        assert result.context["summary"] == "completed"
        assert result.context["original_count"] == 1
        assert result.is_success is True

    def test_exit_node_returns_final_context(self) -> None:
        """終端ノードの返り値が最終コンテキストになる。"""

        def start():
            return {"initial": True}, Outcome.success("done")

        start._node_name = "start"

        def exit_success_done(ctx):
            return {
                "status": "completed",
                "original": ctx,
            }

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "start::success::done": exit_success_done,
        }
        exit_codes = {
            "exit.success.done": 0,
        }

        result = dag_runner(
            start=start,
            transitions=transitions,
            exit_codes=exit_codes,
        )

        assert result.context["status"] == "completed"
        assert result.context["original"]["initial"] is True

    def test_exit_code_zero_is_green(self) -> None:
        """終了コード 0 は green。"""

        def start():
            return {}, Outcome.success("done")

        start._node_name = "start"

        def exit_success_done(ctx):
            return ctx

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "start::success::done": exit_success_done,
        }
        exit_codes = {
            "exit.success.done": 0,
        }

        result = dag_runner(
            start=start,
            transitions=transitions,
            exit_codes=exit_codes,
        )

        assert "green" in result.exit_code
        assert "exit.success.done" in result.exit_code
        assert result.is_success is True

    def test_exit_code_nonzero_is_red(self) -> None:
        """終了コード 0 以外は red。"""

        def start():
            return {}, Outcome.failure("error")

        start._node_name = "start"

        def exit_failure_error(ctx):
            return ctx

        exit_failure_error._node_name = "exit.failure.error"

        transitions = {
            "start::failure::error": exit_failure_error,
        }
        exit_codes = {
            "exit.failure.error": 1,
        }

        result = dag_runner(
            start=start,
            transitions=transitions,
            exit_codes=exit_codes,
        )

        assert "red" in result.exit_code
        assert "exit.failure.error" in result.exit_code
        assert result.is_success is False

    def test_on_step_called_for_exit_node(self) -> None:
        """on_step コールバックが終端ノードでも呼ばれる。"""
        step_log: list[tuple[str, str]] = []

        def start():
            return {}, Outcome.success("done")

        start._node_name = "start"

        def exit_success_done(ctx):
            return ctx

        exit_success_done._node_name = "exit.success.done"

        def on_step(node_name: str, state: str, ctx) -> None:
            step_log.append((node_name, state))

        transitions = {
            "start::success::done": exit_success_done,
        }
        exit_codes = {
            "exit.success.done": 0,
        }

        dag_runner(
            start=start,
            transitions=transitions,
            exit_codes=exit_codes,
            on_step=on_step,
        )

        assert ("start", "start::success::done") in step_log
        # 終端ノードは exit:: 形式
        assert any(
            "exit.success.done" in node and "exit::green" in state
            for node, state in step_log
        )

    def test_execution_path_includes_exit_node(self) -> None:
        """execution_path に終端ノードが含まれる。"""

        def start():
            return {}, Outcome.success("done")

        start._node_name = "start"

        def exit_success_done(ctx):
            return ctx

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "start::success::done": exit_success_done,
        }
        exit_codes = {
            "exit.success.done": 0,
        }

        result = dag_runner(
            start=start,
            transitions=transitions,
            exit_codes=exit_codes,
        )

        assert "start" in result.execution_path
        assert "exit.success.done" in result.execution_path

    def test_backward_compatible_without_exit_codes(self) -> None:
        """exit_codes なしでも動作（後方互換）。"""

        def start():
            return {}, Outcome.success("done")

        start._node_name = "start"

        def process(ctx):
            return ctx, Outcome.success("complete")

        process._node_name = "process"

        transitions = {
            "start::success::done": process,
            # process::success::complete に遷移先がない → strict=False で終了
        }

        result = dag_runner(
            start=start,
            transitions=transitions,
            strict=False,  # 遷移先がなくてもエラーにしない
        )

        # 遷移先がないため終了（exit_code は空文字列）
        assert result.exit_code == ""

    def test_custom_exit_code(self) -> None:
        """カスタム終了コード。"""

        def start():
            return {}, Outcome.success("warn")

        start._node_name = "start"

        def exit_warning_low_disk(ctx):
            return {"warning": "disk space low"}

        exit_warning_low_disk._node_name = "exit.warning.low_disk"

        transitions = {
            "start::success::warn": exit_warning_low_disk,
        }
        exit_codes = {
            "exit.warning.low_disk": 2,  # カスタム終了コード
        }

        result = dag_runner(
            start=start,
            transitions=transitions,
            exit_codes=exit_codes,
        )

        # 0 以外は red
        assert "red" in result.exit_code
        assert "exit.warning.low_disk" in result.exit_code


class TestDagRunnerExitNodeAsync:
    """async_dag_runner の終端ノード実行テスト。"""

    @pytest.mark.asyncio
    async def test_async_executes_exit_node(self) -> None:
        """非同期版でも終端ノードが実行される。"""

        async def start():
            return {"count": 1}, Outcome.success("done")

        start._node_name = "start"

        async def exit_success_done(ctx):
            return {"summary": "completed"}

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "start::success::done": exit_success_done,
        }
        exit_codes = {
            "exit.success.done": 0,
        }

        result = await async_dag_runner(
            start=start,
            transitions=transitions,
            exit_codes=exit_codes,
        )

        assert result.context["summary"] == "completed"
        assert result.is_success is True

    @pytest.mark.asyncio
    async def test_async_sync_exit_node(self) -> None:
        """非同期 runner で同期終端ノードも実行可能。"""

        async def start():
            return {"count": 1}, Outcome.success("done")

        start._node_name = "start"

        def exit_success_done(ctx):  # 同期関数
            return {"summary": "completed"}

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "start::success::done": exit_success_done,
        }
        exit_codes = {
            "exit.success.done": 0,
        }

        result = await async_dag_runner(
            start=start,
            transitions=transitions,
            exit_codes=exit_codes,
        )

        assert result.context["summary"] == "completed"
