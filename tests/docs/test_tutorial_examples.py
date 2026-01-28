"""TUTORIAL.md のコード例が動作することを確認するテスト。

Issue #47: TUTORIAL.md 更新
TDD によりドキュメントのコード例が実際に動作することを担保する。
"""

import pytest

from railway import Contract, ExitContract, node
from railway.core.dag import dag_runner, async_dag_runner, Outcome


class TestTutorialExitNodeExamples:
    """TUTORIAL.md の終端ノード例が動作することを確認。"""

    def test_basic_exit_node_example(self) -> None:
        """基本的な終端ノードの例が動作する。"""

        # TUTORIAL.md のコード例を再現
        class SuccessDoneResult(ExitContract):
            """正常終了時の結果。"""

            exit_state: str = "success.done"
            processed_count: int
            summary: str

        @node(name="exit.success.done")
        def done(ctx: dict) -> SuccessDoneResult:
            return SuccessDoneResult(
                processed_count=ctx["count"],
                summary="All items processed",
            )

        @node(name="start")
        def start() -> tuple[dict, Outcome]:
            return {"count": 42}, Outcome.success("done")

        result = dag_runner(
            start=start,
            transitions={"start::success::done": done},
        )

        assert result.is_success
        assert result.processed_count == 42
        assert result.summary == "All items processed"
        assert result.exit_code == 0
        assert result.exit_state == "success.done"

    def test_failure_exit_node_example(self) -> None:
        """失敗終端ノードの例が動作する。"""

        class TimeoutResult(ExitContract):
            """タイムアウト時の結果。"""

            exit_state: str = "failure.timeout"
            error_message: str
            retry_count: int

        @node(name="exit.failure.timeout")
        def timeout(ctx: dict) -> TimeoutResult:
            return TimeoutResult(
                error_message="API request timed out",
                retry_count=ctx.get("retries", 0),
            )

        @node(name="start")
        def start() -> tuple[dict, Outcome]:
            return {"retries": 3}, Outcome.failure("timeout")

        result = dag_runner(
            start=start,
            transitions={"start::failure::timeout": timeout},
        )

        assert result.is_success is False
        assert result.exit_code == 1
        assert result.exit_state == "failure.timeout"
        assert result.error_message == "API request timed out"
        assert result.retry_count == 3

    def test_dag_runner_result_properties(self) -> None:
        """dag_runner の返り値プロパティが正しく設定される。"""

        class ProcessResult(ExitContract):
            exit_state: str = "success.done"
            status: str

        @node(name="start")
        def start() -> tuple[dict, Outcome]:
            return {"step": 1}, Outcome.success("next")

        @node(name="process")
        def process(ctx: dict) -> tuple[dict, Outcome]:
            return {"step": 2}, Outcome.success("done")

        @node(name="exit.success.done")
        def done(ctx: dict) -> ProcessResult:
            return ProcessResult(status="completed")

        result = dag_runner(
            start=start,
            transitions={
                "start::success::next": process,
                "process::success::done": done,
            },
        )

        # 基本プロパティ
        assert result.is_success is True
        assert result.exit_code == 0
        assert result.exit_state == "success.done"

        # カスタムフィールド
        assert result.status == "completed"

        # メタデータ
        assert "start" in result.execution_path
        assert "process" in result.execution_path
        assert "exit.success.done" in result.execution_path
        assert result.iterations == 3

    def test_exit_state_determines_exit_code(self) -> None:
        """exit_state から exit_code が自動導出される。"""

        class WarningResult(ExitContract):
            exit_state: str = "warning.low_disk"
            message: str

        @node(name="start")
        def start() -> tuple[dict, Outcome]:
            return {}, Outcome.success("warn")

        @node(name="exit.warning.low_disk")
        def warn(ctx: dict) -> WarningResult:
            return WarningResult(message="Disk space is low")

        result = dag_runner(
            start=start,
            transitions={"start::success::warn": warn},
        )

        # success.* 以外は exit_code = 1
        assert result.exit_code == 1
        assert result.is_success is False

    def test_custom_exit_code(self) -> None:
        """カスタム exit_code を指定できる。"""

        class CustomExitResult(ExitContract):
            exit_state: str = "warning.threshold"
            exit_code: int = 2  # カスタム exit_code

        @node(name="start")
        def start() -> tuple[dict, Outcome]:
            return {}, Outcome.success("threshold")

        @node(name="exit.warning.threshold")
        def threshold(ctx: dict) -> CustomExitResult:
            return CustomExitResult()

        result = dag_runner(
            start=start,
            transitions={"start::success::threshold": threshold},
        )

        assert result.exit_code == 2


class TestTutorialMigrationExamples:
    """v0.12.x からの移行例のテスト。"""

    def test_v013_exit_contract_pattern(self) -> None:
        """v0.12.3 の ExitContract パターンが動作する。"""

        # v0.12.3 の正しいパターン
        class DoneResult(ExitContract):
            exit_state: str = "success.done"
            status: str

        @node(name="start")
        def start() -> tuple[dict, Outcome]:
            return {}, Outcome.success("done")

        @node(name="exit.success.done")
        def done(ctx: dict) -> DoneResult:
            return DoneResult(status="ok")

        result = dag_runner(
            start=start,
            transitions={"start::success::done": done},
        )

        assert isinstance(result, DoneResult)
        assert result.status == "ok"
        assert result.is_success

    def test_exit_node_with_contract_context(self) -> None:
        """Contract を使ったワークフローでの終端ノード。"""

        class WorkflowContext(Contract):
            """ワークフローコンテキスト。"""

            user_id: int
            processed: bool = False

        class CompletedResult(ExitContract):
            """完了結果。"""

            exit_state: str = "success.done"
            user_id: int
            message: str

        @node(name="start")
        def start() -> tuple[WorkflowContext, Outcome]:
            return WorkflowContext(user_id=123), Outcome.success("process")

        @node(name="process")
        def process(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx.model_copy(update={"processed": True}), Outcome.success("done")

        @node(name="exit.success.done")
        def done(ctx: WorkflowContext) -> CompletedResult:
            return CompletedResult(
                user_id=ctx.user_id,
                message=f"User {ctx.user_id} processed",
            )

        result = dag_runner(
            start=start,
            transitions={
                "start::success::process": process,
                "process::success::done": done,
            },
        )

        assert result.is_success
        assert result.user_id == 123
        assert result.message == "User 123 processed"


@pytest.mark.asyncio
class TestTutorialAsyncExamples:
    """非同期ワークフローのテスト。"""

    async def test_async_exit_node_example(self) -> None:
        """非同期終端ノードの例が動作する。"""

        class AsyncResult(ExitContract):
            exit_state: str = "success.done"
            data: str

        @node(name="start")
        async def start() -> tuple[dict, Outcome]:
            return {"key": "value"}, Outcome.success("done")

        @node(name="exit.success.done")
        async def done(ctx: dict) -> AsyncResult:
            return AsyncResult(data="async completed")

        result = await async_dag_runner(
            start=start,
            transitions={"start::success::done": done},
        )

        assert result.is_success
        assert result.data == "async completed"
