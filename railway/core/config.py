"""
Settings provider registry for framework-user code separation.

This module allows the @node decorator to access user settings
without directly importing user code.
"""

from collections.abc import Callable
from typing import Any, Protocol, cast


class RetrySettingsProtocol(Protocol):
    """Protocol for retry settings objects."""

    max_attempts: int
    min_wait: int
    max_wait: int
    multiplier: int


# Global settings provider
_settings_provider: Callable[[], Any] | None = None


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
