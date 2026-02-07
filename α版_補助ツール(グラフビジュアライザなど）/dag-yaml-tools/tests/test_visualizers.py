"""Tests for visualizers module."""

import pytest
import networkx as nx
from pathlib import Path

from dag_yaml_tools.visualizers import (
    get_node_style,
    get_node_label,
    create_pyvis_network,
    visualize_html,
    create_graphviz_digraph,
    visualize_png,
    COLOR_START,
    COLOR_SUCCESS,
    COLOR_FAILURE,
    COLOR_PROCESS,
)


@pytest.fixture
def sample_graph() -> nx.DiGraph:
    """Create a sample graph for testing."""
    G = nx.DiGraph()
    G.add_node("start_node")
    G.add_node("process_a")
    G.add_node("exit.success")
    G.add_node("exit.failure")
    G.add_edge("start_node", "process_a", label="success")
    G.add_edge("process_a", "exit.success", label="done")
    G.add_edge("process_a", "exit.failure", label="error")
    return G


class TestGetNodeStyle:
    """Tests for get_node_style function."""

    def test_get_node_style_start(self) -> None:
        """Test start node style."""
        style = get_node_style("start_node", "start_node")
        assert style.color == COLOR_START
        assert style.shape == "ellipse"

    def test_get_node_style_success(self) -> None:
        """Test success terminal node style."""
        style = get_node_style("exit.success.pattern1", "start_node")
        assert style.color == COLOR_SUCCESS
        assert style.shape == "box"

    def test_get_node_style_failure(self) -> None:
        """Test failure terminal node style."""
        style = get_node_style("exit.failure.unknown", "start_node")
        assert style.color == COLOR_FAILURE
        assert style.shape == "box"

    def test_get_node_style_process(self) -> None:
        """Test process node style."""
        style = get_node_style("process_a", "start_node")
        assert style.color == COLOR_PROCESS
        assert style.shape == "ellipse"

    def test_get_node_style_deep_success(self) -> None:
        """Test deeply nested success node."""
        style = get_node_style("exit.success.api.response.ok", "start")
        assert style.color == COLOR_SUCCESS

    def test_get_node_style_deep_failure(self) -> None:
        """Test deeply nested failure node."""
        style = get_node_style("exit.failure.ssh.auth.perm", "start")
        assert style.color == COLOR_FAILURE


class TestGetNodeLabel:
    """Tests for get_node_label function."""

    def test_get_node_label_simple(self) -> None:
        """Test simple label."""
        label = get_node_label("process_a")
        assert label == "process_a"

    def test_get_node_label_with_description(self) -> None:
        """Test label with description."""
        label = get_node_label("start_node", "開始ノード")
        assert "start_node" in label
        assert "開始ノード" in label

    def test_get_node_label_no_description(self) -> None:
        """Test label with None description."""
        label = get_node_label("process_a", None)
        assert label == "process_a"


class TestCreatePyvisNetwork:
    """Tests for create_pyvis_network function."""

    def test_create_pyvis_network_node_count(
        self, sample_graph: nx.DiGraph
    ) -> None:
        """Test correct number of nodes."""
        net = create_pyvis_network(sample_graph, "start_node", {})
        assert len(net.nodes) == len(sample_graph.nodes)

    def test_create_pyvis_network_edge_count(
        self, sample_graph: nx.DiGraph
    ) -> None:
        """Test correct number of edges."""
        net = create_pyvis_network(sample_graph, "start_node", {})
        assert len(net.edges) == len(sample_graph.edges)

    def test_create_pyvis_network_node_colors(
        self, sample_graph: nx.DiGraph
    ) -> None:
        """Test nodes have colors."""
        net = create_pyvis_network(sample_graph, "start_node", {})
        for node in net.nodes:
            assert "color" in node


class TestVisualizeHtml:
    """Tests for visualize_html function."""

    def test_visualize_html_creates_file(
        self, tmp_path: Path, sample_graph: nx.DiGraph
    ) -> None:
        """Test HTML file is created."""
        output = tmp_path / "graph.html"
        result = visualize_html(sample_graph, "start_node", {}, output)
        assert result.exists()
        assert result.suffix == ".html"

    def test_visualize_html_contains_nodes(
        self, tmp_path: Path, sample_graph: nx.DiGraph
    ) -> None:
        """Test HTML contains node names."""
        output = tmp_path / "graph.html"
        visualize_html(sample_graph, "start_node", {}, output)
        content = output.read_text()
        assert "start_node" in content

    def test_visualize_html_with_descriptions(
        self, tmp_path: Path, sample_graph: nx.DiGraph
    ) -> None:
        """Test descriptions appear in HTML."""
        descriptions = {"start_node": "test_description_marker"}
        output = tmp_path / "graph.html"
        visualize_html(sample_graph, "start_node", descriptions, output)
        content = output.read_text()
        # pyvis may escape unicode, so check for ASCII marker
        assert "test_description_marker" in content


class TestCreateGraphvizDigraph:
    """Tests for create_graphviz_digraph function."""

    def test_create_graphviz_digraph_has_nodes(
        self, sample_graph: nx.DiGraph
    ) -> None:
        """Test nodes are in Graphviz source."""
        dot = create_graphviz_digraph(sample_graph, "start_node", {})
        source = dot.source
        for node in sample_graph.nodes:
            assert node in source

    def test_create_graphviz_digraph_has_edges(
        self, sample_graph: nx.DiGraph
    ) -> None:
        """Test edges are in Graphviz source."""
        dot = create_graphviz_digraph(sample_graph, "start_node", {})
        source = dot.source
        assert "->" in source

    def test_create_graphviz_digraph_edge_labels(
        self, sample_graph: nx.DiGraph
    ) -> None:
        """Test edge labels are in Graphviz source."""
        dot = create_graphviz_digraph(sample_graph, "start_node", {})
        source = dot.source
        assert "success" in source


class TestVisualizePng:
    """Tests for visualize_png function."""

    def test_visualize_png_creates_file(
        self, tmp_path: Path, sample_graph: nx.DiGraph
    ) -> None:
        """Test PNG file is created."""
        output = tmp_path / "graph.png"
        result = visualize_png(sample_graph, "start_node", {}, output)
        assert result.exists()
        assert result.suffix == ".png"

    def test_visualize_png_valid_image(
        self, tmp_path: Path, sample_graph: nx.DiGraph
    ) -> None:
        """Test valid PNG image is created."""
        output = tmp_path / "graph.png"
        visualize_png(sample_graph, "start_node", {}, output)
        # Check PNG magic number
        with open(output, "rb") as f:
            magic = f.read(8)
        assert magic[:4] == b"\x89PNG"
