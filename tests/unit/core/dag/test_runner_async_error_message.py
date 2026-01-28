"""Issue #39: async_dag_runner エラーメッセージテスト。

async_dag_runner の UndefinedStateError にノード名が含まれることを検証。
dag_runner と同じフォーマットであること。
"""
import pytest

from railway import Contract
from railway.core.dag.outcome import Outcome
from railway.core.dag.runner import UndefinedStateError, async_dag_runner


class TestAsyncDagRunnerErrorMessage:
    """async_dag_runner のエラーメッセージテスト。"""

    @pytest.mark.asyncio
    async def test_strict_mode_error_includes_node_name(self) -> None:
        """strict モードのエラーメッセージにノード名が含まれる。"""

        class EmptyContext(Contract):
            pass

        async def start() -> tuple[EmptyContext, Outcome]:
            return EmptyContext(), Outcome.success("undefined_outcome")

        transitions: dict = {}  # 空の遷移テーブル

        with pytest.raises(UndefinedStateError) as exc_info:
            await async_dag_runner(start=start, transitions=transitions)

        error_message = str(exc_info.value)
        assert "start" in error_message, f"エラーメッセージにノード名 'start' が含まれていない: {error_message}"
        assert "undefined_outcome" in error_message, f"エラーメッセージに状態 'undefined_outcome' が含まれていない: {error_message}"

    @pytest.mark.asyncio
    async def test_strict_mode_error_format_matches_sync(self) -> None:
        """async 版のエラーメッセージフォーマットが sync 版と一致する。

        dag_runner のフォーマット: "未定義の状態です: {state_string} (ノード: {node_name})"
        """

        class EmptyContext(Contract):
            pass

        async def my_node() -> tuple[EmptyContext, Outcome]:
            return EmptyContext(), Outcome.failure("unknown_error")

        transitions: dict = {}

        with pytest.raises(UndefinedStateError) as exc_info:
            await async_dag_runner(start=my_node, transitions=transitions)

        error_message = str(exc_info.value)
        # dag_runner と同じフォーマットであることを確認
        assert "(ノード:" in error_message, f"エラーメッセージにノード部分が含まれていない: {error_message}"
        assert "my_node" in error_message

    @pytest.mark.asyncio
    async def test_strict_mode_error_with_decorated_node(self) -> None:
        """@node デコレータ付き関数でもノード名が含まれる。"""
        from railway import node

        class EmptyContext(Contract):
            pass

        @node(name="custom_start_node")
        async def start() -> tuple[EmptyContext, Outcome]:
            return EmptyContext(), Outcome.success("unknown_state")

        transitions: dict = {}

        with pytest.raises(UndefinedStateError) as exc_info:
            await async_dag_runner(start=start, transitions=transitions)

        error_message = str(exc_info.value)
        assert "custom_start_node" in error_message, f"カスタムノード名が含まれていない: {error_message}"
