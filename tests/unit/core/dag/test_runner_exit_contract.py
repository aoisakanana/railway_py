"""dag_runner の ExitContract 対応テスト（Issue #36）。

TDD Red Phase: 失敗するテストを先に作成。

Issue #40: 終端ノード例外伝播テスト追加
ADR-004 の仕様「終端ノードで発生した例外はそのまま伝播する」を検証。

v0.12.3 破壊的変更:
- 終端ノードは ExitContract サブクラスを返す必要がある
- dict, None 等を返すと ExitNodeTypeError
"""
import pytest

from railway import Contract, ExitContract, node
from railway.core.dag import Outcome, dag_runner, async_dag_runner
from railway.core.dag.runner import _is_exit_node, _derive_exit_state
from railway.core.dag.errors import ExitNodeTypeError


class StartContext(Contract):
    """開始ノード用 Context。"""

    value: str = "test"


class DoneResult(ExitContract):
    """テスト用の成功 ExitContract。"""

    data: str
    exit_state: str = "success.done"


class TimeoutResult(ExitContract):
    """テスト用の失敗 ExitContract。"""

    error: str
    exit_state: str = "failure.timeout"


class TestDagRunnerExitContract:
    """dag_runner が ExitContract を返すことのテスト。"""

    def test_returns_exit_contract(self) -> None:
        """終端ノードが ExitContract を返す場合、そのまま返す。"""

        @node
        def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.success("done")

        @node(name="exit.success.done")
        def done(ctx: StartContext) -> DoneResult:
            return DoneResult(data="completed")

        result = dag_runner(
            start=start,
            transitions={"start::success::done": done},
        )

        assert isinstance(result, DoneResult)
        assert result.data == "completed"
        assert result.is_success is True
        assert result.exit_state == "success.done"
        assert result.exit_code == 0  # 自動導出
        assert "start" in result.execution_path
        assert "exit.success.done" in result.execution_path

    def test_context_only_raises_exit_node_type_error(self) -> None:
        """v0.12.3: Context のみ返す終端ノードは ExitNodeTypeError。"""

        @node
        def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.success("done")

        @node(name="exit.success.done")
        def done(ctx: StartContext) -> dict:
            return {"key": "value"}  # ExitContract ではない

        with pytest.raises(ExitNodeTypeError) as exc_info:
            dag_runner(
                start=start,
                transitions={"start::success::done": done},
            )

        assert "exit.success.done" in str(exc_info.value)
        assert "dict" in str(exc_info.value)

    def test_none_return_raises_exit_node_type_error(self) -> None:
        """v0.12.3: None を返す終端ノードは ExitNodeTypeError。"""

        @node
        def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.failure("timeout")

        @node(name="exit.failure.timeout")
        def timeout(ctx: StartContext) -> None:
            return None

        with pytest.raises(ExitNodeTypeError) as exc_info:
            dag_runner(
                start=start,
                transitions={"start::failure::timeout": timeout},
            )

        assert "NoneType" in str(exc_info.value)

    def test_custom_exit_contract_preserves_fields(self) -> None:
        """ユーザー定義 ExitContract のフィールドが保持される。"""

        @node
        def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.failure("timeout")

        @node(name="exit.failure.timeout")
        def timeout(ctx: StartContext) -> TimeoutResult:
            return TimeoutResult(error="API timeout after 30s")

        result = dag_runner(
            start=start,
            transitions={"start::failure::timeout": timeout},
        )

        assert isinstance(result, TimeoutResult)
        assert result.error == "API timeout after 30s"
        assert result.exit_state == "failure.timeout"
        assert result.exit_code == 1  # 自動導出

    def test_execution_path_includes_exit_node(self) -> None:
        """execution_path に終端ノードが含まれる。"""

        @node
        def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.success("done")

        @node(name="exit.success.done")
        def done(ctx: StartContext) -> DoneResult:
            return DoneResult(data="done")

        result = dag_runner(
            start=start,
            transitions={"start::success::done": done},
        )

        assert "start" in result.execution_path
        assert "exit.success.done" in result.execution_path

    def test_iterations_is_set(self) -> None:
        """iterations が設定される。"""

        @node
        def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.success("done")

        @node(name="exit.success.done")
        def done(ctx: StartContext) -> DoneResult:
            return DoneResult(data="done")

        result = dag_runner(
            start=start,
            transitions={"start::success::done": done},
        )

        assert result.iterations == 2  # start + exit node


class TestIsExitNode:
    """_is_exit_node 関数のテスト（純粋関数として独立テスト）。"""

    def test_exit_dot_prefix_is_exit_node(self) -> None:
        """'exit.' で始まるノードは終端ノード。"""
        assert _is_exit_node("exit.success.done") is True
        assert _is_exit_node("exit.failure.timeout") is True

    def test_underscore_exit_prefix_is_exit_node(self) -> None:
        """'_exit_' で始まるノードは終端ノード。"""
        assert _is_exit_node("_exit_success_done") is True
        assert _is_exit_node("_exit_failure_error") is True

    def test_regular_node_is_not_exit_node(self) -> None:
        """通常ノードは終端ノードではない。"""
        assert _is_exit_node("start") is False
        assert _is_exit_node("process") is False
        assert _is_exit_node("finalize") is False


class TestDeriveExitState:
    """_derive_exit_state 関数のテスト（純粋関数として独立テスト）。"""

    def test_removes_exit_dot_prefix(self) -> None:
        """'exit.' プレフィックスを除去する。"""
        assert _derive_exit_state("exit.success.done") == "success.done"

    def test_removes_underscore_exit_prefix(self) -> None:
        """'_exit_' プレフィックスを除去し '.' に変換。"""
        assert _derive_exit_state("_exit_failure_timeout") == "failure.timeout"

    def test_handles_deep_nested_path(self) -> None:
        """深いネストパスを正しく処理する。"""
        assert _derive_exit_state("exit.failure.ssh.handshake") == "failure.ssh.handshake"

    def test_returns_as_is_if_no_prefix(self) -> None:
        """プレフィックスがない場合はそのまま返す。"""
        assert _derive_exit_state("custom_state") == "custom_state"


# =============================================================================
# Issue #40: 終端ノード例外伝播テスト
# ADR-004: 「終端ノードで発生した例外はそのまま伝播する」
# =============================================================================


class ExitNodeExceptionResult(ExitContract):
    """テスト用 ExitContract。"""

    exit_state: str = "success.done"


class TestExitNodeExceptionPropagation:
    """終端ノード例外伝播のテスト（同期版）。

    ADR-004 の設計方針:
    - Outcome.failure は「想定内のエラー」→ 遷移グラフで処理
    - Python例外は「想定外のバグ」→ そのまま伝播（特別な処理なし）
    """

    def test_exit_node_exception_propagates(self) -> None:
        """終端ノードの例外は呼び出し元に伝播する。"""

        @node(name="exit.success.done")
        def exit_raises(ctx: StartContext) -> ExitNodeExceptionResult:
            raise RuntimeError("Exit node error")

        @node(name="start")
        def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.success("done")

        transitions = {
            "start::success::done": exit_raises,
        }

        with pytest.raises(RuntimeError, match="Exit node error"):
            dag_runner(start=start, transitions=transitions)

    def test_exit_node_value_error_propagates(self) -> None:
        """終端ノードの ValueError も伝播する。"""

        class FailureResult(ExitContract):
            exit_state: str = "failure.error"

        @node(name="exit.failure.error")
        def exit_raises_value_error(ctx: StartContext) -> FailureResult:
            raise ValueError("Invalid value in exit node")

        @node(name="start")
        def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.failure("error")

        transitions = {
            "start::failure::error": exit_raises_value_error,
        }

        with pytest.raises(ValueError, match="Invalid value in exit node"):
            dag_runner(start=start, transitions=transitions)

    def test_exit_node_type_error_propagates(self) -> None:
        """終端ノードの TypeError も伝播する。"""

        @node(name="exit.success.done")
        def exit_raises_type_error(ctx: StartContext) -> ExitNodeExceptionResult:
            # 意図的な型エラー
            raise TypeError("Type mismatch in exit node")

        @node(name="start")
        def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.success("done")

        transitions = {
            "start::success::done": exit_raises_type_error,
        }

        with pytest.raises(TypeError, match="Type mismatch in exit node"):
            dag_runner(start=start, transitions=transitions)

    def test_exit_node_custom_exception_propagates(self) -> None:
        """終端ノードのカスタム例外も伝播する。"""

        class ExitNodeCustomError(Exception):
            """終端ノード固有のエラー。"""

            pass

        @node(name="exit.success.done")
        def exit_raises_custom(ctx: StartContext) -> ExitNodeExceptionResult:
            raise ExitNodeCustomError("Custom error from exit node")

        @node(name="start")
        def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.success("done")

        transitions = {
            "start::success::done": exit_raises_custom,
        }

        with pytest.raises(ExitNodeCustomError, match="Custom error from exit node"):
            dag_runner(start=start, transitions=transitions)


@pytest.mark.asyncio
class TestExitNodeExceptionPropagationAsync:
    """非同期終端ノード例外伝播のテスト。

    同期版と同じく、例外はそのまま伝播する。
    """

    async def test_async_exit_node_exception_propagates(self) -> None:
        """非同期終端ノードの例外は呼び出し元に伝播する。"""

        @node(name="exit.success.done")
        async def exit_raises(ctx: StartContext) -> ExitNodeExceptionResult:
            raise RuntimeError("Async exit node error")

        @node(name="start")
        async def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.success("done")

        transitions = {
            "start::success::done": exit_raises,
        }

        with pytest.raises(RuntimeError, match="Async exit node error"):
            await async_dag_runner(start=start, transitions=transitions)

    async def test_async_exit_node_value_error_propagates(self) -> None:
        """非同期終端ノードの ValueError も伝播する。"""

        class FailureResult(ExitContract):
            exit_state: str = "failure.error"

        @node(name="exit.failure.error")
        async def exit_raises(ctx: StartContext) -> FailureResult:
            raise ValueError("Async invalid value")

        @node(name="start")
        async def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.failure("error")

        transitions = {
            "start::failure::error": exit_raises,
        }

        with pytest.raises(ValueError, match="Async invalid value"):
            await async_dag_runner(start=start, transitions=transitions)

    async def test_sync_exit_node_in_async_runner_exception_propagates(self) -> None:
        """async_dag_runner で同期終端ノードの例外も伝播する。"""

        @node(name="exit.success.done")
        def sync_exit_raises(ctx: StartContext) -> ExitNodeExceptionResult:
            raise RuntimeError("Sync exit node in async runner")

        @node(name="start")
        async def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.success("done")

        transitions = {
            "start::success::done": sync_exit_raises,
        }

        with pytest.raises(RuntimeError, match="Sync exit node in async runner"):
            await async_dag_runner(start=start, transitions=transitions)
