"""Tests for TUTORIAL mypy troubleshooting section."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestTutorialHasMypyTroubleshooting:
    """Test that TUTORIAL includes mypy troubleshooting guidance."""

    def test_tutorial_has_mypy_troubleshooting_section(self):
        """TUTORIAL should have troubleshooting for mypy issues."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                # Should mention troubleshooting for mypy
                has_troubleshooting = (
                    "トラブルシューティング" in content
                    or "Troubleshooting" in content
                    or "問題が発生" in content
                )
                assert has_troubleshooting, "TUTORIAL should have troubleshooting section"
            finally:
                os.chdir(original_cwd)

    def test_tutorial_mentions_mypy_cache_clear(self):
        """TUTORIAL should mention clearing mypy cache as solution."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                # Should mention mypy cache
                assert ".mypy_cache" in content or "mypy_cache" in content
            finally:
                os.chdir(original_cwd)

    def test_tutorial_mentions_package_reinstall(self):
        """TUTORIAL should mention reinstalling package as solution."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                # Should mention reinstalling or uv sync
                has_reinstall = (
                    "再インストール" in content
                    or "uv sync" in content
                    or "pip install" in content
                )
                assert has_reinstall, "TUTORIAL should mention reinstalling package"
            finally:
                os.chdir(original_cwd)
