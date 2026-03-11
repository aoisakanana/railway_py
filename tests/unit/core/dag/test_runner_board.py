"""Tests for dag_runner Board mode (Issues 22-01 to 22-03)."""
from __future__ import annotations

import pytest

from railway.core.board import BoardBase, WorkflowResult
from railway.core.dag.outcome import Outcome
from railway.core.dag.runner import MaxIterationsError, dag_runner


def _make_exit(name: str = "exit.success.done"):
    """Helper to create exit node functions."""

    def exit_node(board) -> None:  # type: ignore[no-untyped-def]
        pass

    exit_node._node_name = name  # type: ignore[attr-defined]
    return exit_node


def _make_node(name: str):
    """Helper to create board node functions."""

    def the_node(board):  # type: ignore[no-untyped-def]
        return Outcome.success("done")

    the_node._node_name = name  # type: ignore[attr-defined]
    return the_node


class TestDagRunnerBoardBasic:
    def test_basic_workflow(self) -> None:
        def start(board):  # type: ignore[no-untyped-def]
            board.value = "initialized"
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        transitions: dict = {"start::success::done": _make_exit()}
        board = BoardBase()
        result = dag_runner(start=start, transitions=transitions, board=board)
        assert isinstance(result, WorkflowResult)
        assert result.is_success
        assert result.board.value == "initialized"  # type: ignore[attr-defined]

    def test_board_shared_between_nodes(self) -> None:
        def start(board):  # type: ignore[no-untyped-def]
            board.step1 = True
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        def process(board):  # type: ignore[no-untyped-def]
            assert board.step1 is True
            board.step2 = True
            return Outcome.success("done")

        process._node_name = "process"  # type: ignore[attr-defined]

        transitions: dict = {
            "start::success::done": process,
            "process::success::done": _make_exit(),
        }
        board = BoardBase()
        result = dag_runner(start=start, transitions=transitions, board=board)
        assert result.is_success
        assert result.board.step1 is True  # type: ignore[attr-defined]
        assert result.board.step2 is True  # type: ignore[attr-defined]

    def test_execution_path_recorded(self) -> None:
        def start(board):  # type: ignore[no-untyped-def]
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        transitions: dict = {"start::success::done": _make_exit()}
        board = BoardBase()
        result = dag_runner(start=start, transitions=transitions, board=board)
        assert result.execution_path == ("start", "exit.success.done")

    def test_branching(self) -> None:
        def start(board):  # type: ignore[no-untyped-def]
            if board.severity == "critical":
                return Outcome.success("critical")
            return Outcome.success("normal")

        start._node_name = "start"  # type: ignore[attr-defined]

        def escalate(board):  # type: ignore[no-untyped-def]
            board.escalated = True
            return Outcome.success("done")

        escalate._node_name = "escalate"  # type: ignore[attr-defined]

        def log_only(board):  # type: ignore[no-untyped-def]
            board.logged = True
            return Outcome.success("done")

        log_only._node_name = "log_only"  # type: ignore[attr-defined]

        transitions: dict = {
            "start::success::critical": escalate,
            "start::success::normal": log_only,
            "escalate::success::done": _make_exit(),
            "log_only::success::done": _make_exit(),
        }
        board = BoardBase(severity="critical")
        result = dag_runner(start=start, transitions=transitions, board=board)
        assert result.is_success
        assert result.board.escalated is True  # type: ignore[attr-defined]

    def test_max_iterations_raises(self) -> None:
        def start(board):  # type: ignore[no-untyped-def]
            return Outcome.success("loop")

        start._node_name = "start"  # type: ignore[attr-defined]

        def loop_node(board):  # type: ignore[no-untyped-def]
            return Outcome.success("loop")

        loop_node._node_name = "loop"  # type: ignore[attr-defined]

        transitions: dict = {
            "start::success::loop": loop_node,
            "loop::success::loop": loop_node,
        }
        board = BoardBase()
        with pytest.raises(MaxIterationsError):
            dag_runner(
                start=start,
                transitions=transitions,
                board=board,
                max_iterations=5,
            )

    def test_on_step_receives_snapshot(self) -> None:
        snapshots: list[dict] = []

        def on_step(name, state, snapshot):  # type: ignore[no-untyped-def]
            snapshots.append(dict(snapshot))

        def start(board):  # type: ignore[no-untyped-def]
            board.x = 1
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        transitions: dict = {"start::success::done": _make_exit()}
        board = BoardBase()
        dag_runner(
            start=start, transitions=transitions, board=board, on_step=on_step
        )
        assert len(snapshots) >= 1
        assert snapshots[0]["x"] == 1

    def test_iterations_count(self) -> None:
        def start(board):  # type: ignore[no-untyped-def]
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        def process(board):  # type: ignore[no-untyped-def]
            return Outcome.success("done")

        process._node_name = "process"  # type: ignore[attr-defined]

        transitions: dict = {
            "start::success::done": process,
            "process::success::done": _make_exit(),
        }
        board = BoardBase()
        result = dag_runner(start=start, transitions=transitions, board=board)
        # start(1) + process(2) + exit(3) = 3
        assert result.iterations == 3


class TestDagRunnerBoardExitNodes:
    def test_exit_node_receives_board(self) -> None:
        received_board: dict = {}

        def exit_done(board) -> None:  # type: ignore[no-untyped-def]
            received_board["got"] = board._snapshot()

        exit_done._node_name = "exit.success.done"  # type: ignore[attr-defined]

        def start(board):  # type: ignore[no-untyped-def]
            board.data = "test"
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        transitions: dict = {"start::success::done": exit_done}
        board = BoardBase()
        result = dag_runner(start=start, transitions=transitions, board=board)
        assert result.is_success
        assert received_board["got"]["data"] == "test"

    def test_exit_node_return_ignored(self) -> None:
        def exit_done(board):  # type: ignore[no-untyped-def]
            return "this is ignored"

        exit_done._node_name = "exit.success.done"  # type: ignore[attr-defined]

        def start(board):  # type: ignore[no-untyped-def]
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        transitions: dict = {"start::success::done": exit_done}
        board = BoardBase()
        result = dag_runner(start=start, transitions=transitions, board=board)
        assert isinstance(result, WorkflowResult)
        assert result.is_success

    def test_failure_exit_code(self) -> None:
        exit_fail = _make_exit("exit.failure.timeout")

        def start(board):  # type: ignore[no-untyped-def]
            return Outcome.failure("timeout")

        start._node_name = "start"  # type: ignore[attr-defined]

        transitions: dict = {"start::failure::timeout": exit_fail}
        board = BoardBase()
        result = dag_runner(start=start, transitions=transitions, board=board)
        assert result.is_failure
        assert result.exit_code == 1
        assert result.exit_state == "failure.timeout"

    def test_exit_state_derived_from_name(self) -> None:
        exit_node = _make_exit("exit.success.completed")

        def start(board):  # type: ignore[no-untyped-def]
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        transitions: dict = {"start::success::done": exit_node}
        board = BoardBase()
        result = dag_runner(start=start, transitions=transitions, board=board)
        assert result.exit_state == "success.completed"

    def test_exit_state_codegen_format(self) -> None:
        """_exit_ prefix (codegen format) also works."""
        exit_node = _make_exit("_exit_success_done")

        def start(board):  # type: ignore[no-untyped-def]
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        transitions: dict = {"start::success::done": exit_node}
        board = BoardBase()
        result = dag_runner(start=start, transitions=transitions, board=board)
        assert result.exit_state == "success.done"
        assert result.is_success


class TestDagRunnerBoardContractModeStillWorks:
    """Existing Contract mode still works when board=None."""

    def test_contract_mode_unchanged(self) -> None:
        """Contract mode (board=None) returns ExitContract."""
        from railway.core.exit_contract import ExitContract

        class DoneResult(ExitContract):
            exit_state: str = "success.done"

        def start():  # type: ignore[no-untyped-def]
            return DoneResult(), Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        def exit_done(ctx):  # type: ignore[no-untyped-def]
            return DoneResult()

        exit_done._node_name = "exit.success.done"  # type: ignore[attr-defined]

        transitions: dict = {
            "start::success::done": exit_done,
        }
        # board=None (default) → Contract mode
        result = dag_runner(start=start, transitions=transitions)
        assert isinstance(result, ExitContract)
        assert result.is_success


class TestAsyncDagRunnerBoard:
    @pytest.mark.asyncio
    async def test_async_basic(self) -> None:
        from railway.core.dag.runner import async_dag_runner

        async def start(board):  # type: ignore[no-untyped-def]
            board.data = "fetched"
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        transitions: dict = {"start::success::done": _make_exit()}
        board = BoardBase()
        result = await async_dag_runner(
            start=start, transitions=transitions, board=board
        )
        assert isinstance(result, WorkflowResult)
        assert result.is_success
        assert result.board.data == "fetched"  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_async_mixed_nodes(self) -> None:
        from railway.core.dag.runner import async_dag_runner

        def start(board):  # type: ignore[no-untyped-def]
            board.step1 = True
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        async def process(board):  # type: ignore[no-untyped-def]
            board.step2 = True
            return Outcome.success("done")

        process._node_name = "process"  # type: ignore[attr-defined]

        transitions: dict = {
            "start::success::done": process,
            "process::success::done": _make_exit(),
        }
        board = BoardBase()
        result = await async_dag_runner(
            start=start, transitions=transitions, board=board
        )
        assert result.is_success
        assert result.board.step1 is True  # type: ignore[attr-defined]
        assert result.board.step2 is True  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_async_exit_node(self) -> None:
        from railway.core.dag.runner import async_dag_runner

        async def exit_done(board) -> None:  # type: ignore[no-untyped-def]
            board.finalized = True

        exit_done._node_name = "exit.success.done"  # type: ignore[attr-defined]

        def start(board):  # type: ignore[no-untyped-def]
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        transitions: dict = {"start::success::done": exit_done}
        board = BoardBase()
        result = await async_dag_runner(
            start=start, transitions=transitions, board=board
        )
        assert result.is_success
        assert result.board.finalized is True  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_async_failure_exit(self) -> None:
        from railway.core.dag.runner import async_dag_runner

        exit_fail = _make_exit("exit.failure.error")

        async def start(board):  # type: ignore[no-untyped-def]
            return Outcome.failure("error")

        start._node_name = "start"  # type: ignore[attr-defined]

        transitions: dict = {"start::failure::error": exit_fail}
        board = BoardBase()
        result = await async_dag_runner(
            start=start, transitions=transitions, board=board
        )
        assert result.is_failure
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_async_execution_path(self) -> None:
        from railway.core.dag.runner import async_dag_runner

        def start(board):  # type: ignore[no-untyped-def]
            return Outcome.success("done")

        start._node_name = "start"  # type: ignore[attr-defined]

        def process(board):  # type: ignore[no-untyped-def]
            return Outcome.success("done")

        process._node_name = "process"  # type: ignore[attr-defined]

        transitions: dict = {
            "start::success::done": process,
            "process::success::done": _make_exit(),
        }
        board = BoardBase()
        result = await async_dag_runner(
            start=start, transitions=transitions, board=board
        )
        assert result.execution_path == ("start", "process", "exit.success.done")

    @pytest.mark.asyncio
    async def test_async_max_iterations(self) -> None:
        from railway.core.dag.runner import async_dag_runner

        async def start(board):  # type: ignore[no-untyped-def]
            return Outcome.success("loop")

        start._node_name = "start"  # type: ignore[attr-defined]

        async def loop_node(board):  # type: ignore[no-untyped-def]
            return Outcome.success("loop")

        loop_node._node_name = "loop"  # type: ignore[attr-defined]

        transitions: dict = {
            "start::success::loop": loop_node,
            "loop::success::loop": loop_node,
        }
        board = BoardBase()
        with pytest.raises(MaxIterationsError):
            await async_dag_runner(
                start=start,
                transitions=transitions,
                board=board,
                max_iterations=5,
            )
