"""Tests for railway new command."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

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
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "entry", "daily_report"])
                assert result.exit_code == 0
                assert (Path(tmpdir) / "src" / "daily_report.py").exists()
            finally:
                os.chdir(original_cwd)

    def test_new_entry_contains_decorator(self):
        """Should contain @entry_point decorator."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src").mkdir()
            (Path(tmpdir) / "src" / "__init__.py").touch()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "entry", "my_entry"])
                content = (Path(tmpdir) / "src" / "my_entry.py").read_text()
                assert "@entry_point" in content
                assert "def main" in content
            finally:
                os.chdir(original_cwd)

    def test_new_entry_with_example(self):
        """Should create example code with --example."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src").mkdir()
            (Path(tmpdir) / "src" / "__init__.py").touch()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "entry", "example_entry", "--example"])
                content = (Path(tmpdir) / "src" / "example_entry.py").read_text()
                # Should have actual implementation, not just placeholder
                assert "return" in content
            finally:
                os.chdir(original_cwd)


class TestRailwayNewNode:
    """Test railway new node command."""

    def test_new_node_creates_file(self):
        """Should create node file."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create project structure
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "node", "fetch_data"])
                assert result.exit_code == 0
                assert (Path(tmpdir) / "src" / "nodes" / "fetch_data.py").exists()
            finally:
                os.chdir(original_cwd)

    def test_new_node_contains_decorator(self):
        """Should contain @node decorator."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "node", "process_data"])
                content = (Path(tmpdir) / "src" / "nodes" / "process_data.py").read_text()
                assert "@node" in content
                assert "def process_data" in content
            finally:
                os.chdir(original_cwd)

    def test_new_node_creates_test(self):
        """Should create test file."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "tests" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "node", "my_node"])
                test_file = Path(tmpdir) / "tests" / "nodes" / "test_my_node.py"
                assert test_file.exists()
                content = test_file.read_text()
                assert "def test_" in content
                assert "my_node" in content
            finally:
                os.chdir(original_cwd)

    def test_new_node_with_example(self):
        """Should create example implementation with --example."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "node", "example_node", "--example"])
                content = (Path(tmpdir) / "src" / "nodes" / "example_node.py").read_text()
                assert "return" in content
            finally:
                os.chdir(original_cwd)


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
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "node", "existing", "--force"])
                content = existing_file.read_text()
                assert "# Old content" not in content
                assert "@node" in content
            finally:
                os.chdir(original_cwd)

    def test_new_without_force_fails_on_existing(self):
        """Should fail without --force if file exists."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            (Path(tmpdir) / "src" / "nodes" / "existing.py").write_text("# Old")
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "node", "existing"])
                assert result.exit_code != 0
                output = result.output.lower() if result.output else ""
                assert "exists" in output
            finally:
                os.chdir(original_cwd)


class TestRailwayNewOutput:
    """Test railway new command output."""

    def test_new_shows_success_message(self):
        """Should show success message."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "node", "success_node"])
                assert "Created" in result.stdout or "created" in result.stdout.lower()
            finally:
                os.chdir(original_cwd)

    def test_new_shows_file_path(self):
        """Should show created file path."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "node", "path_node"])
                assert "path_node" in result.stdout
            finally:
                os.chdir(original_cwd)


class TestRailwayNewErrors:
    """Test railway new error handling."""

    def test_new_outside_project_fails(self):
        """Should fail when not in a Railway project."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                # No src/ directory
                result = runner.invoke(app, ["new", "node", "orphan_node"])
                assert result.exit_code != 0
            finally:
                os.chdir(original_cwd)
