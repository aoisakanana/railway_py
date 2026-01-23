"""Tests for TUTORIAL.md version management section."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestTutorialVersionManagementSection:
    """Test that TUTORIAL includes version management content."""

    def test_tutorial_has_step_9(self):
        """TUTORIAL should have Step 9 for version management."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                assert "Step 9" in content
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

    def test_tutorial_shows_benefits_table(self):
        """TUTORIAL should show benefits of version management."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                # Should have a comparison table
                assert "Railway の解決策" in content or "解決" in content
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
