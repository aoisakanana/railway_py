"""Tests for test template generation."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner


runner = CliRunner()


class TestNodeTestGeneration:
    """Test test file generation for nodes."""

    def test_new_node_creates_test_file(self):
        """Should create test file when creating node."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create project structure
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "tests" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "node", "fetch_data"])

                test_file = Path(tmpdir) / "tests" / "nodes" / "test_fetch_data.py"
                assert test_file.exists()
            finally:
                os.chdir(original_cwd)

    def test_test_file_imports_node(self):
        """Should import the node in test file."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "tests" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "node", "process_data"])

                test_content = (Path(tmpdir) / "tests" / "nodes" / "test_process_data.py").read_text()
                assert "from nodes.process_data import" in test_content
            finally:
                os.chdir(original_cwd)

    def test_test_file_has_test_class(self):
        """Should have test class."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "tests" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "node", "my_node"])

                test_content = (Path(tmpdir) / "tests" / "nodes" / "test_my_node.py").read_text()
                assert "class Test" in test_content
            finally:
                os.chdir(original_cwd)

    def test_test_file_has_success_test(self):
        """Should have success test case."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "tests" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "node", "test_node"])

                test_content = (Path(tmpdir) / "tests" / "nodes" / "test_test_node.py").read_text()
                assert "def test_" in test_content
                assert "success" in test_content.lower()
            finally:
                os.chdir(original_cwd)

    def test_test_file_has_error_test(self):
        """Should have error test case."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "tests" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "node", "error_node"])

                test_content = (Path(tmpdir) / "tests" / "nodes" / "test_error_node.py").read_text()
                assert "error" in test_content.lower()
            finally:
                os.chdir(original_cwd)

    def test_test_file_uses_pytest(self):
        """Should use pytest conventions."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "tests" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "node", "pytest_node"])

                test_content = (Path(tmpdir) / "tests" / "nodes" / "test_pytest_node.py").read_text()
                assert "import pytest" in test_content
            finally:
                os.chdir(original_cwd)

    def test_test_file_has_mock_imports(self):
        """Should import mock utilities."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "tests" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "node", "mock_node"])

                test_content = (Path(tmpdir) / "tests" / "nodes" / "test_mock_node.py").read_text()
                assert "mock" in test_content.lower() or "Mock" in test_content
            finally:
                os.chdir(original_cwd)


class TestTestDirectoryCreation:
    """Test tests directory creation."""

    def test_creates_tests_dir_if_missing(self):
        """Should create tests/nodes/ if missing."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()
            # No tests/ directory
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "node", "new_node"])

                assert (Path(tmpdir) / "tests" / "nodes").exists()
                assert (Path(tmpdir) / "tests" / "nodes" / "test_new_node.py").exists()
            finally:
                os.chdir(original_cwd)


class TestExistingTestPreservation:
    """Test that existing tests are not overwritten."""

    def test_does_not_overwrite_existing_test(self):
        """Should not overwrite existing test file."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "tests" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "nodes" / "__init__.py").touch()

            # Create existing test
            existing_test = Path(tmpdir) / "tests" / "nodes" / "test_existing.py"
            existing_test.write_text("# My custom test\ndef test_custom(): pass")
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                # Force create node (overwrites node, but not test)
                runner.invoke(app, ["new", "node", "existing", "--force"])

                test_content = existing_test.read_text()
                assert "# My custom test" in test_content
            finally:
                os.chdir(original_cwd)
