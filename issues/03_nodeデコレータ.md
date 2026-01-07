# Issue #03: @nodeデコレータ（基本版）

**Phase:** 1a
**優先度:** 高
**依存関係:** #02
**見積もり:** 1日

---

## 概要

処理単位（ノード）を定義するための@nodeデコレータを実装する。
基本版ではリトライ機能は含めず、ロギングと例外処理のみ実装する。

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/core/test_decorators.py
"""Tests for @node decorator."""
import pytest
from unittest.mock import patch, MagicMock


class TestNodeDecorator:
    """Test @node decorator functionality."""

    def test_node_without_parentheses(self):
        """Should work without parentheses."""
        from railway.core.decorators import node

        @node
        def simple_node(x: int) -> int:
            return x + 1

        result = simple_node(5)
        assert result == 6

    def test_node_with_parentheses(self):
        """Should work with empty parentheses."""
        from railway.core.decorators import node

        @node()
        def simple_node(x: int) -> int:
            return x * 2

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

        result = add_node(3, 4)
        assert result == 7

    def test_node_with_kwargs(self):
        """Should pass keyword arguments correctly."""
        from railway.core.decorators import node

        @node
        def greeting_node(name: str, prefix: str = "Hello") -> str:
            return f"{prefix}, {name}!"

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
```

```bash
# 実行して失敗を確認
pytest tests/unit/core/test_decorators.py -v
# Expected: FAILED (ImportError)
```

### Step 2: Green（最小限の実装）

```python
# railway/core/decorators.py
"""
Decorators for Railway nodes and entry points.
"""
from functools import wraps
from typing import Callable, TypeVar, ParamSpec, Any
from loguru import logger

P = ParamSpec('P')
T = TypeVar('T')


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
        wrapper._is_railway_node = True  # type: ignore
        wrapper._node_name = node_name  # type: ignore
        wrapper._original_func = f  # type: ignore
        wrapper._is_async = False  # type: ignore

        return wrapper

    # Handle decorator usage with and without parentheses
    if func is None:
        return decorator
    return decorator(func)
```

```bash
# 実行して成功を確認
pytest tests/unit/core/test_decorators.py -v
# Expected: PASSED
```

### Step 3: Refactor

- 型ヒントの改善
- エラーメッセージの統一

---

## 完了条件

- [ ] `@node` と `@node()` の両方で動作する
- [ ] 関数名とdocstringが保持される
- [ ] `_is_railway_node`, `_node_name` メタデータが設定される
- [ ] 開始・完了・エラーがログ出力される
- [ ] `log_input=True` で入力がログ出力される
- [ ] `log_output=True` で出力がログ出力される
- [ ] 例外が適切に伝播される
- [ ] テストカバレッジ90%以上

---

## 次のIssue

- #04: @entry_pointデコレータ
- #05: pipeline()関数
