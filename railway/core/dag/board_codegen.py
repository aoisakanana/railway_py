"""Board 型自動生成モジュール。

YAML の遷移グラフとノード解析結果から Board 型の Python コードを生成する。
Issue 23-01.

設計原則:
- 純粋関数: 副作用なし、同じ入力に同じ出力
- イミュータブル: 入力データを変更しない
"""
from __future__ import annotations

from railway.core.dag.board_analyzer import NodeAnalysis


def _to_board_class_name(entrypoint: str) -> str:
    """entrypoint を PascalCase + "Board" に変換する（純粋関数）。

    Args:
        entrypoint: エントリーポイント名（例: "alert_workflow"）

    Returns:
        クラス名（例: "AlertWorkflowBoard"）

    Examples:
        >>> _to_board_class_name("alert_workflow")
        'AlertWorkflowBoard'
        >>> _to_board_class_name("alert")
        'AlertBoard'
    """
    pascal = "".join(word.capitalize() for word in entrypoint.split("_"))
    return f"{pascal}Board"


def _infer_field_type(
    field_name: str,
    analyses: dict[str, NodeAnalysis],
) -> tuple[str, str]:
    """フィールド名から型とデフォルト値を推論する（純粋関数）。

    v0.14.0 初期は簡易推論。将来的に AST ベースの型推論に拡張可能。

    Args:
        field_name: フィールド名
        analyses: ノード解析結果の辞書

    Returns:
        (type_str, default_str) のタプル
    """
    # v0.14.0 初期: 全フィールドを Any, None とする
    return ("Any", "None")


def _collect_write_fields(
    analyses: dict[str, NodeAnalysis],
    entry_fields: frozenset[str],
) -> tuple[tuple[str, str, str], ...]:
    """ノード解析から writes フィールドを収集する（純粋関数）。

    entry_fields に含まれるフィールドは除外する。
    フィールドは最初に writes したノード名をコメントとして記録する。

    Args:
        analyses: ノード解析結果の辞書
        entry_fields: エントリーポイントで提供されるフィールド名

    Returns:
        (field_name, node_name, comment) のタプル。field_name でソート済み。
    """
    # field_name -> 最初に writes したノード名
    field_to_node: dict[str, str] = {}

    for node_name in sorted(analyses.keys()):
        analysis = analyses[node_name]
        for field in sorted(analysis.all_writes):
            if field not in entry_fields and field not in field_to_node:
                field_to_node[field] = node_name

    result: list[tuple[str, str, str]] = []
    for field_name in sorted(field_to_node.keys()):
        node_name = field_to_node[field_name]
        comment = f"# {node_name} が writes"
        result.append((field_name, node_name, comment))

    return tuple(result)


def generate_board_type(
    entrypoint: str,
    analyses: dict[str, NodeAnalysis],
    entry_fields: frozenset[str] = frozenset(),
    source_file: str = "",
) -> str:
    """Board 型の Python コードを生成する（純粋関数）。

    Args:
        entrypoint: エントリーポイント名
        analyses: ノード解析結果の辞書
        entry_fields: エントリーポイントで提供されるフィールド名
        source_file: ソース YAML ファイルパス

    Returns:
        生成された Python コード文字列
    """
    class_name = _to_board_class_name(entrypoint)
    write_fields = _collect_write_fields(analyses, entry_fields)

    lines: list[str] = []

    # ヘッダー
    lines.append('"""Board 型定義（自動生成）。')
    lines.append("")
    lines.append("DO NOT EDIT - このファイルは railway sync で生成されます。")
    if source_file:
        lines.append(f"Source: {source_file}")
    lines.append('"""')

    # imports
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append("from typing import Any")
    lines.append("")
    lines.append("from railway.core.board import BoardBase")
    lines.append("")
    lines.append("")

    # クラス定義
    lines.append(f"class {class_name}(BoardBase):")
    lines.append(f'    """{entrypoint} の Board 型（自動生成）。"""')

    has_fields = False

    # entry_fields（必須フィールド、デフォルト値なし）
    if entry_fields:
        lines.append("")
        lines.append("    # entry_point で提供")
        for field_name in sorted(entry_fields):
            lines.append(f"    {field_name}: Any")
            has_fields = True

    # writes フィールド（デフォルト値あり）
    if write_fields:
        # ノードごとにグルーピング
        current_node = ""
        for field_name, node_name, comment in write_fields:
            if node_name != current_node:
                lines.append("")
                lines.append(f"    {comment}")
                current_node = node_name
            type_str, default_str = _infer_field_type(field_name, analyses)
            lines.append(f"    {field_name}: {type_str} = {default_str}")
            has_fields = True

    # フィールドがない場合は pass
    if not has_fields:
        lines.append("    pass")

    # 末尾の改行
    lines.append("")

    return "\n".join(lines)
