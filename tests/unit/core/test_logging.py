"""Tests for logging initialization."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestLoggingInit:
    """Test logging initialization."""

    def test_init_logging_removes_default(self):
        """Should remove default loguru handler."""
        from railway.core.logging import init_logging
        from railway.core.settings import LoggingSettings

        with patch("railway.core.logging.logger") as mock_logger:
            settings = LoggingSettings(level="INFO")
            init_logging(settings)

            mock_logger.remove.assert_called()

    def test_init_logging_adds_console_handler(self):
        """Should add console handler when configured."""
        from railway.core.logging import init_logging
        from railway.core.settings import LoggingHandlerSettings, LoggingSettings

        with patch("railway.core.logging.logger") as mock_logger:
            settings = LoggingSettings(
                level="DEBUG",
                handlers=[LoggingHandlerSettings(type="console", level="DEBUG")],
            )
            init_logging(settings)

            # Should call logger.add for console handler
            mock_logger.add.assert_called()

    def test_init_logging_adds_file_handler(self):
        """Should add file handler when configured."""
        from railway.core.logging import init_logging
        from railway.core.settings import LoggingHandlerSettings, LoggingSettings

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "app.log"

            with patch("railway.core.logging.logger") as mock_logger:
                settings = LoggingSettings(
                    level="INFO",
                    handlers=[
                        LoggingHandlerSettings(
                            type="file",
                            path=str(log_path),
                            level="INFO",
                            rotation="1 day",
                            retention="7 days",
                        )
                    ],
                )
                init_logging(settings)

                mock_logger.add.assert_called()

    def test_init_logging_applies_format(self):
        """Should apply custom log format."""
        from railway.core.logging import init_logging
        from railway.core.settings import LoggingHandlerSettings, LoggingSettings

        custom_format = "{time:YYYY-MM-DD} | {level} | {message}"

        with patch("railway.core.logging.logger") as mock_logger:
            settings = LoggingSettings(
                level="INFO",
                format=custom_format,
                handlers=[LoggingHandlerSettings(type="console", level="INFO")],
            )
            init_logging(settings)

            # Check that format was passed to logger.add
            call_kwargs = mock_logger.add.call_args_list[0][1]
            assert call_kwargs.get("format") == custom_format

    def test_init_logging_default_handler_when_none_configured(self):
        """Should add default console handler when none configured."""
        from railway.core.logging import init_logging
        from railway.core.settings import LoggingSettings

        with patch("railway.core.logging.logger") as mock_logger:
            settings = LoggingSettings(level="INFO", handlers=[])
            init_logging(settings)

            # Should still add a handler
            mock_logger.add.assert_called()


class TestLoggingHelpers:
    """Test logging helper functions."""

    def test_get_logger(self):
        """Should return loguru logger."""
        from railway.core.logging import get_logger

        log = get_logger()

        # Should be loguru logger
        assert hasattr(log, "info")
        assert hasattr(log, "debug")
        assert hasattr(log, "error")
        assert hasattr(log, "success")

    def test_get_logger_with_context(self):
        """Should return logger with context."""
        from railway.core.logging import get_logger

        log = get_logger("my_module")

        # Should support binding context
        assert log is not None


class TestLoggingExport:
    """Test logging module exports."""

    def test_logger_exported(self):
        """Should export logger from module."""
        from railway.core.logging import logger

        assert hasattr(logger, "info")
        assert hasattr(logger, "debug")
