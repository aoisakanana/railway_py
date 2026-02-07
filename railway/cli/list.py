"""railway list command implementation."""

import ast
from pathlib import Path

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


def _analyze_contract_file(file_path: Path) -> list[dict]:
    """Analyze a Python file for Contract/Params classes."""
    results = []
    try:
        content = file_path.read_text()
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if class inherits from Contract or Params
                for base in node.bases:
                    base_name = ""
                    if isinstance(base, ast.Name):
                        base_name = base.id
                    elif isinstance(base, ast.Attribute):
                        base_name = base.attr

                    if base_name in ("Contract", "Params"):
                        docstring = ast.get_docstring(node)
                        results.append({
                            "name": node.name,
                            "path": str(file_path.relative_to(Path.cwd())),
                            "type": base_name,
                            "description": (docstring.split("\n")[0].strip() if docstring else "No description"),
                        })
                        break

        return results
    except Exception:
        return []


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


def _find_contracts() -> tuple[list[dict], list[dict]]:
    """Find all contracts in src/contracts/.

    Returns:
        Tuple of (contracts, params) lists.
    """
    contracts_dir = Path.cwd() / "src" / "contracts"

    if not contracts_dir.exists():
        return [], []

    contracts = []
    params = []

    for py_file in contracts_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue

        for info in _analyze_contract_file(py_file):
            if info["type"] == "Params":
                params.append(info)
            else:
                contracts.append(info)

    return contracts, params


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


def _display_contracts(contracts: list[dict], params: list[dict]) -> None:
    """Display contracts and params."""
    typer.echo("\nContracts:")
    if not contracts:
        typer.echo("  (none)")
    else:
        for contract in contracts:
            typer.echo(f"  * {contract['name']:25} {contract['path']}")

    typer.echo("\nParams:")
    if not params:
        typer.echo("  (none)")
    else:
        for param in params:
            typer.echo(f"  * {param['name']:25} {param['path']}")


def _display_all(entries: list[dict], nodes: list[dict], tests: int) -> None:
    """Display all components."""
    _display_entries(entries)
    _display_nodes(nodes)

    typer.echo("\nStatistics:")
    typer.echo(f"  {len(entries)} entry points, {len(nodes)} nodes, {tests} tests")


def list_components(
    filter_type: str | None = typer.Argument(None, help="Filter: entries, nodes, or contracts"),
) -> None:
    """
    List entry points, nodes, and contracts in the project.

    Examples:
        railway list           # Show all
        railway list entries   # Show only entry points
        railway list nodes     # Show only nodes
        railway list contracts # Show only contracts
    """
    if filter_type == "contracts":
        # For contracts, we don't require src/ (might list from registry)
        contracts, params = _find_contracts()
        _display_contracts(contracts, params)
        return

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
