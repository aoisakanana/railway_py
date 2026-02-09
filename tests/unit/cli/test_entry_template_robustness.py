"""Tests for entry test template robustness - ensuring tests work after user rewrites."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestEntryTestTemplateUsesMainTyperApp:
    """Test that entry test template uses main._typer_app instead of app."""

    def test_entry_test_template_imports_main_not_app(self):
        """Entry test template should import main, not app."""
        from railway.cli.new import _get_entry_test_template

        template = _get_entry_test_template("user_report")

        # Should import main
        assert "from user_report import main" in template
        # Should NOT import app directly
        assert "from user_report import app" not in template

    def test_entry_test_template_uses_main_typer_app(self):
        """Entry test template should use main._typer_app for CliRunner."""
        from railway.cli.new import _get_entry_test_template

        template = _get_entry_test_template("user_report")

        # Should use main._typer_app
        assert "main._typer_app" in template

    def test_entry_test_template_still_uses_clirunner(self):
        """Entry test template should still use CliRunner pattern."""
        from railway.cli.new import _get_entry_test_template

        template = _get_entry_test_template("user_report")

        assert "CliRunner" in template
        assert "runner.invoke" in template


class TestEntryTestWorksAfterRewrite:
    """Test that generated entry tests work even after user rewrites entry point."""

    def test_entry_test_works_with_minimal_entry_point(self):
        """Generated test should work with minimal entry point (no app export)."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                # Create project
                runner.invoke(app, ["init", "test_project"])
                os.chdir(Path(tmpdir) / "test_project")

                # Create entry point
                runner.invoke(app, ["new", "entry", "my_report"])

                # Simulate user rewriting entry point (remove app export)
                entry_file = Path("src/my_report.py")
                minimal_content = '''"""My report entry point."""

from railway import entry_point


@entry_point
def main():
    """Minimal entry point without app export."""
    print("Report generated")
    return {"status": "success"}


if __name__ == "__main__":
    main()
'''
                entry_file.write_text(minimal_content)

                # Run the generated test - should still work
                result = subprocess.run(
                    ["uv", "run", "pytest", "tests/test_my_report.py", "-v"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                # Should pass or skip, not fail with ImportError
                assert "ImportError" not in result.stderr
                assert "cannot import name 'app'" not in result.stderr
                # Accept dependency resolution failure (unpublished version)
                if "No solution found" in result.stderr:
                    pytest.skip("railway-framework version not published on PyPI")
                assert result.returncode in [0, 5], (
                    f"Test failed:\n{result.stdout}\n{result.stderr}"
                )
            finally:
                os.chdir(original_cwd)
