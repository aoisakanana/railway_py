"""
Decorators for Railway nodes and entry points.
"""

from __future__ import annotations

import inspect
import os
import traceback
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    ParamSpec,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)

import typer
from loguru import logger
from tenacity import (
    AsyncRetrying,
    RetryError,
    stop_after_attempt,
    wait_exponential,
)
from tenacity import (
    retry as tenacity_retry,
)

if TYPE_CHECKING:
    from railway.core.contract import Contract
    from railway.core.retry import RetryPolicy

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


@overload
def node(func: Callable[P, T]) -> Callable[P, T]: ...


@overload
def node(
    func: None = None,
    *,
    inputs: dict[str, type[Contract]] | None = None,
    output: type[Contract] | None = None,
    requires: list[str] | None = None,
    optional: list[str] | None = None,
    provides: list[str] | None = None,
    retry: bool | Retry = False,
    retry_policy: RetryPolicy | None = None,
    retries: int | None = None,
    retry_on: tuple[type[Exception], ...] | None = None,
    retry_delay: float | None = None,
    log_input: bool = False,
    log_output: bool = False,
    name: str | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]: ...


def node(
    func: Callable[P, T] | None = None,
    *,
    inputs: dict[str, type[Contract]] | None = None,
    output: type[Contract] | None = None,
    requires: list[str] | None = None,
    optional: list[str] | None = None,
    provides: list[str] | None = None,
    retry: bool | Retry = False,
    retry_policy: RetryPolicy | None = None,
    retries: int | None = None,
    retry_on: tuple[type[Exception], ...] | None = None,
    retry_delay: float | None = None,
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
    6. Field-based dependency declaration (requires/optional/provides)

    Args:
        func: Function to decorate
        inputs: Dictionary mapping parameter names to expected Contract types
        output: Expected output Contract type
        requires: Required fields (node cannot execute without these)
        optional: Optional fields (used if available)
        provides: Fields this node adds to the context
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


        # RetryPolicy ショートハンド
        @node(retries=3, retry_on=(ConnectionError, TimeoutError))
        def fetch_with_retry_on() -> dict:
            return api.get("/data")

        # RetryPolicy 明示的指定
        from railway.core.retry import RetryPolicy
        @node(retry_policy=RetryPolicy(max_retries=5, backoff="exponential"))
        def fetch_with_policy() -> dict:
            return api.get("/data")
    """
    # Normalize inputs to empty dict if None
    inputs_dict = inputs or {}

    # Build field dependency
    from railway.core.dag.field_dependency import FieldDependency

    field_requires = frozenset(requires or [])
    field_optional = frozenset(optional or [])
    field_provides = frozenset(provides or [])
    field_dependency = FieldDependency(
        requires=field_requires,
        optional=field_optional,
        provides=field_provides,
    )

    # Resolve retry configuration
    # Priority: retry_policy > shorthand (retries/retry_on/retry_delay) > retry (legacy)
    resolved_retry_policy = _resolve_retry_config(
        retry=retry,
        retry_policy=retry_policy,
        retries=retries,
        retry_on=retry_on,
        retry_delay=retry_delay,
    )

    def decorator(f: Callable[P, T]) -> Callable[P, T]:
        node_name = name or f.__name__
        is_async = inspect.iscoroutinefunction(f)

        # Resolve inputs: explicit inputs take precedence, otherwise infer from hints
        resolved_inputs = inputs_dict if inputs_dict else _infer_inputs_from_hints(f)

        wrapper: Callable[P, T]
        if is_async:
            async_wrapper = _create_async_wrapper(
                cast(Callable[P, Awaitable[T]], f),
                node_name, resolved_inputs, output, retry, log_input, log_output,
                resolved_retry_policy
            )
            wrapper = cast(Callable[P, T], async_wrapper)
        else:
            wrapper = _create_sync_wrapper(
                f, node_name, resolved_inputs, output, retry, log_input, log_output,
                resolved_retry_policy
            )

        # Add field dependency metadata
        wrapper._requires = field_requires  # type: ignore[attr-defined]
        wrapper._optional = field_optional  # type: ignore[attr-defined]
        wrapper._provides = field_provides  # type: ignore[attr-defined]
        wrapper._field_dependency = field_dependency  # type: ignore[attr-defined]

        return wrapper

    # Handle decorator usage with and without parentheses
    if func is None:
        return decorator
    return decorator(func)


def _resolve_retry_config(
    retry: bool | Retry,
    retry_policy: RetryPolicy | None,
    retries: int | None,
    retry_on: tuple[type[Exception], ...] | None,
    retry_delay: float | None,
) -> RetryPolicy | None:
    """Resolve retry configuration from various parameter combinations.

    Priority: retry_policy > shorthand (retries/retry_on/retry_delay) > None

    Returns:
        RetryPolicy instance or None if no retry configured.
    """
    from railway.core.retry import RetryPolicy

    # Explicit retry_policy takes highest priority
    if retry_policy is not None:
        return retry_policy

    # Shorthand: retries + optional retry_on/retry_delay
    if retries is not None:
        return RetryPolicy(
            max_retries=retries,
            retry_on=retry_on or (Exception,),
            base_delay=retry_delay or 1.0,
        )

    # Legacy retry parameter is handled separately in _get_retry_configuration
    return None


def _infer_inputs_from_hints(func: Callable[..., Any]) -> dict[str, type[Any]]:
    """型ヒントから inputs を推論する純粋関数

    Contract のサブクラスである型ヒントのみを inputs として抽出します。
    Union 型（Optional を含む）からは Contract 型を抽出します。

    Args:
        func: 型ヒントを持つ関数

    Returns:
        パラメータ名から Contract 型へのマッピング
    """

    try:
        hints = get_type_hints(func)
    except Exception:
        # get_type_hints が失敗した場合（前方参照の解決失敗など）
        return {}

    sig = inspect.signature(func)
    result: dict[str, type[Any]] = {}

    for param_name in sig.parameters:
        if param_name not in hints:
            continue

        hint = hints[param_name]
        contract_type = _extract_contract_type(hint)

        if contract_type is not None:
            result[param_name] = contract_type

    return result


def _extract_contract_type(hint: Any) -> type[Any] | None:
    """型ヒントから Contract 型を抽出する

    Union 型（Optional を含む）の場合は、Contract サブクラスを抽出します。
    Python 3.10+ の `X | None` 構文もサポートします。

    Args:
        hint: 型ヒント

    Returns:
        Contract サブクラス、または None
    """
    import types


    # Union 型の場合（Optional[X] は Union[X, None]）
    # Python 3.10+ の X | None は types.UnionType を使用
    origin = get_origin(hint)
    is_union = origin is Union or isinstance(hint, types.UnionType)

    if is_union:
        args = get_args(hint)
        for arg in args:
            if arg is type(None):
                continue
            if _is_contract_type(arg):
                return cast(type[Any], arg)
        return None

    # 直接の Contract 型
    if _is_contract_type(hint):
        return cast(type[Any], hint)

    return None


def _is_contract_type(hint: type) -> bool:
    """Contract のサブクラスか判定する"""
    from railway.core.contract import Contract

    try:
        return isinstance(hint, type) and issubclass(hint, Contract)
    except TypeError:
        return False


def _create_sync_wrapper(
    f: Callable[P, T],
    node_name: str,
    inputs_dict: dict[str, type[Contract]],
    output_type: type[Contract] | None,
    retry: bool | Retry,
    log_input: bool,
    log_output: bool,
    retry_policy: RetryPolicy | None = None,
) -> Callable[P, T]:
    """Create wrapper for synchronous function."""

    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        # Log input if enabled
        if log_input:
            logger.debug(f"[{node_name}] 入力: args={args}, kwargs={kwargs}")

        logger.info(f"[{node_name}] 開始...")

        try:
            # Use RetryPolicy if provided, otherwise fall back to legacy retry
            if retry_policy is not None:
                result = _execute_with_retry_policy(f, retry_policy, node_name, args, kwargs)
            else:
                # Determine legacy retry configuration
                retry_config = _get_retry_configuration(retry, node_name)
                if retry_config is not None:
                    # Execute with legacy retry
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
                logger.debug(f"[{node_name}] 出力: {result}")

            logger.info(f"[{node_name}] ✓ 完了")
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
    f: Callable[P, Awaitable[T]],
    node_name: str,
    inputs_dict: dict[str, type[Contract]],
    output_type: type[Contract] | None,
    retry: bool | Retry,
    log_input: bool,
    log_output: bool,
    retry_policy: RetryPolicy | None = None,
) -> Callable[P, Awaitable[T]]:
    """Create wrapper for asynchronous function."""

    @wraps(f)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        # Log input if enabled
        if log_input:
            logger.debug(f"[{node_name}] 入力: args={args}, kwargs={kwargs}")

        logger.info(f"[{node_name}] 開始...")

        try:
            # Use RetryPolicy if provided, otherwise fall back to legacy retry
            if retry_policy is not None:
                result = await _execute_async_with_retry_policy(
                    cast(Callable[P, T], f), retry_policy, node_name, args, kwargs
                )
            else:
                # Determine legacy retry configuration
                retry_config = _get_retry_configuration(retry, node_name)
                if retry_config is not None:
                    # Execute with legacy retry
                    result = await _execute_async_with_retry(
                        cast(Callable[P, T], f), retry_config, node_name, args, kwargs
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
                logger.debug(f"[{node_name}] 出力: {result}")

            logger.info(f"[{node_name}] ✓ 完了")
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
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> T:
    """Execute async function with retry logic."""
    max_attempts = retry_config.max_attempts
    attempt_count = 0
    result: T | None = None

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
            result = await func(*args, **kwargs)  # type: ignore[misc]
            return result

    # This line should never be reached due to tenacity's reraise=True,
    # but is needed for type completeness
    raise RuntimeError("Unexpected retry loop termination")


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
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> T:
    """Execute function with retry logic."""
    attempt_count = 0
    max_attempts = retry_config.max_attempts

    def before_retry(retry_state: Any) -> None:
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
        result: T = retryable_func(*args, **kwargs)
        return result
    except RetryError as e:
        # Extract original exception
        exc = e.last_attempt.exception()
        if exc is not None:
            raise exc from None
        raise


def _execute_with_retry_policy(
    func: Callable[P, T],
    policy: RetryPolicy,
    node_name: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> T:
    """Execute function with RetryPolicy-based retry logic."""
    import time

    last_exception: Exception | None = None

    for attempt in range(1, policy.max_retries + 2):  # +2 for initial attempt + retries
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if not policy.should_retry(e, attempt):
                raise
            last_exception = e
            if attempt <= policy.max_retries:
                delay = policy.get_delay(attempt)
                logger.warning(
                    f"[{node_name}] リトライ中... (試行 {attempt}/{policy.max_retries})"
                )
                time.sleep(delay)

    # Should not reach here, but raise last exception if it does
    if last_exception is not None:
        raise last_exception
    raise RuntimeError("Unexpected retry loop termination")


async def _execute_async_with_retry_policy(
    func: Callable[P, T],
    policy: RetryPolicy,
    node_name: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> T:
    """Execute async function with RetryPolicy-based retry logic."""
    import asyncio

    last_exception: Exception | None = None

    for attempt in range(1, policy.max_retries + 2):
        try:
            # func is an async function, so func(*args, **kwargs) returns an awaitable
            awaitable: Any = func(*args, **kwargs)
            result: T = await awaitable
            return result
        except Exception as e:
            if not policy.should_retry(e, attempt):
                raise
            last_exception = e
            if attempt <= policy.max_retries:
                delay = policy.get_delay(attempt)
                logger.warning(
                    f"[{node_name}] リトライ中... (試行 {attempt}/{policy.max_retries})"
                )
                await asyncio.sleep(delay)

    if last_exception is not None:
        raise last_exception
    raise RuntimeError("Unexpected retry loop termination")


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
            logger.info(f"[{entry_name}] エントリポイント開始")
            logger.debug(f"[{entry_name}] 引数: {kwargs}")

            try:
                # Execute the main function
                _ = f(**kwargs)  # type: ignore[call-arg]

                # Log success
                logger.info(f"[{entry_name}] ✓ 正常完了")

            except KeyboardInterrupt:
                logger.warning(f"[{entry_name}] ユーザーにより中断されました")
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
