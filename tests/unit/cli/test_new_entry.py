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

        # Check entry file uses run() helper (v0.13.1+)
        entry_file = tmp_path / "src" / "my_workflow.py"
        assert entry_file.exists()
        content = entry_file.read_text()
        # v0.13.1+: run() ヘルパーを使用（dag_runner は直接呼び出さない）
        assert "from _railway.generated.my_workflow_transitions import run" in content
        assert "result = run(" in content
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

    def test_creates_board_mode_node(self, tmp_path, monkeypatch):
        """Should create Board mode node (board argument, returns Outcome)."""
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
        assert "def start(board)" in content

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


class TestNewEntryOutput:
    """Test command output messages."""

    def test_shows_dag_mode_in_output(self, tmp_path, monkeypatch):
        """Should show mode in output message."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(app, ["new", "entry", "my_workflow"])

        assert "dag" in result.stdout.lower() or "DAG" in result.stdout
