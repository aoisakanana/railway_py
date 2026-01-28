"""Issue #46: 終端ノード ExitContract 強制のテスト。

TDD Red Phase: 失敗するテストを先に作成。

v0.12.3 破壊的変更:
- 終端ノードは ExitContract サブクラスを返す必要がある
- dict, None 等を返すと ExitNodeTypeError
- レガシー形式 "exit::green::done" は LegacyExitFormatError
"""
import pytest

from railway import ExitContract, Contract, node
from railway.core.dag import dag_runner, async_dag_runner, Outcome


class ValidExitResult(ExitContract):
    """テスト用の正しい ExitContract。"""

    exit_state: str = "success.done"
    message: str = "completed"


class CustomExitResult(ExitContract):
    """カスタムフィールドを持つ ExitContract。"""

    exit_state: str = "success.done"
    processed_count: int
    summary: str


class StartContext(Contract):
    """開始ノードのコンテキスト。"""

    value: str = "initial"


# --- フィクスチャ用の関数 ---


def make_start_node():
    """開始ノードを生成するファクトリ。"""

    @node(name="start")
    def start() -> tuple[StartContext, Outcome]:
        return StartContext(), Outcome.success("done")

    return start


class TestExitNodeMustReturnExitContract:
    """終端ノードは ExitContract を返す必要がある。"""

    def test_exit_node_returning_dict_raises_type_error(self) -> None:
        """終端ノードが dict を返すと ExitNodeTypeError。"""
        from railway.core.dag.errors import ExitNodeTypeError

        @node(name="exit.success.done")
        def exit_returns_dict(ctx: StartContext) -> dict:
            return {"status": "ok"}

        start = make_start_node()
        transitions = {"start::success::done": exit_returns_dict}

        with pytest.raises(ExitNodeTypeError) as exc_info:
            dag_runner(start=start, transitions=transitions)

        error = exc_info.value
        assert "exit.success.done" in str(error)
        assert "dict" in str(error)

    def test_exit_node_returning_none_raises_type_error(self) -> None:
        """終端ノードが None を返すと ExitNodeTypeError。"""
        from railway.core.dag.errors import ExitNodeTypeError

        @node(name="exit.success.done")
        def exit_returns_none(ctx: StartContext) -> None:
            return None

        start = make_start_node()
        transitions = {"start::success::done": exit_returns_none}

        with pytest.raises(ExitNodeTypeError) as exc_info:
            dag_runner(start=start, transitions=transitions)

        assert "NoneType" in str(exc_info.value)

    def test_exit_node_returning_exit_contract_succeeds(self) -> None:
        """終端ノードが ExitContract を返すと成功。"""

        @node(name="exit.success.done")
        def exit_returns_contract(ctx: StartContext) -> ValidExitResult:
            return ValidExitResult()

        start = make_start_node()
        transitions = {"start::success::done": exit_returns_contract}

        result = dag_runner(start=start, transitions=transitions)

        assert isinstance(result, ExitContract)
        assert result.is_success

    def test_exit_node_returning_custom_exit_contract_succeeds(self) -> None:
        """終端ノードがカスタム ExitContract サブクラスを返すと成功。

        Note:
            開発者は ExitContract を継承した独自のクラスを定義し、
            カスタムフィールドを追加できる。
        """

        @node(name="exit.success.done")
        def exit_returns_custom(ctx: StartContext) -> CustomExitResult:
            return CustomExitResult(
                processed_count=42,
                summary="All items processed",
            )

        start = make_start_node()
        transitions = {"start::success::done": exit_returns_custom}

        result = dag_runner(start=start, transitions=transitions)

        assert isinstance(result, CustomExitResult)
        assert result.processed_count == 42
        assert result.summary == "All items processed"
        assert result.exit_state == "success.done"
        assert result.exit_code == 0
        assert result.is_success


class TestExitNodeWithFailureState:
    """failure 状態の終端ノードのテスト。"""

    def test_failure_exit_node_returns_exit_code_1(self) -> None:
        """failure 状態の終端ノードは exit_code=1 を返す。"""

        class FailureTimeoutResult(ExitContract):
            exit_state: str = "failure.timeout"
            reason: str

        @node(name="exit.failure.timeout")
        def exit_timeout(ctx: StartContext) -> FailureTimeoutResult:
            return FailureTimeoutResult(reason="Request timed out")

        start = make_start_node()
        transitions = {"start::success::done": exit_timeout}

        result = dag_runner(start=start, transitions=transitions)

        assert isinstance(result, FailureTimeoutResult)
        assert result.exit_state == "failure.timeout"
        assert result.exit_code == 1
        assert result.is_success is False
        assert result.is_failure is True
        assert result.reason == "Request timed out"


class TestLegacyExitFormatIsRejected:
    """レガシー exit 形式は拒否される。"""

    def test_legacy_exit_format_raises_error(self) -> None:
        """レガシー形式 'exit::green::done' は LegacyExitFormatError。"""
        from railway.core.dag.errors import LegacyExitFormatError

        start = make_start_node()
        transitions = {"start::success::done": "exit::green::done"}

        with pytest.raises(LegacyExitFormatError) as exc_info:
            dag_runner(start=start, transitions=transitions)

        assert "exit::green::done" in str(exc_info.value)
        assert "railway update" in str(exc_info.value)


@pytest.mark.asyncio
class TestExitNodeMustReturnExitContractAsync:
    """非同期終端ノードも ExitContract を返す必要がある。"""

    async def test_async_exit_node_returning_dict_raises_type_error(self) -> None:
        """非同期終端ノードが dict を返すと ExitNodeTypeError。"""
        from railway.core.dag.errors import ExitNodeTypeError

        @node(name="exit.success.done")
        async def exit_returns_dict(ctx: StartContext) -> dict:
            return {"status": "ok"}

        @node(name="start")
        async def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.success("done")

        transitions = {"start::success::done": exit_returns_dict}

        with pytest.raises(ExitNodeTypeError):
            await async_dag_runner(start=start, transitions=transitions)

    async def test_async_exit_node_returning_exit_contract_succeeds(self) -> None:
        """非同期終端ノードが ExitContract を返すと成功。"""

        @node(name="exit.success.done")
        async def exit_returns_contract(ctx: StartContext) -> ValidExitResult:
            return ValidExitResult()

        @node(name="start")
        async def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.success("done")

        transitions = {"start::success::done": exit_returns_contract}

        result = await async_dag_runner(start=start, transitions=transitions)

        assert isinstance(result, ExitContract)
        assert result.is_success

    async def test_async_legacy_exit_format_raises_error(self) -> None:
        """非同期版でもレガシー形式は LegacyExitFormatError。"""
        from railway.core.dag.errors import LegacyExitFormatError

        @node(name="start")
        async def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.success("done")

        transitions = {"start::success::done": "exit::red::error"}

        with pytest.raises(LegacyExitFormatError):
            await async_dag_runner(start=start, transitions=transitions)
