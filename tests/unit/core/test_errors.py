"""Tests for custom error types."""

import pytest


class TestRailwayError:
    """Test base RailwayError."""

    def test_railway_error_is_exception(self):
        """Should be an Exception subclass."""
        from railway.core.errors import RailwayError

        assert issubclass(RailwayError, Exception)

    def test_railway_error_has_message(self):
        """Should store message."""
        from railway.core.errors import RailwayError

        error = RailwayError("Test error")
        assert str(error) == "Test error"

    def test_railway_error_has_code(self):
        """Should have error code."""
        from railway.core.errors import RailwayError

        error = RailwayError("Test", code="E001")
        assert error.code == "E001"

    def test_railway_error_has_hint(self):
        """Should have hint message."""
        from railway.core.errors import RailwayError

        error = RailwayError("Test", hint="Try doing X")
        assert error.hint == "Try doing X"


class TestConfigurationError:
    """Test ConfigurationError."""

    def test_config_error_is_railway_error(self):
        """Should be RailwayError subclass."""
        from railway.core.errors import ConfigurationError, RailwayError

        assert issubclass(ConfigurationError, RailwayError)

    def test_config_error_not_retryable(self):
        """Configuration errors should not be retryable."""
        from railway.core.errors import ConfigurationError

        error = ConfigurationError("Missing config")
        assert error.retryable is False

    def test_config_error_has_default_hint(self):
        """Should have default hint for config errors."""
        from railway.core.errors import ConfigurationError

        error = ConfigurationError("Missing API key")
        assert error.hint is not None
        assert "config" in error.hint.lower() or "設定" in error.hint


class TestNodeError:
    """Test NodeError."""

    def test_node_error_stores_node_name(self):
        """Should store node name."""
        from railway.core.errors import NodeError

        error = NodeError("Failed", node_name="fetch_data")
        assert error.node_name == "fetch_data"

    def test_node_error_stores_original_error(self):
        """Should store original exception."""
        from railway.core.errors import NodeError

        original = ValueError("Original")
        error = NodeError("Wrapped", original_error=original)
        assert error.original_error is original

    def test_node_error_retryable_by_default(self):
        """Node errors should be retryable by default."""
        from railway.core.errors import NodeError

        error = NodeError("Temporary failure")
        assert error.retryable is True


class TestPipelineError:
    """Test PipelineError."""

    def test_pipeline_error_stores_step_info(self):
        """Should store step information."""
        from railway.core.errors import PipelineError

        error = PipelineError(
            "Pipeline failed",
            step_number=3,
            step_name="process_data",
            total_steps=5,
        )
        assert error.step_number == 3
        assert error.step_name == "process_data"
        assert error.total_steps == 5

    def test_pipeline_error_shows_remaining_steps(self):
        """Should show remaining steps count."""
        from railway.core.errors import PipelineError

        error = PipelineError(
            "Failed", step_number=2, step_name="step2", total_steps=5
        )
        assert error.remaining_steps == 3


class TestNetworkError:
    """Test NetworkError."""

    def test_network_error_is_retryable(self):
        """Network errors should be retryable."""
        from railway.core.errors import NetworkError

        error = NetworkError("Connection failed")
        assert error.retryable is True

    def test_network_error_has_network_hint(self):
        """Should have network-related hint."""
        from railway.core.errors import NetworkError

        error = NetworkError("Timeout")
        assert "ネットワーク" in error.hint or "network" in error.hint.lower()


class TestValidationError:
    """Test ValidationError."""

    def test_validation_error_not_retryable(self):
        """Validation errors should not be retryable."""
        from railway.core.errors import ValidationError

        error = ValidationError("Invalid input")
        assert error.retryable is False

    def test_validation_error_stores_field(self):
        """Should store field name."""
        from railway.core.errors import ValidationError

        error = ValidationError("Invalid", field="email")
        assert error.field == "email"


class TestErrorHierarchy:
    """Test error hierarchy relationships."""

    def test_all_errors_are_railway_errors(self):
        """All custom errors should be RailwayError subclass."""
        from railway.core.errors import (
            ConfigurationError,
            NetworkError,
            NodeError,
            PipelineError,
            RailwayError,
            ValidationError,
        )

        for error_class in [
            ConfigurationError,
            NodeError,
            PipelineError,
            NetworkError,
            ValidationError,
        ]:
            assert issubclass(error_class, RailwayError)

    def test_errors_catchable_as_railway_error(self):
        """Should be catchable as RailwayError."""
        from railway.core.errors import (
            ConfigurationError,
            NodeError,
            RailwayError,
        )

        with pytest.raises(RailwayError):
            raise ConfigurationError("Test")

        with pytest.raises(RailwayError):
            raise NodeError("Test")


class TestErrorFormatting:
    """Test error message formatting."""

    def test_error_full_message(self):
        """Should format full error message with all details."""
        from railway.core.errors import NodeError

        error = NodeError(
            "Processing failed",
            node_name="process_data",
            code="E100",
            hint="Check input data format",
        )

        full_msg = error.full_message()
        assert "E100" in full_msg
        assert "process_data" in full_msg
        assert "Processing failed" in full_msg
        assert "Check input data format" in full_msg

    def test_error_to_dict(self):
        """Should convert to dictionary."""
        from railway.core.errors import PipelineError

        error = PipelineError(
            "Step failed",
            step_number=2,
            step_name="step2",
            total_steps=5,
            code="P001",
        )

        d = error.to_dict()
        assert d["message"] == "Step failed"
        assert d["code"] == "P001"
        assert d["step_number"] == 2
        assert d["step_name"] == "step2"
