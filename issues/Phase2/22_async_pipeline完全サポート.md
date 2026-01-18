# Issue #22: async_pipeline完全サポート

**Phase:** 2a
**優先度:** 高
**依存関係:** #17 (非同期ノード基本サポート), #21 (並列パイプライン実行)
**見積もり:** 3日

---

## 概要

Phase 1では `@node` で `async def` をサポートしましたが、`pipeline()` は同期ノードのみ対応でした。
Phase 2では `async_pipeline()` を実装し、同期・非同期ノードを混在させたパイプライン実行を可能にします。

---

## TDD実装手順

### Step 1: async_pipelineのテスト (Red)

```python
# tests/unit/core/test_async_pipeline_full.py
"""Tests for complete async_pipeline support."""
import pytest
import asyncio
from unittest.mock import patch


class TestAsyncPipelineBasic:
    """Test basic async_pipeline functionality."""

    @pytest.mark.asyncio
    async def test_async_pipeline_with_async_nodes(self):
        """Should execute async nodes in async_pipeline."""
        from railway.core.decorators import node
        from railway.core.pipeline import async_pipeline

        @node
        async def async_fetch(url: str) -> dict:
            await asyncio.sleep(0.01)
            return {"url": url, "data": "fetched"}

        @node
        async def async_process(data: dict) -> dict:
            await asyncio.sleep(0.01)
            data["processed"] = True
            return data

        @node
        async def async_save(data: dict) -> str:
            await asyncio.sleep(0.01)
            return f"Saved: {data['url']}"

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                result = await async_pipeline(
                    "https://api.example.com",
                    async_fetch,
                    async_process,
                    async_save
                )

        assert result == "Saved: https://api.example.com"

    @pytest.mark.asyncio
    async def test_async_pipeline_with_sync_nodes(self):
        """Should execute sync nodes in async_pipeline."""
        from railway.core.decorators import node
        from railway.core.pipeline import async_pipeline

        @node
        def sync_fetch(x: int) -> int:
            return x + 1

        @node
        def sync_double(x: int) -> int:
            return x * 2

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                result = await async_pipeline(
                    1,
                    sync_fetch,  # Sync node in async pipeline
                    sync_double
                )

        assert result == 4  # (1 + 1) * 2

    @pytest.mark.asyncio
    async def test_async_pipeline_mixed_nodes(self):
        """Should mix sync and async nodes in async_pipeline."""
        from railway.core.decorators import node
        from railway.core.pipeline import async_pipeline

        execution_log = []

        @node
        async def async_step(x: int) -> int:
            execution_log.append(('async', x))
            await asyncio.sleep(0.01)
            return x + 1

        @node
        def sync_step(x: int) -> int:
            execution_log.append(('sync', x))
            return x * 2

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                result = await async_pipeline(
                    1,
                    async_step,  # Async
                    sync_step,   # Sync
                    async_step,  # Async
                    sync_step    # Sync
                )

        assert result == ((1 + 1) * 2 + 1) * 2  # 10
        assert len(execution_log) == 4
        assert execution_log[0][0] == 'async'
        assert execution_log[1][0] == 'sync'


class TestAsyncPipelineParallel:
    """Test parallel execution in async_pipeline."""

    @pytest.mark.asyncio
    async def test_async_pipeline_parallel_gather(self):
        """Should gather multiple async tasks in parallel."""
        from railway.core.decorators import node
        from railway.core.pipeline import async_pipeline, parallel

        @node
        async def fetch_api1(x: int) -> int:
            await asyncio.sleep(0.1)
            return x + 1

        @node
        async def fetch_api2(x: int) -> int:
            await asyncio.sleep(0.1)
            return x + 2

        @node
        async def fetch_api3(x: int) -> int:
            await asyncio.sleep(0.1)
            return x + 3

        @node
        def aggregate(results: list) -> int:
            return sum(results)

        import time
        start = time.time()

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                result = await async_pipeline(
                    1,
                    parallel([fetch_api1, fetch_api2, fetch_api3]),
                    aggregate
                )

        elapsed = time.time() - start

        assert result == (1+1) + (1+2) + (1+3)  # 9
        assert elapsed < 0.2  # Should be ~0.1s, not ~0.3s

    @pytest.mark.asyncio
    async def test_async_pipeline_parallel_mixed_sync_async(self):
        """Should handle mixed sync/async nodes in parallel."""
        from railway.core.decorators import node
        from railway.core.pipeline import async_pipeline, parallel

        @node
        async def async_task(x: int) -> int:
            await asyncio.sleep(0.01)
            return x + 1

        @node
        def sync_task(x: int) -> int:
            return x + 2

        @node
        def combine(results: list) -> int:
            return sum(results)

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                result = await async_pipeline(
                    1,
                    parallel([async_task, sync_task]),  # Mix sync/async
                    combine
                )

        assert result == (1+1) + (1+2)  # 5


class TestAsyncPipelineErrors:
    """Test error handling in async_pipeline."""

    @pytest.mark.asyncio
    async def test_async_pipeline_propagates_async_error(self):
        """Should propagate error from async node."""
        from railway.core.decorators import node
        from railway.core.pipeline import async_pipeline

        @node
        async def failing_async(x: int) -> int:
            await asyncio.sleep(0.01)
            raise ValueError("Async task failed")

        @node
        async def never_called(x: int) -> int:
            return x + 1

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                with pytest.raises(ValueError, match="Async task failed"):
                    await async_pipeline(
                        1,
                        failing_async,
                        never_called
                    )

    @pytest.mark.asyncio
    async def test_async_pipeline_retry_async_node(self):
        """Should retry failed async nodes."""
        from railway.core.decorators import node, Retry
        from railway.core.pipeline import async_pipeline

        attempt_count = 0

        @node(retry=Retry(max_attempts=3, min_wait=0.01, max_wait=0.02))
        async def flaky_async(x: int) -> int:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ConnectionError("Temporary failure")
            await asyncio.sleep(0.01)
            return x + 1

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                result = await async_pipeline(1, flaky_async)

        assert result == 2
        assert attempt_count == 2


class TestAsyncPipelineTypeCheck:
    """Test type checking in async_pipeline."""

    @pytest.mark.asyncio
    async def test_async_pipeline_strict_mode(self):
        """Should check types in strict mode."""
        from railway.core.decorators import node
        from railway.core.pipeline import async_pipeline

        @node
        async def returns_int(x: int) -> int:
            return x + 1

        @node
        async def expects_str(x: str) -> str:
            return x.upper()

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                with pytest.raises(TypeError):
                    await async_pipeline(
                        1,
                        returns_int,  # Returns int
                        expects_str,  # Expects str
                        strict=True
                    )
```

```bash
# 実行して失敗を確認 (Red)
pytest tests/unit/core/test_async_pipeline_full.py -v
# Expected: FAILED (async_pipeline not implemented)
```

---

### Step 2: async_pipelineの実装 (Green)

```python
# railway/core/pipeline.py に追加

import asyncio
import inspect
from typing import Awaitable


async def async_pipeline(
    initial: T,
    *steps: Callable | ParallelGroup,
    strict: bool = False,
    type_check: bool = True,
    max_workers: int = 4,
    timeout: float | None = None
) -> Any:
    """
    Execute an asynchronous pipeline with support for mixed sync/async nodes.

    This function can execute both synchronous and asynchronous nodes.
    Sync nodes are automatically wrapped to run in the event loop.

    Args:
        initial: Initial value to pass to first step
        *steps: Processing functions (sync or async) or ParallelGroup instances
        strict: Enable strict type checking
        type_check: Enable runtime type checking
        max_workers: Maximum number of parallel workers
        timeout: Timeout for each parallel group (seconds)

    Returns:
        Final result from the last step

    Raises:
        Exception: If any step fails
        TypeError: If type mismatch in strict mode
        TimeoutError: If parallel execution exceeds timeout

    Example:
        # All async nodes
        result = await async_pipeline(
            "https://api.example.com",
            async_fetch,
            async_process,
            async_save
        )

        # Mixed sync and async
        result = await async_pipeline(
            data,
            async_fetch,   # Async
            sync_process,  # Sync (automatically handled)
            async_save     # Async
        )

        # Parallel async execution
        result = await async_pipeline(
            data,
            parallel([async_api1, async_api2, async_api3]),
            aggregate
        )
    """
    from loguru import logger

    logger.debug(f"Async pipeline starting with {len(steps)} steps")
    current_value = initial

    for step_idx, step in enumerate(steps, 1):
        if isinstance(step, ParallelGroup):
            # Execute functions in parallel (async)
            logger.debug(f"Step {step_idx}: Parallel async execution of {len(step.functions)} functions")
            results = await _execute_async_parallel(current_value, step.functions, timeout)
            current_value = results
        else:
            # Sequential execution (sync or async)
            func_name = step.__name__ if hasattr(step, '__name__') else str(step)
            logger.debug(f"Step {step_idx}: Executing {func_name}")

            # Type check if enabled
            if type_check or strict:
                _check_step_types(step, current_value, step_idx, strict)

            # Execute step (handle both sync and async)
            try:
                if asyncio.iscoroutinefunction(step):
                    # Async function
                    current_value = await step(current_value)
                else:
                    # Sync function - run in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    current_value = await loop.run_in_executor(
                        None, step, current_value
                    )
            except Exception as e:
                logger.error(f"Step {step_idx} ({func_name}) failed: {e}")
                raise

    logger.debug("Async pipeline completed successfully")
    return current_value


async def _execute_async_parallel(
    input_value: Any,
    functions: List[Callable],
    timeout: float | None = None
) -> List[Any]:
    """
    Execute multiple functions in parallel using asyncio.gather.

    Handles both sync and async functions.

    Args:
        input_value: Input value to pass to all functions
        functions: List of functions to execute (sync or async)
        timeout: Timeout for parallel execution (seconds)

    Returns:
        List of results from all functions

    Raises:
        Exception: If any function fails
        asyncio.TimeoutError: If execution exceeds timeout
    """
    from loguru import logger

    # Create tasks for all functions
    tasks = []
    for func in functions:
        if asyncio.iscoroutinefunction(func):
            # Async function
            task = func(input_value)
        else:
            # Sync function - wrap in coroutine
            loop = asyncio.get_event_loop()
            task = loop.run_in_executor(None, func, input_value)
        tasks.append(task)

    # Execute all tasks in parallel
    try:
        if timeout:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks),
                timeout=timeout
            )
        else:
            results = await asyncio.gather(*tasks)

        for i, func in enumerate(functions):
            func_name = func.__name__ if hasattr(func, '__name__') else str(func)
            logger.debug(f"Parallel async task {func_name} completed successfully")

        return results

    except asyncio.TimeoutError:
        logger.error(f"Parallel async execution exceeded timeout of {timeout}s")
        raise TimeoutError(f"Parallel async execution exceeded timeout of {timeout}s")
    except Exception as e:
        logger.error(f"Parallel async execution failed: {e}")
        raise
```

```bash
# 実行して成功を確認 (Green)
pytest tests/unit/core/test_async_pipeline_full.py -v
# Expected: PASSED
```

---

## 完了条件

- [x] `async_pipeline()` 関数の実装
- [x] 同期ノードの自動ラップ (run_in_executor)
- [x] 非同期ノードの直接実行
- [x] `asyncio.gather` による並列実行
- [x] エラーハンドリング
- [x] タイムアウト機能
- [x] 型チェック対応
- [x] リトライ機能との統合
- [x] テスト (15テスト以上)
- [x] テストカバレッジ 90%以上
- [x] ドキュメント更新
- [x] readme.md の使用例更新

---

## 設計判断

### run_in_executor vs ThreadPoolExecutor
- **選択:** run_in_executor
- **理由:**
  - 既存のイベントループと統合
  - コンテキスト管理が容易
  - 標準的な asyncio パターン

### asyncio.gather vs asyncio.wait
- **選択:** asyncio.gather
- **理由:**
  - 結果の順序が保証される
  - エラーハンドリングがシンプル
  - より高レベルなAPI

---

## 関連Issue

- Issue #17: 非同期ノード基本サポート (Phase 1で実装済み)
- Issue #21: 並列パイプライン実行 (同期版の並列実行)
- Issue #23: ストリーミング処理 (非同期ストリーム)

---

## Phase 2aへの影響

`async_pipeline()` の実装により、高速なI/O処理が可能になり、
API統合やWebスクレイピングなどのユースケースで大幅な性能向上が期待できます。
