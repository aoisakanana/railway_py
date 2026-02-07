"""railway show command implementation."""

import ast
from pathlib import Path
from typing import Any

import typer


def _is_railway_project() -> bool:
    """Check if current directory is a Railway project."""
    return (Path.cwd() / "src").exists()


def _extract_node_info(file_path: Path) -> dict[str, Any] | None:
    """Extract node information from a Python file."""
    try:
        content = file_path.read_text()
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if function has @node decorator
                for decorator in node.decorator_list:
                    is_node = False
                    decorator_args: dict[str, Any] = {}

                    if isinstance(decorator, ast.Name) and decorator.id == "node":
                        is_node = True
                    elif isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Name) and decorator.func.id == "node":
                            is_node = True
                            # Extract keyword arguments
                            for kw in decorator.keywords:
                                if kw.arg == "output":
                                    if isinstance(kw.value, ast.Name):
                                        decorator_args["output"] = kw.value.id
                                elif kw.arg == "inputs":
                                    if isinstance(kw.value, ast.Dict):
                                        inputs: dict[str, str] = {}
                                        for k, v in zip(kw.value.keys, kw.value.values):
                                            if isinstance(k, ast.Constant) and isinstance(v, ast.Name):
                                                inputs[str(k.value)] = v.id
                                        decorator_args["inputs"] = inputs

                    if is_node:
                        # Get docstring
                        docstring = ast.get_docstring(node)

                        # Get return annotation
                        return_type = None
                        if node.returns:
                            if isinstance(node.returns, ast.Name):
                                return_type = node.returns.id

                        # Get function arguments
                        args = []
                        for arg in node.args.args:
                            arg_info = {"name": arg.arg}
                            if arg.annotation:
                                if isinstance(arg.annotation, ast.Name):
                                    arg_info["type"] = arg.annotation.id
                            args.append(arg_info)

                        return {
                            "name": node.name,
                            "path": str(file_path),
                            "docstring": docstring,
                            "return_type": return_type,
                            "args": args,
                            "inputs": decorator_args.get("inputs", {}),
                            "output": decorator_args.get("output"),
                        }

        return None
    except Exception:
        return None


def _find_node(name: str) -> dict[str, Any] | None:
    """Find a node by name in src/nodes/."""
    nodes_dir = Path.cwd() / "src" / "nodes"

    if not nodes_dir.exists():
        return None

    node_file = nodes_dir / f"{name}.py"
    if node_file.exists():
        return _extract_node_info(node_file)

    return None


def _display_node_info(info: dict[str, Any]) -> None:
    """Display node information."""
    typer.echo(f"\nNode: {info['name']}")
    typer.echo(f"File: {info['path']}")

    if info.get("docstring"):
        typer.echo("\nDescription:")
        typer.echo(f"  {info['docstring'].split(chr(10))[0]}")

    # Display inputs
    typer.echo("\nInputs:")
    if info.get("inputs"):
        for param_name, type_name in info["inputs"].items():
            typer.echo(f"  {param_name}: {type_name}")
    elif info.get("args"):
        for arg in info["args"]:
            type_str = arg.get("type", "Any")
            typer.echo(f"  {arg['name']}: {type_str}")
    else:
        typer.echo("  (none)")

    # Display output
    typer.echo("\nOutput:")
    output = info.get("output") or info.get("return_type")
    if output:
        typer.echo(f"  {output}")
    else:
        typer.echo("  (untyped)")


def show(
    component_type: str = typer.Argument(..., help="Component type: node"),
    name: str = typer.Argument(..., help="Name of the component"),
) -> None:
    """
    Show detailed information about a component.

    Examples:
        railway show node fetch_users
        railway show node generate_report
    """
    if not _is_railway_project():
        typer.echo("Error: Not in a Railway project (src/ directory not found)", err=True)
        raise typer.Exit(1)

    if component_type == "node":
        info = _find_node(name)
        if info:
            _display_node_info(info)
        else:
            typer.echo(f"Error: Node '{name}' not found in src/nodes/", err=True)
            raise typer.Exit(1)
    else:
        typer.echo(f"Error: Unknown component type '{component_type}'", err=True)
        raise typer.Exit(1)
