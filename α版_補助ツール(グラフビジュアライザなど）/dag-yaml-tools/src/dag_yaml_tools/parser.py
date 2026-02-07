"""Parser module for DAG YAML files."""

from pathlib import Path
from typing import Any, NamedTuple, TypedDict

import networkx as nx
import yaml


class DAGYamlData(TypedDict):
    """Typed dictionary for parsed DAG YAML data."""

    start: str
    nodes: dict[str, Any]
    transitions: dict[str, dict[str, str]]


class DAGGraph(NamedTuple):
    """Result of graph construction."""

    graph: nx.DiGraph
    start_node: str
    all_nodes: set[str]
    terminal_nodes: set[str]


REQUIRED_SECTIONS = ("start", "nodes", "transitions")
METADATA_KEYS = frozenset({"description", "module", "function"})


def load_yaml(filepath: Path) -> DAGYamlData:
    """
    Load and parse a YAML file.

    Args:
        filepath: Path to the YAML file.

    Returns:
        Parsed YAML data as DAGYamlData.

    Raises:
        FileNotFoundError: If the file does not exist.
        yaml.YAMLError: If the YAML syntax is invalid.
        ValueError: If required sections are missing.
    """
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        data = {}

    for section in REQUIRED_SECTIONS:
        if section not in data:
            raise ValueError(f"Required section '{section}' is missing")

    return DAGYamlData(
        start=data["start"],
        nodes=data["nodes"] or {},
        transitions=data["transitions"] or {},
    )


def _is_leaf_node(value: Any) -> bool:
    """
    Determine if a node value represents a leaf node.

    A node is a leaf if:
    - It is None
    - It is a dict containing only metadata keys (description, module, function)
    - It is not a dict

    Args:
        value: The node value to check.

    Returns:
        True if the node is a leaf, False otherwise.
    """
    if value is None:
        return True
    if isinstance(value, dict):
        return all(k in METADATA_KEYS for k in value.keys())
    return True


def flatten_nodes(nodes: dict[str, Any], prefix: str = "") -> set[str]:
    """
    Flatten nested node definitions into dot-separated node names.

    Args:
        nodes: Nested node dictionary.
        prefix: Current path prefix (for recursion).

    Returns:
        Set of flattened node names.
    """
    result: set[str] = set()

    for key, value in nodes.items():
        full_path = f"{prefix}.{key}" if prefix else key

        if _is_leaf_node(value):
            result.add(full_path)
        else:
            # Recursively process nested nodes
            result.update(flatten_nodes(value, full_path))

    return result


def get_terminal_nodes(nodes: set[str]) -> set[str]:
    """
    Extract terminal nodes (nodes starting with 'exit.').

    Args:
        nodes: Set of all node names.

    Returns:
        Set of terminal node names.
    """
    return {n for n in nodes if n.startswith("exit.")}


def get_node_type(node_name: str, start_node: str) -> str:
    """
    Determine the type of a node.

    Args:
        node_name: Name of the node.
        start_node: Name of the start node.

    Returns:
        One of: "start", "success", "failure", "process"
    """
    if node_name == start_node:
        return "start"
    if node_name.startswith("exit.success"):
        return "success"
    if node_name.startswith("exit.failure"):
        return "failure"
    return "process"


def build_graph(yaml_data: DAGYamlData) -> DAGGraph:
    """
    Build a NetworkX DiGraph from parsed YAML data.

    Args:
        yaml_data: Parsed DAG YAML data.

    Returns:
        DAGGraph containing the graph and metadata.
    """
    graph = nx.DiGraph()

    # Flatten nodes
    all_nodes = flatten_nodes(yaml_data["nodes"])

    # Add all nodes to the graph
    for node in all_nodes:
        graph.add_node(node)

    # Add edges from transitions
    transitions = yaml_data["transitions"]
    for source, state_targets in transitions.items():
        for state, target in state_targets.items():
            graph.add_edge(source, target, label=state)

    # Get terminal nodes
    terminal_nodes = get_terminal_nodes(all_nodes)

    return DAGGraph(
        graph=graph,
        start_node=yaml_data["start"],
        all_nodes=all_nodes,
        terminal_nodes=terminal_nodes,
    )
