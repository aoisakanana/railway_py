"""Tests for Outcome class and @node decorator mapping."""
import pytest


class TestOutcome:
    """Test Outcome class."""

    def test_success_outcome(self):
        """Should create success outcome."""
        from railway.core.dag.outcome import Outcome

        outcome = Outcome.success("done")

        assert outcome.is_success is True
        assert outcome.is_failure is False
        assert outcome.outcome_type == "success"
        assert outcome.detail == "done"

    def test_failure_outcome(self):
        """Should create failure outcome."""
        from railway.core.dag.outcome import Outcome

        outcome = Outcome.failure("http")

        assert outcome.is_success is False
        assert outcome.is_failure is True
        assert outcome.outcome_type == "failure"
        assert outcome.detail == "http"

    def test_outcome_to_state_string(self):
        """Should convert to state string format."""
        from railway.core.dag.outcome import Outcome

        outcome = Outcome.success("done")

        assert outcome.to_state_string("fetch_alert") == "fetch_alert::success::done"

    def test_outcome_is_immutable(self):
        """Outcome should be immutable."""
        from railway.core.dag.outcome import Outcome

        outcome = Outcome.success("done")

        with pytest.raises((AttributeError, TypeError)):
            outcome.detail = "modified"

    def test_outcome_equality(self):
        """Outcomes with same values should be equal."""
        from railway.core.dag.outcome import Outcome

        o1 = Outcome.success("done")
        o2 = Outcome.success("done")
        o3 = Outcome.failure("done")

        assert o1 == o2
        assert o1 != o3

    def test_outcome_default_detail(self):
        """Should use default detail values."""
        from railway.core.dag.outcome import Outcome

        success = Outcome.success()
        failure = Outcome.failure()

        assert success.detail == "done"
        assert failure.detail == "error"


class TestOutcomeMapping:
    """Test Outcome to State Enum mapping (internal use only)."""

    def test_map_outcome_to_state_enum(self):
        """Should map Outcome to State Enum value (internal)."""
        from railway.core.dag.outcome import Outcome, map_to_state
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            FETCH_SUCCESS_DONE = "fetch::success::done"
            FETCH_FAILURE_HTTP = "fetch::failure::http"

        outcome = Outcome.success("done")
        state = map_to_state(outcome, "fetch", MyState)

        assert state == MyState.FETCH_SUCCESS_DONE

    def test_map_failure_outcome(self):
        """Should map failure Outcome to State Enum (internal)."""
        from railway.core.dag.outcome import Outcome, map_to_state
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            FETCH_SUCCESS_DONE = "fetch::success::done"
            FETCH_FAILURE_HTTP = "fetch::failure::http"

        outcome = Outcome.failure("http")
        state = map_to_state(outcome, "fetch", MyState)

        assert state == MyState.FETCH_FAILURE_HTTP

    def test_map_unknown_outcome_raises(self):
        """Should raise error for unknown outcome (internal)."""
        from railway.core.dag.outcome import Outcome, OutcomeMappingError, map_to_state
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            FETCH_SUCCESS_DONE = "fetch::success::done"

        outcome = Outcome.failure("unknown")

        with pytest.raises(OutcomeMappingError):
            map_to_state(outcome, "fetch", MyState)


class TestNodeDecorator:
    """Test @node decorator (simple, no state_enum needed)."""

    def test_node_decorator_passes_outcome_through(self):
        """@node should pass Outcome through unchanged (dag_runner handles conversion)."""
        from railway import Contract
        from railway.core.dag.outcome import Outcome
        from railway.core.decorators import node

        class TestContext(Contract):
            value: int

        @node
        def process(ctx: TestContext) -> tuple[TestContext, Outcome]:
            return ctx, Outcome.success("done")

        result_ctx, result_outcome = process(TestContext(value=1))

        # @node returns Outcome unchanged (dag_runner converts)
        assert isinstance(result_outcome, Outcome)
        assert result_outcome.is_success
        assert result_outcome.detail == "done"

    def test_node_decorator_preserves_function_name(self):
        """@node should preserve function name for dag_runner state resolution."""
        from railway import Contract
        from railway.core.dag.outcome import Outcome
        from railway.core.decorators import node

        class Ctx(Contract):
            value: int

        @node
        def my_custom_node(ctx: Ctx) -> tuple[Ctx, Outcome]:
            return ctx, Outcome.success("ok")

        # Function name preserved for dag_runner state string generation
        assert my_custom_node.__name__ == "my_custom_node"

    def test_node_decorator_preserves_context_type(self):
        """@node should preserve Contract type in return."""
        from railway import Contract
        from railway.core.dag.outcome import Outcome
        from railway.core.decorators import node

        class InputCtx(Contract):
            input_value: str

        class OutputCtx(Contract):
            output_value: str

        @node
        def transform(ctx: InputCtx) -> tuple[OutputCtx, Outcome]:
            return OutputCtx(output_value=ctx.input_value.upper()), Outcome.success(
                "done"
            )

        result_ctx, result_outcome = transform(InputCtx(input_value="hello"))

        assert isinstance(result_ctx, OutputCtx)
        assert result_ctx.output_value == "HELLO"
        assert isinstance(result_outcome, Outcome)

    def test_node_decorator_failure_outcome(self):
        """@node should handle failure outcomes."""
        from railway import Contract
        from railway.core.dag.outcome import Outcome
        from railway.core.decorators import node

        class Ctx(Contract):
            value: int

        @node
        def may_fail(ctx: Ctx) -> tuple[Ctx, Outcome]:
            if ctx.value < 0:
                return ctx, Outcome.failure("negative")
            return ctx, Outcome.success("done")

        _, failure_outcome = may_fail(Ctx(value=-1))
        assert failure_outcome.is_failure
        assert failure_outcome.detail == "negative"

        _, success_outcome = may_fail(Ctx(value=1))
        assert success_outcome.is_success

    def test_node_decorator_marks_node(self):
        """@node should mark function as railway node."""
        from railway import Contract
        from railway.core.dag.outcome import Outcome
        from railway.core.decorators import node

        class Ctx(Contract):
            value: int

        @node
        def test_node(ctx: Ctx) -> tuple[Ctx, Outcome]:
            return ctx, Outcome.success("done")

        assert hasattr(test_node, "_is_railway_node")
        assert test_node._is_railway_node is True
        assert hasattr(test_node, "_node_name")
        assert test_node._node_name == "test_node"


class TestIsOutcome:
    """Test is_outcome helper."""

    def test_is_outcome_true(self):
        """Should return True for Outcome instances."""
        from railway.core.dag.outcome import Outcome, is_outcome

        assert is_outcome(Outcome.success("done")) is True
        assert is_outcome(Outcome.failure("error")) is True

    def test_is_outcome_false(self):
        """Should return False for non-Outcome values."""
        from railway.core.dag.outcome import is_outcome

        assert is_outcome("string") is False
        assert is_outcome(123) is False
        assert is_outcome(None) is False
        assert is_outcome({"key": "value"}) is False
