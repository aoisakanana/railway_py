# Issue #06: グラフバリデータ実装

**Phase:** 2a
**優先度:** 高
**依存関係:** #04
**見積もり:** 1日

---

## 概要

`TransitionGraph` の整合性を検証する純粋関数群を実装する。
検証結果はイミュータブルなデータ構造として返し、副作用を持たない。

---

## 設計原則

### 純粋関数としての検証

```python
# ✅ 検証結果をデータとして返す
def validate_graph(graph: TransitionGraph) -> ValidationResult:
    ...

# ValidationResult は成功/失敗とメッセージを含むイミュータブル構造
```

### 検証の合成

```python
# 小さな検証関数を合成して全体検証を構築
def validate_graph(graph: TransitionGraph) -> ValidationResult:
    return combine_results(
        validate_start_node_exists(graph),
        validate_all_transitions_have_targets(graph),
        validate_no_orphan_nodes(graph),
        validate_all_paths_terminate(graph),
    )
```

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/core/dag/test_validator.py
"""Tests for graph validator (pure functions)."""
import pytest
from textwrap import dedent


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
        from railway.core.dag.validator import ValidationResult, ValidationError

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
            ValidationResult,
            ValidationError,
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
        from railway.core.dag.validator import validate_start_node_exists
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, GraphOptions
        )

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
        from railway.core.dag.validator import validate_start_node_exists
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, GraphOptions
        )

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
        from railway.core.dag.validator import validate_transition_targets
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, StateTransition, GraphOptions
        )

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
        from railway.core.dag.validator import validate_transition_targets
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, ExitDefinition,
            StateTransition, GraphOptions
        )

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
        from railway.core.dag.validator import validate_transition_targets
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, StateTransition, GraphOptions
        )

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
        from railway.core.dag.validator import validate_transition_targets
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, StateTransition, GraphOptions
        )

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
        from railway.core.dag.validator import validate_reachability
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, ExitDefinition,
            StateTransition, GraphOptions
        )

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
        from railway.core.dag.validator import validate_reachability
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, ExitDefinition,
            StateTransition, GraphOptions
        )

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
        from railway.core.dag.validator import validate_termination
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, ExitDefinition,
            StateTransition, GraphOptions
        )

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
        from railway.core.dag.validator import validate_termination
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, ExitDefinition,
            StateTransition, GraphOptions
        )

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
        from railway.core.dag.validator import validate_no_duplicate_states
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, ExitDefinition,
            StateTransition, GraphOptions
        )

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
        from railway.core.dag.validator import validate_no_duplicate_states
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, ExitDefinition,
            StateTransition, GraphOptions
        )

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
        assert any("success" in e.message and "重複" in e.message for e in result.errors)


class TestValidateGraph:
    """Test full graph validation."""

    def test_validate_valid_graph(self):
        """Should pass for a fully valid graph."""
        from railway.core.dag.validator import validate_graph
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, ExitDefinition,
            StateTransition, GraphOptions
        )

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
        from railway.core.dag.validator import validate_graph
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, StateTransition, GraphOptions
        )

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(NodeDefinition("a", "m", "f", "d"),),
            exits=(),
            transitions=(
                StateTransition("a", "s", "nonexistent"),
            ),
            start_node="missing_start",  # Error 1: start not found
            options=GraphOptions(),
        )

        result = validate_graph(graph)

        assert result.is_valid is False
        assert len(result.errors) >= 2  # Multiple errors collected
```

```bash
pytest tests/unit/core/dag/test_validator.py -v
# Expected: FAILED (ImportError)
```

### Step 2: Green（最小限の実装）

```python
# railway/core/dag/validator.py
"""
Graph validator for transition graphs.

All validation functions are pure - they take a TransitionGraph
and return a ValidationResult without side effects.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

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
                errors.append(ValidationError(
                    "E002",
                    f"遷移先の終了コード '{exit_name}' が定義されていません "
                    f"(ノード '{transition.from_node}' の状態 '{transition.from_state}')",
                ))
        else:
            if transition.to_target not in node_names:
                errors.append(ValidationError(
                    "E003",
                    f"遷移先ノード '{transition.to_target}' が定義されていません "
                    f"(ノード '{transition.from_node}' の状態 '{transition.from_state}')",
                ))

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
        warnings.append(ValidationWarning(
            "W001",
            f"ノード '{node_name}' は開始ノードから到達できません",
        ))

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
            errors.append(ValidationError(
                "E004",
                f"ノード '{node_name}' に遷移が定義されていません（行き止まり）",
            ))

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
                errors.append(ValidationError(
                    "E005",
                    f"ノード '{node.name}' で状態 '{state}' が重複しています",
                ))
            seen.add(state)

    if errors:
        return ValidationResult(is_valid=False, errors=tuple(errors), warnings=())
    return ValidationResult.valid()
```

```bash
pytest tests/unit/core/dag/test_validator.py -v
# Expected: PASSED
```

### Step 3: Refactor

- 検証関数のプラグイン化検討
- カスタム検証ルールの追加機能
- パフォーマンス最適化（大規模グラフ対応）

---

## 完了条件

- [ ] `ValidationResult` がイミュータブル
- [ ] `combine_results()` が複数結果を合成
- [ ] 開始ノード存在チェック
- [ ] 遷移先（ノード/終了）存在チェック
- [ ] 到達可能性チェック（警告）
- [ ] 終了可能性チェック
- [ ] 状態重複チェック
- [ ] `validate_graph()` が全検証を統合
- [ ] テストカバレッジ90%以上

---

## 次のIssue

- #07: 状態Enum基底クラス
