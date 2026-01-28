"""Tests for DAG transition graph data types."""
from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest


class TestNodeDefinition:
    """Test NodeDefinition data type."""

    def test_create_node_definition(self):
        """Should create a valid NodeDefinition."""
        from railway.core.dag.types import NodeDefinition

        node = NodeDefinition(
            name="fetch_alert",
            module="nodes.fetch_alert",
            function="fetch_alert",
            description="外部SaaS APIからアラート情報を取得",
        )

        assert node.name == "fetch_alert"
        assert node.module == "nodes.fetch_alert"
        assert node.function == "fetch_alert"
        assert node.description == "外部SaaS APIからアラート情報を取得"

    def test_node_definition_is_immutable(self):
        """NodeDefinition should be immutable."""
        from railway.core.dag.types import NodeDefinition

        node = NodeDefinition(
            name="fetch_alert",
            module="nodes.fetch_alert",
            function="fetch_alert",
            description="",
        )

        with pytest.raises(FrozenInstanceError):
            node.name = "other_name"

    def test_node_definition_equality(self):
        """Two NodeDefinitions with same values should be equal."""
        from railway.core.dag.types import NodeDefinition

        node1 = NodeDefinition("a", "m", "f", "d")
        node2 = NodeDefinition("a", "m", "f", "d")

        assert node1 == node2

    def test_node_definition_hashable(self):
        """NodeDefinition should be hashable (usable in sets/dicts)."""
        from railway.core.dag.types import NodeDefinition

        node = NodeDefinition("a", "m", "f", "d")
        node_set = {node}

        assert node in node_set


class TestExitDefinition:
    """Test ExitDefinition data type."""

    def test_create_exit_definition(self):
        """Should create a valid ExitDefinition."""
        from railway.core.dag.types import ExitDefinition

        exit_def = ExitDefinition(
            name="green_resolved",
            code=0,
            description="インシデント解決による正常終了",
        )

        assert exit_def.name == "green_resolved"
        assert exit_def.code == 0
        assert exit_def.description == "インシデント解決による正常終了"

    def test_exit_definition_is_immutable(self):
        """ExitDefinition should be immutable."""
        from railway.core.dag.types import ExitDefinition

        exit_def = ExitDefinition("green", 0, "success")

        with pytest.raises(FrozenInstanceError):
            exit_def.code = 1


class TestStateTransition:
    """Test StateTransition data type."""

    def test_create_transition_to_node(self):
        """Should create a transition to another node."""
        from railway.core.dag.types import StateTransition

        transition = StateTransition(
            from_node="fetch_alert",
            from_state="success::done",
            to_target="check_session_exists",
        )

        assert transition.from_node == "fetch_alert"
        assert transition.from_state == "success::done"
        assert transition.to_target == "check_session_exists"
        assert transition.is_exit is False

    def test_create_transition_to_exit(self):
        """Should create a transition to an exit."""
        from railway.core.dag.types import StateTransition

        transition = StateTransition(
            from_node="fetch_alert",
            from_state="failure::http",
            to_target="exit::red_error",
        )

        assert transition.to_target == "exit::red_error"
        assert transition.is_exit is True

    def test_transition_is_immutable(self):
        """StateTransition should be immutable."""
        from railway.core.dag.types import StateTransition

        transition = StateTransition("n", "s", "t")

        with pytest.raises(FrozenInstanceError):
            transition.to_target = "other"

    def test_transition_exit_name(self):
        """Should extract exit name from target."""
        from railway.core.dag.types import StateTransition

        t1 = StateTransition("n", "s", "exit::green_done")
        t2 = StateTransition("n", "s", "other_node")

        assert t1.exit_name == "green_done"
        assert t2.exit_name is None


class TestGraphOptions:
    """Test GraphOptions data type."""

    def test_default_options(self):
        """Should have sensible defaults."""
        from railway.core.dag.types import GraphOptions

        options = GraphOptions()

        assert options.max_iterations == 100
        assert options.enable_loop_detection is True
        assert options.strict_state_check is True

    def test_custom_options(self):
        """Should accept custom values."""
        from railway.core.dag.types import GraphOptions

        options = GraphOptions(
            max_iterations=20,
            enable_loop_detection=False,
            strict_state_check=False,
        )

        assert options.max_iterations == 20
        assert options.enable_loop_detection is False


class TestTransitionGraph:
    """Test TransitionGraph data type."""

    def test_create_minimal_graph(self):
        """Should create a minimal valid graph."""
        from railway.core.dag.types import (
            ExitDefinition,
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
        )

        node = NodeDefinition("start", "nodes.start", "start", "開始ノード")
        exit_def = ExitDefinition("done", 0, "完了")
        transition = StateTransition("start", "success", "exit::done")

        graph = TransitionGraph(
            version="1.0",
            entrypoint="my_workflow",
            description="テストワークフロー",
            nodes=(node,),
            exits=(exit_def,),
            transitions=(transition,),
            start_node="start",
            options=GraphOptions(),
        )

        assert graph.version == "1.0"
        assert graph.entrypoint == "my_workflow"
        assert len(graph.nodes) == 1
        assert len(graph.exits) == 1
        assert len(graph.transitions) == 1
        assert graph.start_node == "start"

    def test_graph_is_immutable(self):
        """TransitionGraph should be immutable."""
        from railway.core.dag.types import (
            ExitDefinition,
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
        )

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(NodeDefinition("a", "m", "f", "d"),),
            exits=(ExitDefinition("e", 0, ""),),
            transitions=(StateTransition("a", "s", "exit::e"),),
            start_node="a",
            options=GraphOptions(),
        )

        with pytest.raises(FrozenInstanceError):
            graph.version = "2.0"

    def test_graph_nodes_are_tuple(self):
        """Graph nodes should be tuple (immutable sequence)."""
        from railway.core.dag.types import NodeDefinition, TransitionGraph

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(NodeDefinition("a", "m", "f", "d"),),
            exits=(),
            transitions=(),
            start_node="a",
            options=None,
        )

        assert isinstance(graph.nodes, tuple)

    def test_graph_get_node_by_name(self):
        """Should get node by name."""
        from railway.core.dag.types import (
            GraphOptions,
            NodeDefinition,
            TransitionGraph,
        )

        node1 = NodeDefinition("fetch", "m1", "f1", "d1")
        node2 = NodeDefinition("process", "m2", "f2", "d2")

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(node1, node2),
            exits=(),
            transitions=(),
            start_node="fetch",
            options=GraphOptions(),
        )

        assert graph.get_node("fetch") == node1
        assert graph.get_node("process") == node2
        assert graph.get_node("unknown") is None

    def test_graph_get_transitions_for_node(self):
        """Should get all transitions for a node."""
        from railway.core.dag.types import (
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
        )

        t1 = StateTransition("fetch", "success", "process")
        t2 = StateTransition("fetch", "failure", "exit::error")
        t3 = StateTransition("process", "success", "exit::done")

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(
                NodeDefinition("fetch", "m", "f", "d"),
                NodeDefinition("process", "m", "f", "d"),
            ),
            exits=(),
            transitions=(t1, t2, t3),
            start_node="fetch",
            options=GraphOptions(),
        )

        fetch_transitions = graph.get_transitions_for_node("fetch")
        assert len(fetch_transitions) == 2
        assert t1 in fetch_transitions
        assert t2 in fetch_transitions

    def test_graph_get_states_for_node(self):
        """Should get all states for a node."""
        from railway.core.dag.types import (
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
        )

        t1 = StateTransition("fetch", "success::done", "process")
        t2 = StateTransition("fetch", "failure::http", "exit::error")

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(NodeDefinition("fetch", "m", "f", "d"),),
            exits=(),
            transitions=(t1, t2),
            start_node="fetch",
            options=GraphOptions(),
        )

        states = graph.get_states_for_node("fetch")
        assert "success::done" in states
        assert "failure::http" in states

    def test_graph_get_exit(self):
        """Should get exit by name."""
        from railway.core.dag.types import (
            ExitDefinition,
            GraphOptions,
            NodeDefinition,
            TransitionGraph,
        )

        exit1 = ExitDefinition("green", 0, "success")
        exit2 = ExitDefinition("red", 1, "error")

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(NodeDefinition("a", "m", "f", "d"),),
            exits=(exit1, exit2),
            transitions=(),
            start_node="a",
            options=GraphOptions(),
        )

        assert graph.get_exit("green") == exit1
        assert graph.get_exit("red") == exit2
        assert graph.get_exit("unknown") is None


class TestGeneratedFileMetadata:
    """Test GeneratedFileMetadata data type."""

    def test_create_metadata(self):
        """Should create file generation metadata."""
        from railway.core.dag.types import GeneratedFileMetadata

        meta = GeneratedFileMetadata(
            source_file="transition_graphs/top2_20250125.yml",
            generated_at=datetime(2025, 1, 25, 14, 30, 0),
            graph_version="1.0",
            entrypoint="top2",
        )

        assert meta.source_file == "transition_graphs/top2_20250125.yml"
        assert meta.entrypoint == "top2"

    def test_metadata_is_immutable(self):
        """GeneratedFileMetadata should be immutable."""
        from railway.core.dag.types import GeneratedFileMetadata

        meta = GeneratedFileMetadata(
            source_file="test.yml",
            generated_at=datetime.now(),
            graph_version="1.0",
            entrypoint="test",
        )

        with pytest.raises(FrozenInstanceError):
            meta.entrypoint = "other"
