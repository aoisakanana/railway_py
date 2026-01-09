"""Tests for TUTORIAL.md generation."""

import os
import tempfile
from pathlib import Path

import pytest


class TestTutorialGeneration:
    """Test TUTORIAL.md generation."""

    def test_init_creates_tutorial(self):
        """Should create TUTORIAL.md."""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)

            tutorial = project_path / "TUTORIAL.md"
            assert tutorial.exists()

    def test_tutorial_has_title(self):
        """Should have title with project name."""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "my_automation"
            _create_project_structure(project_path, "my_automation", "3.10", False)

            content = (project_path / "TUTORIAL.md").read_text()
            assert "my_automation" in content or "Tutorial" in content

    def test_tutorial_has_quick_start(self):
        """Should have quick start section."""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)

            content = (project_path / "TUTORIAL.md").read_text()
            assert "quick start" in content.lower() or "step 1" in content.lower()

    def test_tutorial_has_code_examples(self):
        """Should have code examples."""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)

            content = (project_path / "TUTORIAL.md").read_text()
            assert "```" in content  # Code blocks

    def test_tutorial_mentions_railway_commands(self):
        """Should mention railway CLI commands."""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)

            content = (project_path / "TUTORIAL.md").read_text()
            assert "railway" in content.lower()

    def test_tutorial_has_troubleshooting(self):
        """Should have troubleshooting section."""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)

            content = (project_path / "TUTORIAL.md").read_text()
            # May have troubleshooting or common errors section
            assert "error" in content.lower() or "troubleshoot" in content.lower()


class TestTutorialContent:
    """Test TUTORIAL.md content quality."""

    def test_tutorial_explains_node_decorator(self):
        """Should explain @node decorator."""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)

            content = (project_path / "TUTORIAL.md").read_text()
            assert "@node" in content

    def test_tutorial_explains_entry_point(self):
        """Should explain @entry_point decorator."""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)

            content = (project_path / "TUTORIAL.md").read_text()
            assert "@entry_point" in content or "entry_point" in content

    def test_tutorial_explains_pipeline(self):
        """Should explain pipeline function."""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)

            content = (project_path / "TUTORIAL.md").read_text()
            assert "pipeline" in content.lower()

    def test_tutorial_explains_settings(self):
        """Should explain settings usage."""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)

            content = (project_path / "TUTORIAL.md").read_text()
            assert "settings" in content.lower() or "config" in content.lower()

    def test_tutorial_has_testing_section(self):
        """Should have testing section."""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)

            content = (project_path / "TUTORIAL.md").read_text()
            assert "test" in content.lower() or "pytest" in content.lower()
