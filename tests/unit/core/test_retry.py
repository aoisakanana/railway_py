"""Tests for retry functionality."""

import pytest
from unittest.mock import patch, MagicMock


class TestNodeRetry:
    """Test @node decorator retry functionality."""

    def test_node_with_retry_enabled(self):
        """Should retry on failure when retry=True."""
        from railway.core.decorators import node

        call_count = 0

        @node(retry=True)
        def flaky_node() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.config.get_retry_config") as mock_config:
                mock_settings = MagicMock()
                mock_settings.max_attempts = 5
                mock_settings.min_wait = 0.01
                mock_settings.max_wait = 0.02
                mock_settings.multiplier = 1
                mock_config.return_value = mock_settings

                result = flaky_node()

        assert result == "success"
        assert call_count == 3

    def test_node_retry_exhausted(self):
        """Should raise exception after max retries."""
        from railway.core.decorators import node

        call_count = 0

        @node(retry=True)
        def always_fails() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.config.get_retry_config") as mock_config:
                mock_settings = MagicMock()
                mock_settings.max_attempts = 3
                mock_settings.min_wait = 0.01
                mock_settings.max_wait = 0.02
                mock_settings.multiplier = 1
                mock_config.return_value = mock_settings

                with pytest.raises(ValueError, match="Always fails"):
                    always_fails()

        assert call_count == 3

    def test_node_retry_false(self):
        """Should not retry when retry=False."""
        from railway.core.decorators import node

        call_count = 0

        @node(retry=False)
        def no_retry_node() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("Fails")

        with patch("railway.core.decorators.logger"):
            with pytest.raises(ValueError):
                no_retry_node()

        assert call_count == 1

    def test_node_custom_retry_config(self):
        """Should use custom Retry configuration."""
        from railway.core.decorators import node, Retry

        call_count = 0

        @node(retry=Retry(max_attempts=5, min_wait=0.01, max_wait=0.02))
        def custom_retry_node() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise ValueError("Temp failure")
            return "done"

        with patch("railway.core.decorators.logger"):
            result = custom_retry_node()

        assert result == "done"
        assert call_count == 4


class TestRetryLogging:
    """Test retry logging."""

    def test_retry_logs_attempts(self):
        """Should log retry attempts."""
        from railway.core.decorators import node

        call_count = 0

        @node(retry=True)
        def retry_with_log() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temp")
            return "ok"

        with patch("railway.core.decorators.logger") as mock_logger:
            with patch("railway.core.config.get_retry_config") as mock_config:
                mock_settings = MagicMock()
                mock_settings.max_attempts = 3
                mock_settings.min_wait = 0.01
                mock_settings.max_wait = 0.02
                mock_settings.multiplier = 1
                mock_config.return_value = mock_settings

                retry_with_log()

        # Should have warning for retry attempt
        warning_calls = [str(c) for c in mock_logger.warning.call_args_list]
        assert any("リトライ" in str(c) or "retry" in str(c).lower() for c in warning_calls)


class TestRetryWithSettings:
    """Test retry with settings integration."""

    def test_retry_uses_node_specific_settings(self):
        """Should use node-specific retry settings."""
        from railway.core.decorators import node

        call_count = 0

        @node(retry=True, name="special_node")
        def special_node() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temp")
            return "done"

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.config.get_retry_config") as mock_config:
                mock_settings = MagicMock()
                mock_settings.max_attempts = 5
                mock_settings.min_wait = 0.01
                mock_settings.max_wait = 0.02
                mock_settings.multiplier = 1
                mock_config.return_value = mock_settings

                special_node()

                # Should be called with node name
                mock_config.assert_called_with("special_node")


class TestRetrySuccessWithoutRetries:
    """Test retry when no retries needed."""

    def test_node_with_retry_success_first_attempt(self):
        """Should succeed on first attempt without retrying."""
        from railway.core.decorators import node

        call_count = 0

        @node(retry=True)
        def success_node() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.config.get_retry_config") as mock_config:
                mock_settings = MagicMock()
                mock_settings.max_attempts = 3
                mock_settings.min_wait = 0.01
                mock_settings.max_wait = 0.02
                mock_settings.multiplier = 1
                mock_config.return_value = mock_settings

                result = success_node()

        assert result == "success"
        assert call_count == 1
