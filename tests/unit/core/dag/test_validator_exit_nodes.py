"""Tests for validator exit node support."""

import pytest
from railway.core.dag.validator import (
    validate_graph,
    validate_transition_targets,
    validate_termination,
    validate_no_infinite_loop,
)
from railway.core.dag.types import (
    NodeDefinition,
    StateTransition,
    TransitionGraph,
)


class TestValidateTransitionTargetsExitNodes:
    """遷移先検証の終端ノード対応テスト。"""

    def test_valid_exit_node_target(self) -> None:
        """終端ノードへの遷移が有効。"""
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

        result = validate_transition_targets(graph)

        assert result.is_valid

    def test_invalid_exit_node_target(self) -> None:
        """存在しない終端ノードへの遷移がエラー。"""
        nodes = (
            NodeDefinition(
                name="start",
                module="nodes.start",
                function="start",
                description="開始",
            ),
        )
        transitions = (
            StateTransition(
                from_node="start",
                from_state="success::done",
                to_target="exit.success.nonexistent",  # 存在しない
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

        result = validate_transition_targets(graph)

        assert not result.is_valid
        assert any("E003" in e.code for e in result.errors)


class TestValidateTerminationExitNodes:
    """終端検証の終端ノード対応テスト。"""

    def test_exit_node_needs_no_transitions(self) -> None:
        """終端ノードは遷移定義不要。"""
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

        result = validate_termination(graph)

        # 終端ノードに遷移がなくてもエラーにならない
        assert result.is_valid


class TestValidateNoInfiniteLoopExitNodes:
    """無限ループ検証の終端ノード対応テスト。"""

    def test_all_paths_reach_exit(self) -> None:
        """全パスが終端ノードに到達。"""
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
                to_target="process",
            ),
            StateTransition(
                from_node="process",
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

        result = validate_no_infinite_loop(graph)

        assert result.is_valid

    def test_no_exit_nodes_error(self) -> None:
        """終端ノードがなく到達できない場合はエラー。"""
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

        result = validate_no_infinite_loop(graph)

        # 終端ノードがなく、終了に到達できないのでエラー
        assert not result.is_valid
        assert any("E006" in e.code for e in result.errors)


class TestValidateFullGraphWithExitNodes:
    """終端ノードを含むグラフの完全検証。"""

    def test_validate_complete_exit_node_graph(self) -> None:
        """終端ノードを含むグラフの完全検証。"""
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
            NodeDefinition(
                name="exit.failure.error",
                module="nodes.exit.failure.error",
                function="error",
                description="異常終了",
                is_exit=True,
                exit_code=1,
            ),
        )
        transitions = (
            StateTransition(
                from_node="start",
                from_state="success::done",
                to_target="exit.success.done",
            ),
            StateTransition(
                from_node="start",
                from_state="failure::error",
                to_target="exit.failure.error",
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

        result = validate_graph(graph)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_with_fixtures(self, exit_node_fixtures) -> None:
        """フィクスチャを使用した検証。"""
        from railway.core.dag.parser import load_transition_graph

        yaml_path = exit_node_fixtures / "basic_exit.yml"
        graph = load_transition_graph(yaml_path)

        result = validate_graph(graph)

        assert result.is_valid

    def test_validate_multiple_exits_fixture(self, exit_node_fixtures) -> None:
        """複数終端ノードを持つグラフの検証。"""
        from railway.core.dag.parser import load_transition_graph

        yaml_path = exit_node_fixtures / "multiple_exits.yml"
        graph = load_transition_graph(yaml_path)

        result = validate_graph(graph)

        assert result.is_valid
