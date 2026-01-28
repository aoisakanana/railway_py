"""Tests for NodeDefinition exit node support."""

import pytest
from railway.core.dag.types import NodeDefinition


class TestNodeDefinitionExitSupport:
    """NodeDefinition の終端ノード対応テスト。"""

    def test_default_is_not_exit(self) -> None:
        """デフォルトは終端ノードではない。"""
        node = NodeDefinition(
            name="start",
            module="nodes.start",
            function="start",
            description="開始",
        )
        assert node.is_exit is False
        assert node.exit_code is None

    def test_exit_node_with_explicit_code(self) -> None:
        """終端ノードは明示的な exit_code を持てる。"""
        node = NodeDefinition(
            name="exit.success.done",
            module="nodes.exit.success.done",
            function="done",
            description="正常終了",
            is_exit=True,
            exit_code=0,
        )
        assert node.is_exit is True
        assert node.exit_code == 0

    def test_exit_node_code_from_parser(self) -> None:
        """終端ノードの exit_code はパーサーで設定される。

        Note:
            NodeDefinition 単体では exit_code のデフォルト設定を行わない。
            パーサー（Issue #25）が exit.success.* → 0, exit.failure.* → 1 を設定する。
        """
        # パーサーが設定した値がそのまま保持される
        node = NodeDefinition(
            name="exit.failure.error",
            module="nodes.exit.failure.error",
            function="error",
            description="異常終了",
            is_exit=True,
            exit_code=1,  # パーサーが設定
        )
        assert node.is_exit is True
        assert node.exit_code == 1

    def test_has_handler_with_module_and_function(self) -> None:
        """module と function があればハンドラを持つ。"""
        node = NodeDefinition(
            name="start",
            module="nodes.start",
            function="start",
            description="開始",
        )
        assert node.has_handler is True

    def test_has_handler_without_module(self) -> None:
        """module が空ならハンドラを持たない。"""
        node = NodeDefinition(
            name="exit.success.done",
            module="",
            function="done",
            description="終端",
            is_exit=True,
            exit_code=0,
        )
        assert node.has_handler is False

    def test_has_handler_without_function(self) -> None:
        """function が空ならハンドラを持たない。"""
        node = NodeDefinition(
            name="exit.success.done",
            module="nodes.exit.success.done",
            function="",
            description="終端",
            is_exit=True,
            exit_code=0,
        )
        assert node.has_handler is False

    def test_exit_node_can_have_handler(self) -> None:
        """終端ノードもハンドラを持てる。"""
        node = NodeDefinition(
            name="exit.success.done",
            module="nodes.exit.success.done",
            function="done",
            description="正常終了（Slack通知）",
            is_exit=True,
            exit_code=0,
        )
        assert node.is_exit is True
        assert node.has_handler is True

    def test_immutable(self) -> None:
        """frozen=True で不変。"""
        node = NodeDefinition(
            name="start",
            module="nodes.start",
            function="start",
            description="開始",
        )
        with pytest.raises(AttributeError):
            node.name = "changed"  # type: ignore

    def test_hashable(self) -> None:
        """frozen=True で hashable。"""
        node1 = NodeDefinition(
            name="start",
            module="nodes.start",
            function="start",
            description="開始",
        )
        node2 = NodeDefinition(
            name="start",
            module="nodes.start",
            function="start",
            description="開始",
        )
        # 同じ内容なら同じハッシュ
        assert hash(node1) == hash(node2)
        # set に追加可能
        nodes = {node1, node2}
        assert len(nodes) == 1


class TestNodeDefinitionBackwardCompatibility:
    """既存コードとの後方互換性テスト。"""

    def test_existing_node_creation_still_works(self) -> None:
        """既存のノード作成パターンが引き続き動作する。"""
        # 既存のコードがそのまま動く（is_exit, exit_code はデフォルト値を持つ）
        node = NodeDefinition(
            name="process",
            module="nodes.process",
            function="process",
            description="処理ノード",
        )
        assert node.name == "process"
        assert node.module == "nodes.process"
        assert node.function == "process"
        assert node.description == "処理ノード"
        # 新フィールドはデフォルト値
        assert node.is_exit is False
        assert node.exit_code is None
