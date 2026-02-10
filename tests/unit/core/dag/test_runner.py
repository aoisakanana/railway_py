"""Tests for DAG runner with Contract + Outcome (v0.12.2 ExitContract 対応)."""
import pytest

from railway import Contract, ExitContract
from railway.core.dag.outcome import Outcome


class TestDagRunner:
    """Test dag_runner function with Contract and Outcome."""

    def test_simple_workflow(self):
        """Should execute a simple linear workflow."""
        from railway.core.dag.runner import dag_runner

        class WorkflowContext(Contract):
            value: int

        def node_a() -> tuple[WorkflowContext, Outcome]:
            return WorkflowContext(value=1), Outcome.success("done")

        def node_b(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            # Contract はイミュータブル、model_copy で新規生成
            return ctx.model_copy(update={"value": 2}), Outcome.success("done")

        class DoneResult(ExitContract):
            exit_state: str = "success.done"
            context: WorkflowContext

        def exit_success_done(ctx: WorkflowContext) -> DoneResult:
            return DoneResult(context=ctx)

        exit_success_done._node_name = "exit.success.done"

        # 文字列キーのみ（シンプル！）
        transitions = {
            "node_a::success::done": node_b,
            "node_b::success::done": exit_success_done,
        }

        result = dag_runner(
            start=node_a,
            transitions=transitions,
        )

        assert result.exit_state == "success.done"
        assert result.is_success is True
        assert result.context.value == 2
        assert result.iterations == 3  # node_a + node_b + exit

    def test_branching_workflow(self):
        """Should handle conditional branching."""
        from railway.core.dag.runner import dag_runner

        class BranchContext(Contract):
            path: str

        call_log = []

        def check_true() -> tuple[BranchContext, Outcome]:
            call_log.append("check_true")
            return BranchContext(path="a"), Outcome.success("true")

        def path_a(ctx: BranchContext) -> tuple[BranchContext, Outcome]:
            call_log.append("path_a")
            return ctx, Outcome.success("done")

        def path_b(ctx: BranchContext) -> tuple[BranchContext, Outcome]:
            call_log.append("path_b")
            return ctx, Outcome.success("done")

        class BranchResult(ExitContract):
            context: BranchContext

        def exit_success_done_a(ctx: BranchContext) -> BranchResult:
            return BranchResult(exit_state="success.done_a", context=ctx)

        exit_success_done_a._node_name = "exit.success.done_a"

        def exit_success_done_b(ctx: BranchContext) -> BranchResult:
            return BranchResult(exit_state="success.done_b", context=ctx)

        exit_success_done_b._node_name = "exit.success.done_b"

        transitions = {
            "check_true::success::true": path_a,
            "check_true::success::false": path_b,
            "path_a::success::done": exit_success_done_a,
            "path_b::success::done": exit_success_done_b,
        }

        # Test true branch
        call_log.clear()
        result = dag_runner(
            start=check_true,
            transitions=transitions,
        )

        assert result.exit_state == "success.done_a"
        assert call_log == ["check_true", "path_a"]

    def test_false_branch(self):
        """Should handle false branch correctly."""
        from railway.core.dag.runner import dag_runner

        class BranchContext(Contract):
            path: str

        call_log = []

        def check_false() -> tuple[BranchContext, Outcome]:
            call_log.append("check_false")
            return BranchContext(path="b"), Outcome.success("false")

        def path_a(ctx: BranchContext) -> tuple[BranchContext, Outcome]:
            call_log.append("path_a")
            return ctx, Outcome.success("done")

        def path_b(ctx: BranchContext) -> tuple[BranchContext, Outcome]:
            call_log.append("path_b")
            return ctx, Outcome.success("done")

        class BranchResult(ExitContract):
            context: BranchContext

        def exit_success_done_a(ctx: BranchContext) -> BranchResult:
            return BranchResult(exit_state="success.done_a", context=ctx)

        exit_success_done_a._node_name = "exit.success.done_a"

        def exit_success_done_b(ctx: BranchContext) -> BranchResult:
            return BranchResult(exit_state="success.done_b", context=ctx)

        exit_success_done_b._node_name = "exit.success.done_b"

        transitions = {
            "check_false::success::true": path_a,
            "check_false::success::false": path_b,
            "path_a::success::done": exit_success_done_a,
            "path_b::success::done": exit_success_done_b,
        }

        # Test false branch
        call_log.clear()
        result = dag_runner(
            start=check_false,
            transitions=transitions,
        )

        assert result.exit_state == "success.done_b"
        assert call_log == ["check_false", "path_b"]

    def test_max_iterations_limit(self):
        """Should stop when max iterations reached."""
        from railway.core.dag.runner import MaxIterationsError, dag_runner

        class LoopContext(Contract):
            count: int = 0

        def loop_node(ctx: LoopContext) -> tuple[LoopContext, Outcome]:
            return ctx.model_copy(update={"count": ctx.count + 1}), Outcome.success(
                "continue"
            )

        def loop_start() -> tuple[LoopContext, Outcome]:
            return loop_node(LoopContext())

        transitions = {
            "loop_start::success::continue": loop_node,
            "loop_node::success::continue": loop_node,
        }

        with pytest.raises(MaxIterationsError):
            dag_runner(
                start=loop_start,
                transitions=transitions,
                max_iterations=5,
            )

    def test_undefined_state_error(self):
        """Should error on undefined state."""
        from railway.core.dag.runner import UndefinedStateError, dag_runner

        class EmptyContext(Contract):
            pass

        def node() -> tuple[EmptyContext, Outcome]:
            return EmptyContext(), Outcome.failure("unknown")

        transitions = {
            "node::success::known": lambda x: (x, Outcome.success("done")),
        }

        with pytest.raises(UndefinedStateError):
            dag_runner(
                start=node,
                transitions=transitions,
                strict=True,
            )

    def test_undefined_state_non_strict(self):
        """v0.12.3: strict=False でも UndefinedStateError が発生する。

        Note:
            v0.12.3 で strict=False の動作が変更され、
            未定義状態では常に UndefinedStateError が発生する。
        """
        from railway.core.dag.runner import UndefinedStateError, dag_runner

        class EmptyContext(Contract):
            pass

        def node() -> tuple[EmptyContext, Outcome]:
            return EmptyContext(), Outcome.failure("unknown")

        transitions = {
            "node::success::known": lambda x: (x, Outcome.success("done")),
        }

        # v0.12.3: strict=False でも例外が発生
        with pytest.raises(UndefinedStateError):
            dag_runner(
                start=node,
                transitions=transitions,
                strict=False,
            )

    def test_passes_context_between_nodes(self):
        """Should pass context from one node to the next."""
        from railway.core.dag.runner import dag_runner

        class ChainContext(Contract):
            from_a: bool = False
            from_b: bool = False

        def node_a() -> tuple[ChainContext, Outcome]:
            return ChainContext(from_a=True), Outcome.success("done")

        def node_b(ctx: ChainContext) -> tuple[ChainContext, Outcome]:
            assert ctx.from_a is True
            return ctx.model_copy(update={"from_b": True}), Outcome.success("done")

        class ChainResult(ExitContract):
            exit_state: str = "success.done"
            context: ChainContext

        def exit_success_done(ctx: ChainContext) -> ChainResult:
            return ChainResult(context=ctx)

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "node_a::success::done": node_b,
            "node_b::success::done": exit_success_done,
        }

        result = dag_runner(start=node_a, transitions=transitions)

        assert result.context.from_a is True
        assert result.context.from_b is True

    def test_on_step_callback(self):
        """Should call on_step callback for each step."""
        from railway.core.dag.runner import dag_runner

        class StepContext(Contract):
            value: int

        steps = []

        def step_callback(node_name: str, state_string: str, context):
            steps.append((node_name, state_string))

        def node_a() -> tuple[StepContext, Outcome]:
            return StepContext(value=1), Outcome.success("done")

        def node_b(ctx: StepContext) -> tuple[StepContext, Outcome]:
            return ctx.model_copy(update={"value": 2}), Outcome.success("done")

        class StepResult(ExitContract):
            exit_state: str = "success.done"
            context: StepContext

        def exit_success_done(ctx: StepContext) -> StepResult:
            return StepResult(context=ctx)

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "node_a::success::done": node_b,
            "node_b::success::done": exit_success_done,
        }

        dag_runner(start=node_a, transitions=transitions, on_step=step_callback)

        assert len(steps) == 3  # node_a + node_b + exit
        assert steps[0] == ("node_a", "node_a::success::done")
        assert steps[1] == ("node_b", "node_b::success::done")


class TestExitContractResult:
    """Test ExitContract result from dag_runner."""

    def test_exit_contract_is_success(self):
        """Should return ExitContract with is_success for success.* state."""
        result = ExitContract(
            exit_state="success.done",
        )
        assert result.is_success is True
        assert result.exit_code == 0

    def test_exit_contract_is_failure(self):
        """Should return ExitContract with is_failure for failure.* state."""
        result = ExitContract(
            exit_state="failure.error",
        )
        assert result.is_success is False
        assert result.exit_code == 1

    def test_exit_contract_is_immutable(self):
        """ExitContract should be immutable."""
        result = ExitContract(
            exit_state="success.done",
        )

        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            result.exit_state = "changed"  # type: ignore[misc]


class TestLegacyExitFormat:
    """v0.12.3: レガシー exit:: 形式は拒否される。"""

    def test_legacy_exit_green_raises_error(self):
        """v0.12.3: レガシー形式 exit::green::done は LegacyExitFormatError。"""
        from railway.core.dag.errors import LegacyExitFormatError
        from railway.core.dag.runner import dag_runner

        class EmptyContext(Contract):
            pass

        def start() -> tuple[EmptyContext, Outcome]:
            return EmptyContext(), Outcome.success("done")

        # Legacy format is now rejected
        transitions = {
            "start::success::done": "exit::green::done",
        }

        with pytest.raises(LegacyExitFormatError) as exc_info:
            dag_runner(start=start, transitions=transitions)

        assert "exit::green::done" in str(exc_info.value)

    def test_legacy_exit_red_raises_error(self):
        """v0.12.3: レガシー形式 exit::red::error は LegacyExitFormatError。"""
        from railway.core.dag.errors import LegacyExitFormatError
        from railway.core.dag.runner import dag_runner

        class EmptyContext(Contract):
            pass

        def start() -> tuple[EmptyContext, Outcome]:
            return EmptyContext(), Outcome.failure("error")

        # Legacy format is now rejected
        transitions = {
            "start::failure::error": "exit::red::error",
        }

        with pytest.raises(LegacyExitFormatError):
            dag_runner(start=start, transitions=transitions)

    def test_legacy_exit_yellow_raises_error(self):
        """v0.12.3: レガシー形式 exit::yellow::warning は LegacyExitFormatError。"""
        from railway.core.dag.errors import LegacyExitFormatError
        from railway.core.dag.runner import dag_runner

        class EmptyContext(Contract):
            pass

        def start() -> tuple[EmptyContext, Outcome]:
            return EmptyContext(), Outcome.success("warn")

        transitions = {
            "start::success::warn": "exit::yellow::warning",
        }

        with pytest.raises(LegacyExitFormatError):
            dag_runner(start=start, transitions=transitions)


class TestDagRunnerWithOutcome:
    """Test dag_runner with Outcome class (string keys only)."""

    def test_workflow_with_outcome(self):
        """Should work with Outcome and string transition keys."""
        from railway.core.dag.runner import dag_runner

        class WorkflowContext(Contract):
            value: int

        def node_a() -> tuple[WorkflowContext, Outcome]:
            return WorkflowContext(value=1), Outcome.success("done")

        def node_b(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx.model_copy(update={"value": 2}), Outcome.success("complete")

        class WorkflowResult(ExitContract):
            exit_state: str = "success.done"
            context: WorkflowContext

        def exit_success_done(ctx: WorkflowContext) -> WorkflowResult:
            return WorkflowResult(context=ctx)

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "node_a::success::done": node_b,
            "node_b::success::complete": exit_success_done,
        }

        result = dag_runner(start=node_a, transitions=transitions)

        assert result.is_success
        assert result.context.value == 2

    def test_failure_path(self):
        """Should handle failure outcomes correctly."""
        from railway.core.dag.runner import dag_runner

        class FailContext(Contract):
            error_type: str = ""

        def check() -> tuple[FailContext, Outcome]:
            return FailContext(error_type="validation"), Outcome.failure("validation")

        def handle_error(ctx: FailContext) -> tuple[FailContext, Outcome]:
            return ctx, Outcome.success("handled")

        class FailResult(ExitContract):
            context: FailContext

        def exit_success_done(ctx: FailContext) -> FailResult:
            return FailResult(exit_state="success.done", context=ctx)

        exit_success_done._node_name = "exit.success.done"

        def exit_warning_handled(ctx: FailContext) -> FailResult:
            return FailResult(exit_state="success.handled", context=ctx)

        exit_warning_handled._node_name = "exit.success.handled"

        transitions = {
            "check::success::done": exit_success_done,
            "check::failure::validation": handle_error,
            "handle_error::success::handled": exit_warning_handled,
        }

        result = dag_runner(start=check, transitions=transitions)

        assert result.exit_state == "success.handled"
        assert result.context.error_type == "validation"


class TestDagRunnerAsync:
    """Test async dag_runner."""

    @pytest.mark.asyncio
    async def test_async_workflow(self):
        """Should execute async nodes."""
        from railway.core.dag.runner import async_dag_runner

        class AsyncContext(Contract):
            is_async: bool

        async def async_node() -> tuple[AsyncContext, Outcome]:
            return AsyncContext(is_async=True), Outcome.success("done")

        class AsyncResult(ExitContract):
            exit_state: str = "success.done"
            context: AsyncContext

        def exit_success_done(ctx: AsyncContext) -> AsyncResult:
            return AsyncResult(context=ctx)

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "async_node::success::done": exit_success_done,
        }

        result = await async_dag_runner(
            start=async_node,
            transitions=transitions,
        )

        assert result.is_success
        assert result.context.is_async is True

    @pytest.mark.asyncio
    async def test_async_mixed_workflow(self):
        """Should handle mixed sync/async nodes."""
        from railway.core.dag.runner import async_dag_runner

        class MixedContext(Contract):
            sync_called: bool = False
            async_called: bool = False

        def sync_node() -> tuple[MixedContext, Outcome]:
            return MixedContext(sync_called=True), Outcome.success("done")

        async def async_node(ctx: MixedContext) -> tuple[MixedContext, Outcome]:
            return ctx.model_copy(update={"async_called": True}), Outcome.success("done")

        class MixedResult(ExitContract):
            exit_state: str = "success.done"
            context: MixedContext

        def exit_success_done(ctx: MixedContext) -> MixedResult:
            return MixedResult(context=ctx)

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "sync_node::success::done": async_node,
            "async_node::success::done": exit_success_done,
        }

        result = await async_dag_runner(start=sync_node, transitions=transitions)

        assert result.is_success
        assert result.context.sync_called is True
        assert result.context.async_called is True

    @pytest.mark.asyncio
    async def test_async_max_iterations(self):
        """Should respect max_iterations in async runner."""
        from railway.core.dag.runner import MaxIterationsError, async_dag_runner

        class LoopContext(Contract):
            count: int = 0

        async def async_loop(ctx: LoopContext) -> tuple[LoopContext, Outcome]:
            return ctx.model_copy(update={"count": ctx.count + 1}), Outcome.success(
                "continue"
            )

        async def async_loop_start() -> tuple[LoopContext, Outcome]:
            return await async_loop(LoopContext())

        transitions = {
            "async_loop_start::success::continue": async_loop,
            "async_loop::success::continue": async_loop,
        }

        with pytest.raises(MaxIterationsError):
            await async_dag_runner(
                start=async_loop_start,
                transitions=transitions,
                max_iterations=3,
            )


class TestDagRunnerInfoLogging:
    """INFO レベルでステップ情報が出力されるテスト。

    loguru は stderr に出力するため capsys ではなく capfd を使用。
    """

    def _run_simple_workflow(self):
        """テスト用のシンプルなワークフローを実行する。"""
        from railway import ExitContract
        from railway.core.dag.outcome import Outcome
        from railway.core.dag.runner import dag_runner

        class DoneResult(ExitContract):
            exit_state: str = "success.done"

        def start():
            return {"value": 1}, Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        def exit_done(ctx) -> DoneResult:
            return DoneResult()

        exit_done._node_name = "exit.success.done"  # type: ignore[attr-defined]

        transitions = {"start::success::done": exit_done}
        return dag_runner(start=start, transitions=transitions)

    def test_info_log_includes_outcome(self) -> None:
        """INFO レベルのログに Outcome 情報が含まれること。"""
        from loguru import logger

        messages: list[str] = []
        handler_id = logger.add(
            lambda m: messages.append(m.record["message"]),
            level="INFO",
            filter="railway.core.dag.runner",
        )
        try:
            self._run_simple_workflow()
        finally:
            logger.remove(handler_id)

        # start ノードの完了ログに outcome 情報が含まれること
        assert any("start" in m and "success::done" in m for m in messages), (
            f"INFO ログに Outcome 情報がない: {messages}"
        )

    def test_info_log_includes_exit(self) -> None:
        """INFO レベルのログに終端ノード情報が含まれること。"""
        from loguru import logger

        messages: list[str] = []
        handler_id = logger.add(
            lambda m: messages.append(m.record["message"]),
            level="INFO",
            filter="railway.core.dag.runner",
        )
        try:
            self._run_simple_workflow()
        finally:
            logger.remove(handler_id)

        # 終端ノードのログが含まれること
        assert any("exit.success.done" in m for m in messages), (
            f"INFO ログに終端ノード情報がない: {messages}"
        )


class TestDagRunnerIntegration:
    """Integration tests using test YAML fixtures."""

    def test_with_simple_yaml_workflow(self, simple_yaml):
        """Should execute workflow from simple test YAML.

        Note: Uses tests/fixtures/transition_graphs/simple_20250125000000.yml
        """
        from railway.core.dag.parser import load_transition_graph

        # Parse the test YAML
        graph = load_transition_graph(simple_yaml)

        assert graph.entrypoint == "simple"
        assert len(graph.nodes) == 1
        # Further integration tests would mock the nodes

    def test_with_branching_yaml_workflow(self, branching_yaml):
        """Should parse branching workflow from test YAML.

        Note: Uses tests/fixtures/transition_graphs/branching_20250125000000.yml
        """
        from railway.core.dag.parser import load_transition_graph

        graph = load_transition_graph(branching_yaml)

        assert graph.entrypoint == "branching"
        assert len(graph.nodes) == 5  # 5 nodes in branching workflow
