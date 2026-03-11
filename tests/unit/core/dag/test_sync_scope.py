"""sync スコープ計算モジュールのテスト。

Issue 24-03: 解析対象ノードのスコープ指定。
TDD: Red -> Green -> Refactor
"""
from __future__ import annotations

import pytest

from railway.core.dag.sync_scope import compute_sync_scope
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
    nodes: tuple[NodeDefinition, ...] = (),
    transitions: tuple[StateTransition, ...] = (),
    start_node: str = "start",
) -> TransitionGraph:
    """テスト用の TransitionGraph を簡易生成する。"""
    return TransitionGraph(
        version="1.0",
        entrypoint="test_workflow",
        description="test",
        nodes=nodes,
        exits=(),
        transitions=transitions,
        start_node=start_node,
        options=GraphOptions(),
    )


def _make_node(name: str, *, is_exit: bool = False) -> NodeDefinition:
    """テスト用 NodeDefinition を簡易生成する。"""
    return NodeDefinition(
        name=name,
        module=f"nodes.{name}",
        function=name,
        description=f"{name} ノード",
        is_exit=is_exit,
    )


def _make_transition(from_node: str, from_state: str, to_target: str) -> StateTransition:
    """テスト用 StateTransition を簡易生成する。"""
    return StateTransition(
        from_node=from_node,
        from_state=from_state,
        to_target=to_target,
    )


# =========== テスト用グラフ ===========


def _sample_graph() -> TransitionGraph:
    """テスト用のサンプルグラフ。

    start -> process -> finalize -> exit.success.done
    """
    return _make_graph(
        nodes=(
            _make_node("start"),
            _make_node("process"),
            _make_node("finalize"),
            _make_node("exit.success.done", is_exit=True),
        ),
        transitions=(
            _make_transition("start", "success::done", "process"),
            _make_transition("process", "success::done", "finalize"),
            _make_transition("finalize", "success::done", "exit.success.done"),
        ),
        start_node="start",
    )


# =========== Tests ===========


class TestComputeSyncScope:
    """compute_sync_scope のテスト。"""

    def test_full_returns_all_nodes(self) -> None:
        """full=True で全ノード（exit 除く）を返す。"""
        graph = _sample_graph()
        result = compute_sync_scope(graph, full=True)
        assert result == frozenset({"start", "process", "finalize"})

    def test_only_returns_single_node(self) -> None:
        """only_node で単一ノードを返す。"""
        graph = _sample_graph()
        result = compute_sync_scope(graph, only_node="process")
        assert result == frozenset({"process"})

    def test_only_with_deps_includes_neighbors(self) -> None:
        """only_node + with_deps で上流・下流を含む。"""
        graph = _sample_graph()
        result = compute_sync_scope(graph, only_node="process", with_deps=True)
        # process の上流: start, 下流: finalize
        assert "process" in result
        assert "start" in result
        assert "finalize" in result

    def test_default_returns_changed_only(self) -> None:
        """changed_nodes 指定で変更ノードのみ返す。"""
        graph = _sample_graph()
        result = compute_sync_scope(
            graph, changed_nodes=frozenset({"start", "process"})
        )
        assert result == frozenset({"start", "process"})

    def test_empty_when_no_changes(self) -> None:
        """変更がない場合は全ノードを返す（デフォルト動作）。"""
        graph = _sample_graph()
        # changed_nodes が空で full/only_node もなし → 全ノード
        result = compute_sync_scope(graph)
        assert result == frozenset({"start", "process", "finalize"})

    def test_is_pure_function(self) -> None:
        """純粋関数: 同じ入力で同じ出力。"""
        graph = _sample_graph()
        result1 = compute_sync_scope(graph, only_node="process", with_deps=True)
        result2 = compute_sync_scope(graph, only_node="process", with_deps=True)
        assert result1 == result2

    def test_excludes_exit_nodes(self) -> None:
        """exit ノードはスコープから除外される。"""
        graph = _sample_graph()
        result = compute_sync_scope(graph, full=True)
        assert "exit.success.done" not in result

    def test_changed_nodes_intersect_with_graph(self) -> None:
        """changed_nodes はグラフのノードと交差して返す。"""
        graph = _sample_graph()
        # "nonexistent" はグラフに存在しない
        result = compute_sync_scope(
            graph, changed_nodes=frozenset({"start", "nonexistent"})
        )
        assert result == frozenset({"start"})
        assert "nonexistent" not in result

    def test_priority_full_over_only_node(self) -> None:
        """full が only_node より優先される。"""
        graph = _sample_graph()
        result = compute_sync_scope(graph, full=True, only_node="process")
        assert result == frozenset({"start", "process", "finalize"})

    def test_priority_only_node_over_changed(self) -> None:
        """only_node が changed_nodes より優先される。"""
        graph = _sample_graph()
        result = compute_sync_scope(
            graph,
            only_node="process",
            changed_nodes=frozenset({"start"}),
        )
        assert result == frozenset({"process"})
