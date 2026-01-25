"""railway run command implementation."""

import runpy
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


def _setup_src_path(project_root: Path) -> None:
    """Add src/ directory to sys.path for imports.

    This enables importing modules within src/ without the 'src.' prefix.
    For example: `from contracts.my_contract import MyContract`
    instead of: `from src.contracts.my_contract import MyContract`

    Args:
        project_root: Path to the project root directory

    Side effects:
        Modifies sys.path by inserting src/ at the beginning
    """
    src_path = str((project_root / "src").resolve())

    if src_path not in sys.path:
        sys.path.insert(0, src_path)


def _resolve_module_path(entrypoint: str) -> str:
    """Resolve module path from entrypoint name.

    This is a pure function that normalizes entrypoint names.

    Args:
        entrypoint: Entrypoint name (e.g., "my_workflow" or "workflows.daily")

    Returns:
        Normalized module path for import
    """
    # Remove .py extension if present
    if entrypoint.endswith(".py"):
        entrypoint = entrypoint[:-3]

    # Remove src. prefix if present (for backwards compatibility)
    if entrypoint.startswith("src."):
        entrypoint = entrypoint[4:]

    return entrypoint


def _execute_entry(project_root: Path, entry_name: str, extra_args: List[str]) -> None:
    """Execute the entry point."""
    # Add src/ to sys.path for imports (enables 'from contracts.x import y')
    _setup_src_path(project_root)

    # Also add project root for backwards compatibility
    project_path = str(project_root)
    if project_path not in sys.path:
        sys.path.insert(0, project_path)

    entry_path = project_root / "src" / f"{entry_name}.py"

    # Set sys.argv for the entry point
    original_argv = sys.argv
    sys.argv = [str(entry_path)] + list(extra_args or [])

    try:
        runpy.run_path(str(entry_path), run_name="__main__")
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

    This is a simpler alternative to 'uv run python -m entry_name'.

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

    # Resolve module path (handles .py extension and src. prefix)
    resolved_name = _resolve_module_path(entry_name)

    # Check entry exists
    entry_path = project_root / "src" / f"{resolved_name}.py"
    if not entry_path.exists():
        typer.echo(f"Error: Entry point '{resolved_name}' not found at {entry_path}", err=True)
        typer.echo("\nAvailable entries:", err=True)
        entries = _list_entries(project_root)
        for entry in entries:
            typer.echo(f"  • {entry}", err=True)
        raise typer.Exit(1)

    # Run the entry
    typer.echo(f"Running entry point: {resolved_name}")

    try:
        _execute_entry(project_root, resolved_name, extra_args or [])
    except Exception as e:
        typer.echo(f"Error: Failed to run entry: {e}", err=True)
        raise typer.Exit(1)
