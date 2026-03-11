"""E2E テスト: Board mode ワークフロー。

Issue 28-02: Board パターンの統合テスト。
"""

import pytest

from railway.core.board import BoardBase, WorkflowResult
from railway.core.dag import Outcome, dag_runner, async_dag_runner


# =========== ヘルパー: Board mode ノード群 ===========


def _make_start_node(name: str = "start"):
    """Board mode 開始ノードを作成する。"""
    def start(board: BoardBase) -> Outcome:
        board.step = 1
        return Outcome.success("check")
    start._node_name = name  # type: ignore[attr-defined]
    start._is_board_node = True  # type: ignore[attr-defined]
    return start


def _make_check_node(name: str = "check"):
    """Board mode チェックノードを作成する。"""
    def check(board: BoardBase) -> Outcome:
        board.step = 2
        if hasattr(board, "severity") and board.severity == "critical":
            board.escalated = True
            return Outcome.success("escalate")
        return Outcome.success("done")
    check._node_name = name  # type: ignore[attr-defined]
    check._is_board_node = True  # type: ignore[attr-defined]
    return check


def _make_escalate_node(name: str = "escalate"):
    """Board mode エスカレーションノードを作成する。"""
    def escalate(board: BoardBase) -> Outcome:
        board.step = 3
        board.notified = True
        return Outcome.success("done")
    escalate._node_name = name  # type: ignore[attr-defined]
    escalate._is_board_node = True  # type: ignore[attr-defined]
    return escalate


def _make_exit_done(name: str = "exit.success.done"):
    """Board mode 終端ノードを作成する。"""
    def done(board: BoardBase) -> None:
        board.completed = True
    done._node_name = name  # type: ignore[attr-defined]
    done._is_board_node = True  # type: ignore[attr-defined]
    return done


def _make_exit_error(name: str = "exit.failure.error"):
    """Board mode エラー終端ノードを作成する。"""
    def error(board: BoardBase) -> None:
        board.error = True
    error._node_name = name  # type: ignore[attr-defined]
    error._is_board_node = True  # type: ignore[attr-defined]
    return error


# =========== E2E テスト ===========


class TestBoardWorkflowBasic:
    """基本的な Board mode ワークフローの E2E テスト。"""

    def test_simple_board_workflow(self) -> None:
        """単純な start → exit ワークフローが動作する。"""
        start = _make_start_node()
        exit_done = _make_exit_done()

        board = BoardBase(incident_id="INC-001")
        result = dag_runner(
            start=start,
            transitions={"start::success::check": exit_done},
            board=board,
        )

        assert isinstance(result, WorkflowResult)
        assert result.is_success
        assert result.exit_state == "success.done"
        assert result.exit_code == 0
        assert result.board.incident_id == "INC-001"
        assert result.board.step == 1
        assert result.board.completed is True

    def test_multi_step_board_workflow(self) -> None:
        """複数ステップのワークフローが動作する。"""
        start = _make_start_node()
        check = _make_check_node()
        exit_done = _make_exit_done()

        board = BoardBase(severity="low")
        result = dag_runner(
            start=start,
            transitions={
                "start::success::check": check,
                "check::success::done": exit_done,
            },
            board=board,
        )

        assert result.is_success
        assert result.board.step == 2
        assert result.board.completed is True
        assert "start" in result.execution_path
        assert "check" in result.execution_path

    def test_branching_board_workflow(self) -> None:
        """条件分岐のあるワークフローが動作する。"""
        start = _make_start_node()
        check = _make_check_node()
        escalate = _make_escalate_node()
        exit_done = _make_exit_done()

        board = BoardBase(severity="critical")
        result = dag_runner(
            start=start,
            transitions={
                "start::success::check": check,
                "check::success::escalate": escalate,
                "check::success::done": exit_done,
                "escalate::success::done": exit_done,
            },
            board=board,
        )

        assert result.is_success
        assert result.board.escalated is True
        assert result.board.notified is True
        assert result.board.step == 3
        assert "escalate" in result.execution_path

    def test_failure_exit(self) -> None:
        """失敗終端ノードが正しく動作する。"""
        def start(board: BoardBase) -> Outcome:
            return Outcome.failure("error")
        start._node_name = "start"  # type: ignore[attr-defined]

        exit_error = _make_exit_error()

        board = BoardBase()
        result = dag_runner(
            start=start,
            transitions={"start::failure::error": exit_error},
            board=board,
        )

        assert result.is_failure
        assert result.exit_code == 1
        assert result.exit_state == "failure.error"
        assert result.board.error is True


class TestBoardWorkflowExecution:
    """Board mode の実行メタデータテスト。"""

    def test_execution_path_recorded(self) -> None:
        """実行パスが正しく記録される。"""
        start = _make_start_node()
        check = _make_check_node()
        exit_done = _make_exit_done()

        board = BoardBase(severity="low")
        result = dag_runner(
            start=start,
            transitions={
                "start::success::check": check,
                "check::success::done": exit_done,
            },
            board=board,
        )

        assert result.execution_path == ("start", "check", "exit.success.done")
        assert result.iterations == 3

    def test_on_step_callback(self) -> None:
        """on_step コールバックが呼ばれる。"""
        start = _make_start_node()
        exit_done = _make_exit_done()

        steps: list[tuple[str, str]] = []

        def on_step(node_name: str, state: str, snapshot: object) -> None:
            steps.append((node_name, state))

        board = BoardBase()
        dag_runner(
            start=start,
            transitions={"start::success::check": exit_done},
            board=board,
            on_step=on_step,
        )

        assert len(steps) == 2
        assert steps[0][0] == "start"
        assert steps[1][0] == "exit.success.done"

    def test_board_is_shared_reference(self) -> None:
        """Board が参照共有されている。"""
        start = _make_start_node()
        check = _make_check_node()
        exit_done = _make_exit_done()

        board = BoardBase(severity="low")
        result = dag_runner(
            start=start,
            transitions={
                "start::success::check": check,
                "check::success::done": exit_done,
            },
            board=board,
        )

        # result.board は同じオブジェクト
        assert result.board is board
        assert board.step == 2
        assert board.completed is True


@pytest.mark.asyncio
class TestBoardWorkflowAsync:
    """非同期 Board mode ワークフローの E2E テスト。"""

    async def test_async_board_workflow(self) -> None:
        """非同期ノードが動作する。"""
        async def start(board: BoardBase) -> Outcome:
            board.step = 1
            return Outcome.success("done")
        start._node_name = "start"  # type: ignore[attr-defined]

        async def done(board: BoardBase) -> None:
            board.completed = True
        done._node_name = "exit.success.done"  # type: ignore[attr-defined]

        board = BoardBase()
        result = await async_dag_runner(
            start=start,
            transitions={"start::success::done": done},
            board=board,
        )

        assert result.is_success
        assert result.board.step == 1
        assert result.board.completed is True

    async def test_mixed_sync_async_nodes(self) -> None:
        """sync/async ノードの混在が動作する。"""
        def start(board: BoardBase) -> Outcome:
            board.step = 1
            return Outcome.success("next")
        start._node_name = "start"  # type: ignore[attr-defined]

        async def process(board: BoardBase) -> Outcome:
            board.step = 2
            return Outcome.success("done")
        process._node_name = "process"  # type: ignore[attr-defined]

        def done(board: BoardBase) -> None:
            board.completed = True
        done._node_name = "exit.success.done"  # type: ignore[attr-defined]

        board = BoardBase()
        result = await async_dag_runner(
            start=start,
            transitions={
                "start::success::next": process,
                "process::success::done": done,
            },
            board=board,
        )

        assert result.is_success
        assert result.board.step == 2
        assert result.board.completed is True


class TestBoardWorkflowCoexistence:
    """Contract mode と Board mode の共存テスト。"""

    def test_contract_mode_still_works(self) -> None:
        """Contract mode が引き続き動作する。"""
        from railway import Contract, ExitContract, node

        class MyContext(Contract):
            value: str = "initial"

        class DoneResult(ExitContract):
            exit_state: str = "success.done"
            value: str

        @node(output=object, name="start")
        def start() -> tuple[MyContext, Outcome]:
            return MyContext(value="processed"), Outcome.success("done")

        @node(output=object, name="exit.success.done")
        def done(ctx: MyContext) -> DoneResult:
            return DoneResult(value=ctx.value)

        result = dag_runner(
            start=start,
            transitions={"start::success::done": done},
        )

        assert isinstance(result, ExitContract)
        assert result.is_success
        assert result.value == "processed"  # type: ignore[attr-defined]

    def test_board_and_contract_different_workflows(self) -> None:
        """同一プロセス内で Board mode と Contract mode を使い分けられる。"""
        from railway import Contract, ExitContract, node

        # Board mode ワークフロー
        board_start = _make_start_node()
        board_exit = _make_exit_done()
        board = BoardBase()
        board_result = dag_runner(
            start=board_start,
            transitions={"start::success::check": board_exit},
            board=board,
        )
        assert isinstance(board_result, WorkflowResult)

        # Contract mode ワークフロー
        class Ctx(Contract):
            pass

        class Done(ExitContract):
            exit_state: str = "success.done"

        @node(output=object, name="start2")
        def start2() -> tuple[Ctx, Outcome]:
            return Ctx(), Outcome.success("done")

        @node(output=object, name="exit.success.done")
        def done_contract(ctx: Ctx) -> Done:
            return Done()

        contract_result = dag_runner(
            start=start2,
            transitions={"start2::success::done": done_contract},
        )
        assert isinstance(contract_result, ExitContract)

        # 両方とも成功
        assert board_result.is_success
        assert contract_result.is_success
