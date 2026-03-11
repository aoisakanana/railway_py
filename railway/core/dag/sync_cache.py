"""sync キャッシュモジュール: 差分解析用。

Issue 24-02: ノードファイルのハッシュ比較で変更検出し、
変更されたノードのみ再解析する差分解析を実現する。

設計原則:
- 純粋関数: 副作用なし、同じ入力に同じ出力
- イミュータブル: frozenset で返却
"""
from __future__ import annotations

import hashlib
import json

from railway.core.dag.board_analyzer import (
    AnalysisViolation,
    BranchWrites,
    NodeAnalysis,
)


def compute_file_hash(content: str) -> str:
    """ファイル内容の SHA256 ハッシュを計算する（純粋関数）。

    Args:
        content: ファイル内容

    Returns:
        SHA256 ハッシュ文字列
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def detect_changed_nodes(
    current_hashes: dict[str, str],
    cached_hashes: dict[str, str],
) -> frozenset[str]:
    """変更されたノードを検出する（純粋関数）。

    新規追加・ハッシュ変更・削除のすべてを「変更あり」として返す。

    Args:
        current_hashes: 現在のノード名 → ハッシュ
        cached_hashes: キャッシュされたノード名 → ハッシュ

    Returns:
        変更されたノード名の frozenset
    """
    changed: set[str] = set()

    # 新規追加 or 変更
    for name, hash_val in current_hashes.items():
        if name not in cached_hashes or cached_hashes[name] != hash_val:
            changed.add(name)

    # 削除
    for name in cached_hashes:
        if name not in current_hashes:
            changed.add(name)

    return frozenset(changed)


def serialize_analysis(analysis: NodeAnalysis) -> str:
    """NodeAnalysis を JSON 文字列にシリアライズする（純粋関数）。

    Args:
        analysis: ノード解析結果

    Returns:
        JSON 文字列
    """
    data = {
        "node_name": analysis.node_name,
        "file_path": analysis.file_path,
        "reads_required": sorted(analysis.reads_required),
        "reads_optional": sorted(analysis.reads_optional),
        "branch_writes": [
            {"outcome": bw.outcome, "writes": sorted(bw.writes)}
            for bw in analysis.branch_writes
        ],
        "all_writes": sorted(analysis.all_writes),
        "outcomes": list(analysis.outcomes),
        "violations": [
            {
                "code": v.code,
                "message": v.message,
                "line": v.line,
                "file_path": v.file_path,
            }
            for v in analysis.violations
        ],
    }
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def deserialize_analysis(json_str: str) -> NodeAnalysis:
    """JSON 文字列から NodeAnalysis を復元する（純粋関数）。

    Args:
        json_str: JSON 文字列

    Returns:
        復元された NodeAnalysis
    """
    data = json.loads(json_str)
    return NodeAnalysis(
        node_name=data["node_name"],
        file_path=data["file_path"],
        reads_required=frozenset(data["reads_required"]),
        reads_optional=frozenset(data["reads_optional"]),
        branch_writes=tuple(
            BranchWrites(outcome=bw["outcome"], writes=frozenset(bw["writes"]))
            for bw in data["branch_writes"]
        ),
        all_writes=frozenset(data["all_writes"]),
        outcomes=tuple(data["outcomes"]),
        violations=tuple(
            AnalysisViolation(
                code=v["code"],
                message=v["message"],
                line=v["line"],
                file_path=v["file_path"],
            )
            for v in data["violations"]
        ),
    )
