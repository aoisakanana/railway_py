"""Tests for pipeline() function."""

from unittest.mock import patch

import pytest


class TestPipelineBasic:
    """Test basic pipeline functionality."""

    def test_pipeline_single_step(self):
        """Should execute single step pipeline."""
        from railway.core.pipeline import pipeline

        def add_one(x: int) -> int:
            return x + 1

        result = pipeline(5, add_one)
        assert result == 6

    def test_pipeline_multiple_steps(self):
        """Should execute multiple steps sequentially."""
        from railway.core.pipeline import pipeline

        def add_one(x: int) -> int:
            return x + 1

        def multiply_two(x: int) -> int:
            return x * 2

        result = pipeline(5, add_one, multiply_two)
        assert result == 12  # (5 + 1) * 2

    def test_pipeline_with_initial_value(self):
        """Should use initial value correctly."""
        from railway.core.pipeline import pipeline

        def to_upper(s: str) -> str:
            return s.upper()

        result = pipeline("hello", to_upper)
        assert result == "HELLO"

    def test_pipeline_empty_steps(self):
        """Should return initial value when no steps."""
        from railway.core.pipeline import pipeline

        result = pipeline(42)
        assert result == 42

    def test_pipeline_passes_result_to_next_step(self):
        """Should pass each step's result to the next."""
        from railway.core.pipeline import pipeline

        call_order = []

        def step1(x: int) -> dict:
            call_order.append(("step1", x))
            return {"value": x * 2}

        def step2(data: dict) -> str:
            call_order.append(("step2", data))
            return f"Result: {data['value']}"

        result = pipeline(5, step1, step2)

        assert result == "Result: 10"
        assert call_order == [("step1", 5), ("step2", {"value": 10})]


class TestPipelineErrorHandling:
    """Test pipeline error handling."""

    def test_pipeline_stops_on_error(self):
        """Should stop execution when step raises exception."""
        from railway.core.pipeline import pipeline

        call_count = {"step2": 0, "step3": 0}

        def step1(x: int) -> int:
            return x + 1

        def step2(x: int) -> int:
            call_count["step2"] += 1
            raise ValueError("Step 2 failed")

        def step3(x: int) -> int:
            call_count["step3"] += 1
            return x * 2

        with pytest.raises(ValueError, match="Step 2 failed"):
            pipeline(5, step1, step2, step3)

        assert call_count["step2"] == 1
        assert call_count["step3"] == 0  # Never called

    def test_pipeline_propagates_exception(self):
        """Should propagate the original exception."""
        from railway.core.pipeline import pipeline

        class CustomError(Exception):
            pass

        def failing_step(x: int) -> int:
            raise CustomError("Custom error message")

        with pytest.raises(CustomError, match="Custom error message"):
            pipeline(1, failing_step)


class TestPipelineWithNodes:
    """Test pipeline with @node decorated functions."""

    def test_pipeline_with_node_functions(self):
        """Should work with @node decorated functions."""
        from railway.core.decorators import node
        from railway.core.pipeline import pipeline

        @node
        def fetch(x: int) -> dict:
            return {"value": x}

        @node
        def process(data: dict) -> str:
            return str(data["value"])

        with patch("railway.core.decorators.logger"):
            result = pipeline(42, fetch, process)

        assert result == "42"

    def test_pipeline_uses_node_name(self):
        """Should use node name from metadata."""
        from railway.core.decorators import node
        from railway.core.pipeline import pipeline

        @node(name="custom_fetch")
        def fetch(x: int) -> int:
            return x + 1

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger") as mock_logger:
                pipeline(1, fetch)

                # Should log with node name
                debug_calls = str(mock_logger.debug.call_args_list)
                assert "custom_fetch" in debug_calls or "fetch" in debug_calls


class TestPipelineLogging:
    """Test pipeline logging."""

    def test_pipeline_logs_start(self):
        """Should log pipeline start (日本語)."""
        from railway.core.pipeline import pipeline

        with patch("railway.core.pipeline.logger") as mock_logger:
            pipeline(1, lambda x: x)

            debug_calls = str(mock_logger.debug.call_args_list)
            assert "開始" in debug_calls

    def test_pipeline_logs_step_execution(self):
        """Should log each step execution."""
        from railway.core.pipeline import pipeline

        def step1(x: int) -> int:
            return x + 1

        def step2(x: int) -> int:
            return x * 2

        with patch("railway.core.pipeline.logger") as mock_logger:
            pipeline(1, step1, step2)

            # Should log step progress
            debug_calls = str(mock_logger.debug.call_args_list)
            assert "1" in debug_calls and "2" in debug_calls

    def test_pipeline_logs_completion(self):
        """Should log pipeline completion (日本語)."""
        from railway.core.pipeline import pipeline

        with patch("railway.core.pipeline.logger") as mock_logger:
            pipeline(1, lambda x: x)

            debug_calls = str(mock_logger.debug.call_args_list)
            assert "完了" in debug_calls

    def test_pipeline_logs_error(self):
        """Should log error when step fails."""
        from railway.core.pipeline import pipeline

        def failing_step(x: int) -> int:
            raise ValueError("Test error")

        with patch("railway.core.pipeline.logger") as mock_logger:
            with pytest.raises(ValueError):
                pipeline(1, failing_step)

            mock_logger.error.assert_called()


class TestPipelineAsyncRejection:
    """Test that async functions are rejected."""

    def test_rejects_async_function(self):
        """Should reject async functions with clear error."""
        from railway.core.pipeline import pipeline

        async def async_step(x: int) -> int:
            return x + 1

        with pytest.raises(TypeError) as exc_info:
            pipeline(1, async_step)

        error_msg = str(exc_info.value)
        assert "async" in error_msg.lower()
        assert "async_step" in error_msg

    def test_rejects_async_node(self):
        """Should reject async @node functions."""
        from railway.core.decorators import node
        from railway.core.pipeline import pipeline

        @node
        async def async_node(x: int) -> int:
            return x + 1

        with pytest.raises(TypeError) as exc_info:
            pipeline(1, async_node)

        assert "async" in str(exc_info.value).lower()


class TestPipelineTypeCheck:
    """Test pipeline type checking (default enabled)."""

    def test_type_check_enabled_by_default(self):
        """Type check should be enabled by default."""
        import inspect

        from railway.core.pipeline import pipeline

        sig = inspect.signature(pipeline)
        type_check_param = sig.parameters.get("type_check")

        assert type_check_param is not None
        assert type_check_param.default is True

    def test_type_check_can_be_disabled(self):
        """Should allow disabling type check."""
        from railway.core.pipeline import pipeline

        def returns_str(x: int) -> str:
            return str(x)

        # With type_check=False, this should run (may fail at runtime)
        # but the pipeline itself shouldn't raise TypeError
        result = pipeline(1, returns_str, type_check=False)
        assert result == "1"
