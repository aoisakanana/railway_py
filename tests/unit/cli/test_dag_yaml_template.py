"""Tests for YAML template generation (Issue #60).

TDD: Red -> Green -> Refactor
"""

import pytest
import yaml

from railway.cli.new import _get_dag_yaml_template


class TestGetDagYamlTemplate:
    """YAML テンプレート生成のテスト。"""

    def test_generates_nodes_exit_section(self) -> None:
        """nodes.exit セクションが生成される（exits セクションではなく）。"""
        yaml_content = _get_dag_yaml_template("greeting")
        parsed = yaml.safe_load(yaml_content)

        assert "nodes" in parsed
        assert "exit" in parsed["nodes"]
        assert "success" in parsed["nodes"]["exit"]
        assert "done" in parsed["nodes"]["exit"]["success"]

        # レガシー形式が含まれない
        assert "exits" not in parsed

    def test_uses_new_transition_format(self) -> None:
        """新形式 exit.success.done を使用する。"""
        yaml_content = _get_dag_yaml_template("greeting")

        assert "exit.success.done" in yaml_content
        assert "exit.failure.error" in yaml_content

        # レガシー形式が含まれない
        assert "exit::success" not in yaml_content
        assert "exit::error" not in yaml_content
        assert "exit::green" not in yaml_content

    def test_includes_failure_exit(self) -> None:
        """失敗終端ノードも含まれる。"""
        yaml_content = _get_dag_yaml_template("greeting")
        parsed = yaml.safe_load(yaml_content)

        assert "failure" in parsed["nodes"]["exit"]
        assert "error" in parsed["nodes"]["exit"]["failure"]

    def test_start_node_has_description(self) -> None:
        """開始ノードに description がある。"""
        yaml_content = _get_dag_yaml_template("greeting")
        parsed = yaml.safe_load(yaml_content)

        assert parsed["nodes"]["start"]["description"] is not None

    def test_exit_nodes_have_description(self) -> None:
        """終端ノードに description がある。"""
        yaml_content = _get_dag_yaml_template("greeting")
        parsed = yaml.safe_load(yaml_content)

        assert parsed["nodes"]["exit"]["success"]["done"]["description"] is not None
        assert parsed["nodes"]["exit"]["failure"]["error"]["description"] is not None

    @pytest.mark.parametrize("name", ["greeting", "my_workflow", "alert_handler"])
    def test_works_with_various_names(self, name: str) -> None:
        """様々な名前で動作する。"""
        yaml_content = _get_dag_yaml_template(name)
        parsed = yaml.safe_load(yaml_content)

        assert parsed["entrypoint"] == name
        assert f"nodes.{name}.start" in parsed["nodes"]["start"]["module"]


class TestDagYamlTemplateIntegration:
    """YAML 構文の統合テスト。"""

    def test_generated_yaml_is_valid(self) -> None:
        """生成された YAML は構文的に正しい。"""
        yaml_content = _get_dag_yaml_template("greeting")
        parsed = yaml.safe_load(yaml_content)

        assert parsed is not None
        assert "nodes" in parsed
        assert "transitions" in parsed
        assert "start" in parsed

    def test_generated_yaml_passes_parser(self) -> None:
        """生成された YAML は parser を通過する。"""
        from railway.core.dag.parser import parse_transition_graph

        yaml_content = _get_dag_yaml_template("greeting")

        # parse_transition_graph は YAML 文字列を受け取る
        graph = parse_transition_graph(yaml_content)

        assert graph is not None
        assert graph.entrypoint == "greeting"
        assert graph.start_node == "start"

    def test_generated_yaml_passes_validator(self) -> None:
        """生成された YAML は validator を通過する。"""
        from railway.core.dag.parser import parse_transition_graph
        from railway.core.dag.validator import validate_graph

        yaml_content = _get_dag_yaml_template("greeting")

        # parse_transition_graph は YAML 文字列を受け取る
        graph = parse_transition_graph(yaml_content)
        result = validate_graph(graph)

        assert result.is_valid, f"Validation errors: {result.errors}"
