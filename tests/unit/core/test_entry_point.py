"""Tests for @entry_point decorator."""


import pytest
import typer


class TestEntryPointDecorator:
    """Test @entry_point decorator functionality."""

    def test_entry_point_without_parentheses(self):
        """Should work without parentheses."""
        from railway.core.decorators import entry_point

        @entry_point
        def simple_entry() -> str:
            return "done"

        # Should have _typer_app attribute
        assert hasattr(simple_entry, "_typer_app")
        assert hasattr(simple_entry, "_is_railway_entry_point")
        assert simple_entry._is_railway_entry_point is True

    def test_entry_point_with_parentheses(self):
        """Should work with empty parentheses."""
        from railway.core.decorators import entry_point

        @entry_point()
        def another_entry() -> str:
            return "also done"

        assert hasattr(another_entry, "_typer_app")

    def test_entry_point_preserves_metadata(self):
        """Should preserve function name and docstring."""
        from railway.core.decorators import entry_point

        @entry_point
        def documented_entry() -> str:
            """This is a documented entry point."""
            return "doc"

        assert documented_entry.__name__ == "documented_entry"
        assert "documented entry point" in (documented_entry.__doc__ or "")

    def test_entry_point_stores_original_func(self):
        """Should store reference to original function."""
        from railway.core.decorators import entry_point

        @entry_point
        def original_entry() -> int:
            return 42

        assert hasattr(original_entry, "_original_func")
        # Can call original function directly
        assert original_entry._original_func() == 42

    def test_entry_point_with_arguments(self):
        """Should handle function arguments for CLI."""
        from railway.core.decorators import entry_point

        @entry_point
        def greeting_entry(name: str = "World", verbose: bool = False) -> str:
            if verbose:
                return f"Hello, {name}! (verbose mode)"
            return f"Hello, {name}!"

        # Original function should work
        result = greeting_entry._original_func("Alice", False)
        assert result == "Hello, Alice!"

    def test_entry_point_typer_app_created(self):
        """Should create Typer app."""
        from railway.core.decorators import entry_point

        @entry_point
        def cli_entry(name: str = "World") -> str:
            return f"Hello, {name}!"

        assert isinstance(cli_entry._typer_app, typer.Typer)

    def test_entry_point_handle_result_default(self):
        """Should have handle_result=True by default."""
        from railway.core.decorators import entry_point

        @entry_point
        def result_entry() -> str:
            return "success"

        # handle_result should be True by default
        assert result_entry._handle_result is True

    def test_entry_point_handle_result_false(self):
        """Should allow handle_result=False for explicit Result handling."""
        from railway.core.decorators import entry_point

        @entry_point(handle_result=False)
        def explicit_result_entry() -> str:
            return "explicit"

        assert hasattr(explicit_result_entry, "_handle_result")
        assert explicit_result_entry._handle_result is False


class TestEntryPointExecution:
    """Test @entry_point execution behavior."""

    def test_entry_point_original_func_callable(self):
        """Should be able to call original function."""
        from railway.core.decorators import entry_point

        @entry_point
        def logged_entry() -> str:
            return "done"

        # Invoke the original function
        result = logged_entry._original_func()
        assert result == "done"

    def test_entry_point_keyboard_interrupt(self):
        """Should handle KeyboardInterrupt gracefully."""
        from railway.core.decorators import entry_point

        @entry_point
        def interruptible_entry() -> str:
            raise KeyboardInterrupt()

        # KeyboardInterrupt should propagate (handled by CLI wrapper)
        with pytest.raises(KeyboardInterrupt):
            interruptible_entry._original_func()


class TestEntryPointWithResult:
    """Test @entry_point with plain return values."""

    def test_success_result(self):
        """Should handle plain success result."""
        from railway.core.decorators import entry_point

        @entry_point
        def success_entry() -> str:
            return "success value"

        result = success_entry._original_func()
        assert result == "success value"

    def test_direct_call_with_args(self):
        """Should allow direct call with arguments."""
        from railway.core.decorators import entry_point

        @entry_point
        def greeting(name: str, count: int = 1) -> str:
            return f"Hello, {name}!" * count

        # Direct call with arguments
        result = greeting._original_func("World", 2)
        assert result == "Hello, World!Hello, World!"


class TestEntryPointCLIIntegration:
    """Test @entry_point CLI integration with Typer."""

    def test_typer_runner_invoke(self):
        """Should work with Typer testing runner."""
        from typer.testing import CliRunner

        from railway.core.decorators import entry_point

        runner = CliRunner()

        @entry_point
        def cli_test(name: str = "World") -> str:
            """Test CLI command."""
            print(f"Hello, {name}!")
            return f"Hello, {name}!"

        result = runner.invoke(cli_test._typer_app, ["--name", "Alice"])
        # Note: exit code depends on implementation
        assert "Alice" in result.stdout or result.exit_code == 0
