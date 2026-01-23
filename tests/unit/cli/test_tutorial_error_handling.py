"""Tests for TUTORIAL error handling content."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch


class TestTutorialErrorHandlingContent:
    """Test that TUTORIAL contains error handling experience section."""

    def test_tutorial_contains_step_8(self, tmp_path: Path):
        """TUTORIAL should have Step 8 for error handling."""
        from railway.cli.init import init as cli_init

        # Change to tmp_path and use just the project name
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with patch("railway.cli.init.typer.echo"):
                cli_init("test_project")

            tutorial_path = tmp_path / "test_project" / "TUTORIAL.md"
            content = tutorial_path.read_text(encoding="utf-8")

            assert "Step 8" in content
            assert "エラーハンドリング" in content
        finally:
            os.chdir(original_cwd)

    def test_tutorial_contains_on_error(self, tmp_path: Path):
        """TUTORIAL should explain on_error callback."""
        from railway.cli.init import init as cli_init

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with patch("railway.cli.init.typer.echo"):
                cli_init("test_project")

            tutorial_path = tmp_path / "test_project" / "TUTORIAL.md"
            content = tutorial_path.read_text(encoding="utf-8")

            assert "on_error" in content
            assert "smart_error_handler" in content or "handle_error" in content
        finally:
            os.chdir(original_cwd)

    def test_tutorial_contains_retry_on(self, tmp_path: Path):
        """TUTORIAL should explain retry_on feature."""
        from railway.cli.init import init as cli_init

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with patch("railway.cli.init.typer.echo"):
                cli_init("test_project")

            tutorial_path = tmp_path / "test_project" / "TUTORIAL.md"
            content = tutorial_path.read_text(encoding="utf-8")

            assert "retry_on" in content
            assert "retries" in content
        finally:
            os.chdir(original_cwd)

    def test_tutorial_contains_on_step(self, tmp_path: Path):
        """TUTORIAL should explain on_step callback."""
        from railway.cli.init import init as cli_init

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with patch("railway.cli.init.typer.echo"):
                cli_init("test_project")

            tutorial_path = tmp_path / "test_project" / "TUTORIAL.md"
            content = tutorial_path.read_text(encoding="utf-8")

            assert "on_step" in content
            assert "capture_step" in content or "デバッグ" in content
        finally:
            os.chdir(original_cwd)


class TestTutorialFAQ:
    """Test that TUTORIAL contains FAQ section."""

    def test_tutorial_contains_faq(self, tmp_path: Path):
        """TUTORIAL should have FAQ section."""
        from railway.cli.init import init as cli_init

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with patch("railway.cli.init.typer.echo"):
                cli_init("test_project")

            tutorial_path = tmp_path / "test_project" / "TUTORIAL.md"
            content = tutorial_path.read_text(encoding="utf-8")

            assert "FAQ" in content or "よくある質問" in content
        finally:
            os.chdir(original_cwd)

    def test_tutorial_explains_no_result_type(self, tmp_path: Path):
        """TUTORIAL should explain why Result type is not adopted."""
        from railway.cli.init import init as cli_init

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with patch("railway.cli.init.typer.echo"):
                cli_init("test_project")

            tutorial_path = tmp_path / "test_project" / "TUTORIAL.md"
            content = tutorial_path.read_text(encoding="utf-8")

            # Check for Result type mention
            assert "Result" in content
            # Check for explanation (either Japanese or keywords)
            assert "採用" in content or "例外ベース" in content or "exception" in content.lower()
        finally:
            os.chdir(original_cwd)


class TestTutorialPracticalScenario:
    """Test that TUTORIAL has practical scenario."""

    def test_tutorial_contains_practical_scenario(self, tmp_path: Path):
        """TUTORIAL should have practical scenario with external API."""
        from railway.cli.init import init as cli_init

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with patch("railway.cli.init.typer.echo"):
                cli_init("test_project")

            tutorial_path = tmp_path / "test_project" / "TUTORIAL.md"
            content = tutorial_path.read_text(encoding="utf-8")

            # Check for practical scenario
            assert "シナリオ" in content or "外部API" in content or "ConnectionError" in content
        finally:
            os.chdir(original_cwd)

    def test_tutorial_error_handling_levels(self, tmp_path: Path):
        """TUTORIAL should explain different levels of error handling."""
        from railway.cli.init import init as cli_init

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with patch("railway.cli.init.typer.echo"):
                cli_init("test_project")

            tutorial_path = tmp_path / "test_project" / "TUTORIAL.md"
            content = tutorial_path.read_text(encoding="utf-8")

            # Check for level mentions
            assert "レベル" in content or "Level" in content
            # Check for key concepts
            assert "伝播" in content or "propagate" in content.lower()
        finally:
            os.chdir(original_cwd)
