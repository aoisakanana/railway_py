# Issue #08: コード生成器実装

**Phase:** 2b
**優先度:** 高
**依存関係:** #04, #05, #07
**見積もり:** 1.5日

---

## 概要

`TransitionGraph` からPythonコードを生成する純粋関数を実装する。
生成されるコードには状態Enum、遷移テーブル、メタデータが含まれる。

---

## 設計原則

### 純粋関数としてのコード生成

```python
# ✅ 文字列を返す純粋関数
def generate_transition_code(graph: TransitionGraph) -> str:
    ...

# IO境界でファイルに書き込む
def write_generated_code(code: str, path: Path) -> None:
    path.write_text(code)
```

### テンプレートベースの生成

読みやすさと保守性のため、文字列テンプレートを使用。

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/core/dag/test_codegen.py
"""Tests for code generator (pure functions)."""
import pytest
import ast
from textwrap import dedent


class TestGenerateStateEnum:
    """Test state enum generation."""

    def test_generate_state_enum_code(self):
        """Should generate valid state enum code."""
        from railway.core.dag.codegen import generate_state_enum
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, StateTransition, GraphOptions
        )

        graph = TransitionGraph(
            version="1.0",
            entrypoint="my_workflow",
            description="",
            nodes=(NodeDefinition("fetch", "m", "f", "d"),),
            exits=(),
            transitions=(
                StateTransition("fetch", "success::done", "exit::done"),
                StateTransition("fetch", "failure::http", "exit::error"),
            ),
            start_node="fetch",
            options=GraphOptions(),
        )

        code = generate_state_enum(graph)

        # Should be valid Python
        ast.parse(code)

        # Should contain enum definition
        assert "class MyWorkflowState" in code
        assert "NodeOutcome" in code
        assert "FETCH_SUCCESS_DONE" in code
        assert "FETCH_FAILURE_HTTP" in code

    def test_state_enum_values(self):
        """Should generate correct state values."""
        from railway.core.dag.codegen import generate_state_enum
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, StateTransition, GraphOptions
        )

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(NodeDefinition("check", "m", "f", "d"),),
            exits=(),
            transitions=(
                StateTransition("check", "success::exist", "exit::done"),
                StateTransition("check", "success::not_exist", "exit::done"),
            ),
            start_node="check",
            options=GraphOptions(),
        )

        code = generate_state_enum(graph)

        assert '"check::success::exist"' in code
        assert '"check::success::not_exist"' in code


class TestGenerateExitEnum:
    """Test exit enum generation."""

    def test_generate_exit_enum_code(self):
        """Should generate valid exit enum code."""
        from railway.core.dag.codegen import generate_exit_enum
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, ExitDefinition, GraphOptions
        )

        graph = TransitionGraph(
            version="1.0",
            entrypoint="my_workflow",
            description="",
            nodes=(NodeDefinition("a", "m", "f", "d"),),
            exits=(
                ExitDefinition("green_resolved", 0, "正常終了"),
                ExitDefinition("red_error", 1, "異常終了"),
            ),
            transitions=(),
            start_node="a",
            options=GraphOptions(),
        )

        code = generate_exit_enum(graph)

        # Should be valid Python
        ast.parse(code)

        assert "class MyWorkflowExit" in code
        assert "ExitOutcome" in code
        assert "GREEN_RESOLVED" in code
        assert "RED_ERROR" in code


class TestGenerateTransitionTable:
    """Test transition table generation."""

    def test_generate_transition_table(self):
        """Should generate valid transition table."""
        from railway.core.dag.codegen import generate_transition_table
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, ExitDefinition,
            StateTransition, GraphOptions
        )

        graph = TransitionGraph(
            version="1.0",
            entrypoint="workflow",
            description="",
            nodes=(
                NodeDefinition("a", "nodes.a", "node_a", "d"),
                NodeDefinition("b", "nodes.b", "node_b", "d"),
            ),
            exits=(ExitDefinition("done", 0, ""),),
            transitions=(
                StateTransition("a", "success", "b"),
                StateTransition("b", "success", "exit::done"),
            ),
            start_node="a",
            options=GraphOptions(),
        )

        code = generate_transition_table(graph)

        # Should be valid Python
        ast.parse(code)

        assert "TRANSITION_TABLE" in code
        assert "WorkflowState.A_SUCCESS" in code
        assert "node_b" in code
        assert "WorkflowExit.DONE" in code


class TestGenerateImports:
    """Test import statement generation."""

    def test_generate_node_imports(self):
        """Should generate correct import statements."""
        from railway.core.dag.codegen import generate_imports
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, GraphOptions
        )

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(
                NodeDefinition("fetch", "nodes.fetch_alert", "fetch_alert", ""),
                NodeDefinition("check", "nodes.check_session", "check_session_exists", ""),
            ),
            exits=(),
            transitions=(),
            start_node="fetch",
            options=GraphOptions(),
        )

        code = generate_imports(graph)

        assert "from nodes.fetch_alert import fetch_alert" in code
        assert "from nodes.check_session import check_session_exists" in code


class TestGenerateMetadata:
    """Test metadata generation."""

    def test_generate_metadata(self):
        """Should generate graph metadata."""
        from railway.core.dag.codegen import generate_metadata
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, GraphOptions
        )

        graph = TransitionGraph(
            version="1.0",
            entrypoint="top2",
            description="セッション管理",
            nodes=(NodeDefinition("a", "m", "f", "d"),),
            exits=(),
            transitions=(),
            start_node="a",
            options=GraphOptions(max_iterations=20),
        )

        code = generate_metadata(graph, "transition_graphs/top2_20250125.yml")

        assert "GRAPH_METADATA" in code
        assert '"version": "1.0"' in code
        assert '"entrypoint": "top2"' in code
        assert '"start_node": "a"' in code
        assert '"max_iterations": 20' in code
        assert "top2_20250125.yml" in code


class TestGenerateFullCode:
    """Test full code generation."""

    def test_generate_transition_code(self):
        """Should generate complete, valid Python file."""
        from railway.core.dag.codegen import generate_transition_code
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, ExitDefinition,
            StateTransition, GraphOptions
        )

        graph = TransitionGraph(
            version="1.0",
            entrypoint="my_workflow",
            description="テストワークフロー",
            nodes=(
                NodeDefinition("start", "nodes.start", "start_node", "開始"),
                NodeDefinition("process", "nodes.process", "process_data", "処理"),
            ),
            exits=(
                ExitDefinition("success", 0, "成功"),
                ExitDefinition("error", 1, "失敗"),
            ),
            transitions=(
                StateTransition("start", "success::done", "process"),
                StateTransition("start", "failure::init", "exit::error"),
                StateTransition("process", "success::complete", "exit::success"),
                StateTransition("process", "failure::error", "exit::error"),
            ),
            start_node="start",
            options=GraphOptions(max_iterations=50),
        )

        code = generate_transition_code(graph, "test.yml")

        # Should be valid Python
        ast.parse(code)

        # Should have header comment
        assert "DO NOT EDIT" in code
        assert "Generated by" in code

        # Should import from railway
        assert "from railway.core.dag.state import NodeOutcome, ExitOutcome" in code

        # Should have all components
        assert "class MyWorkflowState" in code
        assert "class MyWorkflowExit" in code
        assert "TRANSITION_TABLE" in code
        assert "GRAPH_METADATA" in code
        assert "def get_next_step" in code

    def test_generated_code_is_executable(self):
        """Generated code should be importable when written to file."""
        from railway.core.dag.codegen import generate_transition_code
        from railway.core.dag.types import (
            TransitionGraph, NodeDefinition, ExitDefinition,
            StateTransition, GraphOptions
        )
        import tempfile
        import sys
        from pathlib import Path

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(NodeDefinition("a", "nodes.a", "func_a", ""),),
            exits=(ExitDefinition("done", 0, ""),),
            transitions=(StateTransition("a", "success", "exit::done"),),
            start_node="a",
            options=GraphOptions(),
        )

        code = generate_transition_code(graph, "test.yml")

        # Verify AST is valid
        tree = ast.parse(code)
        assert tree is not None


class TestCodegenHelpers:
    """Test helper functions."""

    def test_to_enum_name(self):
        """Should convert state to valid enum name."""
        from railway.core.dag.codegen import _to_enum_name

        assert _to_enum_name("fetch", "success::done") == "FETCH_SUCCESS_DONE"
        assert _to_enum_name("check_session", "failure::http") == "CHECK_SESSION_FAILURE_HTTP"
        assert _to_enum_name("a", "success::type_a") == "A_SUCCESS_TYPE_A"

    def test_to_class_name(self):
        """Should convert entrypoint to valid class name."""
        from railway.core.dag.codegen import _to_class_name

        assert _to_class_name("my_workflow") == "MyWorkflow"
        assert _to_class_name("top2") == "Top2"
        assert _to_class_name("session_manager") == "SessionManager"

    def test_to_exit_enum_name(self):
        """Should convert exit name to enum name."""
        from railway.core.dag.codegen import _to_exit_enum_name

        assert _to_exit_enum_name("green_resolved") == "GREEN_RESOLVED"
        assert _to_exit_enum_name("red_error") == "RED_ERROR"
```

```bash
pytest tests/unit/core/dag/test_codegen.py -v
# Expected: FAILED (ImportError)
```

### Step 2: Green（最小限の実装）

```python
# railway/core/dag/codegen.py
"""
Code generator for transition graphs.

Generates Python code from TransitionGraph data structures.
All generation functions are pure - they take data and return strings.
"""
from __future__ import annotations

from datetime import datetime
from typing import Sequence

from railway.core.dag.types import TransitionGraph, NodeDefinition


def generate_transition_code(graph: TransitionGraph, source_file: str) -> str:
    """
    Generate complete transition code file.

    This is the main entry point for code generation.
    Returns a complete, valid Python file as a string.

    Args:
        graph: Parsed transition graph
        source_file: Path to source YAML file

    Returns:
        Generated Python code as string
    """
    class_name = _to_class_name(graph.entrypoint)

    parts = [
        _generate_header(source_file),
        _generate_framework_imports(),
        generate_imports(graph),
        "",
        generate_state_enum(graph),
        "",
        generate_exit_enum(graph),
        "",
        generate_transition_table(graph),
        "",
        generate_metadata(graph, source_file),
        "",
        _generate_helper_functions(class_name),
    ]

    return "\n".join(parts)


def _generate_header(source_file: str) -> str:
    """Generate file header with warning."""
    timestamp = datetime.now().isoformat()
    return f'''# DO NOT EDIT - Generated by `railway sync transition`
# Source: {source_file}
# Generated at: {timestamp}
#
# This file is auto-generated from the transition graph YAML.
# Any manual changes will be overwritten on next sync.
'''


def _generate_framework_imports() -> str:
    """Generate framework imports."""
    return '''from typing import Callable, Union
from railway.core.dag.state import NodeOutcome, ExitOutcome
'''


def generate_imports(graph: TransitionGraph) -> str:
    """
    Generate import statements for all nodes.

    Args:
        graph: Transition graph

    Returns:
        Import statements as string
    """
    lines = ["# Node imports"]
    for node in graph.nodes:
        lines.append(f"from {node.module} import {node.function}")
    return "\n".join(lines)


def generate_state_enum(graph: TransitionGraph) -> str:
    """
    Generate state enum from graph transitions.

    Args:
        graph: Transition graph

    Returns:
        State enum class definition as string
    """
    class_name = _to_class_name(graph.entrypoint)
    lines = [
        f"class {class_name}State(NodeOutcome):",
        '    """Auto-generated state enum for this workflow."""',
    ]

    # Collect unique states per node
    for node in graph.nodes:
        states = graph.get_states_for_node(node.name)
        if states:
            lines.append(f"    # {node.name}")
            for state in states:
                enum_name = _to_enum_name(node.name, state)
                full_state = f"{node.name}::{state}"
                lines.append(f'    {enum_name} = "{full_state}"')

    if len(lines) == 2:
        lines.append("    pass  # No states defined")

    return "\n".join(lines)


def generate_exit_enum(graph: TransitionGraph) -> str:
    """
    Generate exit enum from graph exits.

    Args:
        graph: Transition graph

    Returns:
        Exit enum class definition as string
    """
    class_name = _to_class_name(graph.entrypoint)
    lines = [
        f"class {class_name}Exit(ExitOutcome):",
        '    """Auto-generated exit enum for this workflow."""',
    ]

    for exit_def in graph.exits:
        enum_name = _to_exit_enum_name(exit_def.name)
        color = "green" if exit_def.code == 0 else "red"
        value = f"exit::{color}::{exit_def.name}"
        lines.append(f'    {enum_name} = "{value}"  # code={exit_def.code}')

    if len(lines) == 2:
        lines.append("    pass  # No exits defined")

    return "\n".join(lines)


def generate_transition_table(graph: TransitionGraph) -> str:
    """
    Generate transition table mapping states to next steps.

    Args:
        graph: Transition graph

    Returns:
        Transition table definition as string
    """
    class_name = _to_class_name(graph.entrypoint)
    state_class = f"{class_name}State"
    exit_class = f"{class_name}Exit"

    lines = [
        f"TRANSITION_TABLE: dict[{state_class}, Callable | {exit_class}] = {{",
    ]

    for transition in graph.transitions:
        enum_name = _to_enum_name(transition.from_node, transition.from_state)
        state_ref = f"{state_class}.{enum_name}"

        if transition.is_exit:
            exit_name = transition.exit_name
            exit_enum = _to_exit_enum_name(exit_name) if exit_name else "UNKNOWN"
            target_ref = f"{exit_class}.{exit_enum}"
        else:
            # Find the node to get function name
            target_node = graph.get_node(transition.to_target)
            if target_node:
                target_ref = target_node.function
            else:
                target_ref = f"# ERROR: unknown node '{transition.to_target}'"

        lines.append(f"    {state_ref}: {target_ref},")

    lines.append("}")

    return "\n".join(lines)


def generate_metadata(graph: TransitionGraph, source_file: str) -> str:
    """
    Generate graph metadata dictionary.

    Args:
        graph: Transition graph
        source_file: Path to source YAML

    Returns:
        Metadata dictionary definition as string
    """
    max_iter = graph.options.max_iterations if graph.options else 100

    return f'''GRAPH_METADATA = {{
    "version": "{graph.version}",
    "entrypoint": "{graph.entrypoint}",
    "description": "{graph.description}",
    "source_file": "{source_file}",
    "generated_at": "{datetime.now().isoformat()}",
    "start_node": "{graph.start_node}",
    "max_iterations": {max_iter},
}}'''


def _generate_helper_functions(class_name: str) -> str:
    """Generate helper functions."""
    state_class = f"{class_name}State"
    exit_class = f"{class_name}Exit"

    return f'''
def get_next_step(state: {state_class}) -> Callable | {exit_class}:
    """
    Get the next step for a given state.

    Args:
        state: Current state from node execution

    Returns:
        Next node function or exit code

    Raises:
        KeyError: If state is not in transition table
    """
    if state not in TRANSITION_TABLE:
        raise KeyError(f"未定義の状態です: {{state}}")
    return TRANSITION_TABLE[state]


def get_start_node() -> Callable:
    """Get the start node function."""
    return {graph.nodes[0].function if graph.nodes else 'None'}
'''


def _to_enum_name(node_name: str, state: str) -> str:
    """
    Convert node name and state to enum member name.

    Example: ("fetch", "success::done") -> "FETCH_SUCCESS_DONE"
    """
    combined = f"{node_name}_{state}"
    return combined.upper().replace("::", "_").replace("-", "_")


def _to_class_name(entrypoint: str) -> str:
    """
    Convert entrypoint name to class name.

    Example: "my_workflow" -> "MyWorkflow"
    """
    return "".join(word.capitalize() for word in entrypoint.split("_"))


def _to_exit_enum_name(exit_name: str) -> str:
    """
    Convert exit name to enum member name.

    Example: "green_resolved" -> "GREEN_RESOLVED"
    """
    return exit_name.upper().replace("-", "_")
```

```bash
pytest tests/unit/core/dag/test_codegen.py -v
# Expected: PASSED
```

### Step 3: Refactor

- テンプレートエンジン（Jinja2等）への移行検討
- コード整形（black/ruff対応）
- 型ヒントの生成強化

---

## 完了条件

- [ ] `generate_transition_code()` が完全なPythonファイルを生成
- [ ] 生成コードが `ast.parse()` で検証可能
- [ ] 状態Enumが正しく生成される
- [ ] 終了Enumが正しく生成される
- [ ] 遷移テーブルが正しく生成される
- [ ] メタデータが正しく生成される
- [ ] ノードのimport文が正しく生成される
- [ ] ヘルパー関数 `get_next_step()` が生成される
- [ ] テストカバレッジ90%以上

---

## 次のIssue

- #09: CLI `railway sync transition`
