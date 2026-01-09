"""railway new command implementation."""

from enum import Enum
from pathlib import Path

import typer


class ComponentType(str, Enum):
    """Type of component to create."""

    entry = "entry"
    node = "node"


def _is_railway_project() -> bool:
    """Check if current directory is a Railway project."""
    return (Path.cwd() / "src").exists()


def _write_file(path: Path, content: str) -> None:
    """Write content to a file."""
    path.write_text(content)


def _get_entry_template(name: str) -> str:
    """Get basic entry point template."""
    return f'''"""{name} entry point."""

from railway import entry_point, node
from loguru import logger


@entry_point
def main():
    """
    {name} entry point.

    TODO: Add your implementation here.
    """
    logger.info("Starting {name}")
    # Your implementation here
    return "Success"


if __name__ == "__main__":
    main()
'''


def _get_entry_example_template(name: str) -> str:
    """Get example entry point template."""
    return f'''"""{name} entry point with example implementation."""

from datetime import datetime

from railway import entry_point, node, pipeline
from loguru import logger


@node
def fetch_data(date: str) -> dict:
    """Fetch data for the given date."""
    logger.info(f"Fetching data for {{date}}")
    # Example: Replace with actual API call
    return {{"date": date, "records": [1, 2, 3]}}


@node
def process_data(data: dict) -> dict:
    """Process the fetched data."""
    logger.info(f"Processing {{len(data['records'])}} records")
    return {{
        "date": data["date"],
        "summary": {{
            "total": len(data["records"]),
            "sum": sum(data["records"]),
        }}
    }}


@entry_point
def main(date: str = None, dry_run: bool = False):
    """
    {name} entry point.

    Args:
        date: Target date (YYYY-MM-DD), defaults to today
        dry_run: If True, don't make actual changes
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    if dry_run:
        logger.warning("DRY RUN mode - no actual changes")

    result = pipeline(
        fetch_data(date),
        process_data,
    )

    logger.info(f"Result: {{result}}")
    return result


if __name__ == "__main__":
    main()
'''


def _get_node_template(name: str) -> str:
    """Get basic node template."""
    return f'''"""{name} node."""

from railway import node
from loguru import logger


@node
def {name}(data: dict) -> dict:
    """
    {name} node.

    Args:
        data: Input data

    Returns:
        Processed data

    TODO: Add your implementation here.
    """
    logger.info(f"Processing in {name}")
    # Your implementation here
    return data
'''


def _get_node_example_template(name: str) -> str:
    """Get example node template."""
    return f'''"""{name} node with example implementation."""

from railway import node
from loguru import logger


@node(retry=True)
def {name}(data: dict) -> dict:
    """
    {name} node.

    This is an example node that demonstrates:
    - Type annotations
    - Logging
    - Error handling (via @node decorator)
    - Return value

    Args:
        data: Input data dictionary

    Returns:
        Processed data dictionary
    """
    logger.info(f"Starting {name} with {{len(data)}} fields")

    # Example processing
    result = {{
        **data,
        "processed_by": "{name}",
        "status": "completed",
    }}

    logger.debug(f"Processed result: {{result}}")
    return result
'''


def _get_node_test_template(name: str) -> str:
    """Get test template for a node."""
    class_name = "".join(word.title() for word in name.split("_"))
    return f'''"""Tests for {name} node."""

import pytest
from unittest.mock import MagicMock, patch

from src.nodes.{name} import {name}


class Test{class_name}:
    """Test suite for {name} node."""

    def test_{name}_success(self):
        """Test normal case."""
        # TODO: Implement test
        pass

    def test_{name}_error(self):
        """Test error case."""
        # TODO: Implement test
        pass
'''


def _create_entry(name: str, example: bool, force: bool) -> None:
    """Create a new entry point."""
    file_path = Path.cwd() / "src" / f"{name}.py"

    if file_path.exists() and not force:
        typer.echo(f"Error: {file_path} already exists. Use --force to overwrite.", err=True)
        raise typer.Exit(1)

    content = _get_entry_example_template(name) if example else _get_entry_template(name)
    _write_file(file_path, content)

    typer.echo(f"Created entry point: src/{name}.py")
    typer.echo("Entry point is ready to use\n")
    typer.echo("To run:")
    typer.echo(f"  railway run {name}")
    typer.echo(f"  # or: uv run python -m src.{name}")


def _create_node_test(name: str) -> None:
    """Create test file for node."""
    tests_dir = Path.cwd() / "tests" / "nodes"
    if not tests_dir.exists():
        tests_dir.mkdir(parents=True)

    test_file = tests_dir / f"test_{name}.py"
    if test_file.exists():
        return  # Don't overwrite existing tests

    content = _get_node_test_template(name)
    _write_file(test_file, content)


def _create_node(name: str, example: bool, force: bool) -> None:
    """Create a new node."""
    nodes_dir = Path.cwd() / "src" / "nodes"
    if not nodes_dir.exists():
        nodes_dir.mkdir(parents=True)
        (nodes_dir / "__init__.py").write_text('"""Node modules."""\n')

    file_path = nodes_dir / f"{name}.py"

    if file_path.exists() and not force:
        typer.echo(f"Error: {file_path} already exists. Use --force to overwrite.", err=True)
        raise typer.Exit(1)

    content = _get_node_example_template(name) if example else _get_node_template(name)
    _write_file(file_path, content)

    # Create test file
    _create_node_test(name)

    typer.echo(f"Created node: src/nodes/{name}.py")
    typer.echo(f"Created test: tests/nodes/test_{name}.py\n")
    typer.echo("To use in an entry point:")
    typer.echo(f"  from src.nodes.{name} import {name}")


def new(
    component_type: ComponentType = typer.Argument(..., help="Type: entry or node"),
    name: str = typer.Argument(..., help="Name of the component"),
    example: bool = typer.Option(False, "--example", help="Generate with example code"),
    force: bool = typer.Option(False, "--force", help="Overwrite if exists"),
) -> None:
    """
    Create a new entry point or node.

    Examples:
        railway new entry daily_report
        railway new node fetch_data --example
    """
    # Validate we're in a project
    if not _is_railway_project():
        typer.echo("Error: Not in a Railway project (src/ directory not found)", err=True)
        raise typer.Exit(1)

    if component_type == ComponentType.entry:
        _create_entry(name, example, force)
    else:
        _create_node(name, example, force)
