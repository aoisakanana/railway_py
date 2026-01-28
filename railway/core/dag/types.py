"""
Immutable data types for DAG transition graphs.

All types are frozen dataclasses to ensure immutability,
following functional programming principles.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NodeDefinition:
    """Definition of a node in the transition graph (with exit node support).

    Attributes:
        name: Unique identifier (e.g., "start", "exit.success.done")
        module: Python module path (e.g., "nodes.fetch_alert")
        function: Function name to import from module
        description: Human-readable description
        is_exit: Whether this is an exit node
        exit_code: Exit code for exit nodes (None for regular nodes)

    Note:
        Exit nodes are under nodes.exit in YAML (e.g., exit.success.done).
        Exit code defaults are set by the parser:
        - exit.success.* → 0
        - exit.failure.* → 1
        - Custom values can be specified with exit_code field
    """

    name: str
    module: str
    function: str
    description: str
    is_exit: bool = False
    exit_code: int | None = None

    @property
    def has_handler(self) -> bool:
        """Check if this node has an executable handler function.

        A handler exists when both module and function are non-empty.
        Exit nodes can also have handlers for cleanup/notification.
        """
        return bool(self.module and self.function)


@dataclass(frozen=True)
class ExitDefinition:
    """
    Definition of an exit point in the transition graph.

    Attributes:
        name: Unique identifier for the exit (e.g., "green_resolved")
        code: Process exit code (0 for success, non-zero for failure)
        description: Human-readable description
    """

    name: str
    code: int
    description: str


@dataclass(frozen=True)
class StateTransition:
    """
    A single state transition in the graph.

    Attributes:
        from_node: Source node name
        from_state: State that triggers this transition
        to_target: Target node name or exit (prefixed with "exit::")
    """

    from_node: str
    from_state: str
    to_target: str

    @property
    def is_exit(self) -> bool:
        """Check if this transition leads to an exit.

        Supports both formats:
        - Legacy: exit::green_success (v0.11.x)
        - New: exit.success.done (v0.12.0+)
        """
        return self.to_target.startswith("exit::") or self.to_target.startswith("exit.")

    @property
    def exit_name(self) -> str | None:
        """Get exit name if this is an exit transition."""
        if self.is_exit:
            return self.to_target.removeprefix("exit::")
        return None


@dataclass(frozen=True)
class GraphOptions:
    """
    Configuration options for graph execution.

    Attributes:
        max_iterations: Maximum loop iterations before error
        enable_loop_detection: Detect infinite loops at runtime
        strict_state_check: Error on undefined states
    """

    max_iterations: int = 100
    enable_loop_detection: bool = True
    strict_state_check: bool = True


@dataclass(frozen=True)
class TransitionGraph:
    """
    Complete transition graph definition.

    This is the primary data structure representing a DAG workflow.
    All fields are immutable to ensure thread-safety and predictability.

    Attributes:
        version: Schema version (e.g., "1.0")
        entrypoint: Entry point name this graph belongs to
        description: Human-readable description
        nodes: Tuple of node definitions
        exits: Tuple of exit definitions
        transitions: Tuple of state transitions
        start_node: Name of the starting node
        options: Execution options
    """

    version: str
    entrypoint: str
    description: str
    nodes: tuple[NodeDefinition, ...]
    exits: tuple[ExitDefinition, ...]
    transitions: tuple[StateTransition, ...]
    start_node: str
    options: GraphOptions | None = None

    def get_node(self, name: str) -> NodeDefinition | None:
        """
        Get a node by name.

        Args:
            name: Node name to find

        Returns:
            NodeDefinition if found, None otherwise
        """
        for node in self.nodes:
            if node.name == name:
                return node
        return None

    def get_exit(self, name: str) -> ExitDefinition | None:
        """
        Get an exit by name.

        Args:
            name: Exit name to find

        Returns:
            ExitDefinition if found, None otherwise
        """
        for exit_def in self.exits:
            if exit_def.name == name:
                return exit_def
        return None

    def get_transitions_for_node(self, node_name: str) -> tuple[StateTransition, ...]:
        """
        Get all transitions originating from a node.

        Args:
            node_name: Source node name

        Returns:
            Tuple of transitions from the node
        """
        return tuple(t for t in self.transitions if t.from_node == node_name)

    def get_states_for_node(self, node_name: str) -> tuple[str, ...]:
        """
        Get all states defined for a node.

        Args:
            node_name: Node name

        Returns:
            Tuple of state strings
        """
        return tuple(t.from_state for t in self.transitions if t.from_node == node_name)


@dataclass(frozen=True)
class GeneratedFileMetadata:
    """
    Metadata for generated transition code files.

    Attributes:
        source_file: Path to source YAML file
        generated_at: Generation timestamp
        graph_version: Version from the graph
        entrypoint: Entry point name
    """

    source_file: str
    generated_at: datetime
    graph_version: str
    entrypoint: str
