"""dag_runner の ExitContract 対応テスト（Issue #36）。

TDD Red Phase: 失敗するテストを先に作成。
"""
import pytest

from railway import Contract, ExitContract, DefaultExitContract, node
from railway.core.dag import Outcome, dag_runner
from railway.core.dag.runner import _is_exit_node, _derive_exit_state


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

    def test_backward_compat_context_only(self) -> None:
        """Context のみ返す終端ノードは DefaultExitContract でラップ。"""

        @node
        def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.success("done")

        @node(name="exit.success.done")
        def done(ctx: StartContext) -> dict:
            return {"key": "value"}  # ExitContract ではない

        result = dag_runner(
            start=start,
            transitions={"start::success::done": done},
        )

        assert isinstance(result, DefaultExitContract)
        assert result.context == {"key": "value"}
        assert result.exit_state == "success.done"
        assert result.is_success is True

    def test_exit_state_derived_from_node_name(self) -> None:
        """exit_state は終端ノード名から導出される（後方互換用）。"""

        @node
        def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.failure("timeout")

        @node(name="exit.failure.timeout")
        def timeout(ctx: StartContext) -> dict:
            return {"error": "timeout"}

        result = dag_runner(
            start=start,
            transitions={"start::failure::timeout": timeout},
        )

        assert result.exit_state == "failure.timeout"
        assert result.is_failure is True

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
