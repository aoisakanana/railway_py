"""Logging initialization for Railway Framework."""

import sys
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from railway.core.settings import LoggingSettings


def _add_console_handler(
    settings: "LoggingSettings",
    handler_level: str,
) -> None:
    """Add console handler to logger."""
    logger.add(
        sys.stderr,
        level=handler_level,
        format=settings.format,
        colorize=True,
    )


def _add_file_handler(
    settings: "LoggingSettings",
    path: str,
    level: str,
    rotation: str | None,
    retention: str | None,
) -> None:
    """Add file handler to logger."""
    logger.add(
        path,
        level=level,
        format=settings.format,
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
    )


def _add_handler(settings: "LoggingSettings", handler_config: "LoggingSettings") -> None:
    """Add a single handler based on configuration."""
    from railway.core.settings import LoggingHandlerSettings

    if not isinstance(handler_config, LoggingHandlerSettings):
        return

    if handler_config.type == "console":
        _add_console_handler(settings, handler_config.level)
    elif handler_config.type == "file" and handler_config.path:
        _add_file_handler(
            settings,
            handler_config.path,
            handler_config.level,
            handler_config.rotation,
            handler_config.retention,
        )


def _add_default_handler(settings: "LoggingSettings") -> None:
    """Add default console handler when no handlers configured."""
    logger.add(
        sys.stderr,
        level=settings.level,
        format=settings.format,
        colorize=True,
    )


def init_logging(settings: "LoggingSettings") -> None:
    """
    Initialize loguru based on configuration.

    Steps:
    1. Remove default handler
    2. Add configured handlers (console, file)
    3. Apply log level and format

    Args:
        settings: LoggingSettings instance
    """
    # Remove default handler
    logger.remove()

    # Add handlers from config (functional approach using map-like pattern)
    if settings.handlers:
        for handler_config in settings.handlers:
            _add_handler(settings, handler_config)  # type: ignore[arg-type]
    else:
        # If no handlers configured, add default console handler
        _add_default_handler(settings)

    logger.debug(f"Logging initialized (level={settings.level})")


def get_logger(name: str | None = None) -> "logger":  # type: ignore[valid-type]
    """
    Get loguru logger instance.

    Args:
        name: Optional context name (for future use)

    Returns:
        loguru.logger instance
    """
    if name:
        return logger.bind(context=name)
    return logger


# Export logger for convenience
__all__ = ["init_logging", "get_logger", "logger"]
