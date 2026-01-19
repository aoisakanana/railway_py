"""Tests for generated test templates - ensuring they run without errors."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestGeneratedTestsRunnable:
    """Test that generated tests can be executed without crashing."""

    def test_typed_node_test_runs_without_error(self):
        """Generated typed node test should run without NameError or crash."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                # Create project
                runner.invoke(app, ["init", "test_project"])
                os.chdir(Path(tmpdir) / "test_project")

                # Create contract and typed node
                runner.invoke(app, ["new", "contract", "UserResult"])
                runner.invoke(app, ["new", "node", "fetch_users", "--output", "UserResult"])

                # Run the generated test
                result = subprocess.run(
                    ["uv", "run", "pytest", "tests/nodes/test_fetch_users.py", "-v"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                # Test should either pass or skip, but not fail with error
                # Exit code 0 = passed, Exit code 5 = no tests collected (skip), Exit code 1 = failed
                # We accept 0 (pass) or skipped tests
                assert result.returncode in [0, 5] or "skip" in result.stdout.lower(), (
                    f"Test failed with error:\n{result.stdout}\n{result.stderr}"
                )
            finally:
                os.chdir(original_cwd)

    def test_untyped_node_test_runs_without_error(self):
        """Generated untyped node test should run without error (skip is OK)."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                # Create project
                runner.invoke(app, ["init", "test_project"])
                os.chdir(Path(tmpdir) / "test_project")

                # Create untyped node
                runner.invoke(app, ["new", "node", "process_data"])

                # Run the generated test
                result = subprocess.run(
                    ["uv", "run", "pytest", "tests/nodes/test_process_data.py", "-v"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                # Should skip, not fail with error
                assert "skip" in result.stdout.lower() or result.returncode == 0, (
                    f"Test failed:\n{result.stdout}\n{result.stderr}"
                )
            finally:
                os.chdir(original_cwd)


class TestGeneratedTestsHaveSkip:
    """Test that generated tests use pytest.skip() appropriately."""

    def test_typed_node_test_template_contains_skip(self):
        """Typed node test template should contain pytest.skip."""
        from railway.cli.new import _get_typed_node_test_template

        template = _get_typed_node_test_template(
            name="fetch_users",
            output_type="UserResult",
            inputs=[("data", "InputType")],
        )

        assert "pytest.skip" in template or "skip" in template.lower()

    def test_untyped_node_test_template_contains_skip(self):
        """Untyped node test template should contain pytest.skip."""
        from railway.cli.new import _get_node_test_template

        template = _get_node_test_template("process_data")

        assert "pytest.skip" in template
