"""Tests for @node Board mode (Issue 19-02)."""
from __future__ import annotations

import pytest

from railway.core.board import BoardBase
from railway.core.dag.outcome import Outcome
from railway.core.decorators import node


class TestNodeDecoratorBoardMode:
    """@node の Board モード動作テスト。"""

    def test_board_node_returns_outcome_only(self) -> None:
        """Board モードでは Outcome のみ返却。"""

        @node
        def process(board):
            board.result = "done"
            return Outcome.success("done")

        b = BoardBase()
        outcome = process(b)
        assert outcome == Outcome.success("done")
        assert b.result == "done"

    def test_board_node_has_metadata(self) -> None:
        """Board ノードに正しいメタデータがあること。"""

        @node
        def process(board):
            return Outcome.success("done")

        assert process._is_railway_node is True
        assert process._is_board_node is True
        assert process._node_name == "process"

    def test_board_node_with_name_override(self) -> None:
        """name= でノード名オーバーライドが効くこと。"""

        @node(name="custom_name")
        def process(board):
            return Outcome.success("done")

        assert process._node_name == "custom_name"
        assert process._is_board_node is True

    def test_non_board_first_param_raises_e015(self) -> None:
        """第一引数名が board でない場合は E015 エラー。"""
        with pytest.raises(ValueError, match="E015"):

            @node
            def process(state):
                return Outcome.success("done")

    def test_no_params_raises_e015(self) -> None:
        """引数なし関数は E015 エラー。"""
        with pytest.raises(ValueError, match="E015"):

            @node
            def process():
                return Outcome.success("done")

    def test_board_node_with_retry(self) -> None:
        """Board モードでもリトライが動作すること。"""
        call_count = 0

        @node(retries=2, retry_on=(ValueError,))
        def flaky(board):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("transient")
            return Outcome.success("done")

        b = BoardBase()
        outcome = flaky(b)
        assert outcome == Outcome.success("done")
        assert call_count == 2


class TestNodeDecoratorLinearModePreserved:
    """Linear モード（typed_pipeline）が引き続き動作すること。"""

    def test_linear_mode_with_output_param(self) -> None:
        """output パラメータ指定時は board チェックをスキップ。"""

        @node(output=dict)
        def transform(data):
            return {"result": "ok"}

        result = transform({"input": "value"})
        assert result == {"result": "ok"}
        # linear mode では _is_board_node は False
        assert not getattr(transform, "_is_board_node", False)

    def test_linear_mode_with_inputs_param(self) -> None:
        """inputs パラメータ指定時は board チェックをスキップ。"""

        @node(inputs={"data": dict}, output=dict)
        def transform(data):
            return {"result": "ok"}

        result = transform({"input": "value"})
        assert result == {"result": "ok"}
        assert not getattr(transform, "_is_board_node", False)

    def test_linear_mode_no_e015(self) -> None:
        """linear モードでは E015 チェックなし。"""

        # output を指定すれば board でなくてもOK
        @node(output=dict)
        def process(data):
            return {"ok": True}

        # 例外が発生しないことを確認
        assert process._is_railway_node is True


class TestNodeDecoratorBoardAsync:
    """@node の Board モード非同期テスト。"""

    @pytest.mark.asyncio
    async def test_async_board_node(self) -> None:
        """非同期 Board ノードが動作すること。"""

        @node
        async def fetch(board):
            board.data = "fetched"
            return Outcome.success("done")

        b = BoardBase()
        outcome = await fetch(b)
        assert outcome == Outcome.success("done")
        assert b.data == "fetched"

    @pytest.mark.asyncio
    async def test_async_board_node_metadata(self) -> None:
        """非同期 Board ノードのメタデータ。"""

        @node
        async def fetch(board):
            return Outcome.success("done")

        assert fetch._is_board_node is True
        assert fetch._is_async is True


class TestContractModeParamsRemoved:
    """dag モード用の requires/provides/optional が削除されていること。"""

    def test_requires_param_removed(self) -> None:
        with pytest.raises(TypeError):

            @node(requires=["field_a"])  # type: ignore[call-overload]
            def process(board):
                return Outcome.success("done")

    def test_provides_param_removed(self) -> None:
        with pytest.raises(TypeError):

            @node(provides=["field_b"])  # type: ignore[call-overload]
            def process(board):
                return Outcome.success("done")

    def test_optional_dep_param_removed(self) -> None:
        with pytest.raises(TypeError):

            @node(optional=["field_c"])  # type: ignore[call-overload]
            def process(board):
                return Outcome.success("done")
