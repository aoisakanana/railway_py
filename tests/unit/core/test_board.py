"""Tests for BoardBase and WorkflowResult (Issue 19-01)."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from railway.core.board import BoardBase, WorkflowResult


class TestBoardBaseInit:
    """BoardBase の初期化テスト。"""

    def test_empty_init(self) -> None:
        board = BoardBase()
        assert board._field_names() == frozenset()

    def test_kwargs_init(self) -> None:
        board = BoardBase(name="test", count=42)
        assert board.name == "test"
        assert board.count == 42

    def test_field_names_returns_frozenset(self) -> None:
        board = BoardBase(a=1, b=2)
        assert board._field_names() == frozenset({"a", "b"})


class TestBoardBaseReadWrite:
    """BoardBase の読み書きテスト。"""

    def test_write_new_field(self) -> None:
        board = BoardBase()
        board.hostname = "server-01"
        assert board.hostname == "server-01"

    def test_overwrite_field(self) -> None:
        board = BoardBase(count=0)
        board.count = 42
        assert board.count == 42

    def test_read_undefined_field_raises(self) -> None:
        board = BoardBase()
        with pytest.raises(AttributeError):
            _ = board.undefined_field

    def test_write_then_read(self) -> None:
        board = BoardBase()
        board.escalated = True
        board.notified_at = "2026-03-10"
        assert board.escalated is True
        assert board.notified_at == "2026-03-10"


class TestBoardBaseSnapshot:
    """BoardBase のスナップショットテスト。"""

    def test_snapshot_empty(self) -> None:
        board = BoardBase()
        assert board._snapshot() == {}

    def test_snapshot_captures_all_fields(self) -> None:
        board = BoardBase(a=1, b="two")
        snap = board._snapshot()
        assert snap == {"a": 1, "b": "two"}

    def test_snapshot_is_independent_copy(self) -> None:
        board = BoardBase(x=1)
        snap = board._snapshot()
        board.x = 999
        assert snap["x"] == 1

    def test_snapshot_after_mutation(self) -> None:
        board = BoardBase(x=1)
        board.x = 2
        board.y = 3
        assert board._snapshot() == {"x": 2, "y": 3}


class TestBoardBaseRepr:
    """BoardBase の repr テスト。"""

    def test_repr_empty(self) -> None:
        board = BoardBase()
        assert repr(board) == "BoardBase()"

    def test_repr_with_fields(self) -> None:
        board = BoardBase(name="test")
        assert "name='test'" in repr(board)

    def test_repr_subclass(self) -> None:
        class MyBoard(BoardBase):
            pass
        board = MyBoard(x=1)
        assert repr(board).startswith("MyBoard(")


class TestBoardBaseIsMutable:
    """BoardBase が mutable であることのテスト。"""

    def test_is_not_frozen(self) -> None:
        board = BoardBase(x=1)
        board.x = 2
        assert board.x == 2

    def test_multiple_mutations(self) -> None:
        board = BoardBase()
        board.step1 = "done"
        board.step2 = "done"
        board.step3 = "done"
        assert board._field_names() == frozenset({"step1", "step2", "step3"})


class TestWorkflowResultSuccess:
    """WorkflowResult の成功ケーステスト。"""

    def test_success_result(self) -> None:
        board = BoardBase(total=42)
        result = WorkflowResult(
            exit_state="success.done",
            exit_code=0,
            board=board,
            execution_path=("start", "exit.success.done"),
            iterations=2,
        )
        assert result.is_success is True
        assert result.is_failure is False
        assert result.exit_code == 0
        assert result.exit_state == "success.done"
        assert result.board.total == 42

    def test_failure_result(self) -> None:
        board = BoardBase(error="timeout")
        result = WorkflowResult(
            exit_state="failure.timeout",
            exit_code=1,
            board=board,
        )
        assert result.is_success is False
        assert result.is_failure is True
        assert result.exit_code == 1

    def test_frozen(self) -> None:
        board = BoardBase()
        result = WorkflowResult(
            exit_state="success.done",
            exit_code=0,
            board=board,
        )
        with pytest.raises(FrozenInstanceError):
            result.exit_code = 99  # type: ignore[misc]

    def test_defaults(self) -> None:
        board = BoardBase()
        result = WorkflowResult(
            exit_state="success.done",
            exit_code=0,
            board=board,
        )
        assert result.execution_path == ()
        assert result.iterations == 0
        assert result.trace is None

    def test_board_accessible(self) -> None:
        board = BoardBase(processed=10, skipped=2)
        result = WorkflowResult(
            exit_state="success.done",
            exit_code=0,
            board=board,
        )
        assert result.board.processed == 10
        assert result.board.skipped == 2
