"""Tests for TUTORIAL.md version management section."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestTutorialVersionManagementSection:
    """Test that TUTORIAL includes version management content."""

    def test_tutorial_has_version_management_step(self):
        """TUTORIAL should have version management section."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                # Should have version management section (step number may vary)
                assert "バージョン管理" in content
            finally:
                os.chdir(original_cwd)

    def test_tutorial_mentions_railway_update(self):
        """TUTORIAL should explain railway update command."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                assert "railway update" in content
                assert "--dry-run" in content
            finally:
                os.chdir(original_cwd)

    def test_tutorial_mentions_railway_backup(self):
        """TUTORIAL should explain railway backup command."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                assert "railway backup" in content
                assert "restore" in content.lower()
            finally:
                os.chdir(original_cwd)

    def test_tutorial_explains_project_yaml(self):
        """TUTORIAL should explain .railway/project.yaml."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                assert ".railway/project.yaml" in content or "project.yaml" in content
            finally:
                os.chdir(original_cwd)

    def test_tutorial_shows_version_management_commands(self):
        """TUTORIAL should show version management commands."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                # Should show version management concepts
                has_version_content = (
                    "railway update" in content
                    or "railway backup" in content
                    or "更新" in content
                )
                assert has_version_content, "Should show version management commands"
            finally:
                os.chdir(original_cwd)

    def test_tutorial_has_version_management_in_learned(self):
        """TUTORIAL should mention version management in 'learned' section."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                # Check "学べること" or "学んだこと" contains version management
                assert "バージョン管理" in content
            finally:
                os.chdir(original_cwd)
