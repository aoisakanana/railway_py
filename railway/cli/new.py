"""railway new command implementation."""

import re
from enum import Enum
from pathlib import Path
from typing import Optional

import typer


class ComponentType(str, Enum):
    """Type of component to create."""

    entry = "entry"
    node = "node"
    contract = "contract"


def _is_railway_project() -> bool:
    """Check if current directory is a Railway project."""
    return (Path.cwd() / "src").exists()


def _write_file(path: Path, content: str) -> None:
    """Write content to a file."""
    path.write_text(content)


def _camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case."""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


# =============================================================================
# Contract Templates
# =============================================================================


def _get_contract_template(name: str) -> str:
    """Get basic Contract template."""
    return f'''"""{name} contract."""

from railway import Contract


class {name}(Contract):
    """
    Output contract for a node.

    TODO: Define the fields for this contract.
    """
    # Example fields (modify as needed):
    # items: list[dict]
    # total: int
    # fetched_at: datetime
    pass
'''


def _get_entity_contract_template(name: str) -> str:
    """Get entity Contract template."""
    return f'''"""{name} entity contract."""

from railway import Contract


class {name}(Contract):
    """
    Entity contract representing a {name.lower()}.

    TODO: Define the fields for this entity.
    """
    id: int
    # name: str
    # email: str
'''


def _get_params_contract_template(name: str) -> str:
    """Get Params contract template."""
    return f'''"""{name} parameters."""

from railway import Params


class {name}(Params):
    """
    Parameters for an entry point.

    TODO: Define the parameters.
    """
    # user_id: int
    # include_details: bool = False
    pass
'''


# =============================================================================
# Typed Node Templates
# =============================================================================


def _get_typed_node_template(
    name: str,
    output_type: str,
    inputs: list[tuple[str, str]],
) -> str:
    """Get typed node template with input/output contracts."""
    # Build imports
    import_lines = ["from railway import node"]
    output_snake = _camel_to_snake(output_type)
    import_lines.append(f"from contracts.{output_snake} import {output_type}")

    for param_name, type_name in inputs:
        type_snake = _camel_to_snake(type_name)
        import_line = f"from contracts.{type_snake} import {type_name}"
        if import_line not in import_lines:
            import_lines.append(import_line)

    imports = "\n".join(import_lines)

    # Build decorator
    if inputs:
        inputs_dict = ", ".join(f'"{pn}": {tn}' for pn, tn in inputs)
        decorator = f'@node(\n    inputs={{{inputs_dict}}},\n    output={output_type},\n)'
    else:
        decorator = f"@node(output={output_type})"

    # Build function signature
    if inputs:
        params = ", ".join(f"{pn}: {tn}" for pn, tn in inputs)
        signature = f"def {name}({params}) -> {output_type}:"
    else:
        signature = f"def {name}() -> {output_type}:"

    # Build docstring
    if inputs:
        args_doc = "\n".join(f"        {pn}: Input from a node that outputs {tn}." for pn, tn in inputs)
        docstring = f'''"""
    Process data.

    Args:
{args_doc}

    Returns:
        {output_type}: The result of this node.
    """'''
    else:
        docstring = f'''"""
    TODO: Implement this node.

    Returns:
        {output_type}: The result of this node.
    """'''

    return f'''"""{name} node."""

{imports}


{decorator}
{signature}
    {docstring}
    # TODO: Implement the logic
    return {output_type}(
        # Fill in the required fields
    )
'''


def _get_typed_node_test_template(
    name: str,
    output_type: str,
    inputs: list[tuple[str, str]],
) -> str:
    """Get typed node test template.

    Generates tests that use pytest.skip() by default to follow TDD workflow:
    1. Run tests (skip)
    2. Implement the test data
    3. Run tests (pass)
    """
    class_name = "".join(word.title() for word in name.split("_"))

    # Build imports
    import_lines = []
    output_snake = _camel_to_snake(output_type)
    import_lines.append(f"from contracts.{output_snake} import {output_type}")

    for param_name, type_name in inputs:
        type_snake = _camel_to_snake(type_name)
        import_line = f"from contracts.{type_snake} import {type_name}"
        if import_line not in import_lines:
            import_lines.append(import_line)

    import_lines.append(f"from nodes.{name} import {name}")
    imports = "\n".join(import_lines)

    # Build input hints for documentation
    if inputs:
        input_hints = "\n".join(
            f"    #     {pn} = {tn}(...)"
            for pn, tn in inputs
        )
        call_hint = ", ".join(pn for pn, _ in inputs)
        call_example = f"    #     result = {name}({call_hint})"
    else:
        input_hints = ""
        call_example = f"    #     result = {name}()"

    return f'''"""Tests for {name} node."""

import pytest

{imports}


class Test{class_name}:
    """Test suite for {name} node.

    TDD Workflow:
    1. Run tests (expect skip)
    2. Fill in test data and assertions
    3. Run tests (expect pass)
    """

    def test_{name}_returns_correct_type(self):
        """Node should return {output_type}.

        Example:
{input_hints}
{call_example}
            assert isinstance(result, {output_type})
        """
        pytest.skip("TODO: Fill in test data for {name}")

    def test_{name}_basic(self):
        """Basic functionality test."""
        pytest.skip("TODO: Implement this test")
'''


# =============================================================================
# Entry Templates
# =============================================================================


def _get_entry_template(name: str) -> str:
    """Get basic entry point template."""
    return f'''"""{name} entry point."""

from railway import entry_point, node, pipeline
from loguru import logger


@node
def process(data: str) -> str:
    """
    Process data (pure function).

    Args:
        data: Input data

    Returns:
        Processed data
    """
    logger.info(f"Processing: {{data}}")
    # TODO: Add implementation
    return data


@entry_point
def main(input_data: str = "default"):
    """
    {name} entry point.

    Args:
        input_data: Input data to process
    """
    result = pipeline(
        input_data,
        process,
    )
    logger.info(f"Result: {{result}}")
    return result


# Export Typer app for testing with CliRunner
app = main._typer_app


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
    """Fetch data for the specified date (pure function)."""
    logger.info(f"Fetching data for {{date}}")
    # TODO: Replace with actual API call
    return {{"date": date, "records": [1, 2, 3]}}


@node
def process_data(data: dict) -> dict:
    """Process fetched data (pure function)."""
    logger.info(f"Processing {{len(data['records'])}} records")
    return {{
        "date": data["date"],
        "summary": {{
            "total": len(data["records"]),
            "sum": sum(data["records"]),
        }}
    }}


@entry_point
def main(date: str | None = None):
    """
    {name} entry point.

    Args:
        date: Target date (YYYY-MM-DD), defaults to today
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    result = pipeline(
        fetch_data(date),
        process_data,
    )

    logger.info(f"Result: {{result}}")
    return result


# Export Typer app for testing with CliRunner
app = main._typer_app


if __name__ == "__main__":
    main()
'''


# =============================================================================
# Node Templates (basic)
# =============================================================================


def _get_node_template(name: str) -> str:
    """Get basic node template."""
    return f'''"""{name} node."""

from railway import node
from loguru import logger


@node
def {name}(data: dict) -> dict:
    """
    {name} node (pure function).

    Args:
        data: Input data

    Returns:
        Processed data
    """
    logger.info(f"Processing in {name}")
    # TODO: Add implementation
    return data
'''


def _get_node_example_template(name: str) -> str:
    """Get example node template."""
    return f'''"""{name} node with example implementation."""

from railway import node
from loguru import logger


@node
def {name}(data: dict) -> dict:
    """
    {name} node (pure function).

    Features:
    - Type annotations
    - Logging
    - Error handling (via @node decorator)
    - Immutable transformation

    Args:
        data: Input data dictionary

    Returns:
        Processed data dictionary
    """
    logger.info(f"Starting {name} with {{len(data)}} fields")

    # Immutable transformation (original data unchanged)
    result = {{
        **data,
        "processed_by": "{name}",
        "status": "completed",
    }}

    logger.debug(f"Processed result: {{result}}")
    return result
'''


# =============================================================================
# Test Templates
# =============================================================================


def _get_entry_test_template(name: str) -> str:
    """Get test template for an entry point.

    Uses CliRunner with main._typer_app to avoid sys.argv pollution
    and ensure tests work even after user rewrites the entry point.
    """
    class_name = "".join(word.title() for word in name.split("_"))
    return f'''"""Tests for {name} entry point."""

import pytest
from typer.testing import CliRunner

from {name} import main

runner = CliRunner()


class Test{class_name}:
    """Test suite for {name} entry point.

    Uses CliRunner with main._typer_app to isolate from pytest's sys.argv.
    This pattern works regardless of whether 'app' is exported.
    """

    def test_{name}_runs_successfully(self):
        """Entry point should complete without error."""
        result = runner.invoke(main._typer_app, [])
        assert result.exit_code == 0, f"Failed with: {{result.stdout}}"

    def test_{name}_with_help(self):
        """Entry point should show help."""
        result = runner.invoke(main._typer_app, ["--help"])
        assert result.exit_code == 0
'''


def _get_node_test_template(name: str) -> str:
    """Get test template for a node (TDD-style skeleton)."""
    class_name = "".join(word.title() for word in name.split("_"))
    return f'''"""Tests for {name} node."""

import pytest

from nodes.{name} import {name}


class Test{class_name}:
    """Test suite for {name} node.

    TDD Workflow:
    1. Edit this file to define expected behavior
    2. Run: uv run pytest tests/nodes/test_{name}.py -v (expect failure)
    3. Implement src/nodes/{name}.py
    4. Run tests again (expect success)
    """

    def test_{name}_basic(self):
        """TODO: Define expected behavior and implement test.

        Example:
            # Arrange
            input_data = your_input_here

            # Act
            result = {name}(input_data)

            # Assert
            assert result == expected_output
        """
        pytest.skip("Implement this test based on your node's specification")

    def test_{name}_edge_case(self):
        """TODO: Test edge cases and error handling."""
        pytest.skip("Implement edge case tests")
'''


# =============================================================================
# Create Functions
# =============================================================================


def _create_contract(
    name: str,
    entity: bool,
    params: bool,
    force: bool,
) -> None:
    """Create a new Contract."""
    contracts_dir = Path.cwd() / "src" / "contracts"
    if not contracts_dir.exists():
        contracts_dir.mkdir(parents=True)
        (contracts_dir / "__init__.py").write_text('"""Contract modules."""\n')

    file_name = _camel_to_snake(name)
    file_path = contracts_dir / f"{file_name}.py"

    if file_path.exists() and not force:
        typer.echo(f"Error: {file_path} already exists. Use --force to overwrite.", err=True)
        raise typer.Exit(1)

    if params:
        content = _get_params_contract_template(name)
    elif entity:
        content = _get_entity_contract_template(name)
    else:
        content = _get_contract_template(name)

    _write_file(file_path, content)

    typer.echo(f"Created contract: src/contracts/{file_name}.py")
    typer.echo(f"\nTo use in a node:")
    typer.echo(f"  from contracts.{file_name} import {name}")


def _create_entry_test(name: str) -> None:
    """Create test file for entry point."""
    tests_dir = Path.cwd() / "tests"
    if not tests_dir.exists():
        tests_dir.mkdir(parents=True)

    test_file = tests_dir / f"test_{name}.py"
    if test_file.exists():
        return  # Don't overwrite existing tests

    content = _get_entry_test_template(name)
    _write_file(test_file, content)


def _create_entry(name: str, example: bool, force: bool) -> None:
    """Create a new entry point."""
    file_path = Path.cwd() / "src" / f"{name}.py"

    if file_path.exists() and not force:
        typer.echo(f"Error: {file_path} already exists. Use --force to overwrite.", err=True)
        raise typer.Exit(1)

    content = _get_entry_example_template(name) if example else _get_entry_template(name)
    _write_file(file_path, content)

    # Create test file
    _create_entry_test(name)

    typer.echo(f"Created entry point: src/{name}.py")
    typer.echo(f"Created test: tests/test_{name}.py\n")
    typer.echo("To run:")
    typer.echo(f"  uv run railway run {name}")
    typer.echo(f"  # or: uv run python -m {name}")


def _create_node_test(
    name: str,
    output_type: Optional[str] = None,
    inputs: Optional[list[tuple[str, str]]] = None,
) -> None:
    """Create test file for node."""
    tests_dir = Path.cwd() / "tests" / "nodes"
    if not tests_dir.exists():
        tests_dir.mkdir(parents=True)

    test_file = tests_dir / f"test_{name}.py"
    if test_file.exists():
        return  # Don't overwrite existing tests

    if output_type:
        content = _get_typed_node_test_template(name, output_type, inputs or [])
    else:
        content = _get_node_test_template(name)

    _write_file(test_file, content)


def _parse_input_spec(input_spec: str) -> tuple[str, str]:
    """Parse input specification 'param_name:TypeName'.

    Args:
        input_spec: Input in format 'param_name:TypeName'

    Returns:
        Tuple of (param_name, type_name)

    Raises:
        typer.Exit: If format is invalid
    """
    if ":" not in input_spec:
        typer.echo(
            f"Error: Invalid input format '{input_spec}'. "
            "Expected 'param_name:TypeName'.",
            err=True,
        )
        raise typer.Exit(1)

    parts = input_spec.split(":", 1)
    return (parts[0].strip(), parts[1].strip())


def _create_node(
    name: str,
    example: bool,
    force: bool,
    output_type: Optional[str] = None,
    input_specs: Optional[list[str]] = None,
) -> None:
    """Create a new node."""
    nodes_dir = Path.cwd() / "src" / "nodes"
    if not nodes_dir.exists():
        nodes_dir.mkdir(parents=True)
        (nodes_dir / "__init__.py").write_text('"""Node modules."""\n')

    file_path = nodes_dir / f"{name}.py"

    if file_path.exists() and not force:
        typer.echo(f"Error: {file_path} already exists. Use --force to overwrite.", err=True)
        raise typer.Exit(1)

    # Parse inputs
    inputs: list[tuple[str, str]] = []
    if input_specs:
        inputs = [_parse_input_spec(spec) for spec in input_specs]

    # Generate content
    if output_type:
        content = _get_typed_node_template(name, output_type, inputs)
    elif example:
        content = _get_node_example_template(name)
    else:
        content = _get_node_template(name)

    _write_file(file_path, content)

    # Create test file
    _create_node_test(name, output_type, inputs)

    typer.echo(f"Created src/nodes/{name}.py")
    typer.echo(f"Created tests/nodes/test_{name}.py\n")

    if output_type:
        typer.echo("To use in a typed pipeline:")
        typer.echo(f"  from nodes.{name} import {name}")
        typer.echo(f"  result = typed_pipeline({name})")
    else:
        typer.echo("TDD style workflow:")
        typer.echo(f"   1. Write tests in tests/nodes/test_{name}.py")
        typer.echo(f"   2. Run: uv run pytest tests/nodes/test_{name}.py -v")
        typer.echo(f"   3. Implement src/nodes/{name}.py")
        typer.echo("   4. Run tests again\n")
        typer.echo("To use in an entry point:")
        typer.echo(f"  from nodes.{name} import {name}")


# =============================================================================
# Main Command
# =============================================================================


def new(
    component_type: ComponentType = typer.Argument(..., help="Type: entry, node, or contract"),
    name: str = typer.Argument(..., help="Name of the component"),
    example: bool = typer.Option(False, "--example", help="Generate with example code"),
    force: bool = typer.Option(False, "--force", help="Overwrite if exists"),
    entity: bool = typer.Option(False, "--entity", help="Create entity Contract (with id field)"),
    params: bool = typer.Option(False, "--params", help="Create Params Contract"),
    output: Optional[str] = typer.Option(None, "--output", help="Output Contract type for node"),
    input_specs: Optional[list[str]] = typer.Option(
        None, "--input", help="Input spec 'param_name:TypeName' (repeatable)"
    ),
) -> None:
    """
    Create a new entry point, node, or contract.

    Entry points are CLI-accessible functions decorated with @entry_point.
    Nodes are pure functions decorated with @node for use in pipelines.
    Contracts are type-safe data structures for node inputs/outputs.

    Examples:
        railway new entry daily_report
        railway new node fetch_data
        railway new node process_data --example
        railway new contract UsersFetchResult
        railway new contract User --entity
        railway new contract ReportParams --params
        railway new node fetch_users --output UsersFetchResult
        railway new node process --input users:UsersFetchResult --output Result

    Documentation: https://pypi.org/project/railway-framework/
    """
    # Validate we're in a project
    if not _is_railway_project():
        typer.echo("Error: Not in a Railway project (src/ directory not found)", err=True)
        raise typer.Exit(1)

    # Validate mutually exclusive options
    if entity and params:
        typer.echo("Error: --entity and --params are mutually exclusive.", err=True)
        raise typer.Exit(1)

    # Validate --input requires --output
    if input_specs and not output:
        typer.echo("Error: --input requires --output to be specified.", err=True)
        raise typer.Exit(1)

    if component_type == ComponentType.contract:
        _create_contract(name, entity, params, force)
    elif component_type == ComponentType.entry:
        _create_entry(name, example, force)
    else:  # node
        _create_node(name, example, force, output, input_specs)
