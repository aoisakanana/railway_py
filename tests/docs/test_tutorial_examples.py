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


class TestTutorialModelCopyPattern:
    """TUTORIAL.md Step 11: model_copy パターンのテスト。"""

    def test_model_copy_preserves_existing_data(self) -> None:
        """model_copy が既存データを保持すること。"""

        class AlertContext(Contract):
            """ワークフロー全体で必要なデータを含む Contract。"""

            incident_id: str
            severity: str
            hostname: str | None = None
            escalated: bool = False

        @node(name="start")
        def start() -> tuple[AlertContext, Outcome]:
            return AlertContext(incident_id="INC-001", severity="critical"), Outcome.success("check")

        @node(name="check_host")
        def check_host(ctx: AlertContext) -> tuple[AlertContext, Outcome]:
            # model_copy で既存データを保持しつつ hostname を追加
            new_ctx = ctx.model_copy(update={"hostname": "web-01"})
            return new_ctx, Outcome.success("escalate")

        @node(name="escalate")
        def escalate(ctx: AlertContext) -> tuple[AlertContext, Outcome]:
            # すべての既存データが利用可能
            assert ctx.incident_id == "INC-001"
            assert ctx.severity == "critical"
            assert ctx.hostname == "web-01"
            return ctx.model_copy(update={"escalated": True}), Outcome.success("done")

        class DoneResult(ExitContract):
            exit_state: str = "success.done"
            incident_id: str
            escalated: bool

        @node(name="exit.success.done")
        def done(ctx: AlertContext) -> DoneResult:
            return DoneResult(incident_id=ctx.incident_id, escalated=ctx.escalated)

        result = dag_runner(
            start=start,
            transitions={
                "start::success::check": check_host,
                "check_host::success::escalate": escalate,
                "escalate::success::done": done,
            },
        )

        assert result.is_success
        assert result.incident_id == "INC-001"
        assert result.escalated is True

    def test_data_flows_through_multiple_nodes(self) -> None:
        """データが複数ノードを経由して正しく引き継がれること。"""

        class WorkflowContext(Contract):
            step: int = 0
            values: tuple[str, ...] = ()

        @node(name="start")
        def start() -> tuple[WorkflowContext, Outcome]:
            ctx = WorkflowContext(step=1, values=("start",))
            return ctx, Outcome.success("next")

        @node(name="step_a")
        def step_a(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            new_ctx = ctx.model_copy(update={
                "step": ctx.step + 1,
                "values": ctx.values + ("step_a",),
            })
            return new_ctx, Outcome.success("next")

        @node(name="step_b")
        def step_b(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            new_ctx = ctx.model_copy(update={
                "step": ctx.step + 1,
                "values": ctx.values + ("step_b",),
            })
            return new_ctx, Outcome.success("done")

        class FinalResult(ExitContract):
            exit_state: str = "success.done"
            final_step: int
            all_values: tuple[str, ...]

        @node(name="exit.success.done")
        def done(ctx: WorkflowContext) -> FinalResult:
            return FinalResult(final_step=ctx.step, all_values=ctx.values)

        result = dag_runner(
            start=start,
            transitions={
                "start::success::next": step_a,
                "step_a::success::next": step_b,
                "step_b::success::done": done,
            },
        )

        assert result.is_success
        assert result.final_step == 3
        assert result.all_values == ("start", "step_a", "step_b")


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
