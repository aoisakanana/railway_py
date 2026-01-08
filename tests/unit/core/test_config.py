"""Tests for configuration provider registry."""

from unittest.mock import Mock


class TestSettingsProviderRegistry:
    """Test settings provider registration and retrieval."""

    def test_initial_provider_is_none(self):
        """Provider should be None initially."""
        from railway.core import config
        from railway.core.config import get_settings_provider

        # Reset state first
        config._settings_provider = None

        assert get_settings_provider() is None

    def test_register_settings_provider(self):
        """Should be able to register a settings provider."""
        from railway.core import config
        from railway.core.config import (
            get_settings_provider,
            register_settings_provider,
        )

        config._settings_provider = None

        mock_provider = Mock(return_value={"key": "value"})
        register_settings_provider(mock_provider)

        assert get_settings_provider() is mock_provider

    def test_get_retry_config_without_provider(self):
        """Should return default settings when no provider."""
        from railway.core import config
        from railway.core.config import get_retry_config

        config._settings_provider = None

        retry_config = get_retry_config("test_node")

        assert retry_config.max_attempts == 3
        assert retry_config.min_wait == 2
        assert retry_config.max_wait == 10
        assert retry_config.multiplier == 1

    def test_get_retry_config_with_provider(self):
        """Should use provider settings when registered."""
        from railway.core import config
        from railway.core.config import (
            get_retry_config,
            register_settings_provider,
        )

        config._settings_provider = None

        # Create mock settings with get_retry_settings method
        mock_settings = Mock()
        mock_retry = Mock()
        mock_retry.max_attempts = 5
        mock_retry.min_wait = 1
        mock_retry.max_wait = 30
        mock_retry.multiplier = 2
        mock_settings.get_retry_settings.return_value = mock_retry

        register_settings_provider(lambda: mock_settings)

        retry_config = get_retry_config("fetch_data")

        assert retry_config.max_attempts == 5
        mock_settings.get_retry_settings.assert_called_once_with("fetch_data")

    def test_get_retry_config_provider_error(self):
        """Should return default when provider raises exception."""
        from railway.core import config
        from railway.core.config import (
            get_retry_config,
            register_settings_provider,
        )

        config._settings_provider = None

        def failing_provider():
            raise RuntimeError("Config error")

        register_settings_provider(failing_provider)

        retry_config = get_retry_config("test_node")

        # Should fallback to defaults
        assert retry_config.max_attempts == 3


class TestDefaultRetrySettings:
    """Test default retry settings."""

    def test_default_values(self):
        """Should have correct default values."""
        from railway.core.config import DefaultRetrySettings

        settings = DefaultRetrySettings()

        assert settings.max_attempts == 3
        assert settings.min_wait == 2
        assert settings.max_wait == 10
        assert settings.multiplier == 1


class TestResetProvider:
    """Test reset_provider function."""

    def test_reset_clears_provider(self):
        """reset_provider should clear the registered provider."""
        from railway.core.config import (
            get_settings_provider,
            register_settings_provider,
            reset_provider,
        )

        mock_provider = Mock()
        register_settings_provider(mock_provider)
        assert get_settings_provider() is not None

        reset_provider()

        assert get_settings_provider() is None
