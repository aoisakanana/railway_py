"""Tests for failure outcome display in @node decorator.

Issue 37-01: @node decorator shows success log even on failure outcome.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from loguru import logger

from railway.core.dag import Outcome
from railway.core.decorators import _is_failure_outcome


class TestIsFailureOutcome:
    """Pure function tests for _is_failure_outcome."""

    def test_failure_outcome_detected(self) -> None:
        assert _is_failure_outcome(Outcome.failure("error")) is True

    def test_success_outcome_not_failure(self) -> None:
        assert _is_failure_outcome(Outcome.success("done")) is False

    def test_tuple_with_failure_outcome(self) -> None:
        mock_contract = MagicMock()
        result = (mock_contract, Outcome.failure("error"))
        assert _is_failure_outcome(result) is True

    def test_tuple_with_success_outcome(self) -> None:
        mock_contract = MagicMock()
        result = (mock_contract, Outcome.success("done"))
        assert _is_failure_outcome(result) is False

    def test_non_outcome_returns_false(self) -> None:
        assert _is_failure_outcome("string") is False
        assert _is_failure_outcome(42) is False
        assert _is_failure_outcome(None) is False


class TestFailureOutcomeDisplay:
    """Integration tests: verify log output for failure/success outcomes."""

    def test_sync_node_logs_warning_on_failure(self) -> None:
        from railway import node
        from railway.core.board import BoardBase

        @node
        def failing_node(board) -> Outcome:  # type: ignore[type-arg]
            return Outcome.failure("error")

        messages: list[str] = []
        sink_id = logger.add(lambda m: messages.append(m), format="{message}")
        try:
            failing_node(BoardBase())
        finally:
            logger.remove(sink_id)

        combined = "\n".join(messages)
        assert "\u26a0 \u5b8c\u4e86(failure)" in combined

    def test_sync_node_logs_success_on_success(self) -> None:
        from railway import node
        from railway.core.board import BoardBase

        @node
        def passing_node(board) -> Outcome:  # type: ignore[type-arg]
            return Outcome.success("done")

        messages: list[str] = []
        sink_id = logger.add(lambda m: messages.append(m), format="{message}")
        try:
            passing_node(BoardBase())
        finally:
            logger.remove(sink_id)

        combined = "\n".join(messages)
        assert "\u2713 \u5b8c\u4e86" in combined
        assert "\u26a0 \u5b8c\u4e86(failure)" not in combined

    @pytest.mark.asyncio
    async def test_async_node_logs_warning_on_failure(self) -> None:
        from railway import node
        from railway.core.board import BoardBase

        @node
        async def async_failing_node(board) -> Outcome:  # type: ignore[type-arg]
            return Outcome.failure("timeout")

        messages: list[str] = []
        sink_id = logger.add(lambda m: messages.append(m), format="{message}")
        try:
            await async_failing_node(BoardBase())
        finally:
            logger.remove(sink_id)

        combined = "\n".join(messages)
        assert "\u26a0 \u5b8c\u4e86(failure)" in combined

    @pytest.mark.asyncio
    async def test_async_node_logs_success_on_success(self) -> None:
        from railway import node
        from railway.core.board import BoardBase

        @node
        async def async_passing_node(board) -> Outcome:  # type: ignore[type-arg]
            return Outcome.success("done")

        messages: list[str] = []
        sink_id = logger.add(lambda m: messages.append(m), format="{message}")
        try:
            await async_passing_node(BoardBase())
        finally:
            logger.remove(sink_id)

        combined = "\n".join(messages)
        assert "\u2713 \u5b8c\u4e86" in combined
        assert "\u26a0 \u5b8c\u4e86(failure)" not in combined
