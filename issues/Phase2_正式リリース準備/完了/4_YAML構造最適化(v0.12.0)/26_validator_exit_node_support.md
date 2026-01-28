# Issue #26: バリデーション更新 - 終端ノード形式対応

**Phase:** 2
**優先度:** 高
**依存関係:** Issue #24（NodeDefinition）, Issue #25（パーサー）
**見積もり:** 0.25日

---

## 概要

`validator.py` を更新し、新しい終端ノード形式（`nodes.exit` 配下）に対応する。
旧形式 `exit::` プレフィックスから新形式 `exit.` プレフィックスへの移行。

---

## 背景

### 現状の問題

`validate_transition_targets()` が旧形式 `exit::` をチェックしている:

```python
# 現状のコード
def _is_exit_target(target: str) -> bool:
    return target.startswith("exit::")  # 旧形式
```

新形式では遷移先が `exit.success.done` のようになるため、
この判定ロジックでは終端ノードを認識できない。

---

## 変更内容

### 1. StateTransition.is_exit の更新（types.py）

```python
# Before
@property
def is_exit(self) -> bool:
    return self.to_target.startswith("exit::")

# After
@property
def is_exit(self) -> bool:
    """終端ノードへの遷移かチェック。

    新形式: exit.success.done, exit.failure.timeout
    """
    return self.to_target.startswith("exit.")
```

### 2. validate_transition_targets の更新

```python
def validate_transition_targets(graph: TransitionGraph) -> ValidationResult:
    """遷移先の存在を検証（純粋関数）。

    新形式では、遷移先が以下のいずれかであることを確認:
    1. 定義済みノード（nodes 配下）
    2. 終端ノード（nodes.exit 配下、is_exit=True）
    """
    errors: list[ValidationError] = []

    # 全ノード名を収集（終端含む）
    node_names = frozenset(n.name for n in graph.nodes)

    for transition in graph.transitions:
        target = transition.to_target

        if target not in node_names:
            errors.append(ValidationError(
                code="E003",
                message=f"Transition target '{target}' is not defined in nodes",
            ))

    if errors:
        return ValidationResult(
            is_valid=False,
            errors=tuple(errors),
            warnings=(),
        )

    return ValidationResult.valid()
```

### 3. validate_termination の更新

終端ノードは遷移先を持たないため、終端判定を更新:

```python
def validate_termination(graph: TransitionGraph) -> ValidationResult:
    """全到達可能ノードに遷移が定義されているか検証。

    終端ノード（is_exit=True）は遷移定義不要。
    """
    errors: list[ValidationError] = []

    reachable = _find_reachable_nodes(graph)
    nodes_with_transitions = frozenset(t.from_node for t in graph.transitions)

    # 終端ノードの名前を収集
    exit_node_names = frozenset(n.name for n in graph.nodes if n.is_exit)

    for node_name in reachable:
        # 終端ノードは遷移定義不要
        if node_name in exit_node_names:
            continue

        if node_name not in nodes_with_transitions:
            errors.append(ValidationError(
                code="E004",
                message=f"Node '{node_name}' has no transitions defined (dead end)",
            ))

    if errors:
        return ValidationResult(
            is_valid=False,
            errors=tuple(errors),
            warnings=(),
        )

    return ValidationResult.valid()
```

### 4. validate_no_infinite_loop の更新

終端ノードを終着点として認識:

```python
def validate_no_infinite_loop(graph: TransitionGraph) -> ValidationResult:
    """全ノードから終端ノードに到達可能か検証。

    終端ノード（is_exit=True）が終着点となる。
    """
    # 終端ノードの名前を収集
    exit_node_names = frozenset(n.name for n in graph.nodes if n.is_exit)

    # 終端ノードがない場合は警告
    if not exit_node_names:
        return ValidationResult(
            is_valid=True,  # 警告なので valid
            errors=(),
            warnings=(ValidationWarning(
                code="W002",
                message="No exit nodes defined in the graph",
            ),),
        )

    # 逆向き探索で終端ノードから到達可能なノードを収集
    can_reach_exit = _reverse_reachability(graph, exit_node_names)

    # 全到達可能ノードが終端に到達できるか
    reachable = _find_reachable_nodes(graph)
    unreachable_to_exit = reachable - can_reach_exit - exit_node_names

    if unreachable_to_exit:
        return ValidationResult(
            is_valid=False,
            errors=(ValidationError(
                code="E006",
                message=f"Nodes cannot reach any exit: {sorted(unreachable_to_exit)}",
            ),),
            warnings=(),
        )

    return ValidationResult.valid()
```

---

## TDD 実装手順

### Step 1: テスト作成（Red）

```python
# tests/unit/dag/test_validator_exit_nodes.py
"""Tests for validator exit node support."""

import pytest
from railway.core.dag.validator import (
    validate_graph,
    validate_transition_targets,
    validate_termination,
    validate_no_infinite_loop,
)
from railway.core.dag.types import (
    NodeDefinition,
    StateTransition,
    TransitionGraph,
)


class TestValidateTransitionTargetsExitNodes:
    """遷移先検証の終端ノード対応テスト。"""

    def test_valid_exit_node_target(self) -> None:
        """終端ノードへの遷移が有効。"""
        nodes = (
            NodeDefinition(
                name="start",
                module="nodes.start",
                function="start",
                description="開始",
            ),
            NodeDefinition(
                name="exit.success.done",
                module="nodes.exit.success.done",
                function="done",
                description="正常終了",
                is_exit=True,
                exit_code=0,
            ),
        )
        transitions = (
            StateTransition(
                from_node="start",
                from_state="success::done",
                to_target="exit.success.done",
            ),
        )
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=nodes,
            exits=(),
            transitions=transitions,
            start_node="start",
            options=None,
        )

        result = validate_transition_targets(graph)

        assert result.is_valid

    def test_invalid_exit_node_target(self) -> None:
        """存在しない終端ノードへの遷移がエラー。"""
        nodes = (
            NodeDefinition(
                name="start",
                module="nodes.start",
                function="start",
                description="開始",
            ),
        )
        transitions = (
            StateTransition(
                from_node="start",
                from_state="success::done",
                to_target="exit.success.nonexistent",  # 存在しない
            ),
        )
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=nodes,
            exits=(),
            transitions=transitions,
            start_node="start",
            options=None,
        )

        result = validate_transition_targets(graph)

        assert not result.is_valid
        assert any("E003" in e.code for e in result.errors)


class TestValidateTerminationExitNodes:
    """終端検証の終端ノード対応テスト。"""

    def test_exit_node_needs_no_transitions(self) -> None:
        """終端ノードは遷移定義不要。"""
        nodes = (
            NodeDefinition(
                name="start",
                module="nodes.start",
                function="start",
                description="開始",
            ),
            NodeDefinition(
                name="exit.success.done",
                module="nodes.exit.success.done",
                function="done",
                description="正常終了",
                is_exit=True,
                exit_code=0,
            ),
        )
        transitions = (
            StateTransition(
                from_node="start",
                from_state="success::done",
                to_target="exit.success.done",
            ),
        )
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=nodes,
            exits=(),
            transitions=transitions,
            start_node="start",
            options=None,
        )

        result = validate_termination(graph)

        # 終端ノードに遷移がなくてもエラーにならない
        assert result.is_valid


class TestValidateNoInfiniteLoopExitNodes:
    """無限ループ検証の終端ノード対応テスト。"""

    def test_all_paths_reach_exit(self) -> None:
        """全パスが終端ノードに到達。"""
        nodes = (
            NodeDefinition(
                name="start",
                module="nodes.start",
                function="start",
                description="開始",
            ),
            NodeDefinition(
                name="process",
                module="nodes.process",
                function="process",
                description="処理",
            ),
            NodeDefinition(
                name="exit.success.done",
                module="nodes.exit.success.done",
                function="done",
                description="正常終了",
                is_exit=True,
                exit_code=0,
            ),
        )
        transitions = (
            StateTransition(
                from_node="start",
                from_state="success::done",
                to_target="process",
            ),
            StateTransition(
                from_node="process",
                from_state="success::done",
                to_target="exit.success.done",
            ),
        )
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=nodes,
            exits=(),
            transitions=transitions,
            start_node="start",
            options=None,
        )

        result = validate_no_infinite_loop(graph)

        assert result.is_valid

    def test_no_exit_nodes_warning(self) -> None:
        """終端ノードがない場合は警告。"""
        nodes = (
            NodeDefinition(
                name="start",
                module="nodes.start",
                function="start",
                description="開始",
            ),
        )
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=nodes,
            exits=(),
            transitions=(),
            start_node="start",
            options=None,
        )

        result = validate_no_infinite_loop(graph)

        # 終端ノードがないので警告
        assert result.is_valid  # 警告は valid
        assert len(result.warnings) > 0
```

---

## 完了条件

- [ ] `StateTransition.is_exit` を新形式（`exit.`）に対応
- [ ] `validate_transition_targets` を新形式に対応
- [ ] `validate_termination` で終端ノードを除外
- [ ] `validate_no_infinite_loop` で終端ノードを終着点として認識
- [ ] 終端ノードがない場合の警告追加
- [ ] 既存テスト通過
- [ ] 新規テスト通過

---

## 関連 Issue

- Issue #24: NodeDefinition の終端ノード対応（前提）
- Issue #25: パーサーのネスト構造対応（前提）
- Issue #27: codegen の終端ノード対応
- Issue #30: E2E 統合テスト
