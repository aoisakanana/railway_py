"""経路検証エンジンのテスト。

Issue 21: Board パターンの NodeAnalysis を使った DAG 経路ごとのフィールド依存検証。
TDD: Red → Green → Refactor
"""
from __future__ import annotations

import copy

import pytest

from railway.core.dag.board_analyzer import BranchWrites, NodeAnalysis
from railway.core.dag.path_validator import (
    PathIssue,
    PathValidationResult,
    validate_paths,
)
from railway.core.dag.types import (
    ExitDefinition,
    GraphOptions,
    NodeDefinition,
    StateTransition,
    TransitionGraph,
)


# =========== Helper factories ===========


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


def _make_node_def(name: str, *, is_exit: bool = False) -> NodeDefinition:
    """テスト用 NodeDefinition を簡易生成する。"""
    return NodeDefinition(
        name=name,
        module=f"nodes.{name}",
        function=name.split(".")[-1],
        description=f"{name} node",
        is_exit=is_exit,
    )


def _make_analysis(
    node_name: str,
    *,
    reads_required: frozenset[str] = frozenset(),
    reads_optional: frozenset[str] = frozenset(),
    branch_writes: tuple[BranchWrites, ...] = (),
    all_writes: frozenset[str] = frozenset(),
    outcomes: tuple[str, ...] = (),
) -> NodeAnalysis:
    """テスト用 NodeAnalysis を簡易生成する。"""
    return NodeAnalysis(
        node_name=node_name,
        file_path=f"src/nodes/{node_name}.py",
        reads_required=reads_required,
        reads_optional=reads_optional,
        branch_writes=branch_writes,
        all_writes=all_writes,
        outcomes=outcomes,
        violations=(),
    )


# =========== 21-01: E010 path dependency validation ===========


class TestValidatePathsE010:
    """E010: 遷移辺で必須フィールドが不足している場合のエラー検出。"""

    def test_all_dependencies_satisfied_no_issues(self) -> None:
        """全依存が満たされる場合、issues が空。"""
        graph = _make_graph(
            nodes=(
                _make_node_def("start"),
                _make_node_def("process"),
                _make_node_def("exit.success.done", is_exit=True),
            ),
            transitions=(
                StateTransition(from_node="start", from_state="success::done", to_target="process"),
                StateTransition(from_node="process", from_state="success::done", to_target="exit.success.done"),
            ),
            start_node="start",
        )
        analyses = {
            "start": _make_analysis(
                "start",
                all_writes=frozenset({"host_name"}),
                branch_writes=(BranchWrites(outcome="success::done", writes=frozenset({"host_name"})),),
                outcomes=("success::done",),
            ),
            "process": _make_analysis(
                "process",
                reads_required=frozenset({"host_name"}),
                all_writes=frozenset(),
                branch_writes=(BranchWrites(outcome="success::done", writes=frozenset()),),
                outcomes=("success::done",),
            ),
        }

        result = validate_paths(graph, analyses)

        assert not result.has_errors
        assert result.issues == ()

    def test_missing_required_field_produces_e010(self) -> None:
        """必須フィールドが未提供の場合 E010 エラー。"""
        graph = _make_graph(
            nodes=(
                _make_node_def("start"),
                _make_node_def("process"),
                _make_node_def("exit.success.done", is_exit=True),
            ),
            transitions=(
                StateTransition(from_node="start", from_state="success::done", to_target="process"),
                StateTransition(from_node="process", from_state="success::done", to_target="exit.success.done"),
            ),
            start_node="start",
        )
        # start は host_name を書かないが、process は host_name を要求
        analyses = {
            "start": _make_analysis(
                "start",
                all_writes=frozenset(),
                branch_writes=(BranchWrites(outcome="success::done", writes=frozenset()),),
                outcomes=("success::done",),
            ),
            "process": _make_analysis(
                "process",
                reads_required=frozenset({"host_name"}),
                outcomes=("success::done",),
            ),
        }

        result = validate_paths(graph, analyses)

        assert result.has_errors
        assert len(result.errors) == 1
        error = result.errors[0]
        assert error.code == "E010"
        assert error.severity == "error"
        assert error.node_name == "process"
        assert error.field_name == "host_name"

    def test_entry_fields_satisfy_dependency(self) -> None:
        """entry_fields で提供されたフィールドで依存が満たされる。"""
        graph = _make_graph(
            nodes=(
                _make_node_def("start"),
                _make_node_def("exit.success.done", is_exit=True),
            ),
            transitions=(
                StateTransition(from_node="start", from_state="success::done", to_target="exit.success.done"),
            ),
            start_node="start",
        )
        # start は host_name を要求するが、entry_fields で提供される
        analyses = {
            "start": _make_analysis(
                "start",
                reads_required=frozenset({"host_name"}),
                all_writes=frozenset(),
                branch_writes=(BranchWrites(outcome="success::done", writes=frozenset()),),
                outcomes=("success::done",),
            ),
        }

        result = validate_paths(graph, analyses, entry_fields=frozenset({"host_name"}))

        assert not result.has_errors
        assert result.errors == ()

    def test_branch_writes_per_outcome(self) -> None:
        """分岐ごとの writes が正しく考慮される。"""
        # start --success::found--> process (process requires host_name)
        # start --success::not_found--> fallback (fallback does not require host_name)
        # start の branch_writes:
        #   success::found → {host_name}
        #   success::not_found → {}
        graph = _make_graph(
            nodes=(
                _make_node_def("start"),
                _make_node_def("process"),
                _make_node_def("fallback"),
                _make_node_def("exit.success.done", is_exit=True),
            ),
            transitions=(
                StateTransition(from_node="start", from_state="success::found", to_target="process"),
                StateTransition(from_node="start", from_state="success::not_found", to_target="fallback"),
                StateTransition(from_node="process", from_state="success::done", to_target="exit.success.done"),
                StateTransition(from_node="fallback", from_state="success::done", to_target="exit.success.done"),
            ),
            start_node="start",
        )
        analyses = {
            "start": _make_analysis(
                "start",
                all_writes=frozenset({"host_name"}),
                branch_writes=(
                    BranchWrites(outcome="success::found", writes=frozenset({"host_name"})),
                    BranchWrites(outcome="success::not_found", writes=frozenset()),
                ),
                outcomes=("success::found", "success::not_found"),
            ),
            "process": _make_analysis(
                "process",
                reads_required=frozenset({"host_name"}),
                outcomes=("success::done",),
            ),
            "fallback": _make_analysis(
                "fallback",
                reads_required=frozenset(),
                outcomes=("success::done",),
            ),
        }

        result = validate_paths(graph, analyses)

        # process gets host_name from start's "success::found" branch → OK
        # fallback doesn't require host_name → OK
        assert not result.has_errors

    def test_branch_writes_missing_for_specific_outcome(self) -> None:
        """特定 outcome の branch_writes にフィールドが含まれない場合 E010。"""
        # start --success::done--> process
        # start の branch_writes: success::done → {} (host_name を書かない)
        # process は host_name を要求
        graph = _make_graph(
            nodes=(
                _make_node_def("start"),
                _make_node_def("process"),
                _make_node_def("exit.success.done", is_exit=True),
            ),
            transitions=(
                StateTransition(from_node="start", from_state="success::done", to_target="process"),
                StateTransition(from_node="process", from_state="success::done", to_target="exit.success.done"),
            ),
            start_node="start",
        )
        analyses = {
            "start": _make_analysis(
                "start",
                all_writes=frozenset({"host_name"}),
                branch_writes=(
                    BranchWrites(outcome="success::done", writes=frozenset()),
                    BranchWrites(outcome="success::found", writes=frozenset({"host_name"})),
                ),
                outcomes=("success::done", "success::found"),
            ),
            "process": _make_analysis(
                "process",
                reads_required=frozenset({"host_name"}),
                outcomes=("success::done",),
            ),
        }

        result = validate_paths(graph, analyses)

        assert result.has_errors
        assert len(result.errors) == 1
        assert result.errors[0].code == "E010"
        assert result.errors[0].field_name == "host_name"

    def test_multi_hop_field_accumulation(self) -> None:
        """複数ホップにわたるフィールド累積が正しく動作する。"""
        # A → B → C: A provides field_a, B provides field_b, C requires both
        graph = _make_graph(
            nodes=(
                _make_node_def("a"),
                _make_node_def("b"),
                _make_node_def("c"),
                _make_node_def("exit.success.done", is_exit=True),
            ),
            transitions=(
                StateTransition(from_node="a", from_state="success::done", to_target="b"),
                StateTransition(from_node="b", from_state="success::done", to_target="c"),
                StateTransition(from_node="c", from_state="success::done", to_target="exit.success.done"),
            ),
            start_node="a",
        )
        analyses = {
            "a": _make_analysis(
                "a",
                all_writes=frozenset({"field_a"}),
                branch_writes=(BranchWrites(outcome="success::done", writes=frozenset({"field_a"})),),
                outcomes=("success::done",),
            ),
            "b": _make_analysis(
                "b",
                reads_required=frozenset({"field_a"}),
                all_writes=frozenset({"field_b"}),
                branch_writes=(BranchWrites(outcome="success::done", writes=frozenset({"field_b"})),),
                outcomes=("success::done",),
            ),
            "c": _make_analysis(
                "c",
                reads_required=frozenset({"field_a", "field_b"}),
                outcomes=("success::done",),
            ),
        }

        result = validate_paths(graph, analyses)

        assert not result.has_errors

    def test_node_without_analysis_is_skipped(self) -> None:
        """NodeAnalysis が存在しないノードはスキップされる。"""
        graph = _make_graph(
            nodes=(
                _make_node_def("start"),
                _make_node_def("unknown"),
                _make_node_def("exit.success.done", is_exit=True),
            ),
            transitions=(
                StateTransition(from_node="start", from_state="success::done", to_target="unknown"),
                StateTransition(from_node="unknown", from_state="success::done", to_target="exit.success.done"),
            ),
            start_node="start",
        )
        analyses = {
            "start": _make_analysis(
                "start",
                all_writes=frozenset({"field_a"}),
                branch_writes=(BranchWrites(outcome="success::done", writes=frozenset({"field_a"})),),
                outcomes=("success::done",),
            ),
            # "unknown" は解析データなし
        }

        result = validate_paths(graph, analyses)

        # エラーにはならない
        assert not result.has_errors

    def test_start_node_requires_from_entry_fields(self) -> None:
        """開始ノード自身の reads_required が entry_fields に含まれない場合 E010。"""
        graph = _make_graph(
            nodes=(
                _make_node_def("start"),
                _make_node_def("exit.success.done", is_exit=True),
            ),
            transitions=(
                StateTransition(from_node="start", from_state="success::done", to_target="exit.success.done"),
            ),
            start_node="start",
        )
        analyses = {
            "start": _make_analysis(
                "start",
                reads_required=frozenset({"needed_field"}),
                outcomes=("success::done",),
            ),
        }

        result = validate_paths(graph, analyses, entry_fields=frozenset())

        assert result.has_errors
        assert len(result.errors) == 1
        assert result.errors[0].code == "E010"
        assert result.errors[0].node_name == "start"
        assert result.errors[0].field_name == "needed_field"


# =========== 21-01: Pure function tests ===========


class TestValidatePathsPurity:
    """validate_paths が純粋関数であることの検証。"""

    def test_input_not_mutated(self) -> None:
        """入力引数が変更されないことを確認。"""
        graph = _make_graph(
            nodes=(
                _make_node_def("start"),
                _make_node_def("exit.success.done", is_exit=True),
            ),
            transitions=(
                StateTransition(from_node="start", from_state="success::done", to_target="exit.success.done"),
            ),
            start_node="start",
        )
        analyses = {
            "start": _make_analysis(
                "start",
                reads_required=frozenset({"field_a"}),
                outcomes=("success::done",),
            ),
        }
        entry_fields = frozenset({"field_a"})

        # Deep copies for comparison
        analyses_copy = copy.deepcopy(analyses)
        entry_fields_copy = frozenset(entry_fields)

        validate_paths(graph, analyses, entry_fields=entry_fields)

        # Verify no mutation
        assert analyses == analyses_copy
        assert entry_fields == entry_fields_copy

    def test_idempotent(self) -> None:
        """同じ入力で2回呼んでも同じ結果。"""
        graph = _make_graph(
            nodes=(
                _make_node_def("start"),
                _make_node_def("process"),
                _make_node_def("exit.success.done", is_exit=True),
            ),
            transitions=(
                StateTransition(from_node="start", from_state="success::done", to_target="process"),
                StateTransition(from_node="process", from_state="success::done", to_target="exit.success.done"),
            ),
            start_node="start",
        )
        analyses = {
            "start": _make_analysis(
                "start",
                all_writes=frozenset({"host_name"}),
                branch_writes=(BranchWrites(outcome="success::done", writes=frozenset({"host_name"})),),
                outcomes=("success::done",),
            ),
            "process": _make_analysis(
                "process",
                reads_required=frozenset({"missing_field"}),
                outcomes=("success::done",),
            ),
        }

        result1 = validate_paths(graph, analyses)
        result2 = validate_paths(graph, analyses)

        assert result1 == result2


# =========== 21-02: W001 unused writes ===========


class TestValidatePathsW001:
    """W001: writes したフィールドを後続のどのノードも reads しない。"""

    def test_unused_write_produces_w001(self) -> None:
        """後続ノードで使われない write → W001 警告。"""
        graph = _make_graph(
            nodes=(
                _make_node_def("start"),
                _make_node_def("process"),
                _make_node_def("exit.success.done", is_exit=True),
            ),
            transitions=(
                StateTransition(from_node="start", from_state="success::done", to_target="process"),
                StateTransition(from_node="process", from_state="success::done", to_target="exit.success.done"),
            ),
            start_node="start",
        )
        analyses = {
            "start": _make_analysis(
                "start",
                all_writes=frozenset({"unused_field", "used_field"}),
                branch_writes=(
                    BranchWrites(outcome="success::done", writes=frozenset({"unused_field", "used_field"})),
                ),
                outcomes=("success::done",),
            ),
            "process": _make_analysis(
                "process",
                reads_required=frozenset({"used_field"}),
                all_writes=frozenset(),
                outcomes=("success::done",),
            ),
        }

        result = validate_paths(graph, analyses)

        assert not result.has_errors
        assert len(result.warnings) >= 1
        w001_warnings = [w for w in result.warnings if w.code == "W001"]
        assert len(w001_warnings) == 1
        assert w001_warnings[0].field_name == "unused_field"
        assert w001_warnings[0].node_name == "start"

    def test_used_write_no_w001(self) -> None:
        """後続ノードで使われる write → 警告なし。"""
        graph = _make_graph(
            nodes=(
                _make_node_def("start"),
                _make_node_def("process"),
                _make_node_def("exit.success.done", is_exit=True),
            ),
            transitions=(
                StateTransition(from_node="start", from_state="success::done", to_target="process"),
                StateTransition(from_node="process", from_state="success::done", to_target="exit.success.done"),
            ),
            start_node="start",
        )
        analyses = {
            "start": _make_analysis(
                "start",
                all_writes=frozenset({"field_a"}),
                branch_writes=(BranchWrites(outcome="success::done", writes=frozenset({"field_a"})),),
                outcomes=("success::done",),
            ),
            "process": _make_analysis(
                "process",
                reads_required=frozenset({"field_a"}),
                outcomes=("success::done",),
            ),
        }

        result = validate_paths(graph, analyses)

        w001_warnings = [w for w in result.warnings if w.code == "W001"]
        assert len(w001_warnings) == 0

    def test_optional_read_counts_as_used(self) -> None:
        """optional read でも使用とみなし W001 にならない。"""
        graph = _make_graph(
            nodes=(
                _make_node_def("start"),
                _make_node_def("process"),
                _make_node_def("exit.success.done", is_exit=True),
            ),
            transitions=(
                StateTransition(from_node="start", from_state="success::done", to_target="process"),
                StateTransition(from_node="process", from_state="success::done", to_target="exit.success.done"),
            ),
            start_node="start",
        )
        analyses = {
            "start": _make_analysis(
                "start",
                all_writes=frozenset({"field_a"}),
                branch_writes=(BranchWrites(outcome="success::done", writes=frozenset({"field_a"})),),
                outcomes=("success::done",),
            ),
            "process": _make_analysis(
                "process",
                reads_optional=frozenset({"field_a"}),
                outcomes=("success::done",),
            ),
        }

        result = validate_paths(graph, analyses)

        w001_warnings = [w for w in result.warnings if w.code == "W001"]
        assert len(w001_warnings) == 0


# =========== 21-03: I001 design improvement suggestions ===========


class TestValidatePathsI001:
    """I001: 合流地点での optional reads に対する設計改善提案。"""

    def test_merge_point_optional_from_partial_paths_produces_i001(self) -> None:
        """合流地点で optional フィールドが一部経路からのみ提供 → I001。"""
        # path_a: start --success::a--> node_a --success::done--> merge
        # path_b: start --success::b--> node_b --success::done--> merge
        # merge reads_optional: {extra_field}
        # node_a provides extra_field, node_b does not
        graph = _make_graph(
            nodes=(
                _make_node_def("start"),
                _make_node_def("node_a"),
                _make_node_def("node_b"),
                _make_node_def("merge"),
                _make_node_def("exit.success.done", is_exit=True),
            ),
            transitions=(
                StateTransition(from_node="start", from_state="success::a", to_target="node_a"),
                StateTransition(from_node="start", from_state="success::b", to_target="node_b"),
                StateTransition(from_node="node_a", from_state="success::done", to_target="merge"),
                StateTransition(from_node="node_b", from_state="success::done", to_target="merge"),
                StateTransition(from_node="merge", from_state="success::done", to_target="exit.success.done"),
            ),
            start_node="start",
        )
        analyses = {
            "start": _make_analysis(
                "start",
                all_writes=frozenset(),
                branch_writes=(
                    BranchWrites(outcome="success::a", writes=frozenset()),
                    BranchWrites(outcome="success::b", writes=frozenset()),
                ),
                outcomes=("success::a", "success::b"),
            ),
            "node_a": _make_analysis(
                "node_a",
                all_writes=frozenset({"extra_field"}),
                branch_writes=(BranchWrites(outcome="success::done", writes=frozenset({"extra_field"})),),
                outcomes=("success::done",),
            ),
            "node_b": _make_analysis(
                "node_b",
                all_writes=frozenset(),
                branch_writes=(BranchWrites(outcome="success::done", writes=frozenset()),),
                outcomes=("success::done",),
            ),
            "merge": _make_analysis(
                "merge",
                reads_optional=frozenset({"extra_field"}),
                outcomes=("success::done",),
            ),
        }

        result = validate_paths(graph, analyses)

        assert not result.has_errors
        i001_infos = [i for i in result.infos if i.code == "I001"]
        assert len(i001_infos) >= 1
        assert i001_infos[0].node_name == "merge"
        assert i001_infos[0].field_name == "extra_field"

    def test_no_i001_when_required_read(self) -> None:
        """required read は I001 の対象外。"""
        graph = _make_graph(
            nodes=(
                _make_node_def("start"),
                _make_node_def("node_a"),
                _make_node_def("node_b"),
                _make_node_def("merge"),
                _make_node_def("exit.success.done", is_exit=True),
            ),
            transitions=(
                StateTransition(from_node="start", from_state="success::a", to_target="node_a"),
                StateTransition(from_node="start", from_state="success::b", to_target="node_b"),
                StateTransition(from_node="node_a", from_state="success::done", to_target="merge"),
                StateTransition(from_node="node_b", from_state="success::done", to_target="merge"),
                StateTransition(from_node="merge", from_state="success::done", to_target="exit.success.done"),
            ),
            start_node="start",
        )
        analyses = {
            "start": _make_analysis(
                "start",
                branch_writes=(
                    BranchWrites(outcome="success::a", writes=frozenset()),
                    BranchWrites(outcome="success::b", writes=frozenset()),
                ),
                outcomes=("success::a", "success::b"),
            ),
            "node_a": _make_analysis(
                "node_a",
                all_writes=frozenset({"extra_field"}),
                branch_writes=(BranchWrites(outcome="success::done", writes=frozenset({"extra_field"})),),
                outcomes=("success::done",),
            ),
            "node_b": _make_analysis(
                "node_b",
                all_writes=frozenset(),
                branch_writes=(BranchWrites(outcome="success::done", writes=frozenset()),),
                outcomes=("success::done",),
            ),
            "merge": _make_analysis(
                "merge",
                reads_required=frozenset({"extra_field"}),
                outcomes=("success::done",),
            ),
        }

        result = validate_paths(graph, analyses)

        # This should produce E010 (missing required), not I001
        i001_infos = [i for i in result.infos if i.code == "I001"]
        assert len(i001_infos) == 0

    def test_no_i001_when_all_paths_provide(self) -> None:
        """全経路が optional フィールドを提供 → I001 なし。"""
        graph = _make_graph(
            nodes=(
                _make_node_def("start"),
                _make_node_def("node_a"),
                _make_node_def("node_b"),
                _make_node_def("merge"),
                _make_node_def("exit.success.done", is_exit=True),
            ),
            transitions=(
                StateTransition(from_node="start", from_state="success::a", to_target="node_a"),
                StateTransition(from_node="start", from_state="success::b", to_target="node_b"),
                StateTransition(from_node="node_a", from_state="success::done", to_target="merge"),
                StateTransition(from_node="node_b", from_state="success::done", to_target="merge"),
                StateTransition(from_node="merge", from_state="success::done", to_target="exit.success.done"),
            ),
            start_node="start",
        )
        analyses = {
            "start": _make_analysis(
                "start",
                branch_writes=(
                    BranchWrites(outcome="success::a", writes=frozenset()),
                    BranchWrites(outcome="success::b", writes=frozenset()),
                ),
                outcomes=("success::a", "success::b"),
            ),
            "node_a": _make_analysis(
                "node_a",
                all_writes=frozenset({"extra_field"}),
                branch_writes=(BranchWrites(outcome="success::done", writes=frozenset({"extra_field"})),),
                outcomes=("success::done",),
            ),
            "node_b": _make_analysis(
                "node_b",
                all_writes=frozenset({"extra_field"}),
                branch_writes=(BranchWrites(outcome="success::done", writes=frozenset({"extra_field"})),),
                outcomes=("success::done",),
            ),
            "merge": _make_analysis(
                "merge",
                reads_optional=frozenset({"extra_field"}),
                outcomes=("success::done",),
            ),
        }

        result = validate_paths(graph, analyses)

        i001_infos = [i for i in result.infos if i.code == "I001"]
        assert len(i001_infos) == 0

    def test_no_i001_for_single_incoming_edge(self) -> None:
        """入力辺が1つのノードには I001 を出さない（合流地点ではない）。"""
        graph = _make_graph(
            nodes=(
                _make_node_def("start"),
                _make_node_def("process"),
                _make_node_def("exit.success.done", is_exit=True),
            ),
            transitions=(
                StateTransition(from_node="start", from_state="success::done", to_target="process"),
                StateTransition(from_node="process", from_state="success::done", to_target="exit.success.done"),
            ),
            start_node="start",
        )
        analyses = {
            "start": _make_analysis(
                "start",
                all_writes=frozenset(),
                branch_writes=(BranchWrites(outcome="success::done", writes=frozenset()),),
                outcomes=("success::done",),
            ),
            "process": _make_analysis(
                "process",
                reads_optional=frozenset({"field_x"}),
                outcomes=("success::done",),
            ),
        }

        result = validate_paths(graph, analyses)

        i001_infos = [i for i in result.infos if i.code == "I001"]
        assert len(i001_infos) == 0


# =========== PathValidationResult properties ===========


class TestPathValidationResult:
    """PathValidationResult のプロパティが正しく動作するか。"""

    def test_has_errors_true(self) -> None:
        result = PathValidationResult(
            issues=(
                PathIssue(
                    code="E010", severity="error", message="test",
                    node_name="n", field_name="f", file_path="p", line=1,
                ),
            ),
            node_analyses={},
        )
        assert result.has_errors is True

    def test_has_errors_false(self) -> None:
        result = PathValidationResult(
            issues=(
                PathIssue(
                    code="W001", severity="warning", message="test",
                    node_name="n", field_name="f", file_path="p", line=1,
                ),
            ),
            node_analyses={},
        )
        assert result.has_errors is False

    def test_errors_filter(self) -> None:
        result = PathValidationResult(
            issues=(
                PathIssue(
                    code="E010", severity="error", message="err",
                    node_name="n", field_name="f", file_path="p", line=1,
                ),
                PathIssue(
                    code="W001", severity="warning", message="warn",
                    node_name="n", field_name="f", file_path="p", line=2,
                ),
                PathIssue(
                    code="I001", severity="info", message="info",
                    node_name="n", field_name="f", file_path="p", line=3,
                ),
            ),
            node_analyses={},
        )
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert len(result.infos) == 1

    def test_empty_issues(self) -> None:
        result = PathValidationResult(issues=(), node_analyses={})
        assert result.has_errors is False
        assert result.errors == ()
        assert result.warnings == ()
        assert result.infos == ()
