"""Tests for railway init hello entry creation."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestInitCreatesHelloEntry:
    """Test that railway init creates hello.py by default."""

    def test_init_creates_hello_py_by_default(self):
        """railway init should create src/hello.py by default."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["init", "test_project"])

                assert result.exit_code == 0, f"Init failed: {result.stdout}"

                hello_py = Path(tmpdir) / "test_project" / "src" / "hello.py"
                assert hello_py.exists(), f"hello.py not found at {hello_py}"
            finally:
                os.chdir(original_cwd)

    def test_hello_py_contains_entry_point_decorator(self):
        """Generated hello.py should contain @entry_point decorator."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                hello_py = Path(tmpdir) / "test_project" / "src" / "hello.py"
                content = hello_py.read_text()

                assert "@entry_point" in content
            finally:
                os.chdir(original_cwd)

    def test_hello_py_contains_hello_message(self):
        """Generated hello.py should print a hello message."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                hello_py = Path(tmpdir) / "test_project" / "src" / "hello.py"
                content = hello_py.read_text()

                assert "Hello" in content
                assert "Railway" in content
            finally:
                os.chdir(original_cwd)

    def test_hello_py_is_simple_not_complex(self):
        """Default hello.py should be simple (no pipeline/node chain)."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                hello_py = Path(tmpdir) / "test_project" / "src" / "hello.py"
                content = hello_py.read_text()

                # Should NOT contain complex pipeline
                assert "validate_name" not in content
                assert "create_greeting" not in content
            finally:
                os.chdir(original_cwd)


class TestInitWithExamplesCreatesComplexEntry:
    """Test that --with-examples creates complex example."""

    def test_with_examples_creates_complex_hello(self):
        """--with-examples should create a more complex example."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["init", "test_project", "--with-examples"])

                assert result.exit_code == 0

                hello_py = Path(tmpdir) / "test_project" / "src" / "hello.py"
                content = hello_py.read_text()

                # Complex example should contain pipeline usage
                assert "pipeline" in content
            finally:
                os.chdir(original_cwd)


class TestInitNextStepsOutput:
    """Test that init shows correct next steps."""

    def test_next_steps_shows_railway_run_hello(self):
        """Next steps should show 'railway run hello' command."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["init", "test_project"])

                # Should mention running hello
                assert "railway run hello" in result.stdout or "run hello" in result.stdout
            finally:
                os.chdir(original_cwd)
