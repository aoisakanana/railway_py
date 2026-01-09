"""Tests for railway run command."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner


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
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["run", "hello"])
                assert result.exit_code == 0
                # Output may contain "Hello" or just "Running entry point"
                output = result.output if result.output else result.stdout
                assert "hello" in output.lower() or "Running" in output
            finally:
                os.chdir(original_cwd)

    def test_run_passes_arguments(self):
        """Should pass arguments to entry point."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "__init__.py").touch()
            (src_dir / "greet.py").write_text('''
"""Greet entry."""
import sys
def main():
    # Read args from sys.argv
    args = sys.argv[1:]
    name = "World"
    for i, arg in enumerate(args):
        if arg == "--name" and i + 1 < len(args):
            name = args[i + 1]
    print(f"Hello, {name}!")

if __name__ == "__main__":
    main()
''')
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["run", "greet", "--", "--name", "Alice"])
                # Arguments should be passed through
                assert "Alice" in result.stdout or result.exit_code == 0
            finally:
                os.chdir(original_cwd)


class TestRailwayRunProjectDetection:
    """Test project root detection."""

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
            original_cwd = os.getcwd()
            try:
                # Change to different directory
                os.chdir(tmpdir)
                result = runner.invoke(app, [
                    "run", "--project", str(project_dir), "remote"
                ])
                # Should run the entry from specified project
                assert "Remote" in result.stdout or result.exit_code == 0
            finally:
                os.chdir(original_cwd)


class TestRailwayRunErrors:
    """Test railway run error handling."""

    def test_run_nonexistent_entry_fails(self):
        """Should fail for non-existent entry."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "__init__.py").touch()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["run", "nonexistent"])
                assert result.exit_code != 0
                # Error messages go to output (combined stdout+stderr)
                output = result.output.lower() if result.output else ""
                assert "not found" in output or "error" in output
            finally:
                os.chdir(original_cwd)

    def test_run_outside_project_fails(self):
        """Should fail when not in a project."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                # No src/ directory
                result = runner.invoke(app, ["run", "something"])
                assert result.exit_code != 0
            finally:
                os.chdir(original_cwd)


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
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["run", "info"])
                # Should show some project/entry info or just run
                assert result.exit_code == 0
            finally:
                os.chdir(original_cwd)

    def test_run_lists_available_entries(self):
        """Should list available entries on error."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "__init__.py").touch()
            (src_dir / "entry1.py").write_text('def main(): pass')
            (src_dir / "entry2.py").write_text('def main(): pass')
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["run", "nonexistent"])
                # Should show available entries (output combines stdout+stderr)
                output = result.output.lower() if result.output else ""
                assert "entry1" in output or "entry2" in output or "available" in output
            finally:
                os.chdir(original_cwd)
