"""Tests for entry point test template - ensuring sys.argv isolation."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestEntryTestTemplateUsesBoardMode:
    """Board モードのエントリテストテンプレートのテスト。"""

    def test_entry_test_template_imports_board(self):
        """Entry test template should import BoardBase."""
        from railway.cli.new import _get_entry_test_template

        template = _get_entry_test_template("main")

        assert "BoardBase" in template
        assert "from railway.core.board import BoardBase" in template

    def test_entry_test_template_tests_start_node(self):
        """Entry test template should test start node directly."""
        from railway.cli.new import _get_entry_test_template

        template = _get_entry_test_template("main")

        # Board モード: start ノードを直接インポートしてテスト
        assert "from nodes.main.start import start" in template
        assert "board = BoardBase()" in template
        assert "outcome = start(board)" in template

    def test_entry_test_template_checks_outcome(self):
        """Entry test template should check Outcome type."""
        from railway.cli.new import _get_entry_test_template

        template = _get_entry_test_template("main")

        assert "Outcome" in template
        assert "isinstance(outcome, Outcome)" in template


class TestGeneratedEntryTestRunnable:
    """Test that generated entry tests can run without errors."""

    def test_generated_entry_test_runs_without_error(self):
        """Generated entry test should run without import or sys.argv errors."""
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
                # Accept dependency resolution failure (unpublished version)
                if "No solution found" in result.stderr:
                    pytest.skip("railway-framework version not published on PyPI")
                # Board モード: railway.core.board が未公開の場合はスキップ
                combined_output = result.stdout + result.stderr
                if "No module named 'railway.core.board'" in combined_output:
                    pytest.skip("railway.core.board not available in published version")
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
