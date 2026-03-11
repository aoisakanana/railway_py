"""sync 出力フォーマットのテスト。

Issue 24-04: Board 解析結果のフォーマット関数。
TDD: Red -> Green -> Refactor
"""
from __future__ import annotations

import pytest

from railway.core.dag.board_analyzer import BranchWrites, NodeAnalysis
from railway.core.dag.path_validator import PathIssue
from railway.cli.sync import _format_analysis_summary, _format_path_issue


# =========== Helper ===========


def _make_analysis(
    node_name: str,
    *,
    reads_required: frozenset[str] = frozenset(),
    reads_optional: frozenset[str] = frozenset(),
    all_writes: frozenset[str] = frozenset(),
    branch_writes: tuple[BranchWrites, ...] = (),
) -> NodeAnalysis:
    """テスト用の NodeAnalysis を生成する。"""
    return NodeAnalysis(
        node_name=node_name,
        file_path=f"src/nodes/{node_name}.py",
        reads_required=reads_required,
        reads_optional=reads_optional,
        branch_writes=branch_writes,
        all_writes=all_writes,
        outcomes=(),
        violations=(),
    )


def _make_issue(
    code: str,
    severity: str,
    message: str,
) -> PathIssue:
    """テスト用の PathIssue を生成する。"""
    return PathIssue(
        code=code,
        severity=severity,  # type: ignore[arg-type]
        message=message,
        node_name="test_node",
        field_name="test_field",
        file_path="src/nodes/test_node.py",
        line=10,
    )


# =========== _format_analysis_summary ===========


class TestFormatAnalysisSummary:
    """ノード解析サマリーフォーマットのテスト。"""

    def test_format_analysis_summary_with_reads_writes(self) -> None:
        """reads と writes がある場合のフォーマット。"""
        analysis = _make_analysis(
            "check_severity",
            reads_required=frozenset({"incident_id", "severity"}),
            all_writes=frozenset({"result"}),
        )
        result = _format_analysis_summary(analysis)
        assert "check_severity" in result
        assert "incident_id" in result
        assert "severity" in result
        assert "result" in result

    def test_format_analysis_summary_empty(self) -> None:
        """reads / writes がない場合のフォーマット。"""
        analysis = _make_analysis("empty_node")
        result = _format_analysis_summary(analysis)
        assert "empty_node" in result
        # reads / writes の行が出ない
        assert "reads" not in result
        assert "writes" not in result

    def test_format_analysis_summary_with_branches(self) -> None:
        """branch_writes がある場合のフォーマット。"""
        analysis = _make_analysis(
            "process",
            branch_writes=(
                BranchWrites(outcome="success::done", writes=frozenset({"status"})),
                BranchWrites(outcome="failure::error", writes=frozenset({"error_msg"})),
            ),
        )
        result = _format_analysis_summary(analysis)
        assert "success::done" in result
        assert "status" in result
        assert "failure::error" in result
        assert "error_msg" in result

    def test_format_analysis_summary_with_optional(self) -> None:
        """reads_optional がある場合のフォーマット。"""
        analysis = _make_analysis(
            "check",
            reads_optional=frozenset({"hostname"}),
        )
        result = _format_analysis_summary(analysis)
        assert "optional" in result
        assert "hostname" in result

    def test_format_analysis_summary_is_pure(self) -> None:
        """純粋関数: 同じ入力で同じ出力。"""
        analysis = _make_analysis(
            "node_a",
            reads_required=frozenset({"x"}),
            all_writes=frozenset({"y"}),
        )
        result1 = _format_analysis_summary(analysis)
        result2 = _format_analysis_summary(analysis)
        assert result1 == result2


# =========== _format_path_issue ===========


class TestFormatPathIssue:
    """PathIssue フォーマットのテスト。"""

    def test_format_path_issue_error(self) -> None:
        """エラー severity のフォーマット。"""
        issue = _make_issue("E010", "error", "必須フィールド不足")
        result = _format_path_issue(issue)
        assert "E010" in result
        assert "必須フィールド不足" in result

    def test_format_path_issue_warning(self) -> None:
        """警告 severity のフォーマット。"""
        issue = _make_issue("W001", "warning", "未使用フィールド")
        result = _format_path_issue(issue)
        assert "W001" in result
        assert "未使用フィールド" in result

    def test_format_path_issue_info(self) -> None:
        """情報 severity のフォーマット。"""
        issue = _make_issue("I001", "info", "合流地点の提案")
        result = _format_path_issue(issue)
        assert "I001" in result
        assert "合流地点の提案" in result

    def test_format_path_issue_is_pure(self) -> None:
        """純粋関数: 同じ入力で同じ出力。"""
        issue = _make_issue("E010", "error", "テスト")
        result1 = _format_path_issue(issue)
        result2 = _format_path_issue(issue)
        assert result1 == result2
