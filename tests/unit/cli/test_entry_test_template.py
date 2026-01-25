"""Tests for entry point test template - ensuring sys.argv isolation."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestEntryTestTemplateUsesCliRunner:
    """Test that entry point test templates use CliRunner to avoid sys.argv issues."""

    def test_entry_test_template_imports_clirunner(self):
        """Entry test template should import CliRunner."""
        from railway.cli.new import _get_entry_test_template

        template = _get_entry_test_template("main")

        assert "CliRunner" in template
        assert "from typer.testing import CliRunner" in template

    def test_entry_test_template_uses_runner_invoke(self):
        """Entry test template should use runner.invoke() instead of direct call."""
        from railway.cli.new import _get_entry_test_template

        template = _get_entry_test_template("main")

        # Should use runner.invoke pattern
        assert "runner.invoke" in template
        # Should NOT directly call main() without runner
        lines = template.split("\n")
        for line in lines:
            # Skip lines that are comments or docstrings
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""'):
                continue
            # Check for direct function calls (not via runner)
            if "main()" in line and "runner.invoke" not in line:
                # Allow in comments/examples
                if "#" not in line.split("main()")[0]:
                    pytest.fail(f"Direct main() call found: {line}")

    def test_entry_test_template_checks_exit_code(self):
        """Entry test template should check exit_code for success."""
        from railway.cli.new import _get_entry_test_template

        template = _get_entry_test_template("main")

        assert "exit_code" in template


class TestGeneratedEntryTestRunnable:
    """Test that generated entry tests can run without sys.argv errors."""

    def test_generated_entry_test_runs_without_sysargv_error(self):
        """Generated entry test should not be affected by pytest's sys.argv."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                # Create project
                runner.invoke(app, ["init", "test_project"])
                os.chdir(Path(tmpdir) / "test_project")

                # Create entry point (use linear mode to avoid dag dependencies)
                runner.invoke(app, ["new", "entry", "process_data", "--mode", "linear"])

                # Run the generated test with verbose flag (the problematic case)
                result = subprocess.run(
                    ["uv", "run", "pytest", "tests/test_process_data.py", "-v"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                # Should not fail with sys.argv/typer errors
                assert "BadParameter" not in result.stderr
                assert "Invalid value" not in result.stderr
                # Should pass or skip, not error
                assert result.returncode in [0, 5], (
                    f"Test failed with sys.argv error:\n{result.stdout}\n{result.stderr}"
                )
            finally:
                os.chdir(original_cwd)


class TestEntryPointImplAttribute:
    """Test that entry_point decorator provides _impl for direct testing."""

    def test_entry_point_has_impl_attribute(self):
        """Entry point decorated function should have _impl attribute."""
        from railway import entry_point

        @entry_point
        def sample_entry():
            """Sample entry for testing."""
            return {"result": "success"}

        # Should have _impl attribute for direct testing
        assert hasattr(sample_entry, "_impl")

    def test_entry_point_impl_can_be_called_directly(self):
        """_impl should allow calling the function without Typer."""
        from railway import entry_point

        @entry_point
        def sample_entry():
            """Sample entry for testing."""
            return {"result": "success"}

        # Should be callable without sys.argv interference
        result = sample_entry._impl()
        assert result == {"result": "success"}
