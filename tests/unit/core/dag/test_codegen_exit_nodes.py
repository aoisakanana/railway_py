"""Tests for codegen exit node support."""

import pytest
from railway.core.dag.codegen import (
    generate_imports,
    generate_transition_table,
    generate_transition_code,
    generate_node_name_assignments,
    _find_node_by_name,
    _node_to_alias,
)
from railway.core.dag.types import (
    NodeDefinition,
    StateTransition,
    TransitionGraph,
)


class TestHelperFunctions:
    """ヘルパー関数テスト。"""

    def test_find_node_by_name_found(self) -> None:
        """ノードが見つかる。"""
        nodes = (
            NodeDefinition(
                name="start",
                module="nodes.start",
                function="start",
                description="開始",
            ),
        )
        result = _find_node_by_name(nodes, "start")
        assert result is not None
        assert result.name == "start"

    def test_find_node_by_name_not_found(self) -> None:
        """ノードが見つからない。"""
        nodes = (
            NodeDefinition(
                name="start",
                module="nodes.start",
                function="start",
                description="開始",
            ),
        )
        result = _find_node_by_name(nodes, "nonexistent")
        assert result is None

    def test_node_to_alias(self) -> None:
        """ノード名からエイリアスを生成。"""
        node = NodeDefinition(
            name="exit.success.done",
            module="nodes.exit.success.done",
            function="done",
            description="正常終了",
            is_exit=True,
            exit_code=0,
        )
        assert _node_to_alias(node) == "_exit_success_done"


class TestGenerateImports:
    """import 文生成テスト。"""

    def test_generates_normal_node_import(self) -> None:
        """通常ノードの import 文。"""
        nodes = (
            NodeDefinition(
                name="start",
                module="nodes.start",
                function="start",
                description="開始",
            ),
        )
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=nodes,
            exits=(),
            transitions=(),
            start_node="start",
            options=None,
        )

        result = generate_imports(graph)

        assert "from nodes.start import start" in result

    def test_generates_exit_node_import_with_alias(self) -> None:
        """終端ノードはエイリアス付きでインポート。"""
        nodes = (
            NodeDefinition(
                name="exit.success.done",
                module="nodes.exit.success.done",
                function="done",
                description="正常終了",
                is_exit=True,
                exit_code=0,
            ),
        )
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=nodes,
            exits=(),
            transitions=(),
            start_node="start",
            options=None,
        )

        result = generate_imports(graph)

        assert "from nodes.exit.success.done import done as _exit_success_done" in result

    def test_skips_node_without_handler(self) -> None:
        """ハンドラのないノードは import しない。"""
        nodes = (
            NodeDefinition(
                name="exit.success.done",
                module="",
                function="",
                description="正常終了（ハンドラなし）",
                is_exit=True,
                exit_code=0,
            ),
        )
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=nodes,
            exits=(),
            transitions=(),
            start_node="start",
            options=None,
        )

        result = generate_imports(graph)

        # ヘッダーコメントのみ
        assert "exit.success.done" not in result


class TestGenerateNodeNameAssignments:
    """_node_name 属性設定コード生成テスト。"""

    def test_generates_assignments_for_all_nodes(self) -> None:
        """全ノードに対して _node_name 属性を設定。"""
        nodes = (
            NodeDefinition(
                name="start",
                module="nodes.start",
                function="start",
                description="開始",
            ),
            NodeDefinition(
                name="exit.success.done",
                module="nodes.exit.success.done",
                function="done",
                description="正常終了",
                is_exit=True,
                exit_code=0,
            ),
        )
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=nodes,
            exits=(),
            transitions=(),
            start_node="start",
            options=None,
        )

        result = generate_node_name_assignments(graph)

        assert 'start._node_name = "start"' in result
        assert '_exit_success_done._node_name = "exit.success.done"' in result


class TestGenerateTransitionTable:
    """TRANSITION_TABLE 生成テスト。"""

    def test_transition_to_exit_node_uses_alias(self) -> None:
        """終端ノードへの遷移はエイリアスを使用。"""
        nodes = (
            NodeDefinition(
                name="process",
                module="nodes.process",
                function="process",
                description="処理",
            ),
            NodeDefinition(
                name="exit.success.done",
                module="nodes.exit.success.done",
                function="done",
                description="正常終了",
                is_exit=True,
                exit_code=0,
            ),
        )
        transitions = (
            StateTransition(
                from_node="process",
                from_state="success::done",
                to_target="exit.success.done",  # 新形式
            ),
        )
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=nodes,
            exits=(),
            transitions=transitions,
            start_node="process",
            options=None,
        )

        result = generate_transition_table(graph)

        # エイリアスを使用（アンダースコアプレフィックス）
        assert '"process::success::done": _exit_success_done' in result

    def test_transition_to_normal_node(self) -> None:
        """通常ノードへの遷移は関数名を使用。"""
        nodes = (
            NodeDefinition(
                name="start",
                module="nodes.start",
                function="start",
                description="開始",
            ),
            NodeDefinition(
                name="process",
                module="nodes.process",
                function="process",
                description="処理",
            ),
        )
        transitions = (
            StateTransition(
                from_node="start",
                from_state="success::done",
                to_target="process",
            ),
        )
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=nodes,
            exits=(),
            transitions=transitions,
            start_node="start",
            options=None,
        )

        result = generate_transition_table(graph)

        assert '"start::success::done": process' in result


class TestGenerateTransitionCodeIntegration:
    """統合テスト。"""

    def test_generated_code_is_valid_python(self) -> None:
        """生成されたコードが有効な Python。"""
        nodes = (
            NodeDefinition(
                name="start",
                module="nodes.start",
                function="start",
                description="開始",
            ),
            NodeDefinition(
                name="exit.success.done",
                module="nodes.exit.success.done",
                function="done",
                description="正常終了",
                is_exit=True,
                exit_code=0,
            ),
        )
        transitions = (
            StateTransition(
                from_node="start",
                from_state="success::done",
                to_target="exit.success.done",
            ),
        )
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=nodes,
            exits=(),
            transitions=transitions,
            start_node="start",
            options=None,
        )

        code = generate_transition_code(graph, "test.yml")

        # Python として構文解析可能
        compile(code, "<string>", "exec")

    def test_includes_node_name_assignments(self) -> None:
        """_node_name 属性設定が含まれる。"""
        nodes = (
            NodeDefinition(
                name="start",
                module="nodes.start",
                function="start",
                description="開始",
            ),
        )
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=nodes,
            exits=(),
            transitions=(),
            start_node="start",
            options=None,
        )

        code = generate_transition_code(graph, "test.yml")

        assert "_node_name" in code
