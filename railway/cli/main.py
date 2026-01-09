"""Main CLI entry point for Railway Framework."""

import typer

from railway.cli.init import init
from railway.cli.list import list_components
from railway.cli.new import new
from railway.cli.run import run

app = typer.Typer(
    name="railway",
    help="Railway Framework CLI - Build robust Python automation",
    add_completion=False,
)


@app.callback()
def main() -> None:
    """Railway Framework CLI."""
    pass


# Register commands
app.command(name="init")(init)
app.command(name="new")(new)
app.command(name="list")(list_components)
app.command(name="run")(run)


if __name__ == "__main__":
    app()
