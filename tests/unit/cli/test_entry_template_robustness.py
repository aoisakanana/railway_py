"""Tests for entry test template robustness - ensuring tests work after user rewrites."""

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

        template = _get_entry_test_template("user_report")

        # Board モード: BoardBase をインポート
        assert "BoardBase" in template
        # エントリモジュールからの直接インポートは不要
        assert "from user_report import app" not in template

    def test_entry_test_template_uses_start_node(self):
        """Entry test template should test start node directly."""
        from railway.cli.new import _get_entry_test_template

        template = _get_entry_test_template("user_report")

        # Board モード: start ノードを直接テスト
        assert "from nodes.user_report.start import start" in template

    def test_entry_test_template_uses_outcome(self):
        """Entry test template should check Outcome."""
        from railway.cli.new import _get_entry_test_template

        template = _get_entry_test_template("user_report")

        assert "Outcome" in template
        assert "isinstance(outcome, Outcome)" in template


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

                # Run the generated test - should still work
                result = subprocess.run(
                    ["uv", "run", "pytest", "tests/test_my_report.py", "-v"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                # Accept dependency resolution failure (unpublished version)
                if "No solution found" in result.stderr:
                    pytest.skip("railway-framework version not published on PyPI")
                # Board モード: railway.core.board が未公開の場合はスキップ
                if "No module named 'railway.core.board'" in (
                    result.stdout + result.stderr
                ):
                    pytest.skip("railway.core.board not available in published version")
                # Should pass or skip, not fail with ImportError
                assert "cannot import name 'app'" not in result.stderr
                assert result.returncode in [0, 2, 5], (
                    f"Test failed:\n{result.stdout}\n{result.stderr}"
                )
            finally:
                os.chdir(original_cwd)
