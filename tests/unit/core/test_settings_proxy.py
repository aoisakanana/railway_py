"""Tests for _SettingsProxy lazy initialization."""

import threading

import pytest
from unittest.mock import MagicMock, patch


class TestSettingsProxyLazyInit:
    """Test _SettingsProxy lazy initialization."""

    def test_attribute_access_triggers_load(self):
        """Should load settings on first attribute access."""
        from railway.core.config import _SettingsProxy, reset_settings

        reset_settings()
        proxy = _SettingsProxy()

        with patch("railway.core.config._get_or_create_settings") as mock_get:
            mock_settings = MagicMock()
            mock_settings.api = MagicMock(base_url="https://api.example.com")
            mock_get.return_value = mock_settings

            # Access attribute
            url = proxy.api.base_url

            # Should have called _get_or_create_settings
            mock_get.assert_called()
            assert url == "https://api.example.com"


class TestSettingsProxyBehavior:
    """Test _SettingsProxy behavior matches real settings."""

    def test_proxy_delegates_getattr(self):
        """Should delegate __getattr__ to underlying settings."""
        from railway.core.config import _SettingsProxy, reset_settings

        reset_settings()
        proxy = _SettingsProxy()

        with patch("railway.core.config._get_or_create_settings") as mock_get:
            mock_settings = MagicMock()
            mock_settings.database = MagicMock(host="localhost", port=5432)
            mock_get.return_value = mock_settings

            host = proxy.database.host
            port = proxy.database.port

            assert host == "localhost"
            assert port == 5432

    def test_proxy_supports_nested_access(self):
        """Should support nested attribute access."""
        from railway.core.config import _SettingsProxy, reset_settings

        reset_settings()
        proxy = _SettingsProxy()

        with patch("railway.core.config._get_or_create_settings") as mock_get:
            mock_settings = MagicMock()
            mock_settings.api.auth.token = "secret123"
            mock_get.return_value = mock_settings

            token = proxy.api.auth.token
            assert token == "secret123"


class TestSettingsProxyThread:
    """Test _SettingsProxy thread safety."""

    def test_proxy_thread_safe_init(self):
        """Should be thread-safe during initialization."""
        from railway.core.config import _SettingsProxy, reset_settings

        reset_settings()
        proxy = _SettingsProxy()
        results = []
        errors = []

        def access_settings():
            try:
                with patch("railway.core.config._get_or_create_settings") as mock_get:
                    mock_settings = MagicMock()
                    mock_settings.value = threading.current_thread().name
                    mock_get.return_value = mock_settings

                    value = proxy.value
                    results.append(value)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=access_settings) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 10


class TestSettingsProxyReset:
    """Test _SettingsProxy reset functionality."""

    def test_reset_clears_cache(self):
        """Should clear cache on reset."""
        from railway.core.config import reset_settings

        # Reset should not raise
        reset_settings()


class TestSettingsProviderIntegration:
    """Test _SettingsProxy with settings provider."""

    def test_proxy_uses_registered_provider(self):
        """Should use registered settings provider."""
        from railway.core.config import (
            _SettingsProxy,
            register_settings_provider,
            reset_settings,
        )

        reset_settings()

        # Register custom provider
        custom_settings = MagicMock()
        custom_settings.custom_value = "from_provider"
        register_settings_provider(lambda: custom_settings)

        proxy = _SettingsProxy()
        value = proxy.custom_value

        assert value == "from_provider"
        reset_settings()


class TestSettingsProxyRepr:
    """Test _SettingsProxy representation."""

    def test_proxy_repr(self):
        """Should have readable repr."""
        from railway.core.config import _SettingsProxy

        proxy = _SettingsProxy()
        assert "_SettingsProxy" in repr(proxy)
