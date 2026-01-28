"""Tests for codegen run helper generation."""

import pytest
from railway.core.dag.codegen import (
    generate_start_node_constant,
    generate_run_helper,
    generate_transition_code,
)
from railway.core.dag.types import (
    NodeDefinition,
    TransitionGraph,
)


class TestGenerateStartNodeConstant:
    """START_NODE 定数生成テスト。"""

    def test_generates_start_node_constant(self) -> None:
        """START_NODE 定数が生成される。"""
        nodes = (
            NodeDefinition(
                name="fetch_alert",
                module="nodes.fetch_alert",
                function="fetch_alert",
                description="アラート取得",
            ),
        )
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=nodes,
            exits=(),
            transitions=(),
            start_node="fetch_alert",
            options=None,
        )

        result = generate_start_node_constant(graph)

        assert "START_NODE = fetch_alert" in result


class TestGenerateRunHelper:
    """run() ヘルパー関数生成テスト。"""

    def test_generates_run_function(self) -> None:
        """run() 関数が生成される。"""
        result = generate_run_helper()

        assert "def run(" in result
        assert "initial_context: Any" in result
        assert "on_step:" in result
        assert "dag_runner(" in result
        assert "START_NODE" in result

    def test_generates_run_async_function(self) -> None:
        """run_async() 関数が生成される。"""
        result = generate_run_helper()

        assert "async def run_async(" in result
        assert "async_dag_runner(" in result


class TestGenerateTransitionCodeWithRunHelper:
    """run() ヘルパー込みの統合テスト。"""

    def test_generated_code_includes_run_helper(self) -> None:
        """生成コードに run() が含まれる。"""
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

        code = generate_transition_code(graph, "test.yml")

        assert "START_NODE = start" in code
        assert "def run(" in code

    def test_generated_code_includes_dag_runner_import(self) -> None:
        """dag_runner の import が含まれる。"""
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

        code = generate_transition_code(graph, "test.yml")

        assert "dag_runner" in code
        assert "async_dag_runner" in code
        assert "DagRunnerResult" in code

    def test_generated_code_is_valid_python(self) -> None:
        """生成コードが有効な Python。"""
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

        code = generate_transition_code(graph, "test.yml")

        # Python として構文解析可能
        compile(code, "<string>", "exec")
