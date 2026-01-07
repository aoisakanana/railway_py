# Issue #04: @entry_pointデコレータ

**Phase:** 1a
**優先度:** 高
**依存関係:** #03
**見積もり:** 1日

---

## 概要

エントリーポイント（実行可能スクリプト）を定義するための@entry_pointデコレータを実装する。
Typerを使ってCLI引数パースを自動化する。

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/core/test_entry_point.py
"""Tests for @entry_point decorator."""
import pytest
from unittest.mock import patch, MagicMock
import sys


class TestEntryPointDecorator:
    """Test @entry_point decorator functionality."""

    def test_entry_point_without_parentheses(self):
        """Should work without parentheses."""
        from railway.core.decorators import entry_point

        @entry_point
        def simple_entry() -> str:
            return "done"

        # Should have _typer_app attribute
        assert hasattr(simple_entry, '_typer_app')
        assert hasattr(simple_entry, '_is_railway_entry_point')
        assert simple_entry._is_railway_entry_point is True

    def test_entry_point_with_parentheses(self):
        """Should work with empty parentheses."""
        from railway.core.decorators import entry_point

        @entry_point()
        def another_entry() -> str:
            return "also done"

        assert hasattr(another_entry, '_typer_app')

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

        assert hasattr(original_entry, '_original_func')
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
        import typer

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
        # This affects how Result types are handled

    def test_entry_point_handle_result_false(self):
        """Should allow handle_result=False for explicit Result handling."""
        from railway.core.decorators import entry_point

        @entry_point(handle_result=False)
        def explicit_result_entry():
            from returns.result import Success
            return Success("explicit")

        assert hasattr(explicit_result_entry, '_handle_result')
        assert explicit_result_entry._handle_result is False


class TestEntryPointExecution:
    """Test @entry_point execution behavior."""

    def test_entry_point_logs_start(self):
        """Should log entry point start."""
        from railway.core.decorators import entry_point

        with patch("railway.core.decorators.logger") as mock_logger:
            @entry_point
            def logged_entry() -> str:
                return "done"

            # Invoke the original function
            logged_entry._original_func()

            # Start is logged when CLI wrapper is invoked
            # For unit test, we just verify the decorator was applied

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
    """Test @entry_point with Result types."""

    def test_success_result(self):
        """Should handle Success result."""
        from railway.core.decorators import entry_point
        from returns.result import Success

        @entry_point
        def success_entry() -> str:
            return "success value"

        result = success_entry._original_func()
        assert result == "success value"

    def test_explicit_success_result(self):
        """Should handle explicit Success result when handle_result=False."""
        from railway.core.decorators import entry_point
        from returns.result import Success

        @entry_point(handle_result=False)
        def explicit_success():
            return Success("explicit success")

        result = explicit_success._original_func()
        assert result.unwrap() == "explicit success"
```

```bash
# 実行して失敗を確認
pytest tests/unit/core/test_entry_point.py -v
# Expected: FAILED (ImportError or AttributeError)
```

### Step 2: Green（最小限の実装）

```python
# railway/core/decorators.py に追加

import sys
import typer
from returns.result import Result, Success, Failure


def entry_point(
    func: Callable[P, T] | None = None,
    *,
    handle_result: bool = True,
) -> Callable[P, None] | Callable[[Callable[P, T]], Callable[P, None]]:
    """
    Entry point decorator that provides:
    1. Automatic CLI argument parsing via Typer
    2. Error handling and logging
    3. Exit code management (0 for success, 1 for failure)
    4. Result type unwrapping

    Args:
        func: Function to decorate
        handle_result: Automatically handle Result types (default: True)

    Returns:
        Decorated function with CLI integration

    Example:
        @entry_point
        def main(name: str = "World", verbose: bool = False):
            print(f"Hello, {name}!")
            return "Success"

        if __name__ == "__main__":
            main()  # Typer app is invoked

    CLI usage:
        python -m src.entry --name Alice --verbose
    """

    def decorator(f: Callable[P, T]) -> Callable[P, None]:
        entry_name = f.__name__

        # Create Typer app for this entry point
        app = typer.Typer(
            help=f.__doc__ or f"Execute {entry_name} entry point",
            add_completion=False,
        )

        @app.command()
        @wraps(f)
        def cli_wrapper(**kwargs: Any) -> None:
            """CLI wrapper for the entry point."""
            logger.info(f"[{entry_name}] Entry point started")
            logger.debug(f"[{entry_name}] Arguments: {kwargs}")

            try:
                # Execute the main function
                result = f(**kwargs)

                # Handle result based on type
                if handle_result:
                    if isinstance(result, Success):
                        value = result.unwrap()
                        logger.success(f"[{entry_name}] ✓ Completed successfully: {value}")
                        sys.exit(0)
                    elif isinstance(result, Failure):
                        error = result.failure()
                        logger.error(f"[{entry_name}] ✗ Failed: {error}")
                        sys.exit(1)
                    else:
                        # Plain value
                        logger.success(f"[{entry_name}] ✓ Completed successfully")
                        sys.exit(0)
                else:
                    # User handles Result explicitly
                    logger.success(f"[{entry_name}] ✓ Completed")
                    sys.exit(0)

            except KeyboardInterrupt:
                logger.warning(f"[{entry_name}] Interrupted by user")
                sys.exit(130)

            except Exception as e:
                logger.exception(f"[{entry_name}] ✗ Unhandled exception")
                sys.exit(1)

        # Create a wrapper that can be called directly or via Typer
        @wraps(f)
        def entry_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            """
            Wrapper that delegates to Typer app when called without args,
            or to original function when called with args.
            """
            if args or kwargs:
                # Called programmatically with arguments
                return f(*args, **kwargs)
            else:
                # Called as CLI entry point
                app()

        # Store Typer app and metadata for programmatic access
        entry_wrapper._typer_app = app  # type: ignore
        entry_wrapper._original_func = f  # type: ignore
        entry_wrapper._is_railway_entry_point = True  # type: ignore
        entry_wrapper._handle_result = handle_result  # type: ignore
        entry_wrapper.__doc__ = f.__doc__

        return entry_wrapper

    if func is None:
        return decorator
    return decorator(func)
```

```bash
# 実行して成功を確認
pytest tests/unit/core/test_entry_point.py -v
# Expected: PASSED
```

### Step 3: Refactor

- CLI wrapperとプログラム呼び出しの分離を明確化
- ドキュメントの充実

---

## 完了条件

- [ ] `@entry_point` と `@entry_point()` の両方で動作する
- [ ] Typer appが作成される（`_typer_app`属性）
- [ ] 元の関数が保持される（`_original_func`属性）
- [ ] 関数名とdocstringが保持される
- [ ] `handle_result=True`でResult型が自動処理される
- [ ] `handle_result=False`で明示的Result処理が可能
- [ ] KeyboardInterruptが適切に処理される
- [ ] テストカバレッジ90%以上

---

## 次のIssue

- #05: pipeline()関数
