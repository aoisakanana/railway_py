"""
Decorators for Railway nodes and entry points.
"""

from __future__ import annotations

import inspect
import os
import traceback
from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any, ParamSpec, Type, TypeVar

import typer
from loguru import logger
from tenacity import (
    retry as tenacity_retry,
    stop_after_attempt,
    wait_exponential,
    RetryError,
    before_sleep_log,
    AsyncRetrying,
)

if TYPE_CHECKING:
    from railway.core.contract import Contract

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
        self.multiplier = exponential_base  # Alias for compatibility


def node(
    func: Callable[P, T] | None = None,
    *,
    inputs: dict[str, Type[Contract]] | None = None,
    output: Type[Contract] | None = None,
    retry: bool | Retry = False,
    log_input: bool = False,
    log_output: bool = False,
    name: str | None = None,
) -> Callable[P, T] | Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Node decorator that provides:
    1. Automatic exception handling with logging
    2. Optional retry with exponential backoff
    3. Structured logging
    4. Metadata storage
    5. Type-safe input/output contracts (Output Model pattern)

    Args:
        func: Function to decorate
        inputs: Dictionary mapping parameter names to expected Contract types
        output: Expected output Contract type
        retry: Enable retry (bool) or provide Retry config
        log_input: Log input parameters (caution: may log sensitive data)
        log_output: Log output data (caution: may log sensitive data)
        name: Override node name (default: function name)

    Returns:
        Decorated function with automatic error handling

    Example:
        @node
        def fetch_data() -> dict:
            return api.get("/data")

        @node(retry=True)
        def fetch_with_retry() -> dict:
            return api.get("/data")

        @node(output=UsersFetchResult)
        def fetch_users() -> UsersFetchResult:
            return UsersFetchResult(users=[...], total=10)

        @node(inputs={"users": UsersFetchResult}, output=ReportResult)
        def generate_report(users: UsersFetchResult) -> ReportResult:
            return ReportResult(content=f"{users.total} users")
    """
    # Normalize inputs to empty dict if None
    inputs_dict = inputs or {}

    def decorator(f: Callable[P, T]) -> Callable[P, T]:
        node_name = name or f.__name__
        is_async = inspect.iscoroutinefunction(f)

        if is_async:
            return _create_async_wrapper(
                f, node_name, inputs_dict, output, retry, log_input, log_output
            )
        else:
            return _create_sync_wrapper(
                f, node_name, inputs_dict, output, retry, log_input, log_output
            )

    # Handle decorator usage with and without parentheses
    if func is None:
        return decorator
    return decorator(func)


def _create_sync_wrapper(
    f: Callable[P, T],
    node_name: str,
    inputs_dict: dict[str, Type[Contract]],
    output_type: Type[Contract] | None,
    retry: bool | Retry,
    log_input: bool,
    log_output: bool,
) -> Callable[P, T]:
    """Create wrapper for synchronous function."""

    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        # Log input if enabled
        if log_input:
            logger.debug(f"[{node_name}] Input: args={args}, kwargs={kwargs}")

        logger.info(f"[{node_name}] Starting...")

        # Determine retry configuration
        retry_config = _get_retry_configuration(retry, node_name)

        try:
            if retry_config is not None:
                # Execute with retry
                result = _execute_with_retry(f, retry_config, node_name, args, kwargs)
            else:
                # Execute without retry
                result = f(*args, **kwargs)

            # Validate output type if specified
            if output_type is not None and not isinstance(result, output_type):
                raise TypeError(
                    f"Node '{node_name}' expected to return {output_type.__name__}, "
                    f"got {type(result).__name__}"
                )

            # Log output if enabled
            if log_output:
                logger.debug(f"[{node_name}] Output: {result}")

            logger.info(f"[{node_name}] ✓ Completed")
            return result

        except Exception as e:
            _log_error_with_hint(node_name, e)
            raise

    # Store metadata
    wrapper._is_railway_node = True  # type: ignore[attr-defined]
    wrapper._node_name = node_name  # type: ignore[attr-defined]
    wrapper._original_func = f  # type: ignore[attr-defined]
    wrapper._is_async = False  # type: ignore[attr-defined]
    wrapper._node_inputs = inputs_dict  # type: ignore[attr-defined]
    wrapper._node_output = output_type  # type: ignore[attr-defined]

    return wrapper


def _create_async_wrapper(
    f: Callable[P, T],
    node_name: str,
    inputs_dict: dict[str, Type[Contract]],
    output_type: Type[Contract] | None,
    retry: bool | Retry,
    log_input: bool,
    log_output: bool,
) -> Callable[P, T]:
    """Create wrapper for asynchronous function."""

    @wraps(f)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        # Log input if enabled
        if log_input:
            logger.debug(f"[{node_name}] Input: args={args}, kwargs={kwargs}")

        logger.info(f"[{node_name}] Starting...")

        # Determine retry configuration
        retry_config = _get_retry_configuration(retry, node_name)

        try:
            if retry_config is not None:
                # Execute with retry
                result = await _execute_async_with_retry(
                    f, retry_config, node_name, args, kwargs
                )
            else:
                # Execute without retry
                result = await f(*args, **kwargs)

            # Validate output type if specified
            if output_type is not None and not isinstance(result, output_type):
                raise TypeError(
                    f"Node '{node_name}' expected to return {output_type.__name__}, "
                    f"got {type(result).__name__}"
                )

            # Log output if enabled
            if log_output:
                logger.debug(f"[{node_name}] Output: {result}")

            logger.info(f"[{node_name}] ✓ Completed")
            return result

        except Exception as e:
            _log_error_with_hint(node_name, e)
            raise

    # Store metadata
    wrapper._is_railway_node = True  # type: ignore[attr-defined]
    wrapper._node_name = node_name  # type: ignore[attr-defined]
    wrapper._original_func = f  # type: ignore[attr-defined]
    wrapper._is_async = True  # type: ignore[attr-defined]
    wrapper._node_inputs = inputs_dict  # type: ignore[attr-defined]
    wrapper._node_output = output_type  # type: ignore[attr-defined]

    return wrapper


async def _execute_async_with_retry(
    func: Callable[P, T],
    retry_config: Retry,
    node_name: str,
    args: tuple,
    kwargs: dict,
) -> T:
    """Execute async function with retry logic."""
    max_attempts = retry_config.max_attempts
    attempt_count = 0

    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(retry_config.max_attempts),
        wait=wait_exponential(
            multiplier=retry_config.multiplier,
            min=retry_config.min_wait,
            max=retry_config.max_wait,
        ),
        reraise=True,
    ):
        with attempt:
            attempt_count = attempt.retry_state.attempt_number
            if attempt_count > 1:
                logger.warning(
                    f"[{node_name}] リトライ中... (試行 {attempt_count}/{max_attempts})"
                )
            return await func(*args, **kwargs)


def _get_retry_configuration(retry_param: bool | Retry, node_name: str) -> Retry | None:
    """Get retry configuration from parameter or settings."""
    if retry_param is True:
        # Load from config
        from railway.core.config import get_retry_config
        config = get_retry_config(node_name)
        return Retry(
            max_attempts=config.max_attempts,
            min_wait=config.min_wait,
            max_wait=config.max_wait,
            exponential_base=config.multiplier,
        )
    elif isinstance(retry_param, Retry):
        return retry_param
    else:
        return None


def _get_error_hint(exception: Exception) -> str | None:
    """Get hint message for common errors."""
    if isinstance(exception, ConnectionError):
        return "ヒント: ネットワーク接続を確認してください。APIエンドポイントが正しいか確認してください。"
    elif isinstance(exception, TimeoutError):
        return "ヒント: タイムアウト値を増やすか、APIサーバーの状態を確認してください。"
    elif isinstance(exception, ValueError):
        return "ヒント: 入力データの形式や値を確認してください。"
    elif isinstance(exception, FileNotFoundError):
        return "ヒント: ファイルパスが正しいか確認してください。"
    elif isinstance(exception, PermissionError):
        return "ヒント: ファイルやディレクトリの権限を確認してください。"
    elif isinstance(exception, KeyError):
        return "ヒント: 必要なキーが存在するか確認してください。設定ファイルを確認してください。"

    # Check for API key related errors
    error_str = str(exception).upper()
    if "API_KEY" in error_str or "API_SECRET" in error_str or "UNAUTHORIZED" in error_str:
        return "ヒント: .envファイルでAPI認証情報が正しく設定されているか確認してください。"

    return None


def _log_error_with_hint(node_name: str, exception: Exception) -> None:
    """Log error with hint and log file reference."""
    logger.error(f"[{node_name}] ✗ Failed: {type(exception).__name__}: {exception}")
    logger.error("詳細は logs/app.log を確認してください")

    hint = _get_error_hint(exception)
    if hint:
        logger.error(hint)


def _is_verbose_mode() -> bool:
    """Check if verbose mode is enabled."""
    return os.environ.get("RAILWAY_VERBOSE", "").lower() in ("1", "true", "yes")


def _get_user_frame(exception: Exception) -> str | None:
    """Extract user code location from exception traceback."""
    tb = traceback.extract_tb(exception.__traceback__)
    # Filter out framework internal frames
    internal_patterns = [
        "site-packages/typer/",
        "site-packages/click/",
        "site-packages/railway/",
        "<frozen",
        "runpy.py",
    ]

    for frame in reversed(tb):
        is_internal = any(pattern in frame.filename for pattern in internal_patterns)
        if not is_internal:
            return f"{frame.filename}:{frame.lineno} in {frame.name}"

    return None


def _log_exception_compact(entry_name: str, exception: Exception) -> None:
    """Log exception in compact format for better readability."""
    verbose = _is_verbose_mode()

    # Always log full traceback to file (DEBUG level)
    logger.opt(exception=True).debug(f"[{entry_name}] Full traceback")

    if verbose:
        # Verbose mode: show full traceback
        logger.exception(f"[{entry_name}] ✗ Unhandled exception: {exception}")
    else:
        # Compact mode: show only essential info
        error_type = type(exception).__name__
        error_msg = str(exception)
        location = _get_user_frame(exception)

        logger.error(f"[{entry_name}] ✗ {error_type}: {error_msg}")
        if location:
            logger.error(f"Location: {location}")

        hint = _get_error_hint(exception)
        if hint:
            logger.error(hint)

        logger.info("詳細なスタックトレースは RAILWAY_VERBOSE=1 で表示できます")


def _execute_with_retry(
    func: Callable[P, T],
    retry_config: Retry,
    node_name: str,
    args: tuple,
    kwargs: dict,
) -> T:
    """Execute function with retry logic."""
    attempt_count = 0
    max_attempts = retry_config.max_attempts

    def before_retry(retry_state):
        nonlocal attempt_count
        attempt_count = retry_state.attempt_number
        logger.warning(f"[{node_name}] リトライ中... (試行 {attempt_count}/{max_attempts})")

    retry_decorator = tenacity_retry(
        stop=stop_after_attempt(retry_config.max_attempts),
        wait=wait_exponential(
            multiplier=retry_config.multiplier,
            min=retry_config.min_wait,
            max=retry_config.max_wait,
        ),
        reraise=True,
        before_sleep=before_retry,
    )

    retryable_func = retry_decorator(func)

    try:
        return retryable_func(*args, **kwargs)
    except RetryError as e:
        # Extract original exception
        if e.last_attempt.exception() is not None:
            raise e.last_attempt.exception() from None
        raise


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
                _log_exception_compact(entry_name, e)
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
        entry_wrapper._impl = f  # type: ignore[attr-defined]  # Alias for direct testing
        entry_wrapper._is_railway_entry_point = True  # type: ignore[attr-defined]
        entry_wrapper._handle_result = handle_result  # type: ignore[attr-defined]
        entry_wrapper.__doc__ = f.__doc__

        return entry_wrapper

    if func is None:
        return decorator
    return decorator(func)
