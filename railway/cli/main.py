"""Main CLI entry point for Railway Framework."""

from typing import Optional

import typer

from railway import __version__
from railway.cli.init import init
from railway.cli.list import list_components
from railway.cli.new import new
from railway.cli.run import run


def version_callback(value: bool) -> None:
    """Display version and exit."""
    if value:
        typer.echo(f"railway {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="railway",
    help="Railway Framework CLI - Build robust Python automation",
    add_completion=False,
)


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Railway Framework CLI."""
    pass


# Register commands
app.command(name="init")(init)
app.command(name="new")(new)
app.command(name="list")(list_components)
app.command(name="run")(run)


if __name__ == "__main__":
    app()
