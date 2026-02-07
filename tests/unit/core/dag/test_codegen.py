"""Tests for code generator (pure functions)."""
import ast
from pathlib import Path

import pytest


class TestGenerateStateEnum:
    """Test state enum generation."""

    def test_generate_state_enum_code(self):
        """Should generate valid state enum code."""
        from railway.core.dag.codegen import generate_state_enum
        from railway.core.dag.types import (
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
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
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
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
    """Test exit enum generation (v0.12.2: constants instead of class)."""

    def test_generate_exit_enum_code(self):
        """Should generate valid exit constants (no longer ExitOutcome class)."""
        from railway.core.dag.codegen import generate_exit_enum
        from railway.core.dag.types import (
            ExitDefinition,
            GraphOptions,
            NodeDefinition,
            TransitionGraph,
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

        # v0.12.2: Exit codes are constants, not class
        assert "GREEN_RESOLVED" in code
        assert "RED_ERROR" in code
        assert "exit::green" in code
        assert "exit::red" in code


class TestGenerateTransitionTable:
    """Test transition table generation (string keys)."""

    def test_generate_transition_table(self):
        """Should generate valid transition table with string keys."""
        from railway.core.dag.codegen import generate_transition_table
        from railway.core.dag.types import (
            ExitDefinition,
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
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
                StateTransition("a", "success::done", "b"),
                StateTransition("b", "success::done", "exit::done"),
            ),
            start_node="a",
            options=GraphOptions(),
        )

        code = generate_transition_table(graph)

        # Should be valid Python
        ast.parse(code)

        # 文字列キーで生成
        assert "TRANSITION_TABLE" in code
        assert '"a::success::done"' in code
        assert "node_b" in code


class TestGenerateImports:
    """Test import statement generation."""

    def test_generate_node_imports(self):
        """Should generate correct import statements."""
        from railway.core.dag.codegen import generate_imports
        from railway.core.dag.types import (
            GraphOptions,
            NodeDefinition,
            TransitionGraph,
        )

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(
                NodeDefinition("fetch", "nodes.fetch_alert", "fetch_alert", ""),
                NodeDefinition(
                    "check", "nodes.check_session", "check_session_exists", ""
                ),
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
            GraphOptions,
            NodeDefinition,
            TransitionGraph,
        )

        graph = TransitionGraph(
            version="1.0",
            entrypoint="entry2",
            description="セッション管理",
            nodes=(NodeDefinition("a", "m", "f", "d"),),
            exits=(),
            transitions=(),
            start_node="a",
            options=GraphOptions(max_iterations=20),
        )

        code = generate_metadata(graph, "transition_graphs/entry2_20250125.yml")

        assert "GRAPH_METADATA" in code
        assert '"version": "1.0"' in code
        assert '"entrypoint": "entry2"' in code
        assert '"start_node": "a"' in code
        assert '"max_iterations": 20' in code
        assert "entry2_20250125.yml" in code


class TestGenerateFullCode:
    """Test full code generation."""

    def test_generate_transition_code(self):
        """Should generate complete, valid Python file."""
        from railway.core.dag.codegen import generate_transition_code
        from railway.core.dag.types import (
            ExitDefinition,
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
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
        assert "Generated" in code

        # Should import from railway (v0.12.2: no ExitOutcome)
        assert "from railway.core.dag.state import NodeOutcome" in code
        assert "from railway import ExitContract" in code

        # Should have all components (v0.12.2: no Exit class)
        assert "class MyWorkflowState" in code
        assert "# MyWorkflow exit codes" in code
        assert "TRANSITION_TABLE" in code
        assert "GRAPH_METADATA" in code
        assert "def get_next_step" in code

    def test_generated_code_is_executable(self):
        """Generated code should be syntactically valid."""
        from railway.core.dag.codegen import generate_transition_code
        from railway.core.dag.types import (
            ExitDefinition,
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
        )

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


class TestCodegenWithFixtures:
    """Integration tests using test YAML fixtures."""

    def test_generate_from_simple_yaml(self, simple_yaml: Path):
        """Should generate code from simple test YAML."""
        from railway.core.dag.codegen import generate_transition_code
        from railway.core.dag.parser import load_transition_graph

        graph = load_transition_graph(simple_yaml)
        code = generate_transition_code(graph, str(simple_yaml))

        # Should be valid Python
        ast.parse(code)

        # Should have correct class names (v0.12.2: no Exit class)
        assert "class SimpleState(NodeOutcome)" in code
        assert "# Simple exit codes" in code

    def test_generate_from_branching_yaml(self, branching_yaml: Path):
        """Should generate code from branching test YAML."""
        from railway.core.dag.codegen import generate_transition_code
        from railway.core.dag.parser import load_transition_graph

        graph = load_transition_graph(branching_yaml)
        code = generate_transition_code(graph, str(branching_yaml))

        # Should be valid Python
        ast.parse(code)

        # Should have all 5 nodes' states
        assert "CHECK_CONDITION" in code
        assert "PROCESS_A" in code
        assert "PROCESS_B" in code
        assert "PROCESS_C" in code
        assert "FINALIZE" in code


class TestCodegenHelpers:
    """Test helper functions."""

    def test_to_enum_name(self):
        """Should convert state to valid enum name."""
        from railway.core.dag.codegen import _to_enum_name

        assert _to_enum_name("fetch", "success::done") == "FETCH_SUCCESS_DONE"
        assert (
            _to_enum_name("check_session", "failure::http")
            == "CHECK_SESSION_FAILURE_HTTP"
        )
        assert _to_enum_name("a", "success::type_a") == "A_SUCCESS_TYPE_A"

    def test_to_class_name(self):
        """Should convert entrypoint to valid class name."""
        from railway.core.dag.codegen import _to_class_name

        assert _to_class_name("my_workflow") == "MyWorkflow"
        assert _to_class_name("entry2") == "Entry2"
        assert _to_class_name("session_manager") == "SessionManager"

    def test_to_exit_enum_name(self):
        """Should convert exit name to enum name."""
        from railway.core.dag.codegen import _to_exit_enum_name

        assert _to_exit_enum_name("green_resolved") == "GREEN_RESOLVED"
        assert _to_exit_enum_name("red_error") == "RED_ERROR"
