"""Tests for DAG runner with Contract + Outcome (string keys only)."""
import pytest

from railway import Contract
from railway.core.dag.outcome import Outcome


class TestDagRunner:
    """Test dag_runner function with Contract and Outcome."""

    def test_simple_workflow(self):
        """Should execute a simple linear workflow."""
        from railway.core.dag.runner import Exit, dag_runner

        class WorkflowContext(Contract):
            value: int

        def node_a() -> tuple[WorkflowContext, Outcome]:
            return WorkflowContext(value=1), Outcome.success("done")

        def node_b(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            # Contract はイミュータブル、model_copy で新規生成
            return ctx.model_copy(update={"value": 2}), Outcome.success("done")

        # 文字列キーのみ（シンプル！）
        transitions = {
            "node_a::success::done": node_b,
            "node_b::success::done": Exit.GREEN,
        }

        result = dag_runner(
            start=node_a,
            transitions=transitions,
        )

        assert result.exit_code == Exit.GREEN
        assert result.context.value == 2
        assert result.iterations == 2

    def test_branching_workflow(self):
        """Should handle conditional branching."""
        from railway.core.dag.runner import Exit, dag_runner

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

        transitions = {
            "check_true::success::true": path_a,
            "check_true::success::false": path_b,
            "path_a::success::done": Exit.code("green", "done_a"),
            "path_b::success::done": Exit.code("green", "done_b"),
        }

        # Test true branch
        call_log.clear()
        result = dag_runner(
            start=check_true,
            transitions=transitions,
        )

        assert result.exit_code == "exit::green::done_a"
        assert call_log == ["check_true", "path_a"]

    def test_false_branch(self):
        """Should handle false branch correctly."""
        from railway.core.dag.runner import Exit, dag_runner

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

        transitions = {
            "check_false::success::true": path_a,
            "check_false::success::false": path_b,
            "path_a::success::done": Exit.code("green", "done_a"),
            "path_b::success::done": Exit.code("green", "done_b"),
        }

        # Test false branch
        call_log.clear()
        result = dag_runner(
            start=check_false,
            transitions=transitions,
        )

        assert result.exit_code == "exit::green::done_b"
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
        """Should not error on undefined state when strict=False."""
        from railway.core.dag.runner import dag_runner

        class EmptyContext(Contract):
            pass

        def node() -> tuple[EmptyContext, Outcome]:
            return EmptyContext(), Outcome.failure("unknown")

        transitions = {
            "node::success::known": lambda x: (x, Outcome.success("done")),
        }

        # Should not raise, but result won't have exit code
        result = dag_runner(
            start=node,
            transitions=transitions,
            strict=False,
        )

        # Result should exist but without proper exit
        assert result.iterations == 1

    def test_passes_context_between_nodes(self):
        """Should pass context from one node to the next."""
        from railway.core.dag.runner import Exit, dag_runner

        class ChainContext(Contract):
            from_a: bool = False
            from_b: bool = False

        def node_a() -> tuple[ChainContext, Outcome]:
            return ChainContext(from_a=True), Outcome.success("done")

        def node_b(ctx: ChainContext) -> tuple[ChainContext, Outcome]:
            assert ctx.from_a is True
            return ctx.model_copy(update={"from_b": True}), Outcome.success("done")

        transitions = {
            "node_a::success::done": node_b,
            "node_b::success::done": Exit.GREEN,
        }

        result = dag_runner(start=node_a, transitions=transitions)

        assert result.context.from_a is True
        assert result.context.from_b is True

    def test_on_step_callback(self):
        """Should call on_step callback for each step."""
        from railway.core.dag.runner import Exit, dag_runner

        class StepContext(Contract):
            value: int

        steps = []

        def step_callback(node_name: str, state_string: str, context):
            steps.append((node_name, state_string))

        def node_a() -> tuple[StepContext, Outcome]:
            return StepContext(value=1), Outcome.success("done")

        def node_b(ctx: StepContext) -> tuple[StepContext, Outcome]:
            return ctx.model_copy(update={"value": 2}), Outcome.success("done")

        transitions = {
            "node_a::success::done": node_b,
            "node_b::success::done": Exit.GREEN,
        }

        dag_runner(start=node_a, transitions=transitions, on_step=step_callback)

        assert len(steps) == 2
        assert steps[0] == ("node_a", "node_a::success::done")
        assert steps[1] == ("node_b", "node_b::success::done")


class TestDagRunnerResult:
    """Test DagRunnerResult data type."""

    def test_result_properties(self):
        """Should have expected properties."""
        from railway.core.dag.runner import DagRunnerResult, Exit

        class ResultContext(Contract):
            key: str

        result = DagRunnerResult(
            exit_code=Exit.GREEN,
            context=ResultContext(key="value"),
            iterations=3,
            execution_path=("node_a", "node_b", "node_c"),
        )

        assert result.exit_code == Exit.GREEN
        assert result.context.key == "value"
        assert result.iterations == 3
        assert len(result.execution_path) == 3

    def test_result_is_success_green(self):
        """Should return True for green exit."""
        from railway.core.dag.runner import DagRunnerResult, Exit

        class EmptyContext(Contract):
            pass

        success_result = DagRunnerResult(
            exit_code=Exit.GREEN,
            context=EmptyContext(),
            iterations=1,
            execution_path=(),
        )
        assert success_result.is_success is True

    def test_result_is_success_yellow(self):
        """Should return True for yellow exit (warning is still success)."""
        from railway.core.dag.runner import DagRunnerResult, Exit

        class EmptyContext(Contract):
            pass

        warning_result = DagRunnerResult(
            exit_code=Exit.YELLOW,
            context=EmptyContext(),
            iterations=1,
            execution_path=(),
        )
        # yellowも成功扱い（警告付き成功）
        assert warning_result.is_success is True

    def test_result_is_success_red(self):
        """Should return False for red exit."""
        from railway.core.dag.runner import DagRunnerResult, Exit

        class EmptyContext(Contract):
            pass

        failure_result = DagRunnerResult(
            exit_code=Exit.RED,
            context=EmptyContext(),
            iterations=1,
            execution_path=(),
        )
        assert failure_result.is_success is False

    def test_result_is_immutable(self):
        """DagRunnerResult should be immutable."""
        from railway.core.dag.runner import DagRunnerResult, Exit

        class EmptyContext(Contract):
            pass

        result = DagRunnerResult(
            exit_code=Exit.GREEN,
            context=EmptyContext(),
            iterations=1,
            execution_path=(),
        )

        with pytest.raises((AttributeError, TypeError)):
            result.iterations = 99


class TestExit:
    """Test Exit constant class."""

    def test_exit_green(self):
        """Should have green exit constant."""
        from railway.core.dag.runner import Exit

        assert Exit.GREEN == "exit::green::done"

    def test_exit_yellow(self):
        """Should have yellow exit constant."""
        from railway.core.dag.runner import Exit

        assert Exit.YELLOW == "exit::yellow::warning"

    def test_exit_red(self):
        """Should have red exit constant."""
        from railway.core.dag.runner import Exit

        assert Exit.RED == "exit::red::error"

    def test_exit_code_custom(self):
        """Should generate custom exit codes."""
        from railway.core.dag.runner import Exit

        custom = Exit.code("blue", "custom_detail")
        assert custom == "exit::blue::custom_detail"

    def test_exit_code_default_detail(self):
        """Should use default detail when not specified."""
        from railway.core.dag.runner import Exit

        custom = Exit.code("purple")
        assert custom == "exit::purple::done"


class TestDagRunnerWithOutcome:
    """Test dag_runner with Outcome class (string keys only)."""

    def test_workflow_with_outcome(self):
        """Should work with Outcome and string transition keys."""
        from railway.core.dag.runner import Exit, dag_runner

        class WorkflowContext(Contract):
            value: int

        def node_a() -> tuple[WorkflowContext, Outcome]:
            return WorkflowContext(value=1), Outcome.success("done")

        def node_b(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx.model_copy(update={"value": 2}), Outcome.success("complete")

        transitions = {
            "node_a::success::done": node_b,
            "node_b::success::complete": Exit.GREEN,
        }

        result = dag_runner(start=node_a, transitions=transitions)

        assert result.is_success
        assert result.context.value == 2

    def test_failure_path(self):
        """Should handle failure outcomes correctly."""
        from railway.core.dag.runner import Exit, dag_runner

        class FailContext(Contract):
            error_type: str = ""

        def check() -> tuple[FailContext, Outcome]:
            return FailContext(error_type="validation"), Outcome.failure("validation")

        def handle_error(ctx: FailContext) -> tuple[FailContext, Outcome]:
            return ctx, Outcome.success("handled")

        transitions = {
            "check::success::done": Exit.GREEN,
            "check::failure::validation": handle_error,
            "handle_error::success::handled": Exit.YELLOW,
        }

        result = dag_runner(start=check, transitions=transitions)

        assert result.exit_code == Exit.YELLOW
        assert result.context.error_type == "validation"


class TestDagRunnerAsync:
    """Test async dag_runner."""

    @pytest.mark.asyncio
    async def test_async_workflow(self):
        """Should execute async nodes."""
        from railway.core.dag.runner import Exit, async_dag_runner

        class AsyncContext(Contract):
            is_async: bool

        async def async_node() -> tuple[AsyncContext, Outcome]:
            return AsyncContext(is_async=True), Outcome.success("done")

        transitions = {
            "async_node::success::done": Exit.GREEN,
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
        from railway.core.dag.runner import Exit, async_dag_runner

        class MixedContext(Contract):
            sync_called: bool = False
            async_called: bool = False

        def sync_node() -> tuple[MixedContext, Outcome]:
            return MixedContext(sync_called=True), Outcome.success("done")

        async def async_node(ctx: MixedContext) -> tuple[MixedContext, Outcome]:
            return ctx.model_copy(update={"async_called": True}), Outcome.success("done")

        transitions = {
            "sync_node::success::done": async_node,
            "async_node::success::done": Exit.GREEN,
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
