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


    def test_generate_metadata_description_with_double_quotes(self):
        """Should escape double quotes in description to produce valid Python."""
        from railway.core.dag.codegen import generate_metadata
        from railway.core.dag.types import (
            GraphOptions,
            NodeDefinition,
            TransitionGraph,
        )

        graph = TransitionGraph(
            version="1.0",
            entrypoint="entry2",
            description='He said "hello" to the workflow',
            nodes=(NodeDefinition("a", "m", "f", "d"),),
            exits=(),
            transitions=(),
            start_node="a",
            options=GraphOptions(max_iterations=20),
        )

        code = generate_metadata(graph, "test.yml")

        # Must be valid Python
        ast.parse(code)
        # Evaluate and check the actual value is preserved
        ns: dict = {}
        exec(code, ns)  # noqa: S102
        assert ns["GRAPH_METADATA"]["description"] == 'He said "hello" to the workflow'

    def test_generate_metadata_description_with_backslash(self):
        """Should escape backslashes in description to preserve the value."""
        from railway.core.dag.codegen import generate_metadata
        from railway.core.dag.types import (
            GraphOptions,
            NodeDefinition,
            TransitionGraph,
        )

        graph = TransitionGraph(
            version="1.0",
            entrypoint="entry2",
            description="path\\to\\file",
            nodes=(NodeDefinition("a", "m", "f", "d"),),
            exits=(),
            transitions=(),
            start_node="a",
            options=GraphOptions(max_iterations=20),
        )

        code = generate_metadata(graph, "test.yml")

        # Must be valid Python
        ast.parse(code)
        # Evaluate and check the actual value is preserved
        ns: dict = {}
        exec(code, ns)  # noqa: S102
        assert ns["GRAPH_METADATA"]["description"] == "path\\to\\file"

    def test_generate_metadata_description_with_single_quotes(self):
        """Should handle single quotes in description."""
        from railway.core.dag.codegen import generate_metadata
        from railway.core.dag.types import (
            GraphOptions,
            NodeDefinition,
            TransitionGraph,
        )

        graph = TransitionGraph(
            version="1.0",
            entrypoint="entry2",
            description="it's a workflow",
            nodes=(NodeDefinition("a", "m", "f", "d"),),
            exits=(),
            transitions=(),
            start_node="a",
            options=GraphOptions(max_iterations=20),
        )

        code = generate_metadata(graph, "test.yml")

        # Must be valid Python
        ast.parse(code)
        ns: dict = {}
        exec(code, ns)  # noqa: S102
        assert ns["GRAPH_METADATA"]["description"] == "it's a workflow"


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


class TestDeepNestedNodeCodegen:
    """深いネストノード（sub.deep.process 等）のコード生成テスト。

    バグ: ドット付きノード名がそのまま Python 識別子に使われ SyntaxError。
    """

    def _make_deep_nested_graph(self) -> "TransitionGraph":
        from railway.core.dag.types import (
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
        )

        return TransitionGraph(
            version="1.0",
            entrypoint="deep_test",
            description="深いネストテスト",
            nodes=(
                NodeDefinition("start", "nodes.deep_test.start", "start", "開始"),
                NodeDefinition(
                    "sub.deep.process",
                    "nodes.deep_test.sub.deep.process",
                    "process",
                    "深い処理",
                ),
                NodeDefinition(
                    "exit.success.done",
                    "nodes.exit.success.done",
                    "done",
                    "正常終了",
                    is_exit=True,
                    exit_code=0,
                ),
            ),
            exits=(),
            transitions=(
                StateTransition("start", "success::done", "sub.deep.process"),
                StateTransition(
                    "sub.deep.process", "success::done", "exit.success.done"
                ),
            ),
            start_node="start",
            options=GraphOptions(),
        )

    def test_full_code_is_valid_python(self) -> None:
        """深いネストノードを含む完全な生成コードが有効な Python であること。"""
        from railway.core.dag.codegen import generate_transition_code

        graph = self._make_deep_nested_graph()
        code = generate_transition_code(graph, "test.yml")

        # SyntaxError が発生しないこと
        ast.parse(code)

    def test_imports_use_leaf_function_name(self) -> None:
        """import 文が葉の関数名を使用すること。"""
        from railway.core.dag.codegen import generate_imports

        graph = self._make_deep_nested_graph()
        code = generate_imports(graph)

        # ドット付き名がそのまま import されないこと
        assert "import sub.deep.process" not in code
        # 葉の関数名でインポート（エイリアス付き）
        assert "from nodes.deep_test.sub.deep.process import process" in code

    def test_node_name_assignments_valid_python(self) -> None:
        """_node_name 代入が有効な Python であること。"""
        from railway.core.dag.codegen import generate_node_name_assignments

        graph = self._make_deep_nested_graph()
        code = generate_node_name_assignments(graph)

        ast.parse(code)
        # ドット付き名がそのまま左辺に使われないこと
        assert "sub.deep.process._node_name" not in code
        # エイリアスで代入されること
        assert '_node_name = "sub.deep.process"' in code

    def test_state_enum_valid_python(self) -> None:
        """状態 enum がドットを含まない有効な Python であること。"""
        from railway.core.dag.codegen import generate_state_enum

        graph = self._make_deep_nested_graph()
        code = generate_state_enum(graph)

        ast.parse(code)
        # ドットが含まれないこと
        assert "SUB.DEEP" not in code
        # アンダースコアで正しく置換されること
        assert "SUB_DEEP_PROCESS_SUCCESS_DONE" in code

    def test_transition_table_valid_python(self) -> None:
        """遷移テーブルが有効な Python であること。"""
        from railway.core.dag.codegen import generate_transition_table

        graph = self._make_deep_nested_graph()
        code = generate_transition_table(graph)

        ast.parse(code)
        # ドット付き名がそのまま値に使われないこと（文字列キーは OK）
        assert '"start::success::done": process' not in code or \
               '"start::success::done": _sub_deep_process' in code


class TestCodegenDottedFunctionName:
    """node.function にドットが含まれるケースのテスト。

    パーサーが function を葉の名前に正規化していても、
    codegen 側は防御的にドット付き function を処理できるべき。
    """

    def _make_graph_with_dotted_function(self) -> "TransitionGraph":
        """function フィールドにドット付き名前を持つグラフ。"""
        from railway.core.dag.types import (
            GraphOptions,
            NodeDefinition,
            StateTransition,
            TransitionGraph,
        )

        return TransitionGraph(
            version="1.0",
            entrypoint="deep_test",
            description="ドット付き function テスト",
            nodes=(
                NodeDefinition("start", "nodes.deep_test.start", "start", "開始"),
                NodeDefinition(
                    "sub.deep.process",
                    "nodes.deep_test.sub.deep.process",
                    "sub.deep.process",  # function にもドットが含まれる
                    "深い処理",
                ),
                NodeDefinition(
                    "exit.success.done",
                    "nodes.exit.success.done",
                    "done",
                    "正常終了",
                    is_exit=True,
                    exit_code=0,
                ),
            ),
            exits=(),
            transitions=(
                StateTransition("start", "success::done", "sub.deep.process"),
                StateTransition(
                    "sub.deep.process", "success::done", "exit.success.done"
                ),
            ),
            start_node="start",
            options=GraphOptions(),
        )

    def test_import_uses_leaf_not_dotted_function(self) -> None:
        """import 文が葉の名前を使用すること（ドット付き function でも）。"""
        import ast

        from railway.core.dag.codegen import generate_imports

        graph = self._make_graph_with_dotted_function()
        code = generate_imports(graph)

        # SyntaxError にならないこと
        ast.parse(code)
        # ドット付き function がそのまま import されないこと
        assert "import sub.deep.process" not in code

    def test_full_code_valid_python(self) -> None:
        """ドット付き function でも完全な生成コードが有効な Python であること。"""
        import ast

        from railway.core.dag.codegen import generate_transition_code

        graph = self._make_graph_with_dotted_function()
        code = generate_transition_code(graph, "test.yml")

        # SyntaxError が発生しないこと
        ast.parse(code)

    def test_node_name_assignment_valid(self) -> None:
        """_node_name 代入が有効な Python であること。"""
        import ast

        from railway.core.dag.codegen import generate_node_name_assignments

        graph = self._make_graph_with_dotted_function()
        code = generate_node_name_assignments(graph)

        ast.parse(code)
        # ドットが左辺に現れないこと
        assert "sub.deep.process._node_name" not in code


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

    def test_to_enum_name_with_dots(self):
        """ドット付きノード名の enum 名変換。"""
        from railway.core.dag.codegen import _to_enum_name

        assert (
            _to_enum_name("sub.deep.process", "success::done")
            == "SUB_DEEP_PROCESS_SUCCESS_DONE"
        )

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
