"""Tests for validators module."""

import pytest
import networkx as nx

from dag_yaml_tools.validators import (
    validate_dag,
    validate_reachability,
    validate_undefined_references,
    validate_unused_nodes,
    validate_isolated_nodes,
    validate_transition_coverage,
    aggregate_results,
    format_report,
    ValidationResult,
)


class TestValidateDag:
    """Tests for validate_dag function."""

    def test_validate_dag_no_cycle(self) -> None:
        """Test DAG with no cycle is valid."""
        G = nx.DiGraph()
        G.add_edges_from([("a", "b"), ("b", "c"), ("a", "c")])
        result = validate_dag(G)
        assert result.is_valid is True
        assert result.errors == []

    def test_validate_dag_with_cycle(self) -> None:
        """Test DAG with cycle is invalid."""
        G = nx.DiGraph()
        G.add_edges_from([("a", "b"), ("b", "c"), ("c", "a")])
        result = validate_dag(G)
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_validate_dag_cycle_error_contains_nodes(self) -> None:
        """Test that cycle error mentions involved nodes."""
        G = nx.DiGraph()
        G.add_edges_from([("a", "b"), ("b", "c"), ("c", "a")])
        result = validate_dag(G)
        error_msg = result.errors[0]
        assert "a" in error_msg or "b" in error_msg or "c" in error_msg

    def test_validate_dag_self_loop(self) -> None:
        """Test self-loop detection."""
        G = nx.DiGraph()
        G.add_edge("a", "a")
        result = validate_dag(G)
        assert result.is_valid is False

    def test_validate_dag_empty_graph(self) -> None:
        """Test empty graph is valid."""
        G = nx.DiGraph()
        result = validate_dag(G)
        assert result.is_valid is True

    def test_validate_dag_single_node(self) -> None:
        """Test single node graph is valid."""
        G = nx.DiGraph()
        G.add_node("a")
        result = validate_dag(G)
        assert result.is_valid is True


class TestValidateReachability:
    """Tests for validate_reachability function."""

    def test_validate_reachability_all_reachable(self) -> None:
        """Test all terminal nodes reachable."""
        G = nx.DiGraph()
        G.add_edges_from([("start", "a"), ("a", "exit.success")])
        result = validate_reachability(G, "start", {"exit.success"})
        assert result.is_valid is True
        assert result.errors == []

    def test_validate_reachability_unreachable_node(self) -> None:
        """Test unreachable terminal node."""
        G = nx.DiGraph()
        G.add_edges_from([("start", "a")])
        G.add_node("exit.success")
        result = validate_reachability(G, "start", {"exit.success"})
        assert result.is_valid is False
        assert "exit.success" in result.errors[0]

    def test_validate_reachability_multiple_unreachable(self) -> None:
        """Test multiple unreachable terminal nodes."""
        G = nx.DiGraph()
        G.add_edges_from([("start", "a")])
        G.add_node("exit.success")
        G.add_node("exit.failure")
        result = validate_reachability(
            G, "start", {"exit.success", "exit.failure"}
        )
        assert result.is_valid is False
        assert len(result.errors) == 2

    def test_validate_reachability_partial_reachable(self) -> None:
        """Test some terminal nodes reachable."""
        G = nx.DiGraph()
        G.add_edges_from([("start", "a"), ("a", "exit.success")])
        G.add_node("exit.failure")
        result = validate_reachability(
            G, "start", {"exit.success", "exit.failure"}
        )
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "exit.failure" in result.errors[0]

    def test_validate_reachability_no_terminal_nodes(self) -> None:
        """Test with no terminal nodes."""
        G = nx.DiGraph()
        G.add_edges_from([("start", "a")])
        result = validate_reachability(G, "start", set())
        assert result.is_valid is True

    def test_validate_reachability_start_is_terminal(self) -> None:
        """Test start node is also terminal."""
        G = nx.DiGraph()
        G.add_node("exit.success")
        result = validate_reachability(G, "exit.success", {"exit.success"})
        assert result.is_valid is True


class TestValidateUndefinedReferences:
    """Tests for validate_undefined_references function."""

    def test_validate_undefined_refs_all_defined(self) -> None:
        """Test all targets are defined."""
        transitions = {"start": {"success": "a", "failure": "b"}}
        defined_nodes = {"start", "a", "b"}
        result = validate_undefined_references(transitions, defined_nodes)
        assert result.is_valid is True
        assert result.errors == []

    def test_validate_undefined_refs_missing_target(self) -> None:
        """Test undefined target reference."""
        transitions = {"start": {"success": "undefined_node"}}
        defined_nodes = {"start"}
        result = validate_undefined_references(transitions, defined_nodes)
        assert result.is_valid is False
        assert "undefined_node" in result.errors[0]

    def test_validate_undefined_refs_multiple_missing(self) -> None:
        """Test multiple undefined target references."""
        transitions = {"start": {"success": "a", "failure": "b"}}
        defined_nodes = {"start"}
        result = validate_undefined_references(transitions, defined_nodes)
        assert result.is_valid is False
        assert len(result.errors) == 2

    def test_validate_undefined_refs_error_shows_source(self) -> None:
        """Test error message includes source node."""
        transitions = {"start": {"success": "undefined"}}
        defined_nodes = {"start"}
        result = validate_undefined_references(transitions, defined_nodes)
        assert "start" in result.errors[0]

    def test_validate_undefined_refs_empty_transitions(self) -> None:
        """Test empty transitions."""
        result = validate_undefined_references({}, {"start"})
        assert result.is_valid is True


class TestValidateUnusedNodes:
    """Tests for validate_unused_nodes function."""

    def test_validate_unused_all_used(self) -> None:
        """Test all nodes are used."""
        defined_nodes = {"start", "a", "exit"}
        transitions = {
            "start": {"success": "a"},
            "a": {"done": "exit"},
        }
        result = validate_unused_nodes(defined_nodes, transitions, "start")
        assert result.is_valid is True
        assert result.errors == []

    def test_validate_unused_has_unused(self) -> None:
        """Test unused node detection."""
        defined_nodes = {"start", "a", "unused_node", "exit"}
        transitions = {
            "start": {"success": "a"},
            "a": {"done": "exit"},
        }
        result = validate_unused_nodes(defined_nodes, transitions, "start")
        assert result.is_valid is False
        assert "unused_node" in result.errors[0]

    def test_validate_unused_multiple(self) -> None:
        """Test multiple unused nodes."""
        defined_nodes = {"start", "unused1", "unused2"}
        transitions: dict[str, dict[str, str]] = {}
        result = validate_unused_nodes(defined_nodes, transitions, "start")
        assert result.is_valid is False
        assert len(result.errors) == 2

    def test_validate_unused_start_node_counts(self) -> None:
        """Test start node counts as used."""
        defined_nodes = {"start"}
        transitions: dict[str, dict[str, str]] = {}
        result = validate_unused_nodes(defined_nodes, transitions, "start")
        assert result.is_valid is True

    def test_validate_unused_target_only_counts(self) -> None:
        """Test target-only nodes count as used."""
        defined_nodes = {"start", "exit"}
        transitions = {"start": {"success": "exit"}}
        result = validate_unused_nodes(defined_nodes, transitions, "start")
        assert result.is_valid is True


class TestValidateIsolatedNodes:
    """Tests for validate_isolated_nodes function."""

    def test_validate_isolated_no_isolates(self) -> None:
        """Test no isolated nodes."""
        G = nx.DiGraph()
        G.add_edges_from([("start", "a"), ("a", "exit")])
        result = validate_isolated_nodes(G, "start", {"exit"})
        assert result.is_valid is True
        assert result.errors == []

    def test_validate_isolated_has_isolate(self) -> None:
        """Test isolated node detection."""
        G = nx.DiGraph()
        G.add_edges_from([("start", "a")])
        G.add_node("isolated")
        result = validate_isolated_nodes(G, "start", set())
        assert result.is_valid is False
        assert "isolated" in result.errors[0]

    def test_validate_isolated_start_allowed(self) -> None:
        """Test isolated start node is allowed."""
        G = nx.DiGraph()
        G.add_node("start")
        result = validate_isolated_nodes(G, "start", set())
        assert result.is_valid is True

    def test_validate_isolated_terminal_allowed(self) -> None:
        """Test isolated terminal node is allowed."""
        G = nx.DiGraph()
        G.add_node("exit.success")
        result = validate_isolated_nodes(G, "start", {"exit.success"})
        assert result.is_valid is True

    def test_validate_isolated_multiple(self) -> None:
        """Test multiple isolated nodes."""
        G = nx.DiGraph()
        G.add_node("isolated1")
        G.add_node("isolated2")
        result = validate_isolated_nodes(G, "start", set())
        assert result.is_valid is False
        assert len(result.errors) == 2


class TestValidateTransitionCoverage:
    """Tests for validate_transition_coverage function."""

    def test_validate_coverage_all_covered(self) -> None:
        """Test all non-terminal nodes have transitions."""
        defined_nodes = {"start", "a", "exit.success"}
        transitions = {
            "start": {"success": "a"},
            "a": {"done": "exit.success"},
        }
        terminal_nodes = {"exit.success"}
        result = validate_transition_coverage(
            defined_nodes, transitions, terminal_nodes
        )
        assert result.is_valid is True
        assert result.errors == []

    def test_validate_coverage_missing_transition(self) -> None:
        """Test node without transition definition."""
        defined_nodes = {"start", "a", "exit.success"}
        transitions = {"start": {"success": "a"}}
        terminal_nodes = {"exit.success"}
        result = validate_transition_coverage(
            defined_nodes, transitions, terminal_nodes
        )
        assert result.is_valid is False
        assert "a" in result.errors[0]

    def test_validate_coverage_terminal_excluded(self) -> None:
        """Test terminal nodes don't need transitions."""
        defined_nodes = {"start", "exit.success", "exit.failure"}
        transitions = {
            "start": {"success": "exit.success", "failure": "exit.failure"}
        }
        terminal_nodes = {"exit.success", "exit.failure"}
        result = validate_transition_coverage(
            defined_nodes, transitions, terminal_nodes
        )
        assert result.is_valid is True

    def test_validate_coverage_multiple_missing(self) -> None:
        """Test multiple nodes without transitions."""
        defined_nodes = {"start", "a", "b", "exit"}
        transitions = {"start": {"success": "a"}}
        terminal_nodes = {"exit"}
        result = validate_transition_coverage(
            defined_nodes, transitions, terminal_nodes
        )
        assert result.is_valid is False
        assert len(result.errors) == 2  # a, b


class TestAggregateResults:
    """Tests for aggregate_results function."""

    def test_aggregate_all_valid(self) -> None:
        """Test aggregation with all valid results."""
        valid = ValidationResult(is_valid=True, errors=[])
        report = aggregate_results(valid, valid, valid, valid, valid, valid)
        assert report.is_valid is True
        assert report.total_errors == 0

    def test_aggregate_some_invalid(self) -> None:
        """Test aggregation with some invalid results."""
        valid = ValidationResult(is_valid=True, errors=[])
        invalid = ValidationResult(is_valid=False, errors=["error1"])
        report = aggregate_results(invalid, valid, valid, valid, valid, valid)
        assert report.is_valid is False
        assert report.total_errors == 1

    def test_aggregate_multiple_errors(self) -> None:
        """Test aggregation with multiple errors."""
        valid = ValidationResult(is_valid=True, errors=[])
        invalid1 = ValidationResult(is_valid=False, errors=["error1", "error2"])
        invalid2 = ValidationResult(is_valid=False, errors=["error3"])
        report = aggregate_results(
            invalid1, invalid2, valid, valid, valid, valid
        )
        assert report.total_errors == 3


class TestFormatReport:
    """Tests for format_report function."""

    def test_format_report_success(self) -> None:
        """Test formatting successful report."""
        valid = ValidationResult(is_valid=True, errors=[])
        report = aggregate_results(valid, valid, valid, valid, valid, valid)
        formatted = format_report(report)
        assert "✓" in formatted
        assert "すべてのチェックに合格" in formatted

    def test_format_report_failure(self) -> None:
        """Test formatting failed report."""
        valid = ValidationResult(is_valid=True, errors=[])
        invalid = ValidationResult(is_valid=False, errors=["エラーメッセージ"])
        report = aggregate_results(invalid, valid, valid, valid, valid, valid)
        formatted = format_report(report)
        assert "✗" in formatted
        assert "エラーメッセージ" in formatted

    def test_format_report_error_count(self) -> None:
        """Test error count in formatted report."""
        valid = ValidationResult(is_valid=True, errors=[])
        invalid = ValidationResult(is_valid=False, errors=["e1", "e2"])
        report = aggregate_results(invalid, valid, valid, valid, valid, valid)
        formatted = format_report(report)
        assert "2 件のエラー" in formatted

    def test_format_report_dag_ok_message(self) -> None:
        """Test DAG OK message includes '循環なし'."""
        valid = ValidationResult(is_valid=True, errors=[])
        report = aggregate_results(valid, valid, valid, valid, valid, valid)
        formatted = format_report(report)
        assert "循環なし" in formatted
