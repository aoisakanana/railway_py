"""Tests for on_step callback in typed_pipeline."""

import pytest
from dataclasses import dataclass
from typing import Any
from unittest.mock import patch


@dataclass(frozen=True)
class StepRecord:
    """Immutable step record for capturing callback data."""

    name: str
    output: Any


class TestOnStepCallback:
    """Test on_step callback functionality."""

    def test_callback_receives_step_name_and_output(self):
        """on_step callback should receive step name and output."""
        from railway import node, typed_pipeline
        from railway.core.contract import Contract

        captured: list[StepRecord] = []

        def capture(name: str, output: Any) -> None:
            captured.append(StepRecord(name=name, output=output))

        class Step1Result(Contract):
            value: int

        class Step2Result(Contract):
            value: int

        @node
        def step1() -> Step1Result:
            return Step1Result(value=1)

        @node
        def step2(prev: Step1Result) -> Step2Result:
            return Step2Result(value=prev.value + 1)

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.resolver.logger"):
                result = typed_pipeline(step1, step2, on_step=capture)

        assert result.value == 2
        assert len(captured) == 2
        assert captured[0].name == "step1"
        assert captured[0].output.value == 1
        assert captured[1].name == "step2"
        assert captured[1].output.value == 2

    def test_no_callback_when_not_specified(self):
        """Should work normally without on_step callback."""
        from railway import node, typed_pipeline
        from railway.core.contract import Contract

        class StepResult(Contract):
            value: int

        @node
        def step1() -> StepResult:
            return StepResult(value=1)

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.resolver.logger"):
                result = typed_pipeline(step1)

        assert result.value == 1


class TestOnStepWithOnError:
    """Test on_step callback combined with on_error."""

    def test_callback_with_on_error_fallback(self):
        """on_step should receive fallback value when on_error returns value."""
        from railway import node, typed_pipeline
        from railway.core.contract import Contract

        captured: list[StepRecord] = []

        def capture(name: str, output: Any) -> None:
            captured.append(StepRecord(name=name, output=output))

        class FallbackResult(Contract):
            value: int

        def handle_error(error: Exception, step: str) -> FallbackResult:
            return FallbackResult(value=99)

        @node
        def fail_step() -> int:
            raise ConnectionError("network error")

        @node
        def next_step(prev: FallbackResult) -> int:
            return prev.value * 2

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.resolver.logger"):
                result = typed_pipeline(
                    fail_step,
                    next_step,
                    on_step=capture,
                    on_error=handle_error,
                )

        assert result == 198  # 99 * 2
        # Fallback value should be recorded
        assert captured[0].name == "fail_step"
        assert captured[0].output.value == 99
        assert captured[1] == StepRecord(name="next_step", output=198)

    def test_callback_when_exception_propagates(self):
        """Only completed steps should be recorded when error propagates."""
        from railway import node, typed_pipeline
        from railway.core.contract import Contract

        captured: list[StepRecord] = []

        def capture(name: str, output: Any) -> None:
            captured.append(StepRecord(name=name, output=output))

        class IntResult(Contract):
            value: int

        def handle_error(error: Exception, step: str) -> Any:
            raise  # Re-raise

        @node
        def step1() -> IntResult:
            return IntResult(value=1)

        @node
        def fail_step(prev: IntResult) -> IntResult:
            raise ValueError("validation error")

        @node
        def step3(prev: IntResult) -> IntResult:
            return IntResult(value=prev.value * 3)

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.resolver.logger"):
                with pytest.raises(ValueError, match="validation error"):
                    typed_pipeline(
                        step1,
                        fail_step,
                        step3,
                        on_step=capture,
                        on_error=handle_error,
                    )

        # Only step1 result should be recorded
        assert len(captured) == 1
        assert captured[0].name == "step1"
        assert captured[0].output.value == 1


class TestOnStepPracticalUsage:
    """Test practical usage patterns for on_step."""

    def test_callback_for_logging(self):
        """Practical example: logging each step."""
        import io

        from railway import node, typed_pipeline
        from railway.core.contract import Contract

        log_output = io.StringIO()

        def log_step(name: str, output: Any) -> None:
            print(f"[{name}] -> {output}", file=log_output)

        class FetchResult(Contract):
            count: int

        class ProcessResult(Contract):
            message: str

        @node
        def fetch() -> FetchResult:
            return FetchResult(count=5)

        @node
        def process(data: FetchResult) -> ProcessResult:
            return ProcessResult(message=f"Processed {data.count} items")

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.resolver.logger"):
                typed_pipeline(fetch, process, on_step=log_step)

        log_content = log_output.getvalue()
        assert "[fetch]" in log_content
        assert "[process]" in log_content

    def test_callback_for_metrics(self):
        """Practical example: collecting metrics."""
        from railway import node, typed_pipeline
        from railway.core.contract import Contract

        metrics: dict[str, Any] = {}

        def collect_metrics(name: str, output: Any) -> None:
            metrics[name] = {
                "output_type": type(output).__name__,
                "has_output": output is not None,
            }

        class DataResult(Contract):
            data: list[int]

        @node
        def generate_data() -> DataResult:
            return DataResult(data=[1, 2, 3])

        @node
        def aggregate(prev: DataResult) -> int:
            return sum(prev.data)

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.resolver.logger"):
                typed_pipeline(generate_data, aggregate, on_step=collect_metrics)

        assert "generate_data" in metrics
        assert metrics["generate_data"]["output_type"] == "DataResult"
        assert "aggregate" in metrics
        assert metrics["aggregate"]["has_output"] is True
