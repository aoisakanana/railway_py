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

from railway import entry_point, node, pipeline
from loguru import logger


@node
def process(data: str) -> str:
    """
    データを処理する（純粋関数）

    Args:
        data: 入力データ

    Returns:
        処理済みデータ
    """
    logger.info(f"Processing: {{data}}")
    # TODO: 実装を追加
    return data


@entry_point
def main(input_data: str = "default"):
    """
    {name} entry point.

    Args:
        input_data: 処理する入力データ
    """
    result = pipeline(
        input_data,
        process,
    )
    logger.info(f"Result: {{result}}")
    return result


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
    """指定された日付のデータを取得する（純粋関数）"""
    logger.info(f"Fetching data for {{date}}")
    # TODO: 実際のAPIコールに置き換え
    return {{"date": date, "records": [1, 2, 3]}}


@node
def process_data(data: dict) -> dict:
    """取得したデータを処理する（純粋関数）"""
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
        date: 対象日付 (YYYY-MM-DD)、デフォルトは今日
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

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
    {name} node（純粋関数）

    Args:
        data: 入力データ

    Returns:
        処理済みデータ
    """
    logger.info(f"Processing in {name}")
    # TODO: 実装を追加
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
    {name} node（純粋関数）

    機能:
    - 型アノテーション
    - ログ出力
    - エラーハンドリング（@nodeデコレータ経由）
    - イミュータブルな変換

    Args:
        data: 入力データ辞書

    Returns:
        処理済みデータ辞書
    """
    logger.info(f"Starting {name} with {{len(data)}} fields")

    # イミュータブルな変換（元のdataは変更しない）
    result = {{
        **data,
        "processed_by": "{name}",
        "status": "completed",
    }}

    logger.debug(f"Processed result: {{result}}")
    return result
'''


def _get_entry_test_template(name: str) -> str:
    """Get test template for an entry point."""
    class_name = "".join(word.title() for word in name.split("_"))
    return f'''"""Tests for {name} entry point."""

import pytest

from {name} import main


class Test{class_name}:
    """Test suite for {name} entry point."""

    def test_main_returns_result(self):
        """正常系: mainが結果を返す"""
        # Act
        result = main()

        # Assert
        assert result is not None

    def test_main_with_custom_args(self):
        """正常系: カスタム引数で実行できる"""
        # TODO: entry pointの引数に合わせて修正
        pass
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

    typer.echo(f"✓ Created src/nodes/{name}.py")
    typer.echo(f"✓ Created tests/nodes/test_{name}.py (skeleton)\n")
    typer.echo("💡 TDD style workflow:")
    typer.echo(f"   1. Write tests in tests/nodes/test_{name}.py")
    typer.echo(f"   2. Run: uv run pytest tests/nodes/test_{name}.py -v (expect skip)")
    typer.echo(f"   3. Implement src/nodes/{name}.py")
    typer.echo("   4. Run tests again (expect success)\n")
    typer.echo("To use in an entry point:")
    typer.echo(f"  from nodes.{name} import {name}")


def new(
    component_type: ComponentType = typer.Argument(..., help="Type: entry or node"),
    name: str = typer.Argument(..., help="Name of the component"),
    example: bool = typer.Option(False, "--example", help="Generate with example code"),
    force: bool = typer.Option(False, "--force", help="Overwrite if exists"),
) -> None:
    """
    Create a new entry point or node.

    Entry points are CLI-accessible functions decorated with @entry_point.
    Nodes are pure functions decorated with @node for use in pipelines.

    Both entry points and nodes are created with a corresponding test file
    (TDD-style skeleton with pytest.skip).

    Examples:
        railway new entry daily_report
        railway new node fetch_data
        railway new node process_data --example

    Documentation: https://pypi.org/project/railway-framework/
    """
    # Validate we're in a project
    if not _is_railway_project():
        typer.echo("Error: Not in a Railway project (src/ directory not found)", err=True)
        raise typer.Exit(1)

    if component_type == ComponentType.entry:
        _create_entry(name, example, force)
    else:
        _create_node(name, example, force)
