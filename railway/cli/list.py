"""railway list command implementation."""

import ast
from pathlib import Path
from typing import Optional

import typer


def _is_railway_project() -> bool:
    """Check if current directory is a Railway project."""
    return (Path.cwd() / "src").exists()


def _extract_module_docstring(content: str) -> str | None:
    """Extract module docstring from Python code."""
    try:
        tree = ast.parse(content)
        docstring = ast.get_docstring(tree)
        if docstring:
            # Return first line only
            return docstring.split("\n")[0].strip()
        return None
    except Exception:
        return None


def _analyze_entry_file(file_path: Path) -> dict | None:
    """Analyze a Python file for @entry_point decorator."""
    try:
        content = file_path.read_text()

        # Check for @entry_point decorator
        if "@entry_point" not in content:
            return None

        # Get module docstring
        docstring = _extract_module_docstring(content)

        return {
            "name": file_path.stem,
            "path": str(file_path.relative_to(Path.cwd())),
            "description": docstring or "No description",
        }
    except Exception:
        return None


def _analyze_node_file(file_path: Path) -> dict | None:
    """Analyze a Python file for @node decorator."""
    try:
        content = file_path.read_text()

        # Check for @node decorator
        if "@node" not in content:
            return None

        # Get module docstring
        docstring = _extract_module_docstring(content)

        return {
            "name": file_path.stem,
            "path": str(file_path.relative_to(Path.cwd())),
            "description": docstring or "No description",
        }
    except Exception:
        return None


def _find_entries() -> list[dict]:
    """Find all entry points in src/."""
    src_dir = Path.cwd() / "src"
    skip_files = {"__init__.py", "settings.py"}

    def should_analyze(py_file: Path) -> bool:
        return not py_file.name.startswith("_") and py_file.name not in skip_files

    files = [f for f in src_dir.glob("*.py") if should_analyze(f)]
    entries = [_analyze_entry_file(f) for f in files]
    return [e for e in entries if e is not None]


def _find_nodes() -> list[dict]:
    """Find all nodes in src/nodes/."""
    nodes_dir = Path.cwd() / "src" / "nodes"

    if not nodes_dir.exists():
        return []

    def should_analyze(py_file: Path) -> bool:
        return not py_file.name.startswith("_")

    files = [f for f in nodes_dir.glob("*.py") if should_analyze(f)]
    nodes = [_analyze_node_file(f) for f in files]
    return [n for n in nodes if n is not None]


def _count_tests() -> int:
    """Count test files."""
    tests_dir = Path.cwd() / "tests"
    if not tests_dir.exists():
        return 0

    return sum(1 for _ in tests_dir.rglob("test_*.py"))


def _display_entries(entries: list[dict]) -> None:
    """Display entry points."""
    typer.echo("\nEntry Points:")
    if not entries:
        typer.echo("  (none)")
        return

    for entry in entries:
        typer.echo(f"  * {entry['name']:20} {entry['description']}")


def _display_nodes(nodes: list[dict]) -> None:
    """Display nodes."""
    typer.echo("\nNodes:")
    if not nodes:
        typer.echo("  (none)")
        return

    for node in nodes:
        typer.echo(f"  * {node['name']:20} {node['description']}")


def _display_all(entries: list[dict], nodes: list[dict], tests: int) -> None:
    """Display all components."""
    _display_entries(entries)
    _display_nodes(nodes)

    typer.echo(f"\nStatistics:")
    typer.echo(f"  {len(entries)} entry points, {len(nodes)} nodes, {tests} tests")


def list_components(
    filter_type: Optional[str] = typer.Argument(None, help="Filter: entries or nodes"),
) -> None:
    """
    List entry points and nodes in the project.

    Examples:
        railway list           # Show all
        railway list entries   # Show only entry points
        railway list nodes     # Show only nodes
    """
    if not _is_railway_project():
        typer.echo("Error: Not in a Railway project (src/ directory not found)", err=True)
        raise typer.Exit(1)

    entries = _find_entries()
    nodes = _find_nodes()
    tests = _count_tests()

    if filter_type == "entries":
        _display_entries(entries)
    elif filter_type == "nodes":
        _display_nodes(nodes)
    else:
        _display_all(entries, nodes, tests)
