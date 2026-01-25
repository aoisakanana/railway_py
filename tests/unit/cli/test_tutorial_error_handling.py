"""Tests for TUTORIAL error handling content."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch


class TestTutorialErrorHandlingContent:
    """Test that TUTORIAL contains error handling experience section."""

    def test_tutorial_contains_error_handling_step(self, tmp_path: Path):
        """TUTORIAL should have error handling section."""
        from railway.cli.init import init as cli_init

        # Change to tmp_path and use just the project name
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with patch("railway.cli.init.typer.echo"):
                cli_init("test_project")

            tutorial_path = tmp_path / "test_project" / "TUTORIAL.md"
            content = tutorial_path.read_text(encoding="utf-8")

            # Should have error handling section (step number may vary)
            assert "エラーハンドリング" in content or "失敗パス" in content
        finally:
            os.chdir(original_cwd)

    def test_tutorial_contains_callback_concepts(self, tmp_path: Path):
        """TUTORIAL should mention callback concepts (on_step, on_error, or StepRecorder)."""
        from railway.cli.init import init as cli_init

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with patch("railway.cli.init.typer.echo"):
                cli_init("test_project")

            tutorial_path = tmp_path / "test_project" / "TUTORIAL.md"
            content = tutorial_path.read_text(encoding="utf-8")

            # Should mention callback concepts (dag_runner or typed_pipeline style)
            has_callback = (
                "on_step" in content
                or "on_error" in content
                or "StepRecorder" in content
                or "コールバック" in content
            )
            assert has_callback, "Should mention callback concepts"
        finally:
            os.chdir(original_cwd)


class TestTutorialFAQ:
    """Test that TUTORIAL contains FAQ or troubleshooting section."""

    def test_tutorial_contains_troubleshooting(self, tmp_path: Path):
        """TUTORIAL should have FAQ or troubleshooting section."""
        from railway.cli.init import init as cli_init

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with patch("railway.cli.init.typer.echo"):
                cli_init("test_project")

            tutorial_path = tmp_path / "test_project" / "TUTORIAL.md"
            content = tutorial_path.read_text(encoding="utf-8")

            has_help_section = (
                "FAQ" in content
                or "よくある質問" in content
                or "トラブルシューティング" in content
            )
            assert has_help_section, "Should have FAQ or troubleshooting section"
        finally:
            os.chdir(original_cwd)


class TestTutorialPracticalScenario:
    """Test that TUTORIAL has practical examples."""

    def test_tutorial_contains_practical_example(self, tmp_path: Path):
        """TUTORIAL should have practical examples."""
        from railway.cli.init import init as cli_init

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with patch("railway.cli.init.typer.echo"):
                cli_init("test_project")

            tutorial_path = tmp_path / "test_project" / "TUTORIAL.md"
            content = tutorial_path.read_text(encoding="utf-8")

            # Check for practical examples
            has_example = (
                "シナリオ" in content
                or "ワークフロー" in content
                or "遷移" in content
                or "例" in content
            )
            assert has_example, "Should have practical examples"
        finally:
            os.chdir(original_cwd)

    def test_tutorial_has_code_examples(self, tmp_path: Path):
        """TUTORIAL should have code examples."""
        from railway.cli.init import init as cli_init

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with patch("railway.cli.init.typer.echo"):
                cli_init("test_project")

            tutorial_path = tmp_path / "test_project" / "TUTORIAL.md"
            content = tutorial_path.read_text(encoding="utf-8")

            # Check for code blocks
            assert "```python" in content or "```bash" in content
        finally:
            os.chdir(original_cwd)
