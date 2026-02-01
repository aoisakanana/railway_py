"""railway docs command implementation."""

import webbrowser
from importlib import resources

import typer


PYPI_URL = "https://pypi.org/project/railway-framework/"
GITHUB_URL = "https://github.com/aoisakanana/railway_py"


def _get_readme_content() -> str:
    """readme.md の内容を取得（純粋関数）。

    Returns:
        readme.md の内容
    """
    try:
        # パッケージ内の readme.md を読み込む
        readme_path = resources.files("railway").parent / "readme.md"
        return readme_path.read_text(encoding="utf-8")
    except Exception:
        # フォールバック: 簡易説明
        return """# Railway Framework

型安全なワークフローで、運用自動化をシンプルに。

詳細: https://pypi.org/project/railway-framework/
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
