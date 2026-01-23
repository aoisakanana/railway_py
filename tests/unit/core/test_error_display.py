"""Tests for error display improvements."""

import pytest
from unittest.mock import patch, MagicMock


class TestErrorHints:
    """Test error hints functionality."""

    def test_connection_error_hint(self):
        """Should show hint for connection errors."""
        from railway.core.decorators import node

        @node
        def connection_node() -> str:
            raise ConnectionError("Unable to connect")

        with patch("railway.core.decorators.logger") as mock_logger:
            with pytest.raises(ConnectionError):
                connection_node()

            # Check for hint in error log
            error_calls = [str(c) for c in mock_logger.error.call_args_list]
            assert any("ヒント" in str(c) or "hint" in str(c).lower() for c in error_calls)

    def test_timeout_error_hint(self):
        """Should show hint for timeout errors."""
        from railway.core.decorators import node

        @node
        def timeout_node() -> str:
            raise TimeoutError("Request timed out")

        with patch("railway.core.decorators.logger") as mock_logger:
            with pytest.raises(TimeoutError):
                timeout_node()

            error_calls = [str(c) for c in mock_logger.error.call_args_list]
            assert any("ヒント" in str(c) or "timeout" in str(c).lower() for c in error_calls)

    def test_value_error_hint(self):
        """Should show hint for value errors."""
        from railway.core.decorators import node

        @node
        def value_node() -> str:
            raise ValueError("Invalid input")

        with patch("railway.core.decorators.logger") as mock_logger:
            with pytest.raises(ValueError):
                value_node()

            error_calls = [str(c) for c in mock_logger.error.call_args_list]
            assert any("ヒント" in str(c) for c in error_calls)

    def test_file_not_found_error_hint(self):
        """Should show hint for file not found errors."""
        from railway.core.decorators import node

        @node
        def file_node() -> str:
            raise FileNotFoundError("File not found")

        with patch("railway.core.decorators.logger") as mock_logger:
            with pytest.raises(FileNotFoundError):
                file_node()

            error_calls = [str(c) for c in mock_logger.error.call_args_list]
            assert any("ヒント" in str(c) for c in error_calls)

    def test_key_error_hint(self):
        """Should show hint for key errors."""
        from railway.core.decorators import node

        @node
        def key_node() -> str:
            raise KeyError("missing_key")

        with patch("railway.core.decorators.logger") as mock_logger:
            with pytest.raises(KeyError):
                key_node()

            error_calls = [str(c) for c in mock_logger.error.call_args_list]
            assert any("ヒント" in str(c) for c in error_calls)


class TestLogFileReference:
    """Test log file reference in errors."""

    def test_error_shows_log_file(self):
        """Should reference log file location."""
        from railway.core.decorators import node

        @node
        def failing_node() -> str:
            raise RuntimeError("Something failed")

        with patch("railway.core.decorators.logger") as mock_logger:
            with pytest.raises(RuntimeError):
                failing_node()

            error_calls = [str(c) for c in mock_logger.error.call_args_list]
            assert any("log" in str(c).lower() for c in error_calls)


class TestErrorFormatting:
    """Test error message formatting."""

    def test_error_includes_exception_type(self):
        """Should include exception type in error."""
        from railway.core.decorators import node

        @node
        def type_error_node() -> str:
            raise TypeError("Wrong type")

        with patch("railway.core.decorators.logger") as mock_logger:
            with pytest.raises(TypeError):
                type_error_node()

            error_calls = [str(c) for c in mock_logger.error.call_args_list]
            assert any("TypeError" in str(c) for c in error_calls)

    def test_error_includes_node_name(self):
        """Should include node name in error."""
        from railway.core.decorators import node

        @node(name="my_special_node")
        def named_node() -> str:
            raise Exception("Error")

        with patch("railway.core.decorators.logger") as mock_logger:
            with pytest.raises(Exception):
                named_node()

            error_calls = [str(c) for c in mock_logger.error.call_args_list]
            assert any("my_special_node" in str(c) for c in error_calls)


class TestPipelineErrorDisplay:
    """Test pipeline error display."""

    def test_pipeline_shows_remaining_steps(self):
        """Should show remaining steps count on error."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node

        @node
        def step1(x: int) -> int:
            return x + 1

        @node
        def step2(x: int) -> int:
            raise ValueError("Step 2 failed")

        @node
        def step3(x: int) -> int:
            return x * 2

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger") as mock_logger:
                with pytest.raises(ValueError):
                    pipeline(1, step1, step2, step3)

                info_calls = [str(c) for c in mock_logger.info.call_args_list]
                # Should mention skipping remaining steps (日本語)
                assert any(
                    "スキップ" in str(c) or "残り" in str(c)
                    for c in info_calls
                )


class TestApiKeyErrorHint:
    """Test API key error hints."""

    def test_api_key_error_hint(self):
        """Should show hint for API key errors."""
        from railway.core.decorators import node

        @node
        def api_node() -> str:
            raise Exception("API_KEY is invalid")

        with patch("railway.core.decorators.logger") as mock_logger:
            with pytest.raises(Exception):
                api_node()

            error_calls = [str(c) for c in mock_logger.error.call_args_list]
            assert any("ヒント" in str(c) or ".env" in str(c) for c in error_calls)
