"""CLI用互換性チェック機能。

関数型パラダイム:
- 純粋なロジックは version_checker モジュールに分離
- このモジュールはIO/UIとの統合のみ担当
"""
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import TypeVar

import typer

from railway import __version__
from railway.core.project_discovery import find_project_root
from railway.core.project_metadata import load_metadata
from railway.core.version_checker import (
    check_compatibility,
    format_compatibility_error,
    format_compatibility_warning,
)

F = TypeVar("F", bound=Callable)


def check_project_compatibility(
    project_path: Path | None = None,
) -> None:
    """プロジェクトの互換性をチェックし、必要に応じてユーザーに確認する。

    Args:
        project_path: プロジェクトパス（省略時は自動検出）

    Raises:
        typer.Exit: 互換性エラーまたはユーザー中止時
    """
    path = project_path or find_project_root()
    if path is None:
        return  # プロジェクト外では何もしない

    metadata = load_metadata(path)
    project_version = metadata.railway.version if metadata else None

    result = check_compatibility(project_version, __version__)

    if result.is_compatible:
        return

    if result.is_blocked:
        typer.echo(format_compatibility_error(result), err=True)
        raise typer.Exit(1)

    # 確認が必要な場合
    typer.echo(format_compatibility_warning(result))

    choice = typer.prompt(
        "\n[c] 続行 / [u] 'railway update' を実行 / [a] 中止",
        default="a",
    )

    match choice.lower():
        case "c":
            return
        case "u":
            typer.echo("'railway update' を実行してください。")
            raise typer.Exit(0)
        case _:
            typer.echo("中止しました。")
            raise typer.Exit(0)


def require_compatible_project(func: F) -> F:
    """コマンド実行前に互換性チェックを行うデコレータ。

    Args:
        func: デコレート対象の関数

    Returns:
        ラップされた関数
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # --force オプションがあればスキップ
        if kwargs.get("force", False):
            return func(*args, **kwargs)

        check_project_compatibility()
        return func(*args, **kwargs)

    return wrapper  # type: ignore
