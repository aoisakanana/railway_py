# Issue #09: railway new コマンド

**Phase:** 1a
**優先度:** 高
**依存関係:** #08
**見積もり:** 1日

---

## 概要

新規エントリーポイントやノードを作成する`railway new`コマンドを実装する。
テンプレートからコードを生成し、テストファイルも同時に作成する。

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/cli/test_new.py
"""Tests for railway new command."""
import pytest
from typer.testing import CliRunner
from pathlib import Path
import tempfile
import os


runner = CliRunner()


class TestRailwayNewEntry:
    """Test railway new entry command."""

    def test_new_entry_creates_file(self):
        """Should create entry point file."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create project structure
            (Path(tmpdir) / "src").mkdir()
            (Path(tmpdir) / "src" / "__init__.py").touch()
            os.chdir(tmpdir)

            result = runner.invoke(app, ["new", "entry", "daily_report"])

            assert result.exit_code == 0
            assert (Path(tmpdir) / "src" / "daily_report.py").exists()

    def test_new_entry_contains_decorator(self):
        """Should contain @entry_point decorator."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src").mkdir()
            (Path(tmpdir) / "src" / "__init__.py").touch()
            os.chdir(tmpdir)

            runner.invoke(app, ["new", "entry", "my_entry"])

            content = (Path(tmpdir) / "src" / "my_entry.py").read_text()
            assert "@entry_point" in content
            assert "def main" in content

    def test_new_entry_with_example(self):
        """Should create example code with --example."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src").mkdir()
            (Path(tmpdir) / "src" / "__init__.py").touch()
            os.chdir(tmpdir)

            runner.invoke(app, ["new", "entry", "example_entry", "--example"])

            content = (Path(tmpdir) / "src" / "example_entry.py").read_text()
            # Should have actual implementation, not just placeholder
            assert "return" in content


class TestRailwayNewNode:
    """Test railway new node command."""

    def test_new_node_creates_file(self):
        """Should create node file."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create project structure
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            os.chdir(tmpdir)

            result = runner.invoke(app, ["new", "node", "fetch_data"])

            assert result.exit_code == 0
            assert (Path(tmpdir) / "src" / "nodes" / "fetch_data.py").exists()

    def test_new_node_contains_decorator(self):
        """Should contain @node decorator."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            os.chdir(tmpdir)

            runner.invoke(app, ["new", "node", "process_data"])

            content = (Path(tmpdir) / "src" / "nodes" / "process_data.py").read_text()
            assert "@node" in content
            assert "def process_data" in content

    def test_new_node_creates_test(self):
        """Should create test file."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "tests" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            os.chdir(tmpdir)

            runner.invoke(app, ["new", "node", "my_node"])

            test_file = Path(tmpdir) / "tests" / "nodes" / "test_my_node.py"
            assert test_file.exists()
            content = test_file.read_text()
            assert "def test_" in content
            assert "my_node" in content

    def test_new_node_with_example(self):
        """Should create example implementation with --example."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            os.chdir(tmpdir)

            runner.invoke(app, ["new", "node", "example_node", "--example"])

            content = (Path(tmpdir) / "src" / "nodes" / "example_node.py").read_text()
            assert "return" in content


class TestRailwayNewOptions:
    """Test railway new command options."""

    def test_new_force_overwrites(self):
        """Should overwrite with --force."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            existing_file = Path(tmpdir) / "src" / "nodes" / "existing.py"
            existing_file.write_text("# Old content")
            os.chdir(tmpdir)

            runner.invoke(app, ["new", "node", "existing", "--force"])

            content = existing_file.read_text()
            assert "# Old content" not in content
            assert "@node" in content

    def test_new_without_force_fails_on_existing(self):
        """Should fail without --force if file exists."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            (Path(tmpdir) / "src" / "nodes" / "existing.py").write_text("# Old")
            os.chdir(tmpdir)

            result = runner.invoke(app, ["new", "node", "existing"])

            assert result.exit_code != 0
            assert "exists" in result.stdout.lower()


class TestRailwayNewOutput:
    """Test railway new command output."""

    def test_new_shows_success_message(self):
        """Should show success message."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            os.chdir(tmpdir)

            result = runner.invoke(app, ["new", "node", "success_node"])

            assert "Created" in result.stdout or "✓" in result.stdout

    def test_new_shows_file_path(self):
        """Should show created file path."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            os.chdir(tmpdir)

            result = runner.invoke(app, ["new", "node", "path_node"])

            assert "path_node" in result.stdout


class TestRailwayNewErrors:
    """Test railway new error handling."""

    def test_new_outside_project_fails(self):
        """Should fail when not in a Railway project."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            # No src/ directory

            result = runner.invoke(app, ["new", "node", "orphan_node"])

            assert result.exit_code != 0

    def test_new_invalid_type_fails(self):
        """Should fail with invalid type."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            result = runner.invoke(app, ["new", "invalid_type", "name"])

            assert result.exit_code != 0
```

```bash
# 実行して失敗を確認
pytest tests/unit/cli/test_new.py -v
# Expected: FAILED
```

### Step 2: Green（最小限の実装）

```python
# railway/cli/new.py
"""
railway new command implementation.
"""
import typer
from pathlib import Path
from typing import Optional
from enum import Enum

app = typer.Typer()


class ComponentType(str, Enum):
    """Type of component to create."""
    entry = "entry"
    node = "node"


@app.callback(invoke_without_command=True)
def new(
    component_type: ComponentType = typer.Argument(..., help="Type: entry or node"),
    name: str = typer.Argument(..., help="Name of the component"),
    example: bool = typer.Option(False, "--example", help="Generate with example code"),
    force: bool = typer.Option(False, "--force", help="Overwrite if exists"),
):
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


def _is_railway_project() -> bool:
    """Check if current directory is a Railway project."""
    return (Path.cwd() / "src").exists()


def _create_entry(name: str, example: bool, force: bool) -> None:
    """Create a new entry point."""
    file_path = Path.cwd() / "src" / f"{name}.py"

    if file_path.exists() and not force:
        typer.echo(f"Error: {file_path} already exists. Use --force to overwrite.", err=True)
        raise typer.Exit(1)

    if example:
        content = _get_entry_example_template(name)
    else:
        content = _get_entry_template(name)

    file_path.write_text(content)

    typer.echo(f"✓ Created entry point: src/{name}.py")
    typer.echo(f"✓ Entry point is ready to use\n")
    typer.echo("To run:")
    typer.echo(f"  railway run {name}")
    typer.echo(f"  # or: uv run python -m src.{name}")


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

    if example:
        content = _get_node_example_template(name)
    else:
        content = _get_node_template(name)

    file_path.write_text(content)

    # Create test file
    _create_node_test(name)

    typer.echo(f"✓ Created node: src/nodes/{name}.py")
    typer.echo(f"✓ Created test: tests/nodes/test_{name}.py\n")
    typer.echo("To use in an entry point:")
    typer.echo(f"  from src.nodes.{name} import {name}")


def _create_node_test(name: str) -> None:
    """Create test file for node."""
    tests_dir = Path.cwd() / "tests" / "nodes"
    if not tests_dir.exists():
        tests_dir.mkdir(parents=True)

    test_file = tests_dir / f"test_{name}.py"
    if test_file.exists():
        return  # Don't overwrite existing tests

    content = f'''"""Tests for {name} node."""
import pytest
from unittest.mock import patch, MagicMock

from src.nodes.{name} import {name}


class Test{name.title().replace("_", "")}:
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
    test_file.write_text(content)


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
from railway import entry_point, node, pipeline
from loguru import logger
from datetime import datetime


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
from typing import Any


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
```

```bash
# 実行して成功を確認
pytest tests/unit/cli/test_new.py -v
# Expected: PASSED
```

---

## 完了条件

- [ ] `railway new entry <name>` でエントリーポイントが作成される
- [ ] `railway new node <name>` でノードが作成される
- [ ] 生成されるファイルに適切なデコレータが含まれる
- [ ] ノード作成時にテストファイルも作成される
- [ ] `--example` でサンプルコードが生成される
- [ ] `--force` で既存ファイルを上書きできる
- [ ] プロジェクト外で実行するとエラーになる
- [ ] テストカバレッジ90%以上

---

## 次のIssue

- #10: railway list コマンド
