"""EXIT_CODES 廃止テスト (v0.13.0)。

TDD Red Phase: EXIT_CODES が生成されないことを確認。

v0.13.0 では終端ノードが ExitContract を直接返すため、
EXIT_CODES マッピングは不要になった。
"""

import pytest

from railway.core.dag.codegen import generate_transition_code
from railway.core.dag.types import NodeDefinition, StateTransition, TransitionGraph


class TestExitCodesRemoved:
    """EXIT_CODES が生成されないことを確認するテスト。"""

    def test_no_exit_codes_in_generated_code(self) -> None:
        """生成コードに EXIT_CODES が含まれない。"""
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

        code = generate_transition_code(graph, "test.yml")

        # EXIT_CODES は生成されない
        assert "EXIT_CODES" not in code

    def test_no_exit_codes_with_multiple_exit_nodes(self) -> None:
        """複数の終端ノードがあっても EXIT_CODES は生成されない。"""
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
            NodeDefinition(
                name="exit.failure.timeout",
                module="nodes.exit.failure.timeout",
                function="timeout",
                description="タイムアウト",
                is_exit=True,
                exit_code=1,
            ),
            NodeDefinition(
                name="exit.warning.threshold",
                module="nodes.exit.warning.threshold",
                function="threshold",
                description="警告",
                is_exit=True,
                exit_code=2,
            ),
        )
        transitions = (
            StateTransition(
                from_node="start",
                from_state="success::done",
                to_target="exit.success.done",
            ),
            StateTransition(
                from_node="start",
                from_state="failure::timeout",
                to_target="exit.failure.timeout",
            ),
            StateTransition(
                from_node="start",
                from_state="warning::threshold",
                to_target="exit.warning.threshold",
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

        code = generate_transition_code(graph, "test.yml")

        # EXIT_CODES は生成されない
        assert "EXIT_CODES" not in code
        # 終端ノードは TRANSITION_TABLE に含まれる
        assert "_exit_success_done" in code
        assert "_exit_failure_timeout" in code
        assert "_exit_warning_threshold" in code


class TestGenerateExitCodesRemoved:
    """generate_exit_codes 関数が削除されていることを確認。"""

    def test_generate_exit_codes_not_exported(self) -> None:
        """generate_exit_codes 関数がエクスポートされていない。"""
        from railway.core.dag import codegen

        assert not hasattr(codegen, "generate_exit_codes")
