# Issue #05: YAMLパーサー実装

**Phase:** 2a
**優先度:** 高
**依存関係:** #04
**見積もり:** 1日

---

## 概要

遷移グラフYAMLを `TransitionGraph` データ構造にパースする純粋関数を実装する。
IO操作（ファイル読み込み）は分離し、パース処理自体は副作用を持たない。

---

## 設計原則

### 純粋関数としてのパーサー

```python
# ✅ 純粋関数: 文字列を受け取り、データ構造を返す
def parse_transition_graph(yaml_content: str) -> TransitionGraph:
    ...

# ❌ 避ける: ファイル読み込みを含む
def parse_transition_graph(file_path: Path) -> TransitionGraph:
    content = file_path.read_text()  # 副作用
    ...
```

### IO境界の分離

```python
# IO層（薄く保つ）
def load_transition_graph(file_path: Path) -> TransitionGraph:
    content = file_path.read_text()  # 副作用はここだけ
    return parse_transition_graph(content)  # 純粋関数を呼ぶ
```

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/core/dag/test_parser.py
"""Tests for YAML parser (pure functions)."""
import pytest
from textwrap import dedent


class TestParseTransitionGraph:
    """Test parse_transition_graph pure function."""

    def test_parse_minimal_yaml(self):
        """Should parse a minimal valid YAML."""
        from railway.core.dag.parser import parse_transition_graph

        yaml_content = dedent("""
            version: "1.0"
            entrypoint: simple_workflow
            description: "シンプルなワークフロー"

            nodes:
              start:
                module: nodes.start
                function: start
                description: "開始ノード"

            exits:
              done:
                code: 0
                description: "完了"

            start: start

            transitions:
              start:
                success: exit::done
        """)

        graph = parse_transition_graph(yaml_content)

        assert graph.version == "1.0"
        assert graph.entrypoint == "simple_workflow"
        assert graph.description == "シンプルなワークフロー"
        assert graph.start_node == "start"
        assert len(graph.nodes) == 1
        assert len(graph.exits) == 1
        assert len(graph.transitions) == 1

    def test_parse_multiple_nodes(self):
        """Should parse multiple node definitions."""
        from railway.core.dag.parser import parse_transition_graph

        yaml_content = dedent("""
            version: "1.0"
            entrypoint: multi_node
            description: ""

            nodes:
              fetch_alert:
                module: nodes.fetch_alert
                function: fetch_alert
                description: "アラート取得"
              check_session:
                module: nodes.check_session
                function: check_session_exists
                description: "セッション確認"

            exits:
              done:
                code: 0
                description: ""

            start: fetch_alert

            transitions:
              fetch_alert:
                success: check_session
              check_session:
                success: exit::done
        """)

        graph = parse_transition_graph(yaml_content)

        assert len(graph.nodes) == 2
        fetch_node = graph.get_node("fetch_alert")
        assert fetch_node is not None
        assert fetch_node.module == "nodes.fetch_alert"
        assert fetch_node.function == "fetch_alert"

    def test_parse_multiple_transitions_per_node(self):
        """Should parse multiple transitions from a single node."""
        from railway.core.dag.parser import parse_transition_graph

        yaml_content = dedent("""
            version: "1.0"
            entrypoint: branching
            description: ""

            nodes:
              check:
                module: nodes.check
                function: check
                description: ""
              process_a:
                module: nodes.a
                function: process_a
                description: ""
              process_b:
                module: nodes.b
                function: process_b
                description: ""

            exits:
              done:
                code: 0
                description: ""
              error:
                code: 1
                description: ""

            start: check

            transitions:
              check:
                success::type_a: process_a
                success::type_b: process_b
                failure::http: exit::error
              process_a:
                success: exit::done
              process_b:
                success: exit::done
        """)

        graph = parse_transition_graph(yaml_content)

        check_transitions = graph.get_transitions_for_node("check")
        assert len(check_transitions) == 3

        states = graph.get_states_for_node("check")
        assert "success::type_a" in states
        assert "success::type_b" in states
        assert "failure::http" in states

    def test_parse_options(self):
        """Should parse custom options."""
        from railway.core.dag.parser import parse_transition_graph

        yaml_content = dedent("""
            version: "1.0"
            entrypoint: with_options
            description: ""

            nodes:
              start:
                module: nodes.start
                function: start
                description: ""

            exits:
              done:
                code: 0
                description: ""

            start: start

            transitions:
              start:
                success: exit::done

            options:
              max_iterations: 20
              enable_loop_detection: false
              strict_state_check: true
        """)

        graph = parse_transition_graph(yaml_content)

        assert graph.options is not None
        assert graph.options.max_iterations == 20
        assert graph.options.enable_loop_detection is False
        assert graph.options.strict_state_check is True

    def test_parse_default_options(self):
        """Should use default options when not specified."""
        from railway.core.dag.parser import parse_transition_graph

        yaml_content = dedent("""
            version: "1.0"
            entrypoint: no_options
            description: ""

            nodes:
              start:
                module: nodes.start
                function: start
                description: ""

            exits:
              done:
                code: 0
                description: ""

            start: start

            transitions:
              start:
                success: exit::done
        """)

        graph = parse_transition_graph(yaml_content)

        assert graph.options is not None
        assert graph.options.max_iterations == 100  # default
        assert graph.options.enable_loop_detection is True  # default

    def test_parse_complex_workflow(self):
        """Should parse a complex workflow similar to 事例１."""
        from railway.core.dag.parser import parse_transition_graph

        yaml_content = dedent("""
            version: "1.0"
            entrypoint: top2
            description: "セッション管理ワークフロー"

            nodes:
              fetch_alert:
                module: nodes.fetch_alert
                function: fetch_alert
                description: "PagerDuty APIからアラート情報を取得"
              check_session_exists:
                module: nodes.check_session_exists
                function: check_session_exists
                description: "セッションIDの存在確認"
              resolve_incident:
                module: nodes.resolve_incident
                function: resolve_incident
                description: "インシデント自動解決"

            exits:
              green_resolved:
                code: 0
                description: "インシデント解決"
              red_error:
                code: 1
                description: "異常終了"

            start: fetch_alert

            transitions:
              fetch_alert:
                success::done: check_session_exists
                failure::http: exit::red_error
                failure::api: exit::red_error
              check_session_exists:
                success::exist: resolve_incident
                success::not_exist: resolve_incident
                failure::ssh: exit::red_error
              resolve_incident:
                success::resolved: exit::green_resolved
                failure::api: exit::red_error

            options:
              max_iterations: 20
        """)

        graph = parse_transition_graph(yaml_content)

        assert graph.entrypoint == "top2"
        assert len(graph.nodes) == 3
        assert len(graph.exits) == 2
        assert graph.start_node == "fetch_alert"

        # 遷移の検証
        fetch_transitions = graph.get_transitions_for_node("fetch_alert")
        assert len(fetch_transitions) == 3

        # exit遷移の検証
        exit_transitions = [t for t in fetch_transitions if t.is_exit]
        assert len(exit_transitions) == 2


class TestParseTransitionGraphErrors:
    """Test parser error handling."""

    def test_invalid_yaml_syntax(self):
        """Should raise error for invalid YAML syntax."""
        from railway.core.dag.parser import parse_transition_graph, ParseError

        invalid_yaml = "invalid: yaml: content: ["

        with pytest.raises(ParseError) as exc_info:
            parse_transition_graph(invalid_yaml)

        assert "YAML" in str(exc_info.value) or "syntax" in str(exc_info.value).lower()

    def test_missing_required_field_version(self):
        """Should raise error when version is missing."""
        from railway.core.dag.parser import parse_transition_graph, ParseError

        yaml_content = dedent("""
            entrypoint: test
            description: ""
            nodes: {}
            exits: {}
            start: start
            transitions: {}
        """)

        with pytest.raises(ParseError) as exc_info:
            parse_transition_graph(yaml_content)

        assert "version" in str(exc_info.value).lower()

    def test_missing_required_field_nodes(self):
        """Should raise error when nodes is missing."""
        from railway.core.dag.parser import parse_transition_graph, ParseError

        yaml_content = dedent("""
            version: "1.0"
            entrypoint: test
            description: ""
            exits: {}
            start: start
            transitions: {}
        """)

        with pytest.raises(ParseError) as exc_info:
            parse_transition_graph(yaml_content)

        assert "nodes" in str(exc_info.value).lower()

    def test_missing_node_module(self):
        """Should raise error when node module is missing."""
        from railway.core.dag.parser import parse_transition_graph, ParseError

        yaml_content = dedent("""
            version: "1.0"
            entrypoint: test
            description: ""
            nodes:
              start:
                function: start
                description: ""
            exits: {}
            start: start
            transitions: {}
        """)

        with pytest.raises(ParseError) as exc_info:
            parse_transition_graph(yaml_content)

        assert "module" in str(exc_info.value).lower()

    def test_empty_transitions(self):
        """Should handle empty transitions for a node."""
        from railway.core.dag.parser import parse_transition_graph

        yaml_content = dedent("""
            version: "1.0"
            entrypoint: test
            description: ""
            nodes:
              start:
                module: nodes.start
                function: start
                description: ""
            exits:
              done:
                code: 0
                description: ""
            start: start
            transitions:
              start:
                success: exit::done
        """)

        # Should not raise
        graph = parse_transition_graph(yaml_content)
        assert graph is not None


class TestParseFunctions:
    """Test individual parsing helper functions."""

    def test_parse_node_definition(self):
        """Should parse a single node definition."""
        from railway.core.dag.parser import _parse_node_definition

        node_data = {
            "module": "nodes.fetch",
            "function": "fetch_data",
            "description": "Fetch data from API",
        }

        node = _parse_node_definition("fetch", node_data)

        assert node.name == "fetch"
        assert node.module == "nodes.fetch"
        assert node.function == "fetch_data"
        assert node.description == "Fetch data from API"

    def test_parse_exit_definition(self):
        """Should parse a single exit definition."""
        from railway.core.dag.parser import _parse_exit_definition

        exit_data = {
            "code": 0,
            "description": "Success",
        }

        exit_def = _parse_exit_definition("success", exit_data)

        assert exit_def.name == "success"
        assert exit_def.code == 0
        assert exit_def.description == "Success"

    def test_parse_transitions_for_node(self):
        """Should parse transitions for a single node."""
        from railway.core.dag.parser import _parse_transitions_for_node

        transitions_data = {
            "success::done": "next_node",
            "failure::error": "exit::error",
        }

        transitions = _parse_transitions_for_node("current", transitions_data)

        assert len(transitions) == 2
        assert transitions[0].from_node == "current"
        assert transitions[0].from_state == "success::done"
        assert transitions[0].to_target == "next_node"
        assert transitions[1].to_target == "exit::error"


class TestLoadTransitionGraph:
    """Test file loading (IO boundary)."""

    def test_load_from_file(self, tmp_path):
        """Should load and parse from file."""
        from railway.core.dag.parser import load_transition_graph

        yaml_content = dedent("""
            version: "1.0"
            entrypoint: file_test
            description: ""
            nodes:
              start:
                module: nodes.start
                function: start
                description: ""
            exits:
              done:
                code: 0
                description: ""
            start: start
            transitions:
              start:
                success: exit::done
        """)

        yaml_file = tmp_path / "test.yml"
        yaml_file.write_text(yaml_content)

        graph = load_transition_graph(yaml_file)

        assert graph.entrypoint == "file_test"

    def test_load_file_not_found(self, tmp_path):
        """Should raise error for non-existent file."""
        from railway.core.dag.parser import load_transition_graph, ParseError

        non_existent = tmp_path / "does_not_exist.yml"

        with pytest.raises(ParseError) as exc_info:
            load_transition_graph(non_existent)

        assert "not found" in str(exc_info.value).lower() or "存在しません" in str(exc_info.value)
```

```bash
# 実行して失敗を確認
pytest tests/unit/core/dag/test_parser.py -v
# Expected: FAILED (ImportError)
```

### Step 2: Green（最小限の実装）

```python
# railway/core/dag/parser.py
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
    NodeDefinition,
    ExitDefinition,
    StateTransition,
    GraphOptions,
    TransitionGraph,
)


class ParseError(Exception):
    """Error during YAML parsing."""
    pass


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
    nodes = tuple(
        _parse_node_definition(name, node_data)
        for name, node_data in data.get("nodes", {}).items()
    )

    # Parse exits
    exits = tuple(
        _parse_exit_definition(name, exit_data)
        for name, exit_data in data.get("exits", {}).items()
    )

    # Parse transitions
    all_transitions: list[StateTransition] = []
    for node_name, transitions_data in data.get("transitions", {}).items():
        if transitions_data:
            all_transitions.extend(
                _parse_transitions_for_node(node_name, transitions_data)
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


def _parse_options(data: dict[str, Any]) -> GraphOptions:
    """
    Parse graph options with defaults.

    Args:
        data: Options dict from YAML

    Returns:
        GraphOptions instance
    """
    return GraphOptions(
        max_iterations=int(data.get("max_iterations", 100)),
        enable_loop_detection=bool(data.get("enable_loop_detection", True)),
        strict_state_check=bool(data.get("strict_state_check", True)),
    )
```

```bash
# 実行して成功を確認
pytest tests/unit/core/dag/test_parser.py -v
# Expected: PASSED
```

### Step 3: Refactor

- エラーメッセージの国際化対応検討
- パフォーマンス最適化（大規模YAML対応）
- スキーマバージョンの互換性チェック追加

---

## 完了条件

- [ ] `parse_transition_graph()` が純粋関数として実装
- [ ] `load_transition_graph()` がIO境界として分離
- [ ] 最小限のYAMLがパース可能
- [ ] 複数ノード・複数遷移がパース可能
- [ ] オプションのデフォルト値が適用される
- [ ] 必須フィールド欠損時にエラー
- [ ] YAML構文エラー時にエラー
- [ ] ファイル不在時にエラー
- [ ] テストカバレッジ90%以上

---

## 次のIssue

- #06: グラフバリデータ実装
