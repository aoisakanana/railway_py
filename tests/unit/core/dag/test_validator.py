"""Tests for graph validator (pure functions)."""
from pathlib import Path

import pytest


class TestValidationResult:
    """Test ValidationResult data type."""

    def test_valid_result(self):
        """Should create a valid result."""
        from railway.core.dag.validator import ValidationResult

        result = ValidationResult.valid()

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_invalid_result_with_errors(self):
        """Should create an invalid result with errors."""
        from railway.core.dag.validator import ValidationError, ValidationResult

        errors = [
            ValidationError("E001", "ノード 'foo' が見つかりません"),
            ValidationError("E002", "遷移先 'bar' が未定義です"),
        ]
        result = ValidationResult(is_valid=False, errors=tuple(errors), warnings=())

        assert result.is_valid is False
        assert len(result.errors) == 2
        assert result.errors[0].code == "E001"

    def test_result_with_warnings(self):
        """Should create a result with warnings."""
        from railway.core.dag.validator import ValidationResult, ValidationWarning

        warnings = [ValidationWarning("W001", "ノード 'x' に到達できません")]
        result = ValidationResult(is_valid=True, errors=(), warnings=tuple(warnings))

        assert result.is_valid is True
        assert len(result.warnings) == 1

    def test_combine_results(self):
        """Should combine multiple results."""
        from railway.core.dag.validator import (
            ValidationError,
            ValidationResult,
            combine_results,
        )

        r1 = ValidationResult.valid()
        r2 = ValidationResult(
            is_valid=False,
            errors=(ValidationError("E001", "Error 1"),),
            warnings=(),
        )
        r3 = ValidationResult(
            is_valid=False,
            errors=(ValidationError("E002", "Error 2"),),
            warnings=(),
        )

        combined = combine_results(r1, r2, r3)

        assert combined.is_valid is False
        assert len(combined.errors) == 2


class TestValidateStartNode:
    """Test start node validation."""

    def test_valid_start_node(self):
        """Should pass when start node exists."""
        from railway.core.dag.types import GraphOptions, NodeDefinition, TransitionGraph
        from railway.core.dag.validator import validate_start_node_exists

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(NodeDefinition("start", "m", "f", "d"),),
            exits=(),
            transitions=(),
            start_node="start",
            options=GraphOptions(),
        )

        result = validate_start_node_exists(graph)

        assert result.is_valid is True

    def test_invalid_start_node(self):
        """Should fail when start node doesn't exist."""
        from railway.core.dag.types import GraphOptions, NodeDefinition, TransitionGraph
        from railway.core.dag.validator import validate_start_node_exists

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(NodeDefinition("other", "m", "f", "d"),),
            exits=(),
            transitions=(),
            start_node="nonexistent",
            options=GraphOptions(),
        )

        result = validate_start_node_exists(graph)

        assert result.is_valid is False
        assert any("nonexistent" in e.message for e in result.errors)


class TestValidateTransitionTargets:
    """Test transition target validation."""

    def test_valid_transition_to_node(self):
        """Should pass when transition target is a valid node."""
        from railway.core.dag.types import (
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
        )
        from railway.core.dag.validator import validate_transition_targets

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(
                NodeDefinition("a", "m", "f", "d"),
                NodeDefinition("b", "m", "f", "d"),
            ),
            exits=(),
            transitions=(StateTransition("a", "success", "b"),),
            start_node="a",
            options=GraphOptions(),
        )

        result = validate_transition_targets(graph)

        assert result.is_valid is True

    def test_valid_transition_to_exit(self):
        """Should pass when transition target is a valid exit."""
        from railway.core.dag.types import (
            ExitDefinition,
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
        )
        from railway.core.dag.validator import validate_transition_targets

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(NodeDefinition("a", "m", "f", "d"),),
            exits=(ExitDefinition("done", 0, ""),),
            transitions=(StateTransition("a", "success", "exit::done"),),
            start_node="a",
            options=GraphOptions(),
        )

        result = validate_transition_targets(graph)

        assert result.is_valid is True

    def test_invalid_transition_target_node(self):
        """Should fail when transition target node doesn't exist."""
        from railway.core.dag.types import (
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
        )
        from railway.core.dag.validator import validate_transition_targets

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(NodeDefinition("a", "m", "f", "d"),),
            exits=(),
            transitions=(StateTransition("a", "success", "nonexistent"),),
            start_node="a",
            options=GraphOptions(),
        )

        result = validate_transition_targets(graph)

        assert result.is_valid is False
        assert any("nonexistent" in e.message for e in result.errors)

    def test_invalid_transition_target_exit(self):
        """Should fail when transition target exit doesn't exist."""
        from railway.core.dag.types import (
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
        )
        from railway.core.dag.validator import validate_transition_targets

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(NodeDefinition("a", "m", "f", "d"),),
            exits=(),
            transitions=(StateTransition("a", "success", "exit::unknown"),),
            start_node="a",
            options=GraphOptions(),
        )

        result = validate_transition_targets(graph)

        assert result.is_valid is False
        assert any("unknown" in e.message for e in result.errors)


class TestValidateReachability:
    """Test node reachability validation."""

    def test_all_nodes_reachable(self):
        """Should pass when all nodes are reachable from start."""
        from railway.core.dag.types import (
            ExitDefinition,
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
        )
        from railway.core.dag.validator import validate_reachability

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(
                NodeDefinition("a", "m", "f", "d"),
                NodeDefinition("b", "m", "f", "d"),
                NodeDefinition("c", "m", "f", "d"),
            ),
            exits=(ExitDefinition("done", 0, ""),),
            transitions=(
                StateTransition("a", "s1", "b"),
                StateTransition("a", "s2", "c"),
                StateTransition("b", "s", "exit::done"),
                StateTransition("c", "s", "exit::done"),
            ),
            start_node="a",
            options=GraphOptions(),
        )

        result = validate_reachability(graph)

        assert result.is_valid is True

    def test_unreachable_node_warning(self):
        """Should warn when a node is not reachable."""
        from railway.core.dag.types import (
            ExitDefinition,
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
        )
        from railway.core.dag.validator import validate_reachability

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(
                NodeDefinition("a", "m", "f", "d"),
                NodeDefinition("orphan", "m", "f", "d"),  # Never referenced
            ),
            exits=(ExitDefinition("done", 0, ""),),
            transitions=(StateTransition("a", "s", "exit::done"),),
            start_node="a",
            options=GraphOptions(),
        )

        result = validate_reachability(graph)

        # Unreachable is a warning, not an error
        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert any("orphan" in w.message for w in result.warnings)


class TestValidateTermination:
    """Test that all paths terminate."""

    def test_all_paths_terminate(self):
        """Should pass when all paths lead to exit."""
        from railway.core.dag.types import (
            ExitDefinition,
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
        )
        from railway.core.dag.validator import validate_termination

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(
                NodeDefinition("a", "m", "f", "d"),
                NodeDefinition("b", "m", "f", "d"),
            ),
            exits=(ExitDefinition("done", 0, ""),),
            transitions=(
                StateTransition("a", "s", "b"),
                StateTransition("b", "s", "exit::done"),
            ),
            start_node="a",
            options=GraphOptions(),
        )

        result = validate_termination(graph)

        assert result.is_valid is True

    def test_node_without_transitions(self):
        """Should fail when a node has no outgoing transitions."""
        from railway.core.dag.types import (
            ExitDefinition,
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
        )
        from railway.core.dag.validator import validate_termination

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(
                NodeDefinition("a", "m", "f", "d"),
                NodeDefinition("dead_end", "m", "f", "d"),
            ),
            exits=(ExitDefinition("done", 0, ""),),
            transitions=(
                StateTransition("a", "s", "dead_end"),
                # dead_end has no transitions
            ),
            start_node="a",
            options=GraphOptions(),
        )

        result = validate_termination(graph)

        assert result.is_valid is False
        assert any("dead_end" in e.message for e in result.errors)


class TestValidateDuplicateStates:
    """Test duplicate state detection."""

    def test_no_duplicate_states(self):
        """Should pass when no duplicate states for a node."""
        from railway.core.dag.types import (
            ExitDefinition,
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
        )
        from railway.core.dag.validator import validate_no_duplicate_states

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(NodeDefinition("a", "m", "f", "d"),),
            exits=(ExitDefinition("done", 0, ""),),
            transitions=(
                StateTransition("a", "success", "exit::done"),
                StateTransition("a", "failure", "exit::done"),
            ),
            start_node="a",
            options=GraphOptions(),
        )

        result = validate_no_duplicate_states(graph)

        assert result.is_valid is True

    def test_duplicate_states_error(self):
        """Should fail when same state defined twice for a node."""
        from railway.core.dag.types import (
            ExitDefinition,
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
        )
        from railway.core.dag.validator import validate_no_duplicate_states

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(NodeDefinition("a", "m", "f", "d"),),
            exits=(
                ExitDefinition("done1", 0, ""),
                ExitDefinition("done2", 0, ""),
            ),
            transitions=(
                StateTransition("a", "success", "exit::done1"),
                StateTransition("a", "success", "exit::done2"),  # Duplicate!
            ),
            start_node="a",
            options=GraphOptions(),
        )

        result = validate_no_duplicate_states(graph)

        assert result.is_valid is False
        assert any(e.code == "E005" for e in result.errors)
        assert any("success" in e.message for e in result.errors)


class TestValidateCycleDetection:
    """Test cycle detection validation."""

    def test_no_cycle_passes(self, simple_yaml: Path):
        """Should pass when no cycles exist."""
        from railway.core.dag.parser import load_transition_graph
        from railway.core.dag.validator import validate_no_infinite_loop

        graph = load_transition_graph(simple_yaml)
        result = validate_no_infinite_loop(graph)

        assert result.is_valid is True

    def test_cycle_detected(self, invalid_yaml_cycle: Path):
        """Should fail when cycle exists without exit path."""
        from railway.core.dag.parser import load_transition_graph
        from railway.core.dag.validator import validate_no_infinite_loop

        graph = load_transition_graph(invalid_yaml_cycle)
        result = validate_no_infinite_loop(graph)

        assert result.is_valid is False
        assert any(e.code == "E006" for e in result.errors)

    def test_cycle_with_exit_passes(self):
        """Should pass when cycle has an exit path."""
        from railway.core.dag.types import (
            ExitDefinition,
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
        )
        from railway.core.dag.validator import validate_no_infinite_loop

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(
                NodeDefinition("a", "m", "f", "d"),
                NodeDefinition("b", "m", "f", "d"),
            ),
            exits=(ExitDefinition("done", 0, ""),),
            transitions=(
                StateTransition("a", "success::continue", "b"),
                StateTransition("a", "success::done", "exit::done"),  # Exit path
                StateTransition("b", "success", "a"),  # Cycle but OK
            ),
            start_node="a",
            options=GraphOptions(),
        )

        result = validate_no_infinite_loop(graph)
        assert result.is_valid is True


class TestValidateGraphWithFixtures:
    """Integration tests using test YAML fixtures."""

    def test_validate_simple_yaml(self, simple_yaml: Path):
        """Should validate simple test YAML successfully."""
        from railway.core.dag.parser import load_transition_graph
        from railway.core.dag.validator import validate_graph

        graph = load_transition_graph(simple_yaml)
        result = validate_graph(graph)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_branching_yaml(self, branching_yaml: Path):
        """Should validate branching test YAML successfully."""
        from railway.core.dag.parser import load_transition_graph
        from railway.core.dag.validator import validate_graph

        graph = load_transition_graph(branching_yaml)
        result = validate_graph(graph)

        assert result.is_valid is True
        assert len(result.warnings) == 0

    def test_validate_top2_yaml(self, top2_yaml: Path):
        """Should validate full 事例1 YAML successfully."""
        from railway.core.dag.parser import load_transition_graph
        from railway.core.dag.validator import validate_graph

        graph = load_transition_graph(top2_yaml)
        result = validate_graph(graph)

        assert result.is_valid is True
        assert len(result.errors) == 0


class TestValidateGraph:
    """Test full graph validation."""

    def test_validate_valid_graph(self):
        """Should pass for a fully valid graph."""
        from railway.core.dag.types import (
            ExitDefinition,
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
        )
        from railway.core.dag.validator import validate_graph

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(
                NodeDefinition("start", "m", "f", "d"),
                NodeDefinition("process", "m", "f", "d"),
            ),
            exits=(
                ExitDefinition("done", 0, ""),
                ExitDefinition("error", 1, ""),
            ),
            transitions=(
                StateTransition("start", "success", "process"),
                StateTransition("start", "failure", "exit::error"),
                StateTransition("process", "success", "exit::done"),
                StateTransition("process", "failure", "exit::error"),
            ),
            start_node="start",
            options=GraphOptions(),
        )

        result = validate_graph(graph)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_collects_all_errors(self):
        """Should collect errors from all validations."""
        from railway.core.dag.types import (
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
        )
        from railway.core.dag.validator import validate_graph

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(NodeDefinition("a", "m", "f", "d"),),
            exits=(),
            transitions=(StateTransition("a", "s", "nonexistent"),),
            start_node="missing_start",  # Error: start not found
            options=GraphOptions(),
        )

        result = validate_graph(graph)

        assert result.is_valid is False
        assert len(result.errors) >= 2  # Multiple errors collected
