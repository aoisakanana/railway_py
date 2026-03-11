"""Tests for dag_runner Board mode trace integration (Issue 25-02)."""
from __future__ import annotations

import pytest

from railway.core.board import BoardBase, WorkflowResult
from railway.core.dag.outcome import Outcome
from railway.core.dag.runner import dag_runner
from railway.core.dag.trace import NodeTrace, WorkflowTrace


def _make_exit(name: str = "exit.success.done"):
    """終端ノード関数を作成するヘルパー。"""

    def exit_node(board) -> None:  # type: ignore[no-untyped-def]
        pass

    exit_node._node_name = name  # type: ignore[attr-defined]
    return exit_node


class TestTracDisabled:
    """trace=False の場合のテスト。"""

    def test_trace_disabled_no_trace(self) -> None:
        """trace=False の場合、result.trace は None。"""

        def start(board):  # type: ignore[no-untyped-def]
            board.value = 1
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        transitions: dict = {"start::success::done": _make_exit()}
        board = BoardBase()
        result = dag_runner(
            start=start, transitions=transitions, board=board, trace=False
        )
        assert isinstance(result, WorkflowResult)
        assert result.trace is None

    def test_trace_default_disabled(self) -> None:
        """trace パラメータのデフォルトは False。"""

        def start(board):  # type: ignore[no-untyped-def]
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        transitions: dict = {"start::success::done": _make_exit()}
        board = BoardBase()
        result = dag_runner(start=start, transitions=transitions, board=board)
        assert result.trace is None


class TestTraceEnabled:
    """trace=True の場合のテスト。"""

    def test_trace_enabled_captures_mutations(self) -> None:
        """trace=True でミューテーションが記録される。"""

        def start(board):  # type: ignore[no-untyped-def]
            board.value = 42
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        transitions: dict = {"start::success::done": _make_exit()}
        board = BoardBase()
        result = dag_runner(
            start=start, transitions=transitions, board=board, trace=True
        )
        assert result.trace is not None
        assert isinstance(result.trace, WorkflowTrace)

        # start ノードで value が追加されたことを確認
        traces = result.trace.traces
        assert len(traces) >= 1
        start_trace = traces[0]
        assert start_trace.node_name == "start"
        assert "value" in start_trace.mutations

    def test_trace_captures_initial_fields(self) -> None:
        """初期フィールドが記録される。"""

        def start(board):  # type: ignore[no-untyped-def]
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        transitions: dict = {"start::success::done": _make_exit()}
        board = BoardBase(severity="critical", host="server-01")
        result = dag_runner(
            start=start, transitions=transitions, board=board, trace=True
        )
        assert result.trace is not None
        # 初期フィールドがソート済みで記録される
        assert set(result.trace.initial_fields) == {"severity", "host"}

    def test_trace_multiple_nodes(self) -> None:
        """複数ノードのトレースが正しく記録される。"""

        def start(board):  # type: ignore[no-untyped-def]
            board.step1 = True
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        def process(board):  # type: ignore[no-untyped-def]
            board.step2 = True
            return Outcome.success("done")

        process._node_name = "process"  # type: ignore[attr-defined]

        transitions: dict = {
            "start::success::done": process,
            "process::success::done": _make_exit(),
        }
        board = BoardBase()
        result = dag_runner(
            start=start, transitions=transitions, board=board, trace=True
        )
        assert result.trace is not None

        traces = result.trace.traces
        # start + process + exit = 3 traces
        assert len(traces) >= 2

        # start で step1 が追加
        assert traces[0].node_name == "start"
        assert "step1" in traces[0].mutations

        # process で step2 が追加
        assert traces[1].node_name == "process"
        assert "step2" in traces[1].mutations

    def test_trace_exit_node_included(self) -> None:
        """終端ノードもトレースに含まれる。"""

        def start(board):  # type: ignore[no-untyped-def]
            board.data = "test"
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        def exit_done(board) -> None:  # type: ignore[no-untyped-def]
            board.finalized = True

        exit_done._node_name = "exit.success.done"  # type: ignore[attr-defined]

        transitions: dict = {"start::success::done": exit_done}
        board = BoardBase()
        result = dag_runner(
            start=start, transitions=transitions, board=board, trace=True
        )
        assert result.trace is not None

        traces = result.trace.traces
        # 最後のトレースが終端ノード
        exit_trace = traces[-1]
        assert exit_trace.node_name == "exit.success.done"
        assert "finalized" in exit_trace.mutations

    def test_trace_execution_path(self) -> None:
        """execution_path が正しく記録される。"""

        def start(board):  # type: ignore[no-untyped-def]
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        transitions: dict = {"start::success::done": _make_exit()}
        board = BoardBase()
        result = dag_runner(
            start=start, transitions=transitions, board=board, trace=True
        )
        assert result.trace is not None
        assert result.trace.execution_path == ("start", "exit.success.done")

    def test_trace_before_after_snapshots(self) -> None:
        """before/after が正しいスナップショットを記録する。"""

        def start(board):  # type: ignore[no-untyped-def]
            board.value = 42
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        transitions: dict = {"start::success::done": _make_exit()}
        board = BoardBase(initial="x")
        result = dag_runner(
            start=start, transitions=transitions, board=board, trace=True
        )
        assert result.trace is not None

        start_trace = result.trace.traces[0]
        # before: 初期状態のみ
        assert start_trace.before == {"initial": "x"}
        # after: initial + value
        assert start_trace.after == {"initial": "x", "value": 42}


class TestAsyncTraceEnabled:
    """非同期 dag_runner のトレーステスト。"""

    @pytest.mark.asyncio
    async def test_async_trace_enabled(self) -> None:
        """async_dag_runner でもトレースが動作する。"""
        from railway.core.dag.runner import async_dag_runner

        async def start(board):  # type: ignore[no-untyped-def]
            board.data = "fetched"
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        transitions: dict = {"start::success::done": _make_exit()}
        board = BoardBase()
        result = await async_dag_runner(
            start=start, transitions=transitions, board=board, trace=True
        )
        assert isinstance(result, WorkflowResult)
        assert result.trace is not None
        assert isinstance(result.trace, WorkflowTrace)
        assert len(result.trace.traces) >= 1
        assert "data" in result.trace.traces[0].mutations

    @pytest.mark.asyncio
    async def test_async_trace_disabled(self) -> None:
        """async_dag_runner で trace=False の場合は None。"""
        from railway.core.dag.runner import async_dag_runner

        async def start(board):  # type: ignore[no-untyped-def]
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        transitions: dict = {"start::success::done": _make_exit()}
        board = BoardBase()
        result = await async_dag_runner(
            start=start, transitions=transitions, board=board, trace=False
        )
        assert result.trace is None
