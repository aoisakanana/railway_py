"""
Graph validator for transition graphs.

All validation functions are pure - they take a TransitionGraph
and return a ValidationResult without side effects.
"""
from __future__ import annotations

from dataclasses import dataclass

from railway.core.dag.types import TransitionGraph


@dataclass(frozen=True)
class ValidationError:
    """A validation error."""

    code: str
    message: str


@dataclass(frozen=True)
class ValidationWarning:
    """A validation warning."""

    code: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    """
    Result of graph validation.

    Immutable data structure containing validation outcome.
    """

    is_valid: bool
    errors: tuple[ValidationError, ...]
    warnings: tuple[ValidationWarning, ...]

    @classmethod
    def valid(cls) -> "ValidationResult":
        """Create a valid result with no errors or warnings."""
        return cls(is_valid=True, errors=(), warnings=())

    @classmethod
    def error(cls, code: str, message: str) -> "ValidationResult":
        """Create an invalid result with a single error."""
        return cls(
            is_valid=False,
            errors=(ValidationError(code, message),),
            warnings=(),
        )

    @classmethod
    def warning(cls, code: str, message: str) -> "ValidationResult":
        """Create a valid result with a warning."""
        return cls(
            is_valid=True,
            errors=(),
            warnings=(ValidationWarning(code, message),),
        )


def combine_results(*results: ValidationResult) -> ValidationResult:
    """
    Combine multiple validation results.

    The combined result is valid only if all inputs are valid.
    All errors and warnings are collected.
    """
    all_errors: list[ValidationError] = []
    all_warnings: list[ValidationWarning] = []

    for result in results:
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)

    return ValidationResult(
        is_valid=len(all_errors) == 0,
        errors=tuple(all_errors),
        warnings=tuple(all_warnings),
    )


def validate_graph(graph: TransitionGraph) -> ValidationResult:
    """
    Perform full validation of a transition graph.

    Combines all individual validations.
    """
    return combine_results(
        validate_start_node_exists(graph),
        validate_transition_targets(graph),
        validate_reachability(graph),
        validate_termination(graph),
        validate_no_duplicate_states(graph),
        validate_no_infinite_loop(graph),
    )


def validate_start_node_exists(graph: TransitionGraph) -> ValidationResult:
    """Validate that the start node exists in the graph."""
    if graph.get_node(graph.start_node) is None:
        return ValidationResult.error(
            "E001",
            f"開始ノード '{graph.start_node}' が定義されていません",
        )
    return ValidationResult.valid()


def validate_transition_targets(graph: TransitionGraph) -> ValidationResult:
    """Validate that all transition targets exist."""
    errors: list[ValidationError] = []

    node_names = {node.name for node in graph.nodes}
    exit_names = {exit_def.name for exit_def in graph.exits}

    for transition in graph.transitions:
        if transition.is_exit:
            exit_name = transition.exit_name
            if exit_name and exit_name not in exit_names:
                errors.append(
                    ValidationError(
                        "E002",
                        f"遷移先の終了コード '{exit_name}' が定義されていません "
                        f"(ノード '{transition.from_node}' の状態 '{transition.from_state}')",
                    )
                )
        else:
            if transition.to_target not in node_names:
                errors.append(
                    ValidationError(
                        "E003",
                        f"遷移先ノード '{transition.to_target}' が定義されていません "
                        f"(ノード '{transition.from_node}' の状態 '{transition.from_state}')",
                    )
                )

    if errors:
        return ValidationResult(is_valid=False, errors=tuple(errors), warnings=())
    return ValidationResult.valid()


def validate_reachability(graph: TransitionGraph) -> ValidationResult:
    """Validate that all nodes are reachable from start."""
    reachable = _find_reachable_nodes(graph)
    all_nodes = {node.name for node in graph.nodes}
    unreachable = all_nodes - reachable

    warnings: list[ValidationWarning] = []
    for node_name in unreachable:
        warnings.append(
            ValidationWarning(
                "W001",
                f"ノード '{node_name}' は開始ノードから到達できません",
            )
        )

    if warnings:
        return ValidationResult(is_valid=True, errors=(), warnings=tuple(warnings))
    return ValidationResult.valid()


def _find_reachable_nodes(graph: TransitionGraph) -> set[str]:
    """Find all nodes reachable from the start node using BFS."""
    reachable: set[str] = set()
    queue = [graph.start_node]

    while queue:
        current = queue.pop(0)
        if current in reachable:
            continue
        reachable.add(current)

        for transition in graph.get_transitions_for_node(current):
            if not transition.is_exit:
                queue.append(transition.to_target)

    return reachable


def validate_termination(graph: TransitionGraph) -> ValidationResult:
    """Validate that all reachable nodes have paths to exit."""
    errors: list[ValidationError] = []
    reachable = _find_reachable_nodes(graph)

    for node_name in reachable:
        transitions = graph.get_transitions_for_node(node_name)
        if not transitions:
            errors.append(
                ValidationError(
                    "E004",
                    f"ノード '{node_name}' に遷移が定義されていません（行き止まり）",
                )
            )

    if errors:
        return ValidationResult(is_valid=False, errors=tuple(errors), warnings=())
    return ValidationResult.valid()


def validate_no_duplicate_states(graph: TransitionGraph) -> ValidationResult:
    """Validate that no state is defined twice for the same node."""
    errors: list[ValidationError] = []

    for node in graph.nodes:
        states = graph.get_states_for_node(node.name)
        seen: set[str] = set()
        for state in states:
            if state in seen:
                errors.append(
                    ValidationError(
                        "E005",
                        f"ノード '{node.name}' で状態 '{state}' が重複しています",
                    )
                )
            seen.add(state)

    if errors:
        return ValidationResult(is_valid=False, errors=tuple(errors), warnings=())
    return ValidationResult.valid()


def validate_no_infinite_loop(graph: TransitionGraph) -> ValidationResult:
    """
    Validate that all nodes can eventually reach an exit.

    Detects cycles that have no path to any exit (infinite loops).
    """
    # Find nodes that can reach exit by traversing backwards from exit transitions
    can_reach_exit: set[str] = set()
    queue: list[str] = []

    # First, collect nodes that directly transition to exit
    for transition in graph.transitions:
        if transition.is_exit:
            can_reach_exit.add(transition.from_node)
            queue.append(transition.from_node)

    # Build reverse edges: target -> [sources]
    reverse_edges: dict[str, list[str]] = {}
    for transition in graph.transitions:
        if not transition.is_exit:
            target = transition.to_target
            if target not in reverse_edges:
                reverse_edges[target] = []
            reverse_edges[target].append(transition.from_node)

    # Traverse backwards to find all nodes that can reach exit
    while queue:
        current = queue.pop(0)
        for source in reverse_edges.get(current, []):
            if source not in can_reach_exit:
                can_reach_exit.add(source)
                queue.append(source)

    # Detect reachable nodes that cannot reach exit
    reachable = _find_reachable_nodes(graph)
    stuck_nodes = reachable - can_reach_exit

    if stuck_nodes:
        return ValidationResult.error(
            "E006",
            f"以下のノードから終了に到達できません（無限ループの可能性）: "
            f"{', '.join(sorted(stuck_nodes))}",
        )
    return ValidationResult.valid()
