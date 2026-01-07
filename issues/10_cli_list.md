# Issue #10: railway list コマンド

**Phase:** 1a
**優先度:** 中
**依存関係:** #08
**見積もり:** 0.5日

---

## 概要

プロジェクト内のエントリーポイントとノードを一覧表示する`railway list`コマンドを実装する。

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/cli/test_list.py
"""Tests for railway list command."""
import pytest
from typer.testing import CliRunner
from pathlib import Path
import tempfile
import os


runner = CliRunner()


class TestRailwayList:
    """Test railway list command."""

    def test_list_shows_entries(self):
        """Should list entry points."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "__init__.py").touch()
            (src_dir / "daily_report.py").write_text('''
"""Daily report entry."""
from railway import entry_point

@entry_point
def main():
    """Generate daily report."""
    pass
''')
            os.chdir(tmpdir)

            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0
            assert "daily_report" in result.stdout

    def test_list_shows_nodes(self):
        """Should list nodes."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            nodes_dir = src_dir / "nodes"
            nodes_dir.mkdir(parents=True)
            (src_dir / "__init__.py").touch()
            (nodes_dir / "__init__.py").touch()
            (nodes_dir / "fetch_data.py").write_text('''
"""Fetch data node."""
from railway import node

@node
def fetch_data():
    """Fetch data from API."""
    pass
''')
            os.chdir(tmpdir)

            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0
            assert "fetch_data" in result.stdout

    def test_list_entries_only(self):
        """Should list only entries with 'entries' subcommand."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            nodes_dir = src_dir / "nodes"
            nodes_dir.mkdir(parents=True)
            (src_dir / "__init__.py").touch()
            (nodes_dir / "__init__.py").touch()
            (src_dir / "my_entry.py").write_text('@entry_point\ndef main(): pass')
            (nodes_dir / "my_node.py").write_text('@node\ndef my_node(): pass')
            os.chdir(tmpdir)

            result = runner.invoke(app, ["list", "entries"])

            assert "my_entry" in result.stdout
            # Node should not be shown (or shown in different section)

    def test_list_nodes_only(self):
        """Should list only nodes with 'nodes' subcommand."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            nodes_dir = src_dir / "nodes"
            nodes_dir.mkdir(parents=True)
            (src_dir / "__init__.py").touch()
            (nodes_dir / "__init__.py").touch()
            (src_dir / "my_entry.py").write_text('@entry_point\ndef main(): pass')
            (nodes_dir / "my_node.py").write_text('@node\ndef my_node(): pass')
            os.chdir(tmpdir)

            result = runner.invoke(app, ["list", "nodes"])

            assert "my_node" in result.stdout

    def test_list_shows_statistics(self):
        """Should show statistics."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            nodes_dir = src_dir / "nodes"
            tests_dir = Path(tmpdir) / "tests" / "nodes"
            nodes_dir.mkdir(parents=True)
            tests_dir.mkdir(parents=True)
            (src_dir / "__init__.py").touch()
            (nodes_dir / "__init__.py").touch()
            (src_dir / "entry1.py").write_text('@entry_point\ndef main(): pass')
            (src_dir / "entry2.py").write_text('@entry_point\ndef main(): pass')
            (nodes_dir / "node1.py").write_text('@node\ndef node1(): pass')
            (tests_dir / "test_node1.py").touch()
            os.chdir(tmpdir)

            result = runner.invoke(app, ["list"])

            # Should show counts
            assert "2" in result.stdout  # 2 entries
            assert "1" in result.stdout  # 1 node


class TestRailwayListOutput:
    """Test railway list output formatting."""

    def test_list_shows_docstrings(self):
        """Should show docstrings as descriptions."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "__init__.py").touch()
            (src_dir / "documented.py").write_text('''
"""Documented entry point."""
from railway import entry_point

@entry_point
def main():
    """This is the main function."""
    pass
''')
            os.chdir(tmpdir)

            result = runner.invoke(app, ["list"])

            # Should show module or function docstring
            assert "documented" in result.stdout.lower()


class TestRailwayListErrors:
    """Test railway list error handling."""

    def test_list_outside_project_fails(self):
        """Should fail when not in a Railway project."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            # No src/ directory

            result = runner.invoke(app, ["list"])

            assert result.exit_code != 0

    def test_list_empty_project(self):
        """Should handle empty project gracefully."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "__init__.py").touch()
            os.chdir(tmpdir)

            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0
            # Should indicate no entries/nodes found
```

```bash
# 実行して失敗を確認
pytest tests/unit/cli/test_list.py -v
# Expected: FAILED
```

### Step 2: Green（最小限の実装）

```python
# railway/cli/list.py
"""
railway list command implementation.
"""
import typer
from pathlib import Path
from typing import Optional
import ast
import re

app = typer.Typer()


@app.callback(invoke_without_command=True)
def list_components(
    ctx: typer.Context,
    filter_type: Optional[str] = typer.Argument(None, help="Filter: entries or nodes"),
):
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


def _is_railway_project() -> bool:
    """Check if current directory is a Railway project."""
    return (Path.cwd() / "src").exists()


def _find_entries() -> list[dict]:
    """Find all entry points in src/."""
    entries = []
    src_dir = Path.cwd() / "src"

    for py_file in src_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        if py_file.name == "settings.py":
            continue

        entry_info = _analyze_entry_file(py_file)
        if entry_info:
            entries.append(entry_info)

    return entries


def _find_nodes() -> list[dict]:
    """Find all nodes in src/nodes/."""
    nodes = []
    nodes_dir = Path.cwd() / "src" / "nodes"

    if not nodes_dir.exists():
        return nodes

    for py_file in nodes_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue

        node_info = _analyze_node_file(py_file)
        if node_info:
            nodes.append(node_info)

    return nodes


def _analyze_entry_file(file_path: Path) -> Optional[dict]:
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


def _analyze_node_file(file_path: Path) -> Optional[dict]:
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


def _extract_module_docstring(content: str) -> Optional[str]:
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


def _count_tests() -> int:
    """Count test files."""
    tests_dir = Path.cwd() / "tests"
    if not tests_dir.exists():
        return 0

    count = 0
    for test_file in tests_dir.rglob("test_*.py"):
        count += 1
    return count


def _display_entries(entries: list[dict]) -> None:
    """Display entry points."""
    typer.echo("\nEntry Points:")
    if not entries:
        typer.echo("  (none)")
        return

    for entry in entries:
        typer.echo(f"  • {entry['name']:20} {entry['description']}")


def _display_nodes(nodes: list[dict]) -> None:
    """Display nodes."""
    typer.echo("\nNodes:")
    if not nodes:
        typer.echo("  (none)")
        return

    for node in nodes:
        typer.echo(f"  • {node['name']:20} {node['description']}")


def _display_all(entries: list[dict], nodes: list[dict], tests: int) -> None:
    """Display all components."""
    _display_entries(entries)
    _display_nodes(nodes)

    typer.echo(f"\nStatistics:")
    typer.echo(f"  {len(entries)} entry points, {len(nodes)} nodes, {tests} tests")
```

```python
# railway/cli/main.py を更新
"""
Main CLI entry point for Railway Framework.
"""
import typer

app = typer.Typer(
    name="railway",
    help="Railway Framework CLI - Build robust Python automation",
    add_completion=False,
)


# Import and register subcommands
from railway.cli import init as init_cmd
from railway.cli import new as new_cmd
from railway.cli import list as list_cmd

# Register as direct commands
app.command(name="init")(init_cmd.init)
app.command(name="new")(new_cmd.new)
app.command(name="list")(list_cmd.list_components)


if __name__ == "__main__":
    app()
```

```bash
# 実行して成功を確認
pytest tests/unit/cli/test_list.py -v
# Expected: PASSED
```

---

## 完了条件

- [ ] `railway list` でエントリーポイントとノードが表示される
- [ ] `railway list entries` でエントリーポイントのみ表示される
- [ ] `railway list nodes` でノードのみ表示される
- [ ] 統計情報（エントリー数、ノード数、テスト数）が表示される
- [ ] 説明文（docstring）が表示される
- [ ] プロジェクト外で実行するとエラーになる
- [ ] 空のプロジェクトでも正常に動作する
- [ ] テストカバレッジ90%以上

---

## Phase 1a 完了

これでPhase 1aのすべてのIssueが完了しました。

## 次のPhase

- Phase 1b: 拡張機能（#11〜#15）
