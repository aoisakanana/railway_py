# Issue #05: pipeline()関数（基本版）

**Phase:** 1a
**優先度:** 高
**依存関係:** #03
**見積もり:** 1日

---

## 概要

複数のノードを連結して実行するpipeline()関数を実装する。
基本版では同期実行のみ対応し、型チェックはデフォルト有効とする。

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/core/test_pipeline.py
"""Tests for pipeline() function."""
import pytest
from unittest.mock import patch, MagicMock


class TestPipelineBasic:
    """Test basic pipeline functionality."""

    def test_pipeline_single_step(self):
        """Should execute single step pipeline."""
        from railway.core.pipeline import pipeline

        def add_one(x: int) -> int:
            return x + 1

        result = pipeline(5, add_one)
        assert result == 6

    def test_pipeline_multiple_steps(self):
        """Should execute multiple steps sequentially."""
        from railway.core.pipeline import pipeline

        def add_one(x: int) -> int:
            return x + 1

        def multiply_two(x: int) -> int:
            return x * 2

        result = pipeline(5, add_one, multiply_two)
        assert result == 12  # (5 + 1) * 2

    def test_pipeline_with_initial_value(self):
        """Should use initial value correctly."""
        from railway.core.pipeline import pipeline

        def to_upper(s: str) -> str:
            return s.upper()

        result = pipeline("hello", to_upper)
        assert result == "HELLO"

    def test_pipeline_empty_steps(self):
        """Should return initial value when no steps."""
        from railway.core.pipeline import pipeline

        result = pipeline(42)
        assert result == 42

    def test_pipeline_passes_result_to_next_step(self):
        """Should pass each step's result to the next."""
        from railway.core.pipeline import pipeline

        call_order = []

        def step1(x: int) -> dict:
            call_order.append(("step1", x))
            return {"value": x * 2}

        def step2(data: dict) -> str:
            call_order.append(("step2", data))
            return f"Result: {data['value']}"

        result = pipeline(5, step1, step2)

        assert result == "Result: 10"
        assert call_order == [("step1", 5), ("step2", {"value": 10})]


class TestPipelineErrorHandling:
    """Test pipeline error handling."""

    def test_pipeline_stops_on_error(self):
        """Should stop execution when step raises exception."""
        from railway.core.pipeline import pipeline

        call_count = {"step2": 0, "step3": 0}

        def step1(x: int) -> int:
            return x + 1

        def step2(x: int) -> int:
            call_count["step2"] += 1
            raise ValueError("Step 2 failed")

        def step3(x: int) -> int:
            call_count["step3"] += 1
            return x * 2

        with pytest.raises(ValueError, match="Step 2 failed"):
            pipeline(5, step1, step2, step3)

        assert call_count["step2"] == 1
        assert call_count["step3"] == 0  # Never called

    def test_pipeline_propagates_exception(self):
        """Should propagate the original exception."""
        from railway.core.pipeline import pipeline

        class CustomError(Exception):
            pass

        def failing_step(x: int) -> int:
            raise CustomError("Custom error message")

        with pytest.raises(CustomError, match="Custom error message"):
            pipeline(1, failing_step)


class TestPipelineWithNodes:
    """Test pipeline with @node decorated functions."""

    def test_pipeline_with_node_functions(self):
        """Should work with @node decorated functions."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node

        @node
        def fetch(x: int) -> dict:
            return {"value": x}

        @node
        def process(data: dict) -> str:
            return str(data["value"])

        with patch("railway.core.decorators.logger"):
            result = pipeline(42, fetch, process)

        assert result == "42"

    def test_pipeline_uses_node_name(self):
        """Should use node name from metadata."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node

        @node(name="custom_fetch")
        def fetch(x: int) -> int:
            return x + 1

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger") as mock_logger:
                pipeline(1, fetch)

                # Should log with node name
                debug_calls = str(mock_logger.debug.call_args_list)
                assert "custom_fetch" in debug_calls or "fetch" in debug_calls


class TestPipelineLogging:
    """Test pipeline logging."""

    def test_pipeline_logs_start(self):
        """Should log pipeline start."""
        from railway.core.pipeline import pipeline

        with patch("railway.core.pipeline.logger") as mock_logger:
            pipeline(1, lambda x: x)

            debug_calls = str(mock_logger.debug.call_args_list)
            assert "starting" in debug_calls.lower()

    def test_pipeline_logs_step_execution(self):
        """Should log each step execution."""
        from railway.core.pipeline import pipeline

        def step1(x: int) -> int:
            return x + 1

        def step2(x: int) -> int:
            return x * 2

        with patch("railway.core.pipeline.logger") as mock_logger:
            pipeline(1, step1, step2)

            # Should log step progress
            debug_calls = str(mock_logger.debug.call_args_list)
            assert "1" in debug_calls and "2" in debug_calls

    def test_pipeline_logs_completion(self):
        """Should log pipeline completion."""
        from railway.core.pipeline import pipeline

        with patch("railway.core.pipeline.logger") as mock_logger:
            pipeline(1, lambda x: x)

            debug_calls = str(mock_logger.debug.call_args_list)
            assert "completed" in debug_calls.lower()

    def test_pipeline_logs_error(self):
        """Should log error when step fails."""
        from railway.core.pipeline import pipeline

        def failing_step(x: int) -> int:
            raise ValueError("Test error")

        with patch("railway.core.pipeline.logger") as mock_logger:
            with pytest.raises(ValueError):
                pipeline(1, failing_step)

            mock_logger.error.assert_called()


class TestPipelineAsyncRejection:
    """Test that async functions are rejected."""

    def test_rejects_async_function(self):
        """Should reject async functions with clear error."""
        from railway.core.pipeline import pipeline
        import asyncio

        async def async_step(x: int) -> int:
            return x + 1

        with pytest.raises(TypeError) as exc_info:
            pipeline(1, async_step)

        error_msg = str(exc_info.value)
        assert "async" in error_msg.lower()
        assert "async_step" in error_msg

    def test_rejects_async_node(self):
        """Should reject async @node functions."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node

        @node
        async def async_node(x: int) -> int:
            return x + 1

        with pytest.raises(TypeError) as exc_info:
            pipeline(1, async_node)

        assert "async" in str(exc_info.value).lower()


class TestPipelineTypeCheck:
    """Test pipeline type checking (default enabled)."""

    def test_type_check_enabled_by_default(self):
        """Type check should be enabled by default."""
        # This test verifies the signature
        from railway.core.pipeline import pipeline
        import inspect

        sig = inspect.signature(pipeline)
        type_check_param = sig.parameters.get("type_check")

        assert type_check_param is not None
        assert type_check_param.default is True

    def test_type_check_can_be_disabled(self):
        """Should allow disabling type check."""
        from railway.core.pipeline import pipeline

        def returns_str(x: int) -> str:
            return str(x)

        def expects_int(x: int) -> int:
            return x + 1

        # With type_check=False, this should run (may fail at runtime)
        # but the pipeline itself shouldn't raise TypeError
        result = pipeline(1, returns_str, type_check=False)
        assert result == "1"
```

```bash
# 実行して失敗を確認
pytest tests/unit/core/test_pipeline.py -v
# Expected: FAILED (ImportError)
```

### Step 2: Green（最小限の実装）

```python
# railway/core/pipeline.py
"""
Pipeline execution for Railway Framework.
"""
from typing import TypeVar, Callable, Any, get_type_hints
from loguru import logger
import asyncio
import inspect

T = TypeVar('T')


def pipeline(
    initial: Any,
    *steps: Callable[[Any], Any],
    type_check: bool = True,
    strict: bool = False,
) -> Any:
    """
    Execute a pipeline of processing steps.

    Features:
    1. Sequential execution of steps
    2. Automatic error propagation (skip remaining steps on error)
    3. Runtime type checking between steps (enabled by default)
    4. Detailed logging of execution flow

    IMPORTANT: Understanding the 'initial' argument
    -----------------------------------------------
    The 'initial' argument is the STARTING VALUE for the pipeline.
    It is NOT a function, but a value (or the result of a function call).

    Args:
        initial: Initial value to pass to first step
        *steps: Processing functions to apply sequentially
        type_check: Enable runtime type checking (default: True)
        strict: Require type hints on all steps (default: False)

    Returns:
        Final result from the last step

    Raises:
        Exception: If any step fails
        TypeError: If an async function is passed

    Example:
        result = pipeline(
            fetch_data(),   # Initial value (evaluated immediately)
            process_data,   # Step 1: receives result of fetch_data()
            save_data,      # Step 2: receives result of process_data()
        )
    """
    # Check for async functions (not supported in Phase 1)
    for step in steps:
        # Check the original function if it's a decorated node
        func_to_check = getattr(step, '_original_func', step)
        if asyncio.iscoroutinefunction(func_to_check):
            step_name = getattr(step, '_node_name', step.__name__)
            raise TypeError(
                f"Async function '{step_name}' cannot be used in pipeline(). "
                "Phase 1 supports only synchronous nodes in pipeline(). "
                "Options:\n"
                f"  1. Use 'await {step_name}(value)' directly\n"
                "  2. Wait for pipeline_async() in Phase 2\n"
                "  3. Convert to synchronous function if possible"
            )

    logger.debug(f"Pipeline starting with {len(steps)} steps")

    # Return initial value if no steps
    if not steps:
        return initial

    current_value = initial
    current_step = 0

    try:
        for i, step in enumerate(steps, 1):
            current_step = i
            step_name = getattr(step, '_node_name', step.__name__)

            logger.debug(f"Pipeline step {i}/{len(steps)}: {step_name}")

            try:
                result = step(current_value)
                current_value = result
                logger.debug(f"Pipeline step {i}/{len(steps)}: ✓ Success")

            except Exception as e:
                logger.error(
                    f"Pipeline step {i}/{len(steps)} ({step_name}): "
                    f"✗ Failed with {type(e).__name__}: {e}"
                )
                logger.info(f"Pipeline: Skipping remaining {len(steps) - i} steps")
                raise

        logger.debug("Pipeline completed successfully")
        return current_value

    except Exception as e:
        logger.error(f"Pipeline failed at step {current_step}/{len(steps)}")
        raise
```

```bash
# 実行して成功を確認
pytest tests/unit/core/test_pipeline.py -v
# Expected: PASSED
```

### Step 3: Refactor

- 型チェックロジックの追加（Phase 1c で詳細実装）
- エラーメッセージの改善

---

## 完了条件

- [ ] 単一ステップのパイプラインが動作する
- [ ] 複数ステップが順次実行される
- [ ] ステップ間で結果が正しく渡される
- [ ] エラー発生時に後続ステップがスキップされる
- [ ] 例外が適切に伝播される
- [ ] @nodeデコレータ付き関数と動作する
- [ ] 非同期関数が明確なエラーで拒否される
- [ ] 開始・ステップ・完了・エラーがログ出力される
- [ ] テストカバレッジ90%以上

---

## 次のIssue

- #06: 設定管理（Settings）
