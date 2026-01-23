"""Tests for async node support."""

import asyncio

import pytest
from unittest.mock import patch, MagicMock


class TestAsyncNodeBasic:
    """Test basic async node functionality."""

    @pytest.mark.asyncio
    async def test_async_node_execution(self):
        """Should execute async node."""
        from railway.core.decorators import node

        @node
        async def async_fetch() -> str:
            await asyncio.sleep(0.01)
            return "data"

        with patch("railway.core.decorators.logger"):
            result = await async_fetch()

        assert result == "data"

    @pytest.mark.asyncio
    async def test_async_node_with_args(self):
        """Should pass arguments to async node."""
        from railway.core.decorators import node

        @node
        async def async_process(x: int, y: int) -> int:
            await asyncio.sleep(0.01)
            return x + y

        with patch("railway.core.decorators.logger"):
            result = await async_process(3, 4)

        assert result == 7

    @pytest.mark.asyncio
    async def test_async_node_logging(self):
        """Should log async node execution."""
        from railway.core.decorators import node

        @node
        async def logged_async() -> str:
            return "logged"

        with patch("railway.core.decorators.logger") as mock_logger:
            await logged_async()

            # Should have start and complete logs (日本語)
            info_calls = [str(c) for c in mock_logger.info.call_args_list]
            assert any("開始" in str(c) for c in info_calls)
            assert any("完了" in str(c) for c in info_calls)


class TestAsyncNodeMetadata:
    """Test async node metadata."""

    def test_async_node_has_metadata(self):
        """Should have _is_async=True metadata."""
        from railway.core.decorators import node

        @node
        async def async_func() -> str:
            return "async"

        assert hasattr(async_func, "_is_railway_node")
        assert async_func._is_railway_node is True
        assert hasattr(async_func, "_is_async")
        assert async_func._is_async is True

    def test_sync_node_has_async_false(self):
        """Sync node should have _is_async=False."""
        from railway.core.decorators import node

        @node
        def sync_func() -> str:
            return "sync"

        assert hasattr(sync_func, "_is_async")
        assert sync_func._is_async is False


class TestAsyncNodeErrors:
    """Test async node error handling."""

    @pytest.mark.asyncio
    async def test_async_node_propagates_error(self):
        """Should propagate errors from async node."""
        from railway.core.decorators import node

        @node
        async def failing_async() -> str:
            await asyncio.sleep(0.01)
            raise ValueError("Async error")

        with patch("railway.core.decorators.logger"):
            with pytest.raises(ValueError, match="Async error"):
                await failing_async()

    @pytest.mark.asyncio
    async def test_async_node_logs_error(self):
        """Should log errors from async node."""
        from railway.core.decorators import node

        @node
        async def error_async() -> str:
            raise RuntimeError("Runtime error")

        with patch("railway.core.decorators.logger") as mock_logger:
            with pytest.raises(RuntimeError):
                await error_async()

            error_calls = [str(c) for c in mock_logger.error.call_args_list]
            assert any("RuntimeError" in str(c) for c in error_calls)


class TestAsyncPipeline:
    """Test async pipeline support."""

    @pytest.mark.asyncio
    async def test_async_pipeline_basic(self):
        """Should execute async pipeline."""
        from railway.core.pipeline import async_pipeline
        from railway.core.decorators import node

        @node
        async def step1(x: int) -> int:
            await asyncio.sleep(0.01)
            return x + 1

        @node
        async def step2(x: int) -> int:
            await asyncio.sleep(0.01)
            return x * 2

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                result = await async_pipeline(1, step1, step2)

        assert result == 4  # (1 + 1) * 2

    @pytest.mark.asyncio
    async def test_async_pipeline_with_sync_nodes(self):
        """Should handle mixed sync/async nodes."""
        from railway.core.pipeline import async_pipeline
        from railway.core.decorators import node

        @node
        def sync_step(x: int) -> int:
            return x + 1

        @node
        async def async_step(x: int) -> int:
            await asyncio.sleep(0.01)
            return x * 2

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                result = await async_pipeline(1, sync_step, async_step)

        assert result == 4  # (1 + 1) * 2


class TestSyncPipelineRejectsAsync:
    """Test that sync pipeline rejects async nodes."""

    def test_sync_pipeline_rejects_async_node(self):
        """Should raise error when async node in sync pipeline."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node

        @node
        async def async_node(x: int) -> int:
            return x + 1

        with pytest.raises(TypeError) as exc_info:
            pipeline(1, async_node)

        assert "async" in str(exc_info.value).lower()


class TestAsyncNodeWithRetry:
    """Test async node with retry functionality."""

    @pytest.mark.asyncio
    async def test_async_node_retry(self):
        """Should retry async node on failure."""
        from railway.core.decorators import node, Retry

        call_count = 0

        @node(retry=Retry(max_attempts=3, min_wait=0.01, max_wait=0.02))
        async def flaky_async() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        with patch("railway.core.decorators.logger"):
            result = await flaky_async()

        assert result == "success"
        assert call_count == 3
