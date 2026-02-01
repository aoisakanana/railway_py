"""
YAML parser for transition graphs.

This module provides pure functions for parsing YAML content
into TransitionGraph data structures. IO operations are separated
at the boundary (load_transition_graph).

New in v0.12.0:
- Nested node parsing under nodes.exit
- Automatic module/function resolution from YAML path
- Exit code auto-detection (success=0, failure=1)
"""
from __future__ import annotations

from collections.abc import Iterator, Sequence
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

# Reserved keys that indicate a leaf node (not intermediate)
_LEAF_KEYS: frozenset[str] = frozenset({
    "description",
    "module",
    "function",
    "exit_code",
})


class ParseError(Exception):
    """Error during YAML parsing."""

    pass


SUPPORTED_VERSIONS = ("1.0",)


# =============================================================================
# Exit Node Parsing (v0.12.0+)
# =============================================================================


def parse_nodes(
    data: dict[str, Any],
    entrypoint: str | None = None,
) -> Sequence[NodeDefinition]:
    """Parse nodes section with nested structure support (pure function).

    Supports both flat nodes and nested exit nodes:
    - Flat: {"start": {"description": "..."}}
    - Nested: {"exit": {"success": {"done": {"description": "..."}}}}

    Auto-resolution:
    - module: from YAML path with entrypoint (e.g., "nodes.{entrypoint}.start")
    - function: from key name (e.g., "start")
    - exit_code: success=0, failure/others=1

    Note:
        Exit nodes (nodes.exit.*) do NOT include entrypoint in module path.

    Args:
        data: YAML nodes section dictionary
        entrypoint: Optional entrypoint name for module path resolution

    Returns:
        Immutable sequence of NodeDefinition

    Example:
        >>> nodes_data = {"start": {"description": "開始"}}
        >>> result = parse_nodes(nodes_data, entrypoint="my_workflow")
        >>> result[0].module
        'nodes.my_workflow.start'
    """
    return tuple(_parse_nodes_recursive(data, "nodes", entrypoint))


def _parse_nodes_recursive(
    data: dict[str, Any],
    path_prefix: str,
    entrypoint: str | None = None,
) -> Iterator[NodeDefinition]:
    """Recursively parse node definitions (generator).

    Lazy evaluation for memory efficiency.
    Collect with tuple() for immutable sequence.
    """
    for key, value in data.items():
        current_path = f"{path_prefix}.{key}"

        if _is_leaf_node(value):
            yield _parse_leaf_node(key, value, current_path, entrypoint)
        else:
            # Intermediate node - recurse
            yield from _parse_nodes_recursive(value, current_path, entrypoint)


def _is_leaf_node(value: dict[str, Any] | None) -> bool:
    """Determine if a node value is a leaf node (pure function).

    Leaf node conditions:
    1. None or empty dict
    2. Not a dict
    3. Contains only reserved keys (no child nodes)

    Args:
        value: Node value from YAML

    Returns:
        True if this is a leaf node
    """
    if value is None:
        return True
    if not isinstance(value, dict):
        return True
    if len(value) == 0:
        return True

    # Check for non-reserved keys (child nodes)
    non_reserved_keys = set(value.keys()) - _LEAF_KEYS
    return len(non_reserved_keys) == 0


def _parse_leaf_node(
    key: str,
    data: dict[str, Any] | None,
    yaml_path: str,
    entrypoint: str | None = None,
) -> NodeDefinition:
    """Parse a leaf node definition (pure function).

    Auto-resolution:
    - module: explicit value, or path with entrypoint for non-exit nodes
    - function: explicit value or key

    Note:
        Exit nodes (nodes.exit.*) do NOT include entrypoint in module path.

    Examples:
        yaml_path="nodes.start", entrypoint="my_wf"
            -> module="nodes.my_wf.start"

        yaml_path="nodes.process.check.db", entrypoint="my_wf"
            -> module="nodes.my_wf.process.check.db"

        yaml_path="nodes.exit.success.done", entrypoint="my_wf"
            -> module="nodes.exit.success.done" (exit ignores entrypoint)
    """
    data = data or {}

    # Exit node detection (nodes.exit.* path)
    is_exit = yaml_path.startswith("nodes.exit.")

    # Auto-resolve module with entrypoint (non-exit nodes only)
    module = _resolve_module_path_with_entrypoint(
        yaml_path, entrypoint, is_exit, data.get("module")
    )

    function = data.get("function") or key

    # Exit code resolution
    exit_code = _resolve_exit_code(yaml_path, data) if is_exit else None

    return NodeDefinition(
        name=yaml_path.removeprefix("nodes."),
        module=module,
        function=function,
        description=data.get("description", ""),
        is_exit=is_exit,
        exit_code=exit_code,
    )


def _resolve_module_path_with_entrypoint(
    yaml_path: str,
    entrypoint: str | None,
    is_exit: bool,
    explicit_module: str | None,
) -> str:
    """Resolve module path with entrypoint (pure function).

    Args:
        yaml_path: Full YAML path (e.g., "nodes.process.check.db")
        entrypoint: Optional entrypoint name
        is_exit: True if this is an exit node
        explicit_module: Explicitly specified module (takes priority)

    Returns:
        Resolved module path

    Examples:
        >>> _resolve_module_path_with_entrypoint("nodes.start", "my_wf", False, None)
        'nodes.my_wf.start'
        >>> _resolve_module_path_with_entrypoint("nodes.process.check", "my_wf", False, None)
        'nodes.my_wf.process.check'
        >>> _resolve_module_path_with_entrypoint("nodes.exit.success.done", "my_wf", True, None)
        'nodes.exit.success.done'
    """
    # Explicit module takes priority
    if explicit_module:
        return explicit_module

    # Exit nodes: use yaml_path as-is
    if is_exit:
        return yaml_path

    # Non-exit nodes with entrypoint: insert entrypoint after "nodes."
    if entrypoint:
        # yaml_path is "nodes.xxx.yyy" -> "nodes.{entrypoint}.xxx.yyy"
        node_path = yaml_path.removeprefix("nodes.")
        return f"nodes.{entrypoint}.{node_path}"

    # Fallback: use yaml_path as-is
    return yaml_path


def _resolve_exit_code(yaml_path: str, data: dict[str, Any]) -> int:
    """Resolve exit code for exit nodes (pure function).

    Priority:
    1. Explicit exit_code in data
    2. exit.success.* → 0
    3. Others (failure, warning, etc.) → 1
    """
    if "exit_code" in data:
        return int(data["exit_code"])
    if ".success." in yaml_path:
        return 0
    return 1  # failure, warning, and others default to 1


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
    except OSError as e:
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

    # Parse nodes (v0.12.0: use new nested parser with auto-resolution)
    nodes_data = data.get("nodes", {})
    if not isinstance(nodes_data, dict):
        nodes_data = {}

    # v0.13.3+: Pass entrypoint for module path auto-resolution
    entrypoint = str(data.get("entrypoint", ""))
    nodes = parse_nodes(nodes_data, entrypoint=entrypoint or None)

    # Parse exits (legacy format, kept for backward compatibility)
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
        nodes=tuple(nodes),  # Ensure tuple for immutability
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
