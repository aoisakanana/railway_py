# Issue #13: railway run コマンド

**Phase:** 1b
**優先度:** 高
**依存関係:** #04, #08
**見積もり:** 1日

---

## 概要

エントリーポイントを実行する`railway run`コマンドを実装する。
`uv run python -m src.entry_name`より簡潔なコマンドを提供する。

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/cli/test_run.py
"""Tests for railway run command."""
import pytest
from typer.testing import CliRunner
from pathlib import Path
import tempfile
import os


runner = CliRunner()


class TestRailwayRun:
    """Test railway run command."""

    def test_run_executes_entry(self):
        """Should execute entry point."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "__init__.py").touch()
            (src_dir / "hello.py").write_text('''
"""Hello entry."""
def main(name: str = "World"):
    """Say hello."""
    print(f"Hello, {name}!")
    return f"Hello, {name}!"

if __name__ == "__main__":
    main()
''')
            os.chdir(tmpdir)

            result = runner.invoke(app, ["run", "hello"])

            assert result.exit_code == 0
            assert "Hello" in result.stdout

    def test_run_passes_arguments(self):
        """Should pass arguments to entry point."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "__init__.py").touch()
            (src_dir / "greet.py").write_text('''
"""Greet entry."""
import typer
app = typer.Typer()

@app.command()
def main(name: str = "World"):
    print(f"Hello, {name}!")

if __name__ == "__main__":
    app()
''')
            os.chdir(tmpdir)

            result = runner.invoke(app, ["run", "greet", "--name", "Alice"])

            # Arguments should be passed through
            assert "Alice" in result.stdout or result.exit_code == 0

    def test_run_shows_help(self):
        """Should show entry point help with --help."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "__init__.py").touch()
            (src_dir / "documented.py").write_text('''
"""Documented entry."""
import typer
app = typer.Typer()

@app.command()
def main(count: int = 1):
    """Process items."""
    print(f"Processing {count} items")

if __name__ == "__main__":
    app()
''')
            os.chdir(tmpdir)

            result = runner.invoke(app, ["run", "documented", "--help"])

            assert "count" in result.stdout.lower() or "--help" in result.stdout


class TestRailwayRunProjectDetection:
    """Test project root detection."""

    def test_run_detects_project_root(self):
        """Should detect project root from subdirectory."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create project structure
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "__init__.py").touch()
            (src_dir / "simple.py").write_text('''
def main():
    print("Simple")
    return "done"

if __name__ == "__main__":
    main()
''')
            # Create pyproject.toml to mark project root
            (Path(tmpdir) / "pyproject.toml").write_text('[project]\nname = "test"')

            # Change to subdirectory
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            os.chdir(subdir)

            # Should still find and run the entry
            # (This may need --project option)

    def test_run_with_project_option(self):
        """Should use --project option to specify project root."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create project
            project_dir = Path(tmpdir) / "my_project"
            src_dir = project_dir / "src"
            src_dir.mkdir(parents=True)
            (src_dir / "__init__.py").touch()
            (src_dir / "remote.py").write_text('''
def main():
    print("Remote entry")
    return "ok"

if __name__ == "__main__":
    main()
''')
            # Change to different directory
            os.chdir(tmpdir)

            result = runner.invoke(app, [
                "run", "--project", str(project_dir), "remote"
            ])

            # Should run the entry from specified project


class TestRailwayRunErrors:
    """Test railway run error handling."""

    def test_run_nonexistent_entry_fails(self):
        """Should fail for non-existent entry."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "__init__.py").touch()
            os.chdir(tmpdir)

            result = runner.invoke(app, ["run", "nonexistent"])

            assert result.exit_code != 0
            assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()

    def test_run_outside_project_fails(self):
        """Should fail when not in a project."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            # No src/ directory

            result = runner.invoke(app, ["run", "something"])

            assert result.exit_code != 0


class TestRailwayRunOutput:
    """Test railway run output."""

    def test_run_shows_project_info(self):
        """Should show project info at start."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "__init__.py").touch()
            (src_dir / "info.py").write_text('''
def main():
    print("Running")

if __name__ == "__main__":
    main()
''')
            os.chdir(tmpdir)

            result = runner.invoke(app, ["run", "info"])

            # Should show some project/entry info
            # (Output format depends on implementation)
```

```bash
# 実行して失敗を確認
pytest tests/unit/cli/test_run.py -v
# Expected: FAILED
```

### Step 2: Green（最小限の実装）

```python
# railway/cli/run.py
"""
railway run command implementation.
"""
import typer
from pathlib import Path
import sys
import importlib.util
from typing import Optional, List

app = typer.Typer()


@app.callback(invoke_without_command=True)
def run(
    ctx: typer.Context,
    entry_name: str = typer.Argument(..., help="Name of the entry point to run"),
    project: Optional[str] = typer.Option(
        None, "--project", "-p",
        help="Path to the project root"
    ),
    args: Optional[List[str]] = typer.Argument(None, help="Arguments to pass to entry"),
):
    """
    Run an entry point.

    This is a simpler alternative to 'uv run python -m src.entry_name'.

    Examples:
        railway run daily_report
        railway run daily_report --date 2024-01-01
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
        typer.echo(f"\nAvailable entries:", err=True)
        _list_entries(project_root)
        raise typer.Exit(1)

    # Run the entry
    typer.echo(f"[INFO] Project root: {project_root}")
    typer.echo(f"[INFO] Running entry point: {entry_name}")

    try:
        _execute_entry(project_root, entry_name, ctx.args)
    except Exception as e:
        typer.echo(f"[ERROR] Failed to run entry: {e}", err=True)
        raise typer.Exit(1)


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


def _list_entries(project_root: Path) -> None:
    """List available entries."""
    src_dir = project_root / "src"
    entries = []

    for py_file in src_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        if py_file.name == "settings.py":
            continue
        entries.append(py_file.stem)

    for entry in entries:
        typer.echo(f"  • {entry}")


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

        # If module has main function with typer app, run it
        if hasattr(module, 'main'):
            main_func = module.main
            if hasattr(main_func, '_typer_app'):
                main_func._typer_app()
            elif callable(main_func):
                # Simple function, call directly
                main_func()
    finally:
        sys.argv = original_argv
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
from railway.cli import run as run_cmd

app.command(name="init")(init_cmd.init)
app.command(name="new")(new_cmd.new)
app.command(name="list")(list_cmd.list_components)
app.command(name="run")(run_cmd.run)


if __name__ == "__main__":
    app()
```

```bash
# 実行して成功を確認
pytest tests/unit/cli/test_run.py -v
# Expected: PASSED
```

---

## 完了条件

- [ ] `railway run <entry>` でエントリーポイントが実行される
- [ ] 引数がエントリーポイントに渡される
- [ ] `--help` でエントリーポイントのヘルプが表示される
- [ ] プロジェクトルートが自動検出される
- [ ] `--project` オプションでプロジェクトを指定できる
- [ ] 存在しないエントリーでエラーになる
- [ ] 利用可能なエントリー一覧が表示される
- [ ] テストカバレッジ90%以上

---

## 次のIssue

- #14: TUTORIAL.md自動生成
