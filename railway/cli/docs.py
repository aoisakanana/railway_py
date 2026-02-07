"""railway docs command implementation."""

import webbrowser
from pathlib import Path

import typer

PYPI_URL = "https://pypi.org/project/railway-framework/"
GITHUB_URL = "https://github.com/aoisakanana/railway_py"
RAW_README_URL = "https://raw.githubusercontent.com/aoisakanana/railway_py/master/readme.md"


def _find_readme_path() -> Path | None:
    """readme.md のパスを探す（純粋関数）。

    以下の順序で探索:
    1. カレントディレクトリの readme.md
    2. None（見つからない場合）

    Returns:
        readme.md のパス、または None
    """
    # カレントディレクトリ
    cwd_readme = Path.cwd() / "readme.md"
    if cwd_readme.exists():
        return cwd_readme

    return None


def _read_readme_from_package() -> str | None:
    """パッケージに含まれる readme.md を読み込む。

    uv build 時に readme.md がパッケージに含まれる。

    Returns:
        README 内容、または None
    """
    try:
        from importlib import resources

        content_result = resources.files("railway").joinpath("readme.md").read_text(encoding="utf-8")
        if content_result:
            return str(content_result)
        return None
    except Exception:
        return None


def _fetch_readme_from_github() -> str | None:
    """GitHub から README を取得（副作用あり: ネットワークアクセス）。

    Returns:
        README 内容、または None
    """
    try:
        import urllib.request
        with urllib.request.urlopen(RAW_README_URL, timeout=5) as response:
            content: bytes = response.read()
            return content.decode("utf-8")
    except Exception:
        return None


def _get_readme_content() -> str:
    """readme.md の内容を取得。

    以下の順序で取得を試みる:
    1. カレントディレクトリの readme.md
    2. パッケージに含まれる readme.md
    3. GitHub から取得
    4. フォールバック（簡易説明）

    Returns:
        readme.md の内容
    """
    # 1. カレントディレクトリのファイルを探す
    readme_path = _find_readme_path()
    if readme_path:
        try:
            return readme_path.read_text(encoding="utf-8")
        except Exception:
            pass

    # 2. パッケージに含まれる readme.md を読み込む
    package_content = _read_readme_from_package()
    if package_content:
        return package_content

    # 3. GitHub から取得
    github_content = _fetch_readme_from_github()
    if github_content:
        return github_content

    # 4. フォールバック
    return """# Railway Framework

型安全なワークフローで、運用自動化をシンプルに。

詳細: https://pypi.org/project/railway-framework/

README の取得に失敗しました。以下のコマンドでブラウザで確認できます:
  railway docs --browser
"""


def docs(
    browser: bool = typer.Option(
        False, "--browser", "-b", help="Open documentation in browser"
    ),
    readme: bool = typer.Option(
        False, "--readme", "-r", help="Open GitHub README (with --browser)"
    ),
) -> None:
    """
    Display Railway Framework documentation.

    By default, outputs README to terminal.
    Use --browser to open in browser instead.

    Examples:
        railway docs              # README をターミナルに表示
        railway docs --browser    # PyPI をブラウザで開く
        railway docs -b -r        # GitHub README をブラウザで開く
    """
    if browser:
        if readme:
            url = f"{GITHUB_URL}#readme"
        else:
            url = PYPI_URL
        typer.echo(f"Opening {url} ...")
        webbrowser.open(url)
    else:
        content = _get_readme_content()
        typer.echo(content)
