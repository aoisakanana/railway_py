"""プロジェクト検出機能。

関数型パラダイム:
- 純粋関数によるパス探索
- 副作用なし（ファイルシステムの読み取りのみ）
"""
from pathlib import Path
from typing import Optional


def find_project_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """Railwayプロジェクトのルートディレクトリを探す。

    以下のマーカーを探索:
    1. .railway/ ディレクトリ
    2. src/ と pyproject.toml の組み合わせ

    Args:
        start_path: 探索開始パス（省略時はカレントディレクトリ）

    Returns:
        プロジェクトルートパス、見つからない場合はNone
    """
    current = (start_path or Path.cwd()).resolve()

    for path in [current, *current.parents]:
        # .railway/ ディレクトリがあれば確実
        if (path / ".railway").is_dir():
            return path
        # src/ と pyproject.toml があれば候補
        if (path / "src").is_dir() and (path / "pyproject.toml").exists():
            return path

    return None


def is_railway_project(path: Path) -> bool:
    """指定パスがRailwayプロジェクトかどうかを判定する。

    Args:
        path: 確認するパス

    Returns:
        Railwayプロジェクトの場合True
    """
    return (
        (path / ".railway").is_dir()
        or ((path / "src").is_dir() and (path / "pyproject.toml").exists())
    )
