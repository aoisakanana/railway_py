"""
Settings provider registry for framework-user code separation.

This module allows the @node decorator to access user settings
without directly importing user code.

Features:
- Lazy initialization via _SettingsProxy
- Thread-safe settings access
- Cached settings for performance
"""

import threading
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any, Protocol, cast


class RetrySettingsProtocol(Protocol):
    """Protocol for retry settings objects."""

    max_attempts: int
    min_wait: int
    max_wait: int
    multiplier: int


# Thread-safe settings state
_settings_provider: Callable[[], Any] | None = None
_settings_cache: Any | None = None
_settings_lock = threading.Lock()


def register_settings_provider(provider: Callable[[], Any]) -> None:
    """
    Register a settings provider function.

    The provider should return a settings object with get_retry_settings() method.

    Args:
        provider: A callable that returns the settings object

    Example:
        from railway.core.config import register_settings_provider
        from src.settings import get_settings

        register_settings_provider(get_settings)
    """
    global _settings_provider
    _settings_provider = provider


def get_settings_provider() -> Callable[[], Any] | None:
    """
    Get the registered settings provider.

    Returns:
        The registered provider function, or None if not registered.
    """
    return _settings_provider


class DefaultRetrySettings:
    """
    Default retry settings when no provider is registered.

    Used as fallback when:
    - No settings provider is registered
    - The provider raises an exception
    """

    max_attempts: int = 3
    min_wait: int = 2
    max_wait: int = 10
    multiplier: int = 1


def get_retry_config(node_name: str) -> RetrySettingsProtocol:
    """
    Get retry configuration for a specific node.

    If no settings provider is registered, returns default settings.

    Args:
        node_name: Name of the node to get settings for

    Returns:
        Retry configuration object with max_attempts, min_wait, max_wait, multiplier
    """
    if _settings_provider is None:
        return DefaultRetrySettings()

    try:
        settings = _settings_provider()
        return cast(RetrySettingsProtocol, settings.get_retry_settings(node_name))
    except Exception:
        return DefaultRetrySettings()


def reset_provider() -> None:
    """
    Reset the settings provider (for testing).
    """
    global _settings_provider
    _settings_provider = None


def reset_settings() -> None:
    """
    Reset settings cache and provider.

    Forces settings to be reloaded on next access.
    Useful for testing or when environment changes.
    """
    global _settings_cache, _settings_provider
    with _settings_lock:
        _settings_cache = None
        _settings_provider = None


def _get_or_create_settings() -> Any:
    """
    Get or create the settings object.

    Uses registered provider if available, otherwise returns default settings.
    Thread-safe and cached for performance.

    Returns:
        The settings object.
    """
    global _settings_cache

    with _settings_lock:
        if _settings_cache is not None:
            return _settings_cache

        # Use registered provider if available
        if _settings_provider is not None:
            try:
                _settings_cache = _settings_provider()
                return _settings_cache
            except Exception:
                pass

        # Return default settings
        _settings_cache = _create_default_settings()
        return _settings_cache


def _create_default_settings() -> Any:
    """Create default settings object."""
    return SimpleNamespace(
        api=SimpleNamespace(
            base_url="",
            timeout=30,
        ),
        retry=SimpleNamespace(
            default=SimpleNamespace(
                max_attempts=3,
                min_wait=2.0,
                max_wait=10.0,
                multiplier=2,
            ),
            nodes={},
        ),
        logging=SimpleNamespace(
            level="INFO",
            format="console",
        ),
    )


class _SettingsProxy:
    """
    Proxy object for lazy settings initialization.

    Settings are not loaded until first attribute access.
    This avoids import-time side effects and circular imports.

    Usage:
        from railway.core.config import settings

        # Settings loaded here (first access)
        api_url = settings.api.base_url
    """

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to actual settings object."""
        actual_settings = _get_or_create_settings()
        return getattr(actual_settings, name)

    def __repr__(self) -> str:
        return "<_SettingsProxy>"


# Module-level settings proxy (not initialized until first access)
settings = _SettingsProxy()
