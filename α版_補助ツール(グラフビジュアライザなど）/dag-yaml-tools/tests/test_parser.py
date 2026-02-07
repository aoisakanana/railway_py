"""Tests for parser module."""

import pytest
import yaml
import networkx as nx
from pathlib import Path

from dag_yaml_tools.parser import (
    load_yaml,
    flatten_nodes,
    build_graph,
    get_terminal_nodes,
    get_node_type,
    DAGYamlData,
)


class TestLoadYaml:
    """Tests for load_yaml function."""

    def test_load_yaml_success(self, sample_yaml_path: Path) -> None:
        """Test loading a valid YAML file."""
        result = load_yaml(sample_yaml_path)
        assert "start" in result
        assert "nodes" in result
        assert "transitions" in result

    def test_load_yaml_file_not_found(self) -> None:
        """Test FileNotFoundError for non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_yaml(Path("nonexistent.yaml"))

    def test_load_yaml_invalid_syntax(self, tmp_path: Path) -> None:
        """Test yaml.YAMLError for invalid YAML syntax."""
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text("invalid: yaml: syntax: [")
        with pytest.raises(yaml.YAMLError):
            load_yaml(invalid_file)

    def test_load_yaml_missing_start(self, tmp_path: Path) -> None:
        """Test ValueError when start section is missing."""
        incomplete = tmp_path / "incomplete.yaml"
        incomplete.write_text("nodes: {}\ntransitions: {}")
        with pytest.raises(ValueError, match="start"):
            load_yaml(incomplete)

    def test_load_yaml_missing_nodes(self, tmp_path: Path) -> None:
        """Test ValueError when nodes section is missing."""
        incomplete = tmp_path / "incomplete.yaml"
        incomplete.write_text("start: a\ntransitions: {}")
        with pytest.raises(ValueError, match="nodes"):
            load_yaml(incomplete)

    def test_load_yaml_missing_transitions(self, tmp_path: Path) -> None:
        """Test ValueError when transitions section is missing."""
        incomplete = tmp_path / "incomplete.yaml"
        incomplete.write_text("start: a\nnodes: {}")
        with pytest.raises(ValueError, match="transitions"):
            load_yaml(incomplete)

    def test_load_yaml_returns_correct_types(self, tmp_path: Path) -> None:
        """Test that returned data has correct types."""
        valid_file = tmp_path / "valid.yaml"
        valid_file.write_text("""
start: start_node
nodes:
  start_node:
  end:
transitions:
  start_node:
    next: end
""")
        result = load_yaml(valid_file)
        assert isinstance(result["start"], str)
        assert isinstance(result["nodes"], dict)
        assert isinstance(result["transitions"], dict)


class TestFlattenNodes:
    """Tests for flatten_nodes function."""

    def test_flatten_nodes_simple(self) -> None:
        """Test flattening simple nodes."""
        nodes = {"a": None, "b": None}
        result = flatten_nodes(nodes)
        assert result == {"a", "b"}

    def test_flatten_nodes_nested(self) -> None:
        """Test flattening nested nodes."""
        nodes = {
            "exit": {
                "success": None,
                "failure": None
            }
        }
        result = flatten_nodes(nodes)
        assert result == {"exit.success", "exit.failure"}

    def test_flatten_nodes_deep_nested(self) -> None:
        """Test flattening deeply nested nodes."""
        nodes = {
            "exit": {
                "failure": {
                    "ssh": {
                        "handshake": None
                    }
                }
            }
        }
        result = flatten_nodes(nodes)
        assert result == {"exit.failure.ssh.handshake"}

    def test_flatten_nodes_with_metadata(self) -> None:
        """Test that nodes with metadata are treated as leaves."""
        nodes = {
            "start_node": {
                "description": "開始ノード"
            },
            "exit": {
                "success": {
                    "pattern1": {
                        "module": "nodes.exit.success.pattern1",
                        "function": "pattern1",
                        "description": "成功パターン1"
                    }
                }
            }
        }
        result = flatten_nodes(nodes)
        assert result == {"start_node", "exit.success.pattern1"}

    def test_flatten_nodes_mixed(self) -> None:
        """Test flattening mixed node types."""
        nodes = {
            "process_a": None,
            "process_b": {"description": "処理B"},
            "exit": {
                "success": None
            }
        }
        result = flatten_nodes(nodes)
        assert result == {"process_a", "process_b", "exit.success"}

    def test_flatten_nodes_empty(self) -> None:
        """Test flattening empty dictionary."""
        result = flatten_nodes({})
        assert result == set()

    def test_flatten_nodes_sample_yaml(self, sample_yaml_path: Path) -> None:
        """Test flattening nodes from sample YAML."""
        data = load_yaml(sample_yaml_path)
        result = flatten_nodes(data["nodes"])
        
        # Check some expected nodes
        assert "start_node" in result
        assert "process_a" in result
        assert "exit.success.pattern1" in result
        assert "exit.failure.unknown" in result
        assert "exit.failure.ssh.handshake" in result


class TestGetTerminalNodes:
    """Tests for get_terminal_nodes function."""

    def test_get_terminal_nodes_basic(self) -> None:
        """Test extracting terminal nodes."""
        nodes = {"start_node", "process_a", "exit.success.pattern1", "exit.failure.unknown"}
        result = get_terminal_nodes(nodes)
        assert result == {"exit.success.pattern1", "exit.failure.unknown"}

    def test_get_terminal_nodes_empty(self) -> None:
        """Test with no terminal nodes."""
        nodes = {"start_node", "process_a"}
        result = get_terminal_nodes(nodes)
        assert result == set()

    def test_get_terminal_nodes_all_terminal(self) -> None:
        """Test with all terminal nodes."""
        nodes = {"exit.success", "exit.failure"}
        result = get_terminal_nodes(nodes)
        assert result == {"exit.success", "exit.failure"}


class TestGetNodeType:
    """Tests for get_node_type function."""

    def test_get_node_type_start(self) -> None:
        """Test start node type."""
        assert get_node_type("start_node", "start_node") == "start"

    def test_get_node_type_success(self) -> None:
        """Test success terminal node type."""
        assert get_node_type("exit.success.pattern1", "start_node") == "success"

    def test_get_node_type_failure(self) -> None:
        """Test failure terminal node type."""
        assert get_node_type("exit.failure.unknown", "start_node") == "failure"

    def test_get_node_type_process(self) -> None:
        """Test process node type."""
        assert get_node_type("process_a", "start_node") == "process"

    def test_get_node_type_deep_success(self) -> None:
        """Test deeply nested success node."""
        assert get_node_type("exit.success.api.response.ok", "start") == "success"

    def test_get_node_type_deep_failure(self) -> None:
        """Test deeply nested failure node."""
        assert get_node_type("exit.failure.ssh.auth.perm", "start") == "failure"


class TestBuildGraph:
    """Tests for build_graph function."""

    def test_build_graph_creates_digraph(self) -> None:
        """Test that DiGraph is created."""
        yaml_data: DAGYamlData = {
            "start": "start_node",
            "nodes": {"start_node": None, "end": None},
            "transitions": {"start_node": {"next": "end"}},
        }
        result = build_graph(yaml_data)
        assert isinstance(result.graph, nx.DiGraph)

    def test_build_graph_has_all_nodes(self) -> None:
        """Test that all nodes are in the graph."""
        yaml_data: DAGYamlData = {
            "start": "start_node",
            "nodes": {"start_node": None, "process_a": None, "end": None},
            "transitions": {"start_node": {"next": "process_a"}},
        }
        result = build_graph(yaml_data)
        assert "start_node" in result.graph.nodes
        assert "process_a" in result.graph.nodes
        assert "end" in result.graph.nodes

    def test_build_graph_has_edges(self) -> None:
        """Test that transitions become edges."""
        yaml_data: DAGYamlData = {
            "start": "start_node",
            "nodes": {"start_node": None, "process_a": None},
            "transitions": {"start_node": {"success": "process_a"}},
        }
        result = build_graph(yaml_data)
        assert result.graph.has_edge("start_node", "process_a")

    def test_build_graph_edge_has_label(self) -> None:
        """Test that edges have state labels."""
        yaml_data: DAGYamlData = {
            "start": "start_node",
            "nodes": {"start_node": None, "process_a": None},
            "transitions": {"start_node": {"success::done": "process_a"}},
        }
        result = build_graph(yaml_data)
        edge_data = result.graph.get_edge_data("start_node", "process_a")
        assert edge_data is not None
        assert edge_data["label"] == "success::done"

    def test_build_graph_start_node(self) -> None:
        """Test that start node is correctly set."""
        yaml_data: DAGYamlData = {
            "start": "start_node",
            "nodes": {"start_node": None},
            "transitions": {},
        }
        result = build_graph(yaml_data)
        assert result.start_node == "start_node"

    def test_build_graph_terminal_nodes(self) -> None:
        """Test that terminal nodes are correctly identified."""
        yaml_data: DAGYamlData = {
            "start": "start",
            "nodes": {
                "start": None,
                "exit": {"success": None, "failure": None},
            },
            "transitions": {},
        }
        result = build_graph(yaml_data)
        assert result.terminal_nodes == {"exit.success", "exit.failure"}

    def test_build_graph_sample_yaml(self, sample_yaml_path: Path) -> None:
        """Test building graph from sample YAML."""
        yaml_data = load_yaml(sample_yaml_path)
        result = build_graph(yaml_data)

        # Check graph properties
        assert result.start_node == "start_node"
        assert "start_node" in result.all_nodes
        assert "exit.success.pattern1" in result.terminal_nodes
        assert result.graph.has_edge("start_node", "process_a")
