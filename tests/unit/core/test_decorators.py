"""Tests for @node decorator."""

from unittest.mock import patch

import pytest


class TestNodeDecorator:
    """Test @node decorator functionality."""

    def test_node_without_parentheses(self):
        """Should work without parentheses."""
        from railway.core.decorators import node

        @node
        def simple_node(x: int) -> int:
            return x + 1

        with patch("railway.core.decorators.logger"):
            result = simple_node(5)
        assert result == 6

    def test_node_with_parentheses(self):
        """Should work with empty parentheses."""
        from railway.core.decorators import node

        @node()
        def simple_node(x: int) -> int:
            return x * 2

        with patch("railway.core.decorators.logger"):
            result = simple_node(5)
        assert result == 10

    def test_node_preserves_function_name(self):
        """Should preserve original function name."""
        from railway.core.decorators import node

        @node
        def my_custom_node() -> str:
            return "hello"

        assert my_custom_node.__name__ == "my_custom_node"

    def test_node_preserves_docstring(self):
        """Should preserve original docstring."""
        from railway.core.decorators import node

        @node
        def documented_node() -> str:
            """This is a documented node."""
            return "doc"

        assert documented_node.__doc__ == "This is a documented node."

    def test_node_stores_metadata(self):
        """Should store railway metadata."""
        from railway.core.decorators import node

        @node
        def metadata_node() -> int:
            return 42

        assert metadata_node._is_railway_node is True
        assert metadata_node._node_name == "metadata_node"

    def test_node_custom_name(self):
        """Should allow custom node name."""
        from railway.core.decorators import node

        @node(name="custom_name")
        def original_name() -> int:
            return 1

        assert original_name._node_name == "custom_name"

    def test_node_propagates_exception(self):
        """Should propagate exceptions from node."""
        from railway.core.decorators import node

        @node
        def failing_node() -> int:
            raise ValueError("Test error")

        with patch("railway.core.decorators.logger"):
            with pytest.raises(ValueError, match="Test error"):
                failing_node()

    def test_node_logs_start_and_completion(self):
        """Should log node start and completion."""
        from railway.core.decorators import node

        with patch("railway.core.decorators.logger") as mock_logger:

            @node
            def logged_node() -> str:
                return "done"

            result = logged_node()

            assert result == "done"
            # Check that info was called for start and completion
            calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("Starting" in str(call) for call in calls)
            assert any("Completed" in str(call) for call in calls)

    def test_node_logs_error(self):
        """Should log errors when node fails."""
        from railway.core.decorators import node

        with patch("railway.core.decorators.logger") as mock_logger:

            @node
            def error_node() -> int:
                raise RuntimeError("Node failed")

            with pytest.raises(RuntimeError):
                error_node()

            # Check that error was logged
            mock_logger.error.assert_called()

    def test_node_with_arguments(self):
        """Should pass arguments correctly."""
        from railway.core.decorators import node

        @node
        def add_node(a: int, b: int) -> int:
            return a + b

        with patch("railway.core.decorators.logger"):
            result = add_node(3, 4)
        assert result == 7

    def test_node_with_kwargs(self):
        """Should pass keyword arguments correctly."""
        from railway.core.decorators import node

        @node
        def greeting_node(name: str, prefix: str = "Hello") -> str:
            return f"{prefix}, {name}!"

        with patch("railway.core.decorators.logger"):
            result = greeting_node("World", prefix="Hi")
        assert result == "Hi, World!"

    def test_node_retry_disabled_by_default_in_basic(self):
        """Basic node should not retry (retry=False by default in basic version)."""
        from railway.core.decorators import node

        call_count = 0

        @node(retry=False)
        def counting_node() -> int:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return call_count

        with patch("railway.core.decorators.logger"):
            with pytest.raises(ValueError):
                counting_node()

        assert call_count == 1  # No retry


class TestNodeWithLogInput:
    """Test @node with log_input option."""

    def test_log_input_enabled(self):
        """Should log input when log_input=True."""
        from railway.core.decorators import node

        with patch("railway.core.decorators.logger") as mock_logger:

            @node(log_input=True)
            def input_node(data: dict) -> dict:
                return data

            input_node({"key": "value"})

            # Check debug was called with input
            debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
            assert any("Input" in str(call) for call in debug_calls)


class TestNodeWithLogOutput:
    """Test @node with log_output option."""

    def test_log_output_enabled(self):
        """Should log output when log_output=True."""
        from railway.core.decorators import node

        with patch("railway.core.decorators.logger") as mock_logger:

            @node(log_output=True)
            def output_node() -> str:
                return "result"

            output_node()

            # Check debug was called with output
            debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
            assert any("Output" in str(call) for call in debug_calls)
