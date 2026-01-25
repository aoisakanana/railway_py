# Issue #04: TransitionGraph データ型定義

**Phase:** 2a
**優先度:** 高
**依存関係:** なし
**見積もり:** 0.5日

---

## 概要

DAGワークフローの基盤となるデータ型を定義する。
すべての型はイミュータブル（`frozen=True`）とし、関数型パラダイムに準拠する。

---

## 設計原則

### イミュータブルデータ

```python
# ✅ 正しい: frozen=True でイミュータブル
@dataclass(frozen=True)
class NodeDefinition:
    name: str
    module: str

# ❌ 避ける: ミュータブルなデータ構造
@dataclass
class NodeDefinition:
    name: str
    states: list[str]  # ミュータブル
```

### 型安全性

- すべてのフィールドに型ヒントを付与
- `tuple` を使用（`list` は避ける）
- `Protocol` を活用して振る舞いを定義

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/core/dag/test_types.py
"""Tests for DAG transition graph data types."""
import pytest
from dataclasses import FrozenInstanceError


class TestNodeDefinition:
    """Test NodeDefinition data type."""

    def test_create_node_definition(self):
        """Should create a valid NodeDefinition."""
        from railway.core.dag.types import NodeDefinition

        node = NodeDefinition(
            name="fetch_alert",
            module="nodes.fetch_alert",
            function="fetch_alert",
            description="PagerDuty APIからアラート情報を取得",
        )

        assert node.name == "fetch_alert"
        assert node.module == "nodes.fetch_alert"
        assert node.function == "fetch_alert"
        assert node.description == "PagerDuty APIからアラート情報を取得"

    def test_node_definition_is_immutable(self):
        """NodeDefinition should be immutable."""
        from railway.core.dag.types import NodeDefinition

        node = NodeDefinition(
            name="fetch_alert",
            module="nodes.fetch_alert",
            function="fetch_alert",
            description="",
        )

        with pytest.raises(FrozenInstanceError):
            node.name = "other_name"

    def test_node_definition_equality(self):
        """Two NodeDefinitions with same values should be equal."""
        from railway.core.dag.types import NodeDefinition

        node1 = NodeDefinition("a", "m", "f", "d")
        node2 = NodeDefinition("a", "m", "f", "d")

        assert node1 == node2

    def test_node_definition_hashable(self):
        """NodeDefinition should be hashable (usable in sets/dicts)."""
        from railway.core.dag.types import NodeDefinition

        node = NodeDefinition("a", "m", "f", "d")
        node_set = {node}

        assert node in node_set


class TestExitDefinition:
    """Test ExitDefinition data type."""

    def test_create_exit_definition(self):
        """Should create a valid ExitDefinition."""
        from railway.core.dag.types import ExitDefinition

        exit_def = ExitDefinition(
            name="green_resolved",
            code=0,
            description="インシデント解決による正常終了",
        )

        assert exit_def.name == "green_resolved"
        assert exit_def.code == 0
        assert exit_def.description == "インシデント解決による正常終了"

    def test_exit_definition_is_immutable(self):
        """ExitDefinition should be immutable."""
        from railway.core.dag.types import ExitDefinition

        exit_def = ExitDefinition("green", 0, "success")

        with pytest.raises(FrozenInstanceError):
            exit_def.code = 1


class TestStateTransition:
    """Test StateTransition data type."""

    def test_create_transition_to_node(self):
        """Should create a transition to another node."""
        from railway.core.dag.types import StateTransition

        transition = StateTransition(
            from_node="fetch_alert",
            from_state="success::done",
            to_target="check_session_exists",
        )

        assert transition.from_node == "fetch_alert"
        assert transition.from_state == "success::done"
        assert transition.to_target == "check_session_exists"
        assert transition.is_exit is False

    def test_create_transition_to_exit(self):
        """Should create a transition to an exit."""
        from railway.core.dag.types import StateTransition

        transition = StateTransition(
            from_node="fetch_alert",
            from_state="failure::http",
            to_target="exit::red_error",
        )

        assert transition.to_target == "exit::red_error"
        assert transition.is_exit is True

    def test_transition_is_immutable(self):
        """StateTransition should be immutable."""
        from railway.core.dag.types import StateTransition

        transition = StateTransition("n", "s", "t")

        with pytest.raises(FrozenInstanceError):
            transition.to_target = "other"


class TestGraphOptions:
    """Test GraphOptions data type."""

    def test_default_options(self):
        """Should have sensible defaults."""
        from railway.core.dag.types import GraphOptions

        options = GraphOptions()

        assert options.max_iterations == 100
        assert options.enable_loop_detection is True
        assert options.strict_state_check is True

    def test_custom_options(self):
        """Should accept custom values."""
        from railway.core.dag.types import GraphOptions

        options = GraphOptions(
            max_iterations=20,
            enable_loop_detection=False,
            strict_state_check=False,
        )

        assert options.max_iterations == 20
        assert options.enable_loop_detection is False


class TestTransitionGraph:
    """Test TransitionGraph data type."""

    def test_create_minimal_graph(self):
        """Should create a minimal valid graph."""
        from railway.core.dag.types import (
            TransitionGraph,
            NodeDefinition,
            ExitDefinition,
            StateTransition,
            GraphOptions,
        )

        node = NodeDefinition("start", "nodes.start", "start", "開始ノード")
        exit_def = ExitDefinition("done", 0, "完了")
        transition = StateTransition("start", "success", "exit::done")

        graph = TransitionGraph(
            version="1.0",
            entrypoint="my_workflow",
            description="テストワークフロー",
            nodes=(node,),
            exits=(exit_def,),
            transitions=(transition,),
            start_node="start",
            options=GraphOptions(),
        )

        assert graph.version == "1.0"
        assert graph.entrypoint == "my_workflow"
        assert len(graph.nodes) == 1
        assert len(graph.exits) == 1
        assert len(graph.transitions) == 1
        assert graph.start_node == "start"

    def test_graph_is_immutable(self):
        """TransitionGraph should be immutable."""
        from railway.core.dag.types import (
            TransitionGraph,
            NodeDefinition,
            ExitDefinition,
            StateTransition,
            GraphOptions,
        )

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(NodeDefinition("a", "m", "f", "d"),),
            exits=(ExitDefinition("e", 0, ""),),
            transitions=(StateTransition("a", "s", "exit::e"),),
            start_node="a",
            options=GraphOptions(),
        )

        with pytest.raises(FrozenInstanceError):
            graph.version = "2.0"

    def test_graph_nodes_are_tuple(self):
        """Graph nodes should be tuple (immutable sequence)."""
        from railway.core.dag.types import TransitionGraph, NodeDefinition

        # tupleであることを確認（listではない）
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(NodeDefinition("a", "m", "f", "d"),),
            exits=(),
            transitions=(),
            start_node="a",
            options=None,
        )

        assert isinstance(graph.nodes, tuple)

    def test_graph_get_node_by_name(self):
        """Should get node by name."""
        from railway.core.dag.types import (
            TransitionGraph,
            NodeDefinition,
            GraphOptions,
        )

        node1 = NodeDefinition("fetch", "m1", "f1", "d1")
        node2 = NodeDefinition("process", "m2", "f2", "d2")

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(node1, node2),
            exits=(),
            transitions=(),
            start_node="fetch",
            options=GraphOptions(),
        )

        assert graph.get_node("fetch") == node1
        assert graph.get_node("process") == node2
        assert graph.get_node("unknown") is None

    def test_graph_get_transitions_for_node(self):
        """Should get all transitions for a node."""
        from railway.core.dag.types import (
            TransitionGraph,
            NodeDefinition,
            StateTransition,
            GraphOptions,
        )

        t1 = StateTransition("fetch", "success", "process")
        t2 = StateTransition("fetch", "failure", "exit::error")
        t3 = StateTransition("process", "success", "exit::done")

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(
                NodeDefinition("fetch", "m", "f", "d"),
                NodeDefinition("process", "m", "f", "d"),
            ),
            exits=(),
            transitions=(t1, t2, t3),
            start_node="fetch",
            options=GraphOptions(),
        )

        fetch_transitions = graph.get_transitions_for_node("fetch")
        assert len(fetch_transitions) == 2
        assert t1 in fetch_transitions
        assert t2 in fetch_transitions


class TestGeneratedFileMetadata:
    """Test GeneratedFileMetadata data type."""

    def test_create_metadata(self):
        """Should create file generation metadata."""
        from railway.core.dag.types import GeneratedFileMetadata
        from datetime import datetime

        meta = GeneratedFileMetadata(
            source_file="transition_graphs/top2_20250125.yml",
            generated_at=datetime(2025, 1, 25, 14, 30, 0),
            graph_version="1.0",
            entrypoint="top2",
        )

        assert meta.source_file == "transition_graphs/top2_20250125.yml"
        assert meta.entrypoint == "top2"
```

```bash
# 実行して失敗を確認
pytest tests/unit/core/dag/test_types.py -v
# Expected: FAILED (ImportError - module not found)
```

### Step 2: Green（最小限の実装）

```python
# railway/core/dag/__init__.py
"""DAG workflow support for Railway Framework."""

from railway.core.dag.types import (
    NodeDefinition,
    ExitDefinition,
    StateTransition,
    GraphOptions,
    TransitionGraph,
    GeneratedFileMetadata,
)

__all__ = [
    "NodeDefinition",
    "ExitDefinition",
    "StateTransition",
    "GraphOptions",
    "TransitionGraph",
    "GeneratedFileMetadata",
]
```

```python
# railway/core/dag/types.py
"""
Immutable data types for DAG transition graphs.

All types are frozen dataclasses to ensure immutability,
following functional programming principles.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Sequence


@dataclass(frozen=True)
class NodeDefinition:
    """
    Definition of a node in the transition graph.

    Attributes:
        name: Unique identifier for the node
        module: Python module path (e.g., "nodes.fetch_alert")
        function: Function name to import from module
        description: Human-readable description
    """
    name: str
    module: str
    function: str
    description: str


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
        """Check if this transition leads to an exit."""
        return self.to_target.startswith("exit::")

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
```

```bash
# 実行して成功を確認
pytest tests/unit/core/dag/test_types.py -v
# Expected: PASSED
```

### Step 3: Refactor

- docstringの追加・改善
- 型ヒントの見直し
- `__slots__` の検討（メモリ効率化）

---

## 完了条件

- [ ] `NodeDefinition` が定義され、イミュータブル
- [ ] `ExitDefinition` が定義され、イミュータブル
- [ ] `StateTransition` が定義され、`is_exit` プロパティあり
- [ ] `GraphOptions` がデフォルト値を持つ
- [ ] `TransitionGraph` が全要素を保持
- [ ] `TransitionGraph.get_node()` が動作
- [ ] `TransitionGraph.get_transitions_for_node()` が動作
- [ ] `GeneratedFileMetadata` が定義
- [ ] すべての型がハッシュ可能（set/dict で使用可能）
- [ ] テストカバレッジ90%以上

---

## 次のIssue

- #05: YAMLパーサー実装
