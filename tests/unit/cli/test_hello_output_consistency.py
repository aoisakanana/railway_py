"""Tests for hello output consistency with TUTORIAL."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestHelloOutputMatchesTutorial:
    """Test that hello.py output matches TUTORIAL expectation."""

    def test_hello_py_outputs_hello_world(self):
        """hello.py should output 'Hello, World!' to match TUTORIAL."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                hello_py = Path(tmpdir) / "test_project" / "src" / "hello.py"
                content = hello_py.read_text()

                # Should contain standard "Hello, World!" greeting
                assert 'print("Hello, World!")' in content
            finally:
                os.chdir(original_cwd)

    def test_hello_py_return_value_matches(self):
        """hello.py return value should also use 'Hello, World!'."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                hello_py = Path(tmpdir) / "test_project" / "src" / "hello.py"
                content = hello_py.read_text()

                # Return value should also match
                assert '"Hello, World!"' in content
            finally:
                os.chdir(original_cwd)

    def test_tutorial_expects_hello_world(self):
        """TUTORIAL should expect 'Hello, World!' output."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                # TUTORIAL should show expected output
                assert "Hello, World!" in content
            finally:
                os.chdir(original_cwd)
