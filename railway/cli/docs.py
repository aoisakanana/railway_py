"""railway docs command implementation."""

import webbrowser

import typer


PYPI_URL = "https://pypi.org/project/railway-framework/"
GITHUB_URL = "https://github.com/aoisakanana/railway_py"


def docs(
    readme: bool = typer.Option(
        False, "--readme", "-r", help="Open GitHub README instead of PyPI"
    ),
) -> None:
    """
    Open Railway Framework documentation in browser.

    By default, opens the PyPI package page.
    Use --readme to open the GitHub README.

    Examples:
        railway docs
        railway docs --readme
    """
    if readme:
        url = f"{GITHUB_URL}#readme"
    else:
        url = PYPI_URL

    typer.echo(f"Opening {url} ...")
    webbrowser.open(url)
