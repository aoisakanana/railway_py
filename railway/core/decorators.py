"""
Decorators for Railway nodes and entry points.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

import typer
from loguru import logger

P = ParamSpec("P")
T = TypeVar("T")


class Retry:
    """Retry configuration for nodes."""

    def __init__(
        self,
        max_attempts: int = 3,
        min_wait: float = 2.0,
        max_wait: float = 10.0,
        exponential_base: int = 2,
    ):
        self.max_attempts = max_attempts
        self.min_wait = min_wait
        self.max_wait = max_wait
        self.exponential_base = exponential_base


def node(
    func: Callable[P, T] | None = None,
    *,
    retry: bool | Retry = False,  # Disabled by default in basic version
    log_input: bool = False,
    log_output: bool = False,
    name: str | None = None,
) -> Callable[P, T] | Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Node decorator that provides:
    1. Automatic exception handling with logging
    2. Optional retry with exponential backoff (Phase 1b)
    3. Structured logging
    4. Metadata storage

    Args:
        func: Function to decorate
        retry: Enable retry (bool) or provide Retry config (Phase 1b)
        log_input: Log input parameters (caution: may log sensitive data)
        log_output: Log output data (caution: may log sensitive data)
        name: Override node name (default: function name)

    Returns:
        Decorated function with automatic error handling

    Example:
        @node
        def fetch_data() -> dict:
            return api.get("/data")

        @node(name="critical_fetch", log_input=True)
        def fetch_critical_data(id: int) -> dict:
            return api.get(f"/critical/{id}")
    """

    def decorator(f: Callable[P, T]) -> Callable[P, T]:
        node_name = name or f.__name__

        @wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Log input if enabled
            if log_input:
                logger.debug(f"[{node_name}] Input: args={args}, kwargs={kwargs}")

            logger.info(f"[{node_name}] Starting...")

            try:
                result = f(*args, **kwargs)

                # Log output if enabled
                if log_output:
                    logger.debug(f"[{node_name}] Output: {result}")

                logger.info(f"[{node_name}] ✓ Completed")
                return result

            except Exception as e:
                logger.error(f"[{node_name}] ✗ Failed: {type(e).__name__}: {e}")
                raise

        # Store metadata
        wrapper._is_railway_node = True  # type: ignore[attr-defined]
        wrapper._node_name = node_name  # type: ignore[attr-defined]
        wrapper._original_func = f  # type: ignore[attr-defined]
        wrapper._is_async = False  # type: ignore[attr-defined]

        return wrapper

    # Handle decorator usage with and without parentheses
    if func is None:
        return decorator
    return decorator(func)


def entry_point(
    func: Callable[P, T] | None = None,
    *,
    handle_result: bool = True,
) -> Callable[P, Any] | Callable[[Callable[P, T]], Callable[P, Any]]:
    """
    Entry point decorator that provides:
    1. Automatic CLI argument parsing via Typer
    2. Error handling and logging
    3. Exit code management (0 for success, 1 for failure)

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

    def decorator(f: Callable[P, T]) -> Callable[P, Any]:
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
                _ = f(**kwargs)  # type: ignore[call-arg]

                # Log success
                logger.info(f"[{entry_name}] ✓ Completed successfully")

            except KeyboardInterrupt:
                logger.warning(f"[{entry_name}] Interrupted by user")
                raise

            except Exception as e:
                logger.exception(f"[{entry_name}] ✗ Unhandled exception: {e}")
                raise

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
        entry_wrapper._typer_app = app  # type: ignore[attr-defined]
        entry_wrapper._original_func = f  # type: ignore[attr-defined]
        entry_wrapper._is_railway_entry_point = True  # type: ignore[attr-defined]
        entry_wrapper._handle_result = handle_result  # type: ignore[attr-defined]
        entry_wrapper.__doc__ = f.__doc__

        return entry_wrapper

    if func is None:
        return decorator
    return decorator(func)
