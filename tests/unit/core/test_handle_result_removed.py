"""Tests for handle_result parameter removal from @entry_point."""

import inspect

from railway.core.decorators import entry_point


class TestHandleResultRemoved:
    def test_entry_point_no_handle_result_param(self):
        """entry_point should not accept handle_result parameter."""
        sig = inspect.signature(entry_point)
        assert "handle_result" not in sig.parameters

    def test_entry_wrapper_no_handle_result_attr(self):
        """Decorated function should not have _handle_result attribute."""

        @entry_point
        def my_func():
            pass

        assert not hasattr(my_func, "_handle_result")
