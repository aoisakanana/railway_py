"""Tests for _format_exit_outcome (Issue 41-01).

NodeTrace の outcome フィールドがノード種類間で統一された :: 区切りを使うことを検証する。
"""
from __future__ import annotations

import pytest

from railway.core.dag.runner import _format_exit_outcome


class TestFormatExitOutcome:
    """_format_exit_outcome 純粋関数のテスト。"""

    def test_success_done(self) -> None:
        """success.done → exit::success::done"""
        assert _format_exit_outcome("success.done") == "exit::success::done"

    def test_failure_timeout(self) -> None:
        """failure.timeout → exit::failure::timeout"""
        assert _format_exit_outcome("failure.timeout") == "exit::failure::timeout"

    def test_deep_nesting(self) -> None:
        """failure.ssh.handshake → exit::failure::ssh::handshake"""
        assert (
            _format_exit_outcome("failure.ssh.handshake")
            == "exit::failure::ssh::handshake"
        )

    def test_single_segment(self) -> None:
        """done → exit::done（ドットなしの場合）"""
        assert _format_exit_outcome("done") == "exit::done"


class TestFormatExitOutcomePurity:
    """_format_exit_outcome が純粋関数であることのテスト。"""

    def test_same_input_same_output(self) -> None:
        """同じ入力に対して常に同じ出力を返す。"""
        assert _format_exit_outcome("success.done") == _format_exit_outcome(
            "success.done"
        )


class TestNodeTraceOutcomeConsistency:
    """統合テスト: Board mode runner の exit outcome が :: 区切りを使うこと。"""

    def test_board_runner_exit_outcome_uses_double_colon(self) -> None:
        """Board mode runner が exit outcome に :: 区切りを使うこと。"""
        from railway.core.board import BoardBase
        from railway.core.dag.outcome import Outcome
        from railway.core.dag.runner import dag_runner

        def start(board) -> Outcome:  # type: ignore[no-untyped-def]
            board.handled = True
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        def exit_done(board) -> None:  # type: ignore[no-untyped-def]
            pass

        exit_done._node_name = "exit.success.done"  # type: ignore[attr-defined]

        transitions: dict = {"start::success::done": exit_done}
        board = BoardBase()
        result = dag_runner(
            start=start, transitions=transitions, board=board, trace=True
        )
        assert result.trace is not None

        # 最後のトレースが終端ノード
        exit_trace = result.trace.traces[-1]
        assert exit_trace.node_name == "exit.success.done"
        # outcome は :: 区切りで統一されていること（ドット混在ではない）
        assert exit_trace.outcome == "exit::success::done"
        assert "." not in exit_trace.outcome

    def test_board_runner_on_step_exit_outcome_uses_double_colon(self) -> None:
        """Board mode の on_step コールバックも :: 区切りを使うこと。"""
        from railway.core.board import BoardBase
        from railway.core.dag.outcome import Outcome
        from railway.core.dag.runner import dag_runner

        captured: list[tuple[str, str, object]] = []

        def on_step(node_name: str, outcome: str, state: object) -> None:
            captured.append((node_name, outcome, state))

        def start(board) -> Outcome:  # type: ignore[no-untyped-def]
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        def exit_done(board) -> None:  # type: ignore[no-untyped-def]
            pass

        exit_done._node_name = "exit.success.done"  # type: ignore[attr-defined]

        transitions: dict = {"start::success::done": exit_done}
        board = BoardBase()
        dag_runner(
            start=start,
            transitions=transitions,
            board=board,
            on_step=on_step,
        )

        # 最後のコールバックが exit ノード
        exit_step = captured[-1]
        assert exit_step[0] == "exit.success.done"
        # outcome は :: 区切りで統一
        assert exit_step[1] == "exit::success::done"
        assert "." not in exit_step[1]
