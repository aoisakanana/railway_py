"""sync キャッシュモジュールのテスト。

Issue 24-02: 差分解析用キャッシュ。
TDD: Red -> Green -> Refactor
"""
from __future__ import annotations

import copy

import pytest

from railway.core.dag.board_analyzer import (
    AnalysisViolation,
    BranchWrites,
    NodeAnalysis,
)
from railway.core.dag.sync_cache import (
    compute_file_hash,
    deserialize_analysis,
    detect_changed_nodes,
    serialize_analysis,
)


# =========== Helper ===========


def _make_analysis(
    node_name: str,
    *,
    reads_required: frozenset[str] = frozenset(),
    reads_optional: frozenset[str] = frozenset(),
    all_writes: frozenset[str] = frozenset(),
    branch_writes: tuple[BranchWrites, ...] = (),
    outcomes: tuple[str, ...] = (),
    violations: tuple[AnalysisViolation, ...] = (),
) -> NodeAnalysis:
    """テスト用の NodeAnalysis を生成する。"""
    return NodeAnalysis(
        node_name=node_name,
        file_path=f"src/nodes/{node_name}.py",
        reads_required=reads_required,
        reads_optional=reads_optional,
        branch_writes=branch_writes,
        all_writes=all_writes,
        outcomes=outcomes,
        violations=violations,
    )


# =========== compute_file_hash ===========


class TestComputeFileHash:
    """ファイルハッシュ計算のテスト。"""

    def test_compute_file_hash_deterministic(self) -> None:
        """同じ入力に対して同じハッシュを返す。"""
        content = "def start(board):\n    board.result = 42\n"
        hash1 = compute_file_hash(content)
        hash2 = compute_file_hash(content)
        assert hash1 == hash2

    def test_compute_file_hash_different_content(self) -> None:
        """異なる入力に対して異なるハッシュを返す。"""
        hash1 = compute_file_hash("content_a")
        hash2 = compute_file_hash("content_b")
        assert hash1 != hash2


# =========== detect_changed_nodes ===========


class TestDetectChangedNodes:
    """変更ノード検出のテスト。"""

    def test_detect_changed_nodes_new_node(self) -> None:
        """新しいノードが追加された場合。"""
        current = {"start": "aaa", "process": "bbb"}
        cached: dict[str, str] = {"start": "aaa"}
        result = detect_changed_nodes(current, cached)
        assert "process" in result

    def test_detect_changed_nodes_changed_hash(self) -> None:
        """ハッシュが変更された場合。"""
        current = {"start": "aaa_new"}
        cached = {"start": "aaa_old"}
        result = detect_changed_nodes(current, cached)
        assert "start" in result

    def test_detect_changed_nodes_removed_node(self) -> None:
        """ノードが削除された場合。"""
        current: dict[str, str] = {}
        cached = {"start": "aaa"}
        result = detect_changed_nodes(current, cached)
        assert "start" in result

    def test_detect_changed_nodes_no_changes(self) -> None:
        """変更がない場合。"""
        hashes = {"start": "aaa", "process": "bbb"}
        result = detect_changed_nodes(hashes, hashes)
        assert result == frozenset()


# =========== serialize / deserialize ===========


class TestSerializeDeserialize:
    """シリアライズ / デシリアライズのテスト。"""

    def test_serialize_deserialize_roundtrip(self) -> None:
        """シリアライズ -> デシリアライズで元の NodeAnalysis と一致する。"""
        analysis = _make_analysis(
            "check_severity",
            reads_required=frozenset({"severity", "incident_id"}),
            reads_optional=frozenset({"hostname"}),
            all_writes=frozenset({"result", "status"}),
            branch_writes=(
                BranchWrites(outcome="success::critical", writes=frozenset({"result"})),
                BranchWrites(outcome="success::normal", writes=frozenset({"status"})),
            ),
            outcomes=("success::critical", "success::normal"),
            violations=(
                AnalysisViolation(
                    code="E015",
                    message="テスト違反",
                    line=10,
                    file_path="src/nodes/check_severity.py",
                ),
            ),
        )

        json_str = serialize_analysis(analysis)
        restored = deserialize_analysis(json_str)

        assert restored.node_name == analysis.node_name
        assert restored.file_path == analysis.file_path
        assert restored.reads_required == analysis.reads_required
        assert restored.reads_optional == analysis.reads_optional
        assert restored.all_writes == analysis.all_writes
        assert restored.outcomes == analysis.outcomes
        assert len(restored.branch_writes) == len(analysis.branch_writes)
        for orig, rest in zip(analysis.branch_writes, restored.branch_writes):
            assert orig.outcome == rest.outcome
            assert orig.writes == rest.writes
        assert len(restored.violations) == len(analysis.violations)
        for orig_v, rest_v in zip(analysis.violations, restored.violations):
            assert orig_v.code == rest_v.code
            assert orig_v.message == rest_v.message
            assert orig_v.line == rest_v.line
            assert orig_v.file_path == rest_v.file_path

    def test_serialize_analysis_is_pure(self) -> None:
        """serialize は純粋関数: 2回呼んでも同じ結果。"""
        analysis = _make_analysis(
            "start",
            reads_required=frozenset({"x"}),
            all_writes=frozenset({"y"}),
        )
        result1 = serialize_analysis(analysis)
        result2 = serialize_analysis(analysis)
        assert result1 == result2
