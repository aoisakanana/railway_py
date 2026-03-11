"""DAG 経路ごとのフィールド依存検証エンジン。

Issue 21: Board パターンの NodeAnalysis を使って、
遷移グラフの各辺でフィールド依存を検証する純粋関数群。

検出するもの:
- E010: 遷移辺で必須フィールドが不足（エラー）
- W001: writes したフィールドを後続ノードが reads しない（警告）
- I001: 合流地点で optional フィールドが一部経路からのみ提供（情報）

設計原則:
- 純粋関数: 副作用なし、同じ入力に同じ出力
- イミュータブル: frozen=True の dataclass
- tuple 優先: 変更可能な list より tuple を使用
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from railway.core.dag.board_analyzer import NodeAnalysis
from railway.core.dag.types import StateTransition, TransitionGraph

# =========== Result Types ===========


@dataclass(frozen=True)
class PathIssue:
    """経路検証で検出された問題。

    Attributes:
        code: 問題コード（E010, W001, W002, I001）
        severity: 重要度
        message: 説明メッセージ
        node_name: 対象ノード名
        field_name: 対象フィールド名
        file_path: ファイルパス
        line: 行番号
    """

    code: str
    severity: Literal["error", "warning", "info"]
    message: str
    node_name: str
    field_name: str
    file_path: str
    line: int


@dataclass(frozen=True)
class PathValidationResult:
    """経路検証の結果。

    Attributes:
        issues: 検出された問題のタプル
        node_analyses: ノード名 → NodeAnalysis のマッピング
    """

    issues: tuple[PathIssue, ...]
    node_analyses: dict[str, NodeAnalysis]

    @property
    def has_errors(self) -> bool:
        """エラー（E*）が存在するか。"""
        return any(i.severity == "error" for i in self.issues)

    @property
    def errors(self) -> tuple[PathIssue, ...]:
        """エラー（E*）のみ。"""
        return tuple(i for i in self.issues if i.severity == "error")

    @property
    def warnings(self) -> tuple[PathIssue, ...]:
        """警告（W*）のみ。"""
        return tuple(i for i in self.issues if i.severity == "warning")

    @property
    def infos(self) -> tuple[PathIssue, ...]:
        """情報（I*）のみ。"""
        return tuple(i for i in self.issues if i.severity == "info")


# =========== Public API ===========


def validate_paths(
    graph: TransitionGraph,
    analyses: dict[str, NodeAnalysis],
    entry_fields: frozenset[str] = frozenset(),
) -> PathValidationResult:
    """DAG 経路ごとにフィールド依存を検証する。

    純粋関数。副作用なし。

    Args:
        graph: 遷移グラフ
        analyses: ノード名 → NodeAnalysis のマッピング
        entry_fields: エントリーポイントで提供されるフィールド

    Returns:
        PathValidationResult
    """
    issues: list[PathIssue] = []

    # 各ノードへの入力辺を収集（合流地点検出用）
    incoming_edges = _collect_incoming_edges(graph)

    # 各ノード到達時の利用可能フィールドを辺ごとに計算
    edge_available = _compute_edge_available_fields(graph, analyses, entry_fields)

    # E010: 遷移辺ごとに必須フィールド不足を検出
    issues.extend(_check_e010(graph, analyses, entry_fields, edge_available))

    # W001: 未使用 writes を検出
    issues.extend(_check_w001(graph, analyses))

    # I001: 合流地点の設計改善提案
    issues.extend(_check_i001(graph, analyses, incoming_edges, edge_available))

    return PathValidationResult(
        issues=tuple(issues),
        node_analyses=dict(analyses),
    )


# =========== Internal: Edge Available Fields ===========


def _collect_incoming_edges(
    graph: TransitionGraph,
) -> dict[str, tuple[StateTransition, ...]]:
    """各ノードへの入力辺を収集する。

    Args:
        graph: 遷移グラフ

    Returns:
        ノード名 → そのノードへの遷移辺のタプル
    """
    incoming: dict[str, list[StateTransition]] = {}
    for t in graph.transitions:
        if not t.is_exit:
            incoming.setdefault(t.to_target, []).append(t)
    return {k: tuple(v) for k, v in incoming.items()}


def _compute_edge_available_fields(
    graph: TransitionGraph,
    analyses: dict[str, NodeAnalysis],
    entry_fields: frozenset[str],
) -> dict[str, frozenset[str]]:
    """各遷移辺ごとの、遷移先ノード到達時の利用可能フィールドを計算する。

    キーは "from_node::from_state" 形式の文字列。
    値は遷移先ノード到達時に利用可能なフィールドの集合。

    アルゴリズム:
    - start_node は entry_fields からスタート
    - 各ノードからの遷移辺について、そのノード到達時の available + branch_writes を計算
    - BFS で全辺をカバー

    Args:
        graph: 遷移グラフ
        analyses: ノード名 → NodeAnalysis
        entry_fields: エントリーポイントで提供されるフィールド

    Returns:
        辺キー → 利用可能フィールド
    """
    # ノード到達時の利用可能フィールド（全入力辺の交差ではなく、辺ごとに計算）
    node_available: dict[str, frozenset[str]] = {
        graph.start_node: entry_fields,
    }
    edge_available: dict[str, frozenset[str]] = {}

    # BFS で辺を走査
    visited_edges: set[str] = set()
    queue: list[str] = [graph.start_node]
    visited_nodes: set[str] = set()

    while queue:
        current_node = queue.pop(0)
        if current_node in visited_nodes:
            continue
        visited_nodes.add(current_node)

        current_available = node_available.get(current_node, frozenset())
        analysis = analyses.get(current_node)

        # このノードからの遷移辺を処理
        for t in graph.transitions:
            if t.from_node != current_node:
                continue

            edge_key = f"{t.from_node}::{t.from_state}"
            if edge_key in visited_edges:
                continue
            visited_edges.add(edge_key)

            # from_state に対応する branch_writes を探す
            branch_writes = _get_branch_writes_for_state(analysis, t.from_state)

            # 利用可能フィールド = 到達時 + この分岐の writes
            available_after = current_available | branch_writes
            edge_available[edge_key] = available_after

            # 遷移先ノードの available を更新（既存があれば和集合）
            if not t.is_exit:
                target = t.to_target
                if target in node_available:
                    # 複数辺からの合流: 各辺ごとの available は edge_available で管理
                    # node_available は「最初に到達した辺」を基準にする
                    # （I001 検出では edge_available を使う）
                    pass
                else:
                    node_available[target] = available_after
                    queue.append(target)

    return edge_available


def _get_branch_writes_for_state(
    analysis: NodeAnalysis | None,
    from_state: str,
) -> frozenset[str]:
    """指定された from_state に対応する branch_writes を取得する。

    from_state 形式: "success::done"
    branch_writes の outcome 形式: "success::done"

    完全一致で検索し、見つからなければ all_writes にフォールバック。

    Args:
        analysis: ノード解析結果（None の場合は空集合を返す）
        from_state: 遷移元の状態

    Returns:
        書き込まれるフィールドの集合
    """
    if analysis is None:
        return frozenset()

    for bw in analysis.branch_writes:
        if bw.outcome == from_state:
            return bw.writes

    # branch_writes に from_state が見つからない場合は all_writes を使用
    return analysis.all_writes


# =========== Internal: E010 Check ===========


def _check_e010(
    graph: TransitionGraph,
    analyses: dict[str, NodeAnalysis],
    entry_fields: frozenset[str],
    edge_available: dict[str, frozenset[str]],
) -> tuple[PathIssue, ...]:
    """E010: 遷移辺で必須フィールドが不足しているケースを検出する。

    Args:
        graph: 遷移グラフ
        analyses: ノード名 → NodeAnalysis
        entry_fields: エントリーポイントで提供されるフィールド
        edge_available: 辺キー → 利用可能フィールド

    Returns:
        E010 PathIssue のタプル
    """
    issues: list[PathIssue] = []

    # 開始ノード自体の依存チェック
    start_analysis = analyses.get(graph.start_node)
    if start_analysis is not None:
        missing = start_analysis.reads_required - entry_fields
        for field in sorted(missing):
            issues.append(
                PathIssue(
                    code="E010",
                    severity="error",
                    message=(
                        f"ノード '{graph.start_node}' の必須フィールド '{field}' が "
                        f"entry_fields に含まれていません"
                    ),
                    node_name=graph.start_node,
                    field_name=field,
                    file_path=start_analysis.file_path,
                    line=0,
                ),
            )

    # 各遷移辺について検証
    for t in graph.transitions:
        if t.is_exit:
            continue

        target_analysis = analyses.get(t.to_target)
        if target_analysis is None:
            continue

        edge_key = f"{t.from_node}::{t.from_state}"
        available = edge_available.get(edge_key, frozenset())

        missing_required = target_analysis.reads_required - available
        for field in sorted(missing_required):
            issues.append(
                PathIssue(
                    code="E010",
                    severity="error",
                    message=(
                        f"遷移 '{t.from_node} --{t.from_state}--> {t.to_target}' で "
                        f"必須フィールド '{field}' が不足しています"
                    ),
                    node_name=t.to_target,
                    field_name=field,
                    file_path=target_analysis.file_path,
                    line=0,
                ),
            )

    return tuple(issues)


# =========== Internal: W001 Check ===========


def _check_w001(
    graph: TransitionGraph,
    analyses: dict[str, NodeAnalysis],
) -> tuple[PathIssue, ...]:
    """W001: writes したフィールドを後続のどのノードも reads しない。

    Args:
        graph: 遷移グラフ
        analyses: ノード名 → NodeAnalysis

    Returns:
        W001 PathIssue のタプル
    """
    issues: list[PathIssue] = []

    # 各ノードの all_writes について、後続ノード（直接・間接）の reads に含まれるか
    for node_name, analysis in analyses.items():
        if not analysis.all_writes:
            continue

        # このノードから到達可能な後続ノードの reads_all を収集
        downstream_reads = _collect_downstream_reads(node_name, graph, analyses)

        for field in sorted(analysis.all_writes):
            if field not in downstream_reads:
                issues.append(
                    PathIssue(
                        code="W001",
                        severity="warning",
                        message=(
                            f"ノード '{node_name}' が書き込む '{field}' は "
                            f"後続のどのノードも読み取りません"
                        ),
                        node_name=node_name,
                        field_name=field,
                        file_path=analysis.file_path,
                        line=0,
                    ),
                )

    return tuple(issues)


def _collect_downstream_reads(
    start_node: str,
    graph: TransitionGraph,
    analyses: dict[str, NodeAnalysis],
) -> frozenset[str]:
    """指定ノードから到達可能な全後続ノードの reads_all を収集する。

    Args:
        start_node: 起点ノード名
        graph: 遷移グラフ
        analyses: ノード名 → NodeAnalysis

    Returns:
        後続ノードの全 reads フィールド
    """
    reads: set[str] = set()
    visited: set[str] = set()
    queue: list[str] = []

    # start_node の直接遷移先から開始
    for t in graph.transitions:
        if t.from_node == start_node and not t.is_exit:
            if t.to_target not in visited:
                queue.append(t.to_target)
                visited.add(t.to_target)

    while queue:
        current = queue.pop(0)
        analysis = analyses.get(current)
        if analysis is not None:
            reads.update(analysis.reads_all)

        for t in graph.transitions:
            if t.from_node == current and not t.is_exit:
                if t.to_target not in visited:
                    queue.append(t.to_target)
                    visited.add(t.to_target)

    return frozenset(reads)


# =========== Internal: I001 Check ===========


def _check_i001(
    graph: TransitionGraph,
    analyses: dict[str, NodeAnalysis],
    incoming_edges: dict[str, tuple[StateTransition, ...]],
    edge_available: dict[str, frozenset[str]],
) -> tuple[PathIssue, ...]:
    """I001: 合流地点で optional フィールドが一部経路からのみ提供される。

    条件:
    1. ノードに reads_optional が存在
    2. そのノードへの遷移辺が2つ以上（合流地点）
    3. optional フィールドが一部入力経路からのみ提供される

    Args:
        graph: 遷移グラフ
        analyses: ノード名 → NodeAnalysis
        incoming_edges: ノード名 → 入力辺のタプル
        edge_available: 辺キー → 利用可能フィールド

    Returns:
        I001 PathIssue のタプル
    """
    issues: list[PathIssue] = []

    for node_name, edges in incoming_edges.items():
        # 条件 2: 合流地点（入力辺が2つ以上）
        if len(edges) < 2:
            continue

        analysis = analyses.get(node_name)
        if analysis is None:
            continue

        # 条件 1: reads_optional が存在
        if not analysis.reads_optional:
            continue

        # 各入力辺の available fields を収集
        edge_fields: list[frozenset[str]] = []
        for edge in edges:
            edge_key = f"{edge.from_node}::{edge.from_state}"
            available = edge_available.get(edge_key, frozenset())
            edge_fields.append(available)

        # 条件 3: optional フィールドが一部経路からのみ提供
        for field in sorted(analysis.reads_optional):
            paths_providing = sum(1 for ef in edge_fields if field in ef)
            if 0 < paths_providing < len(edge_fields):
                issues.append(
                    PathIssue(
                        code="I001",
                        severity="info",
                        message=(
                            f"ノード '{node_name}' の optional フィールド '{field}' は "
                            f"{len(edge_fields)}本の入力経路のうち{paths_providing}本でのみ提供されます。"
                            f"Outcome を分離して依存を明確化することを検討してください"
                        ),
                        node_name=node_name,
                        field_name=field,
                        file_path=analysis.file_path,
                        line=0,
                    ),
                )

    return tuple(issues)
