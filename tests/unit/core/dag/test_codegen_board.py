"""Tests for Board-mode transition code generation (pure functions).

Issue 23-02: 遷移コードの Board モード対応。
"""
import ast

import pytest

from railway.core.dag.codegen import generate_board_run_helper
from railway.core.dag.types import (
    ExitDefinition,
    GraphOptions,
    NodeDefinition,
    StateTransition,
    TransitionGraph,
)


# =========== Helper ===========


def _make_graph(
    *,
    entrypoint: str = "alert_workflow",
    start_node: str = "check_severity",
    max_iterations: int = 100,
    nodes: tuple[NodeDefinition, ...] | None = None,
    transitions: tuple[StateTransition, ...] | None = None,
) -> TransitionGraph:
    """テスト用の TransitionGraph を生成する。"""
    if nodes is None:
        nodes = (
            NodeDefinition("check_severity", "nodes.alert_workflow.check_severity", "check_severity", "重要度チェック"),
            NodeDefinition("escalate", "nodes.alert_workflow.escalate", "escalate", "エスカレーション"),
            NodeDefinition("exit.success.done", "nodes.exit.success.done", "done", "正常終了", is_exit=True, exit_code=0),
            NodeDefinition("exit.failure.error", "nodes.exit.failure.error", "error", "エラー終了", is_exit=True, exit_code=1),
        )
    if transitions is None:
        transitions = (
            StateTransition("check_severity", "success::critical", "escalate"),
            StateTransition("escalate", "success::done", "exit.success.done"),
            StateTransition("escalate", "failure::error", "exit.failure.error"),
        )
    return TransitionGraph(
        version="1.0",
        entrypoint=entrypoint,
        description="テストワークフロー",
        nodes=nodes,
        exits=(),
        transitions=transitions,
        start_node=start_node,
        options=GraphOptions(max_iterations=max_iterations),
    )


# =========== 1. BoardBase と WorkflowResult の import 含む ===========


class TestBoardRunHelperImports:
    """import 生成のテスト。"""

    def test_contains_boardbase_import(self):
        """BoardBase の import が含まれること。"""
        graph = _make_graph()
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        assert "BoardBase" in code

    def test_contains_workflow_result_import(self):
        """WorkflowResult の import が含まれること。"""
        graph = _make_graph()
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        assert "WorkflowResult" in code


# =========== 2. dag_runner, async_dag_runner の import 含む ===========


class TestRunnerImports:
    """runner import のテスト。"""

    def test_contains_dag_runner_import(self):
        """dag_runner の import が含まれること。"""
        graph = _make_graph()
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        assert "dag_runner" in code

    def test_contains_async_dag_runner_import(self):
        """async_dag_runner の import が含まれること。"""
        graph = _make_graph()
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        assert "async_dag_runner" in code


# =========== 3. run() の返り値型が WorkflowResult ===========


class TestRunReturnType:
    """run() の返り値型テスト。"""

    def test_run_returns_workflow_result(self):
        """run() の返り値型が WorkflowResult であること。"""
        graph = _make_graph()
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        assert "-> WorkflowResult:" in code


# =========== 4. _create_board ヘルパー含む ===========


class TestCreateBoardHelper:
    """_create_board ヘルパーのテスト。"""

    def test_contains_create_board(self):
        """_create_board ヘルパー関数が含まれること。"""
        graph = _make_graph()
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        assert "def _create_board(" in code

    def test_create_board_handles_none(self):
        """_create_board が None を受け取れること。"""
        graph = _make_graph()
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        assert "if initial is None:" in code

    def test_create_board_handles_boardbase(self):
        """_create_board が BoardBase を受け取れること。"""
        graph = _make_graph()
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        assert "isinstance(initial, BoardBase)" in code

    def test_create_board_handles_dict(self):
        """_create_board が dict を受け取れること。"""
        graph = _make_graph()
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        assert "isinstance(initial, dict)" in code


# =========== 5. board= を dag_runner に渡す ===========


class TestBoardParameter:
    """board パラメータのテスト。"""

    def test_dag_runner_receives_board(self):
        """dag_runner に board= が渡されること。"""
        graph = _make_graph()
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        assert "board=board" in code


# =========== 6. trace= パラメータ含む ===========


class TestTraceParameter:
    """trace パラメータのテスト。"""

    def test_run_has_trace_parameter(self):
        """run() に trace パラメータがあること。"""
        graph = _make_graph()
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        assert "trace: bool = False" in code

    def test_trace_passed_to_dag_runner(self):
        """trace が dag_runner に渡されること。"""
        graph = _make_graph()
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        assert "trace=trace" in code


# =========== 7. strict パラメータなし ===========


class TestNoStrictParameter:
    """strict パラメータが含まれないテスト。"""

    def test_no_strict_parameter(self):
        """strict パラメータが含まれないこと。"""
        graph = _make_graph()
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        assert "strict" not in code


# =========== 8. check_dependencies パラメータなし ===========


class TestNoCheckDependencies:
    """check_dependencies パラメータが含まれないテスト。"""

    def test_no_check_dependencies(self):
        """check_dependencies パラメータが含まれないこと。"""
        graph = _make_graph()
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        assert "check_dependencies" not in code


# =========== 9. 生成コードが valid Python ===========


class TestValidPython:
    """生成コードの構文検証テスト。"""

    def test_generates_valid_python(self):
        """生成コードが compile() を通ること。"""
        graph = _make_graph()
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        compile(code, "<test>", "exec")

    def test_ast_parseable(self):
        """生成コードが AST パースできること。"""
        graph = _make_graph()
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        tree = ast.parse(code)
        # 関数が定義されていること
        func_defs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        func_names = {f.name for f in func_defs}
        assert "_create_board" in func_names
        assert "run" in func_names
        assert "run_async" in func_names


# =========== 10. run_async() も含む ===========


class TestRunAsync:
    """run_async() のテスト。"""

    def test_contains_run_async(self):
        """run_async() が含まれること。"""
        graph = _make_graph()
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        assert "async def run_async(" in code

    def test_run_async_returns_workflow_result(self):
        """run_async() の返り値型が WorkflowResult であること。"""
        graph = _make_graph()
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        # run_async の返り値型を確認
        lines = code.splitlines()
        for i, line in enumerate(lines):
            if "async def run_async(" in line:
                # 後続行で返り値型を確認
                remaining = "\n".join(lines[i:])
                assert "-> WorkflowResult:" in remaining
                break

    def test_run_async_uses_async_dag_runner(self):
        """run_async() が async_dag_runner を使うこと。"""
        graph = _make_graph()
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        # async_dag_runner が呼ばれていること
        assert "await async_dag_runner(" in code


# =========== 11. max_iterations が graph から取得される ===========


class TestMaxIterations:
    """max_iterations のテスト。"""

    def test_default_max_iterations(self):
        """デフォルトの max_iterations が使われること。"""
        graph = _make_graph(max_iterations=100)
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        assert "max_iterations: int = 100" in code

    def test_custom_max_iterations(self):
        """カスタム max_iterations が使われること。"""
        graph = _make_graph(max_iterations=50)
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        assert "max_iterations: int = 50" in code

    def test_large_max_iterations(self):
        """大きな max_iterations が使われること。"""
        graph = _make_graph(max_iterations=500)
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        assert "max_iterations: int = 500" in code


# =========== start_node テスト ===========


class TestStartNode:
    """start_node が正しく埋め込まれるテスト。"""

    def test_start_node_in_run(self):
        """run() で正しい start_node が使われること。"""
        graph = _make_graph(start_node="check_severity")
        code = generate_board_run_helper(graph, "alert_workflow.yml")
        assert "start=check_severity" in code

    def test_different_start_node(self):
        """異なる start_node で生成できること。"""
        nodes = (
            NodeDefinition("init", "nodes.wf.init", "init", "初期化"),
            NodeDefinition("exit.success.done", "nodes.exit.success.done", "done", "終了", is_exit=True, exit_code=0),
        )
        transitions = (
            StateTransition("init", "success::done", "exit.success.done"),
        )
        graph = _make_graph(
            start_node="init",
            nodes=nodes,
            transitions=transitions,
        )
        code = generate_board_run_helper(graph, "test.yml")
        assert "start=init" in code
