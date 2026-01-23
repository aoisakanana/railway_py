"""プレビュー表示機能。

関数型パラダイム:
- 表示フォーマットは純粋関数
- 実際の出力はIO層で行う
"""
from typing import Callable

from railway.migrations.preview_types import (
    ChangePreview,
    PreviewChangeType,
    MigrationPreview,
)


def format_change_type_header(change_type: PreviewChangeType) -> str:
    """変更タイプのヘッダーをフォーマットする純粋関数。"""
    headers = {
        PreviewChangeType.ADD: "[ファイル追加]",
        PreviewChangeType.UPDATE: "[ファイル更新]",
        PreviewChangeType.DELETE: "[ファイル削除]",
        PreviewChangeType.GUIDANCE: "[コード変更ガイダンス（手動対応推奨）]",
    }
    return headers[change_type]


def format_change_symbol(change_type: PreviewChangeType) -> str:
    """変更タイプのシンボルをフォーマットする純粋関数。"""
    symbols = {
        PreviewChangeType.ADD: "+",
        PreviewChangeType.UPDATE: "~",
        PreviewChangeType.DELETE: "-",
        PreviewChangeType.GUIDANCE: "!",
    }
    return symbols[change_type]


def format_change_preview(
    change: ChangePreview,
    verbose: bool = False,
) -> list[str]:
    """個別変更のプレビューをフォーマットする純粋関数。

    Args:
        change: 変更プレビュー
        verbose: 詳細表示

    Returns:
        フォーマット済み行のリスト
    """
    lines: list[str] = []
    symbol = format_change_symbol(change.change_type)

    # メイン行
    diff_str = ""
    if change.line_diff:
        diff_str = f" ({change.line_diff.format()})"
    lines.append(f"   {symbol} {change.path}{diff_str}")

    # 詳細
    if change.change_type == PreviewChangeType.GUIDANCE:
        lines.append(f"     {change.description}")

    if verbose or change.change_type != PreviewChangeType.ADD:
        for detail in change.details:
            lines.append(f"     - {detail}")

    return lines


def format_migration_preview(
    preview: MigrationPreview,
    verbose: bool = False,
) -> list[str]:
    """マイグレーションプレビュー全体をフォーマットする純粋関数。

    Args:
        preview: マイグレーションプレビュー
        verbose: 詳細表示

    Returns:
        フォーマット済み行のリスト
    """
    lines: list[str] = ["", "📋 適用される変更:", ""]

    # タイプごとにグループ化して表示
    for change_type in (
        PreviewChangeType.ADD,
        PreviewChangeType.UPDATE,
        PreviewChangeType.DELETE,
        PreviewChangeType.GUIDANCE,
    ):
        changes = [c for c in preview.changes if c.change_type == change_type]
        if changes:
            lines.append(f"   {format_change_type_header(change_type)}")
            for change in changes:
                lines.extend(format_change_preview(change, verbose))
            lines.append("")

    # 警告
    if preview.warnings:
        lines.append("   ⚠️  警告:")
        for warning in preview.warnings:
            lines.append(f"   - {warning}")
        lines.append("")

    return lines


def display_preview(
    preview: MigrationPreview,
    output: Callable[[str], None],
    verbose: bool = False,
) -> None:
    """プレビューを表示する。

    Args:
        preview: マイグレーションプレビュー
        output: 出力関数（typer.echo など）
        verbose: 詳細表示
    """
    lines = format_migration_preview(preview, verbose)
    for line in lines:
        output(line)
