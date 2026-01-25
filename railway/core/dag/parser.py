"""
YAML parser for transition graphs.

This module provides pure functions for parsing YAML content
into TransitionGraph data structures. IO operations are separated
at the boundary (load_transition_graph).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from railway.core.dag.types import (
    ExitDefinition,
    GraphOptions,
    NodeDefinition,
    StateTransition,
    TransitionGraph,
)


class ParseError(Exception):
    """Error during YAML parsing."""

    pass


SUPPORTED_VERSIONS = ("1.0",)


def parse_transition_graph(yaml_content: str) -> TransitionGraph:
    """
    Parse YAML content into a TransitionGraph.

    This is a pure function - it takes a string and returns
    a data structure, with no side effects.

    Args:
        yaml_content: YAML string to parse

    Returns:
        Parsed TransitionGraph

    Raises:
        ParseError: If parsing fails
    """
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise ParseError(f"YAML構文エラー: {e}") from e

    if not isinstance(data, dict):
        raise ParseError("YAMLのルートは辞書である必要があります")

    return _build_graph(data)


def load_transition_graph(file_path: Path) -> TransitionGraph:
    """
    Load and parse a transition graph from a file.

    This is the IO boundary - it reads the file and delegates
    to the pure parse function.

    Args:
        file_path: Path to YAML file

    Returns:
        Parsed TransitionGraph

    Raises:
        ParseError: If file not found or parsing fails
    """
    if not file_path.exists():
        raise ParseError(f"ファイルが存在しません: {file_path}")

    try:
        content = file_path.read_text(encoding="utf-8")
    except IOError as e:
        raise ParseError(f"ファイル読み込みエラー: {e}") from e

    return parse_transition_graph(content)


def _build_graph(data: dict[str, Any]) -> TransitionGraph:
    """Build TransitionGraph from parsed YAML data."""
    # Required fields validation
    _require_field(data, "version")
    _require_field(data, "entrypoint")
    _require_field(data, "nodes")
    _require_field(data, "start")
    _require_field(data, "transitions")

    # Parse nodes
    nodes_data = data.get("nodes", {})
    if not isinstance(nodes_data, dict):
        nodes_data = {}

    nodes = tuple(
        _parse_node_definition(name, node_data)
        for name, node_data in nodes_data.items()
    )

    # Parse exits
    exits_data = data.get("exits", {})
    if not isinstance(exits_data, dict):
        exits_data = {}

    exits = tuple(
        _parse_exit_definition(name, exit_data)
        for name, exit_data in exits_data.items()
    )

    # Parse transitions
    all_transitions: list[StateTransition] = []
    transitions_data = data.get("transitions", {})
    if isinstance(transitions_data, dict):
        for node_name, node_transitions in transitions_data.items():
            if node_transitions and isinstance(node_transitions, dict):
                all_transitions.extend(
                    _parse_transitions_for_node(node_name, node_transitions)
                )

    # Parse options
    options = _parse_options(data.get("options", {}))

    return TransitionGraph(
        version=str(data["version"]),
        entrypoint=str(data["entrypoint"]),
        description=str(data.get("description", "")),
        nodes=nodes,
        exits=exits,
        transitions=tuple(all_transitions),
        start_node=str(data["start"]),
        options=options,
    )


def _require_field(data: dict, field: str) -> None:
    """Validate that a required field exists."""
    if field not in data:
        raise ParseError(f"必須フィールドがありません: {field}")


def _parse_node_definition(name: str, data: dict[str, Any]) -> NodeDefinition:
    """
    Parse a single node definition.

    Args:
        name: Node name (key in YAML)
        data: Node data dict

    Returns:
        NodeDefinition instance
    """
    if not isinstance(data, dict):
        raise ParseError(f"ノード '{name}' のデータが不正です")

    if "module" not in data:
        raise ParseError(f"ノード '{name}' に module がありません")
    if "function" not in data:
        raise ParseError(f"ノード '{name}' に function がありません")

    return NodeDefinition(
        name=name,
        module=str(data["module"]),
        function=str(data["function"]),
        description=str(data.get("description", "")),
    )


def _parse_exit_definition(name: str, data: dict[str, Any]) -> ExitDefinition:
    """
    Parse a single exit definition.

    Args:
        name: Exit name (key in YAML)
        data: Exit data dict

    Returns:
        ExitDefinition instance
    """
    if not isinstance(data, dict):
        data = {}

    return ExitDefinition(
        name=name,
        code=int(data.get("code", 0)),
        description=str(data.get("description", "")),
    )


def _parse_transitions_for_node(
    node_name: str,
    transitions_data: dict[str, str],
) -> list[StateTransition]:
    """
    Parse all transitions for a single node.

    Args:
        node_name: Source node name
        transitions_data: Dict of state -> target

    Returns:
        List of StateTransition instances
    """
    transitions = []
    for state, target in transitions_data.items():
        transitions.append(
            StateTransition(
                from_node=node_name,
                from_state=str(state),
                to_target=str(target),
            )
        )
    return transitions


def _parse_options(data: dict[str, Any] | None) -> GraphOptions:
    """
    Parse graph options with defaults.

    Args:
        data: Options dict from YAML

    Returns:
        GraphOptions instance
    """
    if not data or not isinstance(data, dict):
        return GraphOptions()

    return GraphOptions(
        max_iterations=int(data.get("max_iterations", 100)),
        enable_loop_detection=bool(data.get("enable_loop_detection", True)),
        strict_state_check=bool(data.get("strict_state_check", True)),
    )
