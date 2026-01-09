"""railway run command implementation."""

import importlib.util
import sys
from pathlib import Path
from typing import List, Optional

import typer


def _find_project_root() -> Optional[Path]:
    """Find project root by looking for src/ directory."""
    current = Path.cwd()

    # Check current directory
    if (current / "src").exists():
        return current

    # Check parent directories
    for parent in current.parents:
        if (parent / "src").exists():
            return parent
        # Stop at markers
        if (parent / "pyproject.toml").exists():
            if (parent / "src").exists():
                return parent
            break

    return None


def _list_entries(project_root: Path) -> List[str]:
    """List available entries."""
    src_dir = project_root / "src"
    entries = []
    skip_files = {"__init__.py", "settings.py"}

    for py_file in src_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        if py_file.name in skip_files:
            continue
        entries.append(py_file.stem)

    return entries


def _execute_entry(project_root: Path, entry_name: str, extra_args: List[str]) -> None:
    """Execute the entry point."""
    # Add project root to sys.path
    src_path = str(project_root)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    # Load the module
    entry_path = project_root / "src" / f"{entry_name}.py"
    spec = importlib.util.spec_from_file_location(f"src.{entry_name}", entry_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module: {entry_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[f"src.{entry_name}"] = module

    # Set sys.argv for the entry point
    original_argv = sys.argv
    sys.argv = [str(entry_path)] + list(extra_args or [])

    try:
        spec.loader.exec_module(module)

        # If module has main function, it may have been called via __name__ == "__main__"
        # If not, try to call it explicitly
        if hasattr(module, "main") and callable(module.main):
            # Check if main was already called
            pass  # Usually __main__ block handles this
    finally:
        sys.argv = original_argv


def run(
    entry_name: str = typer.Argument(..., help="Name of the entry point to run"),
    project: Optional[str] = typer.Option(
        None, "--project", "-p",
        help="Path to the project root"
    ),
    extra_args: Optional[List[str]] = typer.Argument(None, help="Arguments to pass to entry"),
) -> None:
    """
    Run an entry point.

    This is a simpler alternative to 'uv run python -m src.entry_name'.

    Examples:
        railway run daily_report
        railway run daily_report -- --date 2024-01-01
        railway run --project /path/to/project my_entry
    """
    # Determine project root
    if project:
        project_root = Path(project).resolve()
    else:
        project_root = _find_project_root()

    if project_root is None:
        typer.echo("Error: Not in a Railway project (src/ directory not found)", err=True)
        typer.echo("Use --project to specify the project root", err=True)
        raise typer.Exit(1)

    # Check entry exists
    entry_path = project_root / "src" / f"{entry_name}.py"
    if not entry_path.exists():
        typer.echo(f"Error: Entry point '{entry_name}' not found at {entry_path}", err=True)
        typer.echo("\nAvailable entries:", err=True)
        entries = _list_entries(project_root)
        for entry in entries:
            typer.echo(f"  • {entry}", err=True)
        raise typer.Exit(1)

    # Run the entry
    typer.echo(f"Running entry point: {entry_name}")

    try:
        _execute_entry(project_root, entry_name, extra_args or [])
    except Exception as e:
        typer.echo(f"Error: Failed to run entry: {e}", err=True)
        raise typer.Exit(1)
