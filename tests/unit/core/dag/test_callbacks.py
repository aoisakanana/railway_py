"""Tests for step callbacks with Contract + Outcome (v0.12.3 ExitContract 強制)."""
import pytest

from railway import Contract, ExitContract
from railway.core.dag.outcome import Outcome


class TestOnStepCallback:
    """Test on_step callback functionality with Contract context."""

    def test_callback_called_for_each_step(self):
        """Should call callback for each node execution."""
        from railway.core.dag.runner import dag_runner
        from railway.core.decorators import node

        class StepContext(Contract):
            step: int

        class StepResult(ExitContract):
            exit_state: str = "success.done"
            step: int

        @node
        def node_a() -> tuple[StepContext, Outcome]:
            return StepContext(step=1), Outcome.success("done")

        @node
        def node_b(ctx: StepContext) -> tuple[StepContext, Outcome]:
            return StepContext(step=2), Outcome.success("done")

        def exit_success_done(ctx: StepContext) -> StepResult:
            return StepResult(step=ctx.step)

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "node_a::success::done": node_b,
            "node_b::success::done": exit_success_done,
        }

        callback_log = []

        def on_step(node_name: str, state_string: str, context: Contract):
            callback_log.append(
                {
                    "node": node_name,
                    "state": state_string,
                    "context": context.model_dump() if hasattr(context, "model_dump") else context,
                }
            )

        dag_runner(start=node_a, transitions=transitions, on_step=on_step)

        assert len(callback_log) == 3  # node_a + node_b + exit
        assert callback_log[0]["node"] == "node_a"
        assert callback_log[0]["state"] == "node_a::success::done"
        assert callback_log[1]["node"] == "node_b"

    def test_callback_receives_context(self):
        """Should pass current context to callback."""
        from railway.core.dag.runner import dag_runner
        from railway.core.decorators import node

        class KeyContext(Contract):
            key: str

        class KeyResult(ExitContract):
            exit_state: str = "success.done"
            key: str

        @node
        def node_a() -> tuple[KeyContext, Outcome]:
            return KeyContext(key="value"), Outcome.success("done")

        def exit_success_done(ctx: KeyContext) -> KeyResult:
            return KeyResult(key=ctx.key)

        exit_success_done._node_name = "exit.success.done"

        transitions = {"node_a::success::done": exit_success_done}

        received_context = {}

        def on_step(node_name: str, state_string: str, context: Contract):
            if hasattr(context, "model_dump"):
                received_context.update(context.model_dump())

        dag_runner(start=node_a, transitions=transitions, on_step=on_step)

        assert received_context["key"] == "value"


class TestStepRecorder:
    """Test built-in StepRecorder callback with Contract context."""

    def test_records_execution_history(self):
        """Should record complete execution history."""
        from railway.core.dag.callbacks import StepRecorder
        from railway.core.dag.runner import dag_runner
        from railway.core.decorators import node

        class EmptyContext(Contract):
            pass

        class DoneResult(ExitContract):
            exit_state: str = "success.done"

        @node
        def start() -> tuple[EmptyContext, Outcome]:
            return EmptyContext(), Outcome.success("done")

        def exit_success_done(ctx: EmptyContext) -> DoneResult:
            return DoneResult()

        exit_success_done._node_name = "exit.success.done"

        recorder = StepRecorder()

        dag_runner(
            start=start,
            transitions={"start::success::done": exit_success_done},
            on_step=recorder,
        )

        history = recorder.get_history()
        assert len(history) >= 1
        assert history[0].node_name == "start"

    def test_recorder_timestamps(self):
        """Should record timestamps for each step."""
        from railway.core.dag.callbacks import StepRecorder
        from railway.core.dag.runner import dag_runner
        from railway.core.decorators import node

        class EmptyContext(Contract):
            pass

        class DoneResult(ExitContract):
            exit_state: str = "success.done"

        @node
        def start() -> tuple[EmptyContext, Outcome]:
            return EmptyContext(), Outcome.success("done")

        def exit_success_done(ctx: EmptyContext) -> DoneResult:
            return DoneResult()

        exit_success_done._node_name = "exit.success.done"

        recorder = StepRecorder()

        dag_runner(
            start=start,
            transitions={"start::success::done": exit_success_done},
            on_step=recorder,
        )

        history = recorder.get_history()
        assert history[0].timestamp is not None

    def test_recorder_to_dict(self):
        """Should export history as dict for serialization."""
        from railway.core.dag.callbacks import StepRecorder
        from railway.core.dag.runner import dag_runner
        from railway.core.decorators import node

        class DataContext(Contract):
            x: int

        class DataResult(ExitContract):
            exit_state: str = "success.done"
            x: int

        @node
        def start() -> tuple[DataContext, Outcome]:
            return DataContext(x=1), Outcome.success("done")

        def exit_success_done(ctx: DataContext) -> DataResult:
            return DataResult(x=ctx.x)

        exit_success_done._node_name = "exit.success.done"

        recorder = StepRecorder()

        dag_runner(
            start=start,
            transitions={"start::success::done": exit_success_done},
            on_step=recorder,
        )

        data = recorder.to_dict()
        assert "steps" in data
        assert len(data["steps"]) >= 1

    def test_recorder_clear(self):
        """Should be able to clear history."""
        from railway.core.dag.callbacks import StepRecorder
        from railway.core.dag.runner import dag_runner
        from railway.core.decorators import node

        class EmptyContext(Contract):
            pass

        class DoneResult(ExitContract):
            exit_state: str = "success.done"

        @node
        def start() -> tuple[EmptyContext, Outcome]:
            return EmptyContext(), Outcome.success("done")

        def exit_success_done(ctx: EmptyContext) -> DoneResult:
            return DoneResult()

        exit_success_done._node_name = "exit.success.done"

        recorder = StepRecorder()

        dag_runner(
            start=start,
            transitions={"start::success::done": exit_success_done},
            on_step=recorder,
        )

        assert len(recorder.get_history()) >= 1

        recorder.clear()

        assert len(recorder.get_history()) == 0


class TestStepRecord:
    """Test StepRecord dataclass."""

    def test_step_record_is_immutable(self):
        """StepRecord should be immutable."""
        from datetime import datetime

        from railway.core.dag.callbacks import StepRecord

        record = StepRecord(
            node_name="test",
            state="test::success::done",
            context_snapshot={"key": "value"},
            timestamp=datetime.now(),
        )

        with pytest.raises((AttributeError, TypeError)):
            record.node_name = "modified"

    def test_step_record_to_dict(self):
        """Should convert to serializable dict."""
        from datetime import datetime

        from railway.core.dag.callbacks import StepRecord

        now = datetime.now()
        record = StepRecord(
            node_name="test",
            state="test::success::done",
            context_snapshot={"key": "value"},
            timestamp=now,
        )

        data = record.to_dict()
        assert data["node_name"] == "test"
        assert data["state"] == "test::success::done"
        assert data["context"] == {"key": "value"}
        assert data["timestamp"] == now.isoformat()


class TestAuditLogger:
    """Test audit logging callback."""

    def test_logs_to_loguru(self):
        """Should log steps to loguru."""
        from unittest.mock import patch

        from railway.core.dag.callbacks import AuditLogger
        from railway.core.dag.runner import dag_runner
        from railway.core.decorators import node

        class EmptyContext(Contract):
            pass

        class DoneResult(ExitContract):
            exit_state: str = "success.done"

        @node
        def start() -> tuple[EmptyContext, Outcome]:
            return EmptyContext(), Outcome.success("done")

        def exit_success_done(ctx: EmptyContext) -> DoneResult:
            return DoneResult()

        exit_success_done._node_name = "exit.success.done"

        with patch("railway.core.dag.callbacks.logger") as mock_logger:
            audit = AuditLogger(workflow_id="test-123")

            dag_runner(
                start=start,
                transitions={"start::success::done": exit_success_done},
                on_step=audit,
            )

            mock_logger.info.assert_called()

    def test_default_workflow_id(self):
        """Should use 'unknown' as default workflow_id."""
        from railway.core.dag.callbacks import AuditLogger

        audit = AuditLogger()
        assert audit.workflow_id == "unknown"


class TestCompositeCallback:
    """Test composite callback."""

    def test_calls_all_callbacks(self):
        """Should call all registered callbacks."""
        from railway.core.dag.callbacks import CompositeCallback, StepRecorder
        from railway.core.dag.runner import dag_runner
        from railway.core.decorators import node

        class EmptyContext(Contract):
            pass

        class DoneResult(ExitContract):
            exit_state: str = "success.done"

        @node
        def start() -> tuple[EmptyContext, Outcome]:
            return EmptyContext(), Outcome.success("done")

        def exit_success_done(ctx: EmptyContext) -> DoneResult:
            return DoneResult()

        exit_success_done._node_name = "exit.success.done"

        recorder1 = StepRecorder()
        recorder2 = StepRecorder()
        composite = CompositeCallback(recorder1, recorder2)

        dag_runner(
            start=start,
            transitions={"start::success::done": exit_success_done},
            on_step=composite,
        )

        assert len(recorder1.get_history()) >= 1
        assert len(recorder2.get_history()) >= 1

    def test_works_with_function_callbacks(self):
        """Should work with simple function callbacks."""
        from railway.core.dag.callbacks import CompositeCallback
        from railway.core.dag.runner import dag_runner
        from railway.core.decorators import node

        class EmptyContext(Contract):
            pass

        class DoneResult(ExitContract):
            exit_state: str = "success.done"

        @node
        def start() -> tuple[EmptyContext, Outcome]:
            return EmptyContext(), Outcome.success("done")

        def exit_success_done(ctx: EmptyContext) -> DoneResult:
            return DoneResult()

        exit_success_done._node_name = "exit.success.done"

        log1 = []
        log2 = []

        def callback1(node_name, state_string, context):
            log1.append(node_name)

        def callback2(node_name, state_string, context):
            log2.append(node_name)

        composite = CompositeCallback(callback1, callback2)

        dag_runner(
            start=start,
            transitions={"start::success::done": exit_success_done},
            on_step=composite,
        )

        assert "start" in log1
        assert "start" in log2
