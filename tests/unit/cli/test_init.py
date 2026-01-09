"""Tests for railway init command."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestRailwayInit:
    """Test railway init command."""

    def test_init_creates_project_directory(self):
        """Should create project directory."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["init", "my_project"])
                assert result.exit_code == 0
                assert (Path(tmpdir) / "my_project").exists()
            finally:
                os.chdir(original_cwd)

    def test_init_creates_src_directory(self):
        """Should create src directory."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project"])
                assert (Path(tmpdir) / "my_project" / "src").exists()
                assert (Path(tmpdir) / "my_project" / "src" / "__init__.py").exists()
            finally:
                os.chdir(original_cwd)

    def test_init_creates_tests_directory(self):
        """Should create tests directory."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project"])
                assert (Path(tmpdir) / "my_project" / "tests").exists()
                assert (Path(tmpdir) / "my_project" / "tests" / "conftest.py").exists()
            finally:
                os.chdir(original_cwd)

    def test_init_creates_config_directory(self):
        """Should create config directory with YAML files."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project"])
                config_dir = Path(tmpdir) / "my_project" / "config"
                assert config_dir.exists()
                assert (config_dir / "development.yaml").exists()
            finally:
                os.chdir(original_cwd)

    def test_init_creates_logs_directory(self):
        """Should create logs directory."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project"])
                assert (Path(tmpdir) / "my_project" / "logs").exists()
            finally:
                os.chdir(original_cwd)

    def test_init_creates_pyproject_toml(self):
        """Should create pyproject.toml."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project"])
                pyproject = Path(tmpdir) / "my_project" / "pyproject.toml"
                assert pyproject.exists()
                content = pyproject.read_text()
                assert "my_project" in content
                assert "railway" in content.lower()
            finally:
                os.chdir(original_cwd)

    def test_init_creates_env_example(self):
        """Should create .env.example."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project"])
                env_example = Path(tmpdir) / "my_project" / ".env.example"
                assert env_example.exists()
                content = env_example.read_text()
                assert "RAILWAY_ENV" in content
            finally:
                os.chdir(original_cwd)

    def test_init_creates_settings_py(self):
        """Should create settings.py."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project"])
                settings = Path(tmpdir) / "my_project" / "src" / "settings.py"
                assert settings.exists()
                content = settings.read_text()
                assert "Settings" in content
            finally:
                os.chdir(original_cwd)

    def test_init_creates_tutorial_md(self):
        """Should create TUTORIAL.md."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project"])
                tutorial = Path(tmpdir) / "my_project" / "TUTORIAL.md"
                assert tutorial.exists()
            finally:
                os.chdir(original_cwd)

    def test_init_creates_gitignore(self):
        """Should create .gitignore."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project"])
                gitignore = Path(tmpdir) / "my_project" / ".gitignore"
                assert gitignore.exists()
                content = gitignore.read_text()
                assert ".env" in content
                assert "__pycache__" in content
            finally:
                os.chdir(original_cwd)


class TestRailwayInitOptions:
    """Test railway init command options."""

    def test_init_with_python_version(self):
        """Should use specified Python version."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project", "--python-version", "3.11"])
                pyproject = Path(tmpdir) / "my_project" / "pyproject.toml"
                content = pyproject.read_text()
                assert "3.11" in content
            finally:
                os.chdir(original_cwd)

    def test_init_with_examples(self):
        """Should create example entry point with --with-examples."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project", "--with-examples"])
                # Should have example entry point
                hello = Path(tmpdir) / "my_project" / "src" / "hello.py"
                assert hello.exists()
            finally:
                os.chdir(original_cwd)


class TestRailwayInitErrors:
    """Test railway init error handling."""

    def test_init_existing_directory_fails(self):
        """Should fail if directory already exists."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                (Path(tmpdir) / "existing_project").mkdir()
                result = runner.invoke(app, ["init", "existing_project"])
                assert result.exit_code != 0
                # Error message is written to stderr, check output (stdout + stderr combined)
                output = result.output.lower() if result.output else ""
                assert "already exists" in output
            finally:
                os.chdir(original_cwd)

    def test_init_invalid_project_name(self):
        """Should normalize project names with dashes."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["init", "my-project"])
                # Should normalize to my_project
                assert result.exit_code == 0
                assert (Path(tmpdir) / "my_project").exists()
            finally:
                os.chdir(original_cwd)


class TestRailwayInitOutput:
    """Test railway init output messages."""

    def test_init_shows_success_message(self):
        """Should show success message."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["init", "my_project"])
                assert "Created" in result.stdout or "created" in result.stdout.lower()
            finally:
                os.chdir(original_cwd)

    def test_init_shows_next_steps(self):
        """Should show next steps."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["init", "my_project"])
                assert "cd my_project" in result.stdout or "Next" in result.stdout
            finally:
                os.chdir(original_cwd)
