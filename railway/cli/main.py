"""Main CLI entry point for Railway Framework."""

import typer

app = typer.Typer(
    name="railway",
    help="Railway Framework CLI - Build robust Python automation",
    add_completion=False,
)


@app.callback()
def main() -> None:
    """Railway Framework CLI."""
    pass


if __name__ == "__main__":
    app()
