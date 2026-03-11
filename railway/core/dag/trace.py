"""Trace モジュール: ノード実行のミューテーション追跡。

Board mode のワークフロー実行時に、各ノードがどのフィールドを変更したかを追跡する。
すべての関数は純粋関数として設計されている。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NodeTrace:
    """ノード実行のトレース情報。"""

    node_name: str
    before: dict[str, Any]
    after: dict[str, Any]
    outcome: str
    mutations: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowTrace:
    """ワークフロー全体のトレース。"""

    traces: tuple[NodeTrace, ...]
    initial_fields: tuple[str, ...]
    execution_path: tuple[str, ...]


def compute_mutations(
    before: dict[str, Any], after: dict[str, Any]
) -> tuple[str, ...]:
    """before/after のスナップショットから変更されたフィールドを検出する（純粋関数）。

    Returns:
        変更されたフィールド名のソート済みタプル
    """
    changed: list[str] = []
    all_keys = sorted(set(before.keys()) | set(after.keys()))
    for key in all_keys:
        if key not in before:
            changed.append(key)  # 新規追加
        elif key not in after:
            changed.append(key)  # 削除
        elif before[key] != after[key]:
            changed.append(key)  # 変更
    return tuple(changed)


def should_trace(
    cli_flag: bool | None = None,
    env_value: str | None = None,
) -> bool:
    """トレースすべきか判定する（純粋関数）。

    優先度: CLI フラグ > 環境変数
    """
    if cli_flag is not None:
        return cli_flag
    if env_value is not None:
        return env_value.lower() in ("1", "true", "yes")
    return False
