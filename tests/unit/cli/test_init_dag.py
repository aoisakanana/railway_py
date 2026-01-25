"""Tests for DAG-related project initialization."""
import pytest
from pathlib import Path


class TestInitCreatesDAGDirectories:
    """Test that init creates DAG workflow directories."""

    def test_creates_transition_graphs_dir(self, tmp_path, monkeypatch):
        """Should create transition_graphs directory."""
        from typer.testing import CliRunner

        from railway.cli.main import app

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init", "my_project"])

        assert result.exit_code == 0
        project_dir = tmp_path / "my_project"
        assert (project_dir / "transition_graphs").exists()
        assert (project_dir / "transition_graphs" / ".gitkeep").exists()

    def test_creates_railway_generated_dir(self, tmp_path, monkeypatch):
        """Should create _railway/generated directory."""
        from typer.testing import CliRunner

        from railway.cli.main import app

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init", "my_project"])

        assert result.exit_code == 0
        project_dir = tmp_path / "my_project"
        assert (project_dir / "_railway" / "generated").exists()
        assert (project_dir / "_railway" / "generated" / ".gitkeep").exists()

    def test_gitignore_includes_generated(self, tmp_path, monkeypatch):
        """Should add generated files to .gitignore."""
        from typer.testing import CliRunner

        from railway.cli.main import app

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init", "my_project"])

        assert result.exit_code == 0
        gitignore = (tmp_path / "my_project" / ".gitignore").read_text()
        assert "_railway/generated" in gitignore


class TestInitCreatesSampleYAML:
    """Test that init creates sample transition graph YAML."""

    def test_creates_sample_yaml(self, tmp_path, monkeypatch):
        """Should create a sample transition graph YAML."""
        from typer.testing import CliRunner

        from railway.cli.main import app

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init", "my_project"])

        assert result.exit_code == 0
        graphs_dir = tmp_path / "my_project" / "transition_graphs"
        yaml_files = list(graphs_dir.glob("*.yml"))

        # Should have at least one sample YAML
        assert len(yaml_files) >= 1

    def test_sample_yaml_is_valid(self, tmp_path, monkeypatch):
        """Sample YAML should be parseable."""
        from typer.testing import CliRunner

        from railway.cli.main import app
        from railway.core.dag.parser import load_transition_graph

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init", "my_project"])

        assert result.exit_code == 0
        graphs_dir = tmp_path / "my_project" / "transition_graphs"
        yaml_files = list(graphs_dir.glob("*.yml"))

        for yaml_file in yaml_files:
            # Should not raise
            graph = load_transition_graph(yaml_file)
            assert graph.version == "1.0"

    def test_sample_yaml_filename_has_timestamp(self, tmp_path, monkeypatch):
        """Sample YAML filename should include timestamp."""
        from typer.testing import CliRunner

        from railway.cli.main import app

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init", "my_project"])

        assert result.exit_code == 0
        graphs_dir = tmp_path / "my_project" / "transition_graphs"
        yaml_files = list(graphs_dir.glob("*.yml"))

        # File should be named like hello_20250126000000.yml
        for yaml_file in yaml_files:
            parts = yaml_file.stem.split("_")
            assert len(parts) == 2
            # Second part should be a timestamp (14 digits)
            assert len(parts[1]) == 14
            assert parts[1].isdigit()


class TestInitOutputMessage:
    """Test that init shows DAG-related directories in output."""

    def test_shows_transition_graphs_in_structure(self, tmp_path, monkeypatch):
        """Should show transition_graphs in project structure output."""
        from typer.testing import CliRunner

        from railway.cli.main import app

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init", "my_project"])

        assert result.exit_code == 0
        assert "transition_graphs" in result.stdout
