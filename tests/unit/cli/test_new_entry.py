"""Tests for railway new entry command."""
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


def _init_project(path: Path):
    """Initialize a minimal project structure."""
    (path / "src").mkdir()
    (path / "src" / "nodes").mkdir()
    (path / "transition_graphs").mkdir()
    (path / "_railway" / "generated").mkdir(parents=True)
    (path / "pyproject.toml").write_text('[project]\nname = "test"')


class TestNewEntryDefault:
    """Test default (dag_runner) mode."""

    def test_creates_dag_entry_by_default(self, tmp_path, monkeypatch):
        """Should create dag_runner style entry by default."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(app, ["new", "entry", "my_workflow"])

        assert result.exit_code == 0

        # Check entry file contains dag_runner
        entry_file = tmp_path / "src" / "my_workflow.py"
        assert entry_file.exists()
        content = entry_file.read_text()
        assert "dag_runner" in content
        assert "TRANSITION_TABLE" in content
        assert "typed_pipeline" not in content

    def test_creates_transition_yaml(self, tmp_path, monkeypatch):
        """Should create transition graph YAML."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(app, ["new", "entry", "my_workflow"])

        assert result.exit_code == 0

        # Check YAML exists
        yamls = list((tmp_path / "transition_graphs").glob("my_workflow_*.yml"))
        assert len(yamls) == 1

    def test_creates_node_with_outcome(self, tmp_path, monkeypatch):
        """Should create node returning Outcome."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(app, ["new", "entry", "my_workflow"])

        assert result.exit_code == 0

        # Check node file
        node_file = tmp_path / "src" / "nodes" / "my_workflow" / "start.py"
        assert node_file.exists()
        content = node_file.read_text()
        assert "Outcome" in content
        assert "tuple[" in content

    def test_yaml_is_valid(self, tmp_path, monkeypatch):
        """Created YAML should be valid."""
        from railway.cli.main import app
        from railway.core.dag.parser import load_transition_graph

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(app, ["new", "entry", "my_workflow"])

        assert result.exit_code == 0

        yamls = list((tmp_path / "transition_graphs").glob("my_workflow_*.yml"))
        graph = load_transition_graph(yamls[0])
        assert graph.entrypoint == "my_workflow"


class TestNewEntryLinearMode:
    """Test linear (typed_pipeline) mode."""

    def test_creates_pipeline_entry_with_linear_flag(self, tmp_path, monkeypatch):
        """Should create typed_pipeline style entry with --mode linear."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(app, ["new", "entry", "my_workflow", "--mode", "linear"])

        assert result.exit_code == 0

        # Check entry file contains typed_pipeline
        entry_file = tmp_path / "src" / "my_workflow.py"
        content = entry_file.read_text()
        assert "typed_pipeline" in content
        assert "dag_runner" not in content

    def test_no_transition_yaml_in_linear_mode(self, tmp_path, monkeypatch):
        """Should NOT create transition YAML in linear mode."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(app, ["new", "entry", "my_workflow", "--mode", "linear"])

        assert result.exit_code == 0

        # No YAML should be created
        yamls = list((tmp_path / "transition_graphs").glob("my_workflow_*.yml"))
        assert len(yamls) == 0

    def test_creates_node_returning_contract(self, tmp_path, monkeypatch):
        """Should create node returning Contract only."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(app, ["new", "entry", "my_workflow", "--mode", "linear"])

        assert result.exit_code == 0

        # Check node file
        node_files = list((tmp_path / "src" / "nodes" / "my_workflow").glob("*.py"))
        # Filter out __init__.py
        node_files = [f for f in node_files if f.name != "__init__.py"]
        assert len(node_files) >= 1

        content = node_files[0].read_text()
        assert "Contract" in content
        assert "Outcome" not in content


class TestNewEntryValidation:
    """Test command validation."""

    def test_invalid_mode_error(self, tmp_path, monkeypatch):
        """Should error on invalid mode."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(app, ["new", "entry", "my_workflow", "--mode", "invalid"])

        assert result.exit_code != 0

    def test_dag_mode_explicit(self, tmp_path, monkeypatch):
        """Should work with explicit --mode dag."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(app, ["new", "entry", "my_workflow", "--mode", "dag"])

        assert result.exit_code == 0

        entry_file = tmp_path / "src" / "my_workflow.py"
        content = entry_file.read_text()
        assert "dag_runner" in content


class TestNewEntryOutput:
    """Test command output messages."""

    def test_shows_dag_mode_in_output(self, tmp_path, monkeypatch):
        """Should show mode in output message."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(app, ["new", "entry", "my_workflow"])

        assert "dag" in result.stdout.lower() or "DAG" in result.stdout

    def test_shows_linear_mode_in_output(self, tmp_path, monkeypatch):
        """Should show mode in output message."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(app, ["new", "entry", "my_workflow", "--mode", "linear"])

        assert "linear" in result.stdout.lower()
