"""sync スコープ計算モジュール。

Issue 24-03: 解析対象ノードのスコープを計算する。
full / only_node / changed_nodes に応じてスコープを決定する。

設計原則:
- 純粋関数: 副作用なし、同じ入力に同じ出力
- イミュータブル: frozenset で返却
"""
from __future__ import annotations

from railway.core.dag.types import TransitionGraph


def compute_sync_scope(
    graph: TransitionGraph,
    *,
    only_node: str | None = None,
    with_deps: bool = False,
    full: bool = False,
    cached_nodes: frozenset[str] = frozenset(),
    changed_nodes: frozenset[str] = frozenset(),
) -> frozenset[str]:
    """解析対象ノードのスコープを計算する（純粋関数）。

    優先度: full > only_node > changed_nodes > デフォルト（全ノード）

    Args:
        graph: 遷移グラフ
        only_node: 特定ノードのみ解析する場合のノード名
        with_deps: only_node 指定時に上流・下流も含めるか
        full: 全ノードを対象にするか
        cached_nodes: キャッシュ済みノード名（将来用）
        changed_nodes: 変更されたノード名

    Returns:
        解析対象ノード名の frozenset
    """
    # 全 non-exit ノード名
    all_nodes = frozenset(n.name for n in graph.nodes if not n.is_exit)

    if full:
        return all_nodes

    if only_node is not None:
        if with_deps:
            deps = _compute_dependent_nodes(graph, only_node)
            return frozenset({only_node}) | deps
        return frozenset({only_node})

    if changed_nodes:
        return changed_nodes & all_nodes

    return all_nodes


def _compute_dependent_nodes(
    graph: TransitionGraph,
    node_name: str,
) -> frozenset[str]:
    """指定ノードの上流・下流ノードを取得する（純粋関数）。

    Args:
        graph: 遷移グラフ
        node_name: 対象ノード名

    Returns:
        上流・下流ノード名の frozenset（exit ノードは除外）
    """
    deps: set[str] = set()

    for t in graph.transitions:
        if t.from_node == node_name and not t.is_exit:
            deps.add(t.to_target)
        if t.to_target == node_name:
            deps.add(t.from_node)

    return frozenset(deps)
