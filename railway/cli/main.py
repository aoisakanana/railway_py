"""Main CLI entry point for Railway Framework."""


import typer

from railway import __version__
from railway.cli.backup import app as backup_app
from railway.cli.docs import docs
from railway.cli.init import init
from railway.cli.list import list_components
from railway.cli.new import new
from railway.cli.run import run
from railway.cli.show import show
from railway.cli.sync import app as sync_app
from railway.cli.update import app as update_app


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
    version: bool | None = typer.Option(
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
app.command(name="docs")(docs)
app.command(name="show")(show)
app.add_typer(update_app, name="update")
app.add_typer(backup_app, name="backup")
app.add_typer(sync_app, name="sync")


if __name__ == "__main__":
    app()
