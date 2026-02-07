"""Validators module for DAG YAML validation."""

from dataclasses import dataclass
from typing import NamedTuple

import networkx as nx


class ValidationResult(NamedTuple):
    """Result of a single validation check."""

    is_valid: bool
    errors: list[str]


@dataclass(frozen=True)
class CheckResult:
    """Result of a named validation check."""

    name: str
    is_valid: bool
    errors: tuple[str, ...]


@dataclass(frozen=True)
class ValidationReport:
    """Aggregated validation report."""

    checks: tuple[CheckResult, ...]

    @property
    def is_valid(self) -> bool:
        """Return True if all checks passed."""
        return all(check.is_valid for check in self.checks)

    @property
    def total_errors(self) -> int:
        """Return total number of errors across all checks."""
        return sum(len(check.errors) for check in self.checks)


def validate_dag(graph: nx.DiGraph) -> ValidationResult:
    """
    Validate that the graph is a DAG (no cycles).

    Args:
        graph: The directed graph to validate.

    Returns:
        ValidationResult with is_valid=True if no cycles, False otherwise.
    """
    if nx.is_directed_acyclic_graph(graph):
        return ValidationResult(is_valid=True, errors=[])

    try:
        cycle = nx.find_cycle(graph)
        cycle_path = " -> ".join(f"{u}" for u, v in cycle)
        cycle_path += f" -> {cycle[0][0]}"
        return ValidationResult(
            is_valid=False,
            errors=[f"循環を検出しました: {cycle_path}"],
        )
    except nx.NetworkXNoCycle:
        return ValidationResult(is_valid=True, errors=[])


def validate_reachability(
    graph: nx.DiGraph,
    start_node: str,
    terminal_nodes: set[str],
) -> ValidationResult:
    """
    Validate that all terminal nodes are reachable from the start node.

    Args:
        graph: The directed graph.
        start_node: The starting node.
        terminal_nodes: Set of terminal node names.

    Returns:
        ValidationResult with errors for unreachable terminal nodes.
    """
    if not terminal_nodes:
        return ValidationResult(is_valid=True, errors=[])

    if start_node not in graph.nodes:
        reachable: set[str] = set()
    else:
        reachable = nx.descendants(graph, start_node) | {start_node}

    unreachable = terminal_nodes - reachable
    if not unreachable:
        return ValidationResult(is_valid=True, errors=[])

    errors = [
        f"{start_node} から {node} に到達できません"
        for node in sorted(unreachable)
    ]
    return ValidationResult(is_valid=False, errors=errors)


def validate_undefined_references(
    transitions: dict[str, dict[str, str]],
    defined_nodes: set[str],
) -> ValidationResult:
    """
    Validate that all transition targets are defined nodes.

    Args:
        transitions: The transitions dictionary.
        defined_nodes: Set of defined node names.

    Returns:
        ValidationResult with errors for undefined target references.
    """
    errors: list[str] = []

    for source, state_targets in transitions.items():
        for state, target in state_targets.items():
            if target not in defined_nodes:
                errors.append(
                    f"transitions で参照されているノード '{target}' は "
                    f"nodes に定義されていません（遷移元: {source}）"
                )

    return ValidationResult(is_valid=len(errors) == 0, errors=errors)


def validate_unused_nodes(
    defined_nodes: set[str],
    transitions: dict[str, dict[str, str]],
    start_node: str,
) -> ValidationResult:
    """
    Validate that all defined nodes are used in transitions.

    Args:
        defined_nodes: Set of defined node names.
        transitions: The transitions dictionary.
        start_node: The starting node name.

    Returns:
        ValidationResult with warnings for unused nodes.
    """
    # Collect used nodes
    used_nodes: set[str] = {start_node}

    # Add transition sources
    used_nodes.update(transitions.keys())

    # Add transition targets
    for state_targets in transitions.values():
        used_nodes.update(state_targets.values())

    unused = defined_nodes - used_nodes
    if not unused:
        return ValidationResult(is_valid=True, errors=[])

    errors = [
        f"ノード '{node}' は nodes に定義されていますが、"
        f"transitions で使用されていません"
        for node in sorted(unused)
    ]
    return ValidationResult(is_valid=False, errors=errors)


def validate_isolated_nodes(
    graph: nx.DiGraph,
    start_node: str,
    terminal_nodes: set[str],
) -> ValidationResult:
    """
    Validate that there are no isolated nodes (except start/terminal).

    Args:
        graph: The directed graph.
        start_node: The starting node name.
        terminal_nodes: Set of terminal node names.

    Returns:
        ValidationResult with errors for isolated nodes.
    """
    allowed_isolates = {start_node} | terminal_nodes
    isolates = set(nx.isolates(graph))

    problematic = isolates - allowed_isolates
    if not problematic:
        return ValidationResult(is_valid=True, errors=[])

    errors = [
        f"ノード '{node}' は孤立しています（入次数・出次数ともに0）"
        for node in sorted(problematic)
    ]
    return ValidationResult(is_valid=False, errors=errors)


def validate_transition_coverage(
    defined_nodes: set[str],
    transitions: dict[str, dict[str, str]],
    terminal_nodes: set[str],
) -> ValidationResult:
    """
    Validate that all non-terminal nodes have transition definitions.

    Args:
        defined_nodes: Set of defined node names.
        transitions: The transitions dictionary.
        terminal_nodes: Set of terminal node names.

    Returns:
        ValidationResult with errors for nodes missing transitions.
    """
    non_terminal_nodes = defined_nodes - terminal_nodes
    nodes_with_transitions = set(transitions.keys())

    missing = non_terminal_nodes - nodes_with_transitions
    if not missing:
        return ValidationResult(is_valid=True, errors=[])

    errors = [
        f"ノード '{node}' は非終端ノードですが、"
        f"transitions に遷移定義がありません"
        for node in sorted(missing)
    ]
    return ValidationResult(is_valid=False, errors=errors)


# Check name mapping for report formatting
CHECK_NAMES = {
    "dag": "DAG検証",
    "reachability": "到達可能性",
    "undefined_refs": "未定義ノード参照",
    "unused_nodes": "未使用ノード",
    "isolated_nodes": "孤立ノード",
    "transition_coverage": "遷移元の網羅性",
}


def aggregate_results(
    dag_result: ValidationResult,
    reachability_result: ValidationResult,
    undefined_ref_result: ValidationResult,
    unused_node_result: ValidationResult,
    isolated_node_result: ValidationResult,
    coverage_result: ValidationResult,
) -> ValidationReport:
    """
    Aggregate all validation results into a single report.

    Args:
        dag_result: Result from validate_dag.
        reachability_result: Result from validate_reachability.
        undefined_ref_result: Result from validate_undefined_references.
        unused_node_result: Result from validate_unused_nodes.
        isolated_node_result: Result from validate_isolated_nodes.
        coverage_result: Result from validate_transition_coverage.

    Returns:
        ValidationReport containing all check results.
    """
    checks = (
        CheckResult("dag", dag_result.is_valid, tuple(dag_result.errors)),
        CheckResult(
            "reachability",
            reachability_result.is_valid,
            tuple(reachability_result.errors),
        ),
        CheckResult(
            "undefined_refs",
            undefined_ref_result.is_valid,
            tuple(undefined_ref_result.errors),
        ),
        CheckResult(
            "unused_nodes",
            unused_node_result.is_valid,
            tuple(unused_node_result.errors),
        ),
        CheckResult(
            "isolated_nodes",
            isolated_node_result.is_valid,
            tuple(isolated_node_result.errors),
        ),
        CheckResult(
            "transition_coverage",
            coverage_result.is_valid,
            tuple(coverage_result.errors),
        ),
    )
    return ValidationReport(checks=checks)


def format_report(report: ValidationReport) -> str:
    """
    Format a validation report as a human-readable string.

    Args:
        report: The validation report to format.

    Returns:
        Formatted report string.
    """
    lines: list[str] = []

    for check in report.checks:
        name = CHECK_NAMES.get(check.name, check.name)
        if check.is_valid:
            if check.name == "dag":
                lines.append(f"✓ {name}: OK（循環なし）")
            else:
                lines.append(f"✓ {name}: OK")
        else:
            lines.append(f"✗ {name}: NG")
            for error in check.errors:
                lines.append(f"  - {error}")

    lines.append("")
    if report.is_valid:
        lines.append("検証完了: すべてのチェックに合格しました")
    else:
        lines.append(f"検証完了: {report.total_errors} 件のエラーがあります")

    return "\n".join(lines)
