"""Tests for YAML parser (pure functions)."""
from pathlib import Path
from textwrap import dedent

import pytest


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
        """Should parse a complex workflow similar to 事例1."""
        from railway.core.dag.parser import parse_transition_graph

        yaml_content = dedent("""
            version: "1.0"
            entrypoint: top2
            description: "セッション管理ワークフロー"

            nodes:
              fetch_alert:
                module: nodes.fetch_alert
                function: fetch_alert
                description: "外部SaaS APIからアラート情報を取得"
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
        from railway.core.dag.parser import ParseError, parse_transition_graph

        invalid_yaml = "invalid: yaml: content: ["

        with pytest.raises(ParseError) as exc_info:
            parse_transition_graph(invalid_yaml)

        assert exc_info.value is not None

    def test_missing_required_field_version(self):
        """Should raise error when version is missing."""
        from railway.core.dag.parser import ParseError, parse_transition_graph

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
        from railway.core.dag.parser import ParseError, parse_transition_graph

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

    def test_auto_resolve_when_module_omitted(self):
        """Should auto-resolve module when omitted (v0.12.0+ behavior)."""
        from railway.core.dag.parser import parse_transition_graph

        yaml_content = dedent("""
            version: "1.0"
            entrypoint: test
            description: ""
            nodes:
              start:
                description: "Start node without explicit module/function"
            exits: {}
            start: start
            transitions: {}
        """)

        # v0.12.0: module/function are auto-resolved, no error
        graph = parse_transition_graph(yaml_content)
        start_node = graph.get_node("start")
        assert start_node is not None
        assert start_node.module == "nodes.start"
        assert start_node.function == "start"

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

    def test_parse_nodes_single(self):
        """Should parse a single node definition via parse_nodes."""
        from railway.core.dag.parser import parse_nodes

        nodes_data = {
            "fetch": {
                "module": "nodes.fetch",
                "function": "fetch_data",
                "description": "Fetch data from API",
            }
        }

        result = parse_nodes(nodes_data)

        assert len(result) == 1
        node = result[0]
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

    def test_load_simple_test_yaml(self, simple_yaml: Path):
        """Should load simple test YAML from fixtures."""
        from railway.core.dag.parser import load_transition_graph

        graph = load_transition_graph(simple_yaml)

        assert graph.entrypoint == "simple"
        assert graph.start_node == "start"
        assert len(graph.nodes) == 1
        assert len(graph.exits) == 2

    def test_load_branching_test_yaml(self, branching_yaml: Path):
        """Should load branching test YAML from fixtures."""
        from railway.core.dag.parser import load_transition_graph

        graph = load_transition_graph(branching_yaml)

        assert graph.entrypoint == "branching"
        assert len(graph.nodes) == 5
        # Verify 4 transitions from check_condition (3 success + 1 failure)
        check_transitions = graph.get_transitions_for_node("check_condition")
        assert len(check_transitions) == 4

    def test_load_from_file(self, tmp_path: Path):
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

    def test_load_file_not_found(self, tmp_path: Path):
        """Should raise error for non-existent file."""
        from railway.core.dag.parser import ParseError, load_transition_graph

        non_existent = tmp_path / "does_not_exist.yml"

        with pytest.raises(ParseError) as exc_info:
            load_transition_graph(non_existent)

        error_msg = str(exc_info.value).lower()
        assert "存在しません" in str(exc_info.value) or "not found" in error_msg
