"""Tests for railway sync transition CLI command."""
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a minimal project structure."""
    # Create transition_graphs directory
    graphs_dir = tmp_path / "transition_graphs"
    graphs_dir.mkdir()

    # Create _railway/generated directory
    railway_dir = tmp_path / "_railway" / "generated"
    railway_dir.mkdir(parents=True)

    # Create a sample YAML
    yaml_content = dedent(
        """
        version: "1.0"
        entrypoint: top2
        description: "テストワークフロー"

        nodes:
          start:
            module: nodes.start
            function: start_node
            description: "開始ノード"

        exits:
          done:
            code: 0
            description: "完了"

        start: start

        transitions:
          start:
            success: exit::done
    """
    )
    (graphs_dir / "top2_20250125120000.yml").write_text(yaml_content)

    return tmp_path


class TestSyncTransitionCommand:
    """Test railway sync transition command."""

    def test_sync_single_entry(self, project_dir: Path, monkeypatch):
        """Should sync a single entrypoint."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--entry", "top2"])

        assert result.exit_code == 0
        assert "top2" in result.stdout

        # Check generated file exists
        generated = project_dir / "_railway" / "generated" / "top2_transitions.py"
        assert generated.exists()

    def test_sync_dry_run(self, project_dir: Path, monkeypatch):
        """Should show preview without writing files."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(
            app, ["sync", "transition", "--entry", "top2", "--dry-run"]
        )

        assert result.exit_code == 0
        assert "プレビュー" in result.stdout or "dry-run" in result.stdout.lower()

        # Should NOT create file
        generated = project_dir / "_railway" / "generated" / "top2_transitions.py"
        assert not generated.exists()

    def test_sync_validate_only(self, project_dir: Path, monkeypatch):
        """Should validate without generating code."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(
            app, ["sync", "transition", "--entry", "top2", "--validate-only"]
        )

        assert result.exit_code == 0
        assert "検証" in result.stdout or "valid" in result.stdout.lower()

    def test_sync_entry_not_found(self, project_dir: Path, monkeypatch):
        """Should error when entrypoint YAML not found."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--entry", "nonexistent"])

        assert result.exit_code != 0
        # Error may be in stdout or combined output
        output = result.output if result.output else ""
        assert "見つかりません" in output or "not found" in output.lower()

    def test_sync_all_entries(self, project_dir: Path, monkeypatch):
        """Should sync all entrypoints with --all flag."""
        from railway.cli.main import app

        # Add another YAML
        yaml2 = dedent(
            """
            version: "1.0"
            entrypoint: other
            description: ""
            nodes:
              a:
                module: nodes.a
                function: func_a
                description: ""
            exits:
              done:
                code: 0
                description: ""
            start: a
            transitions:
              a:
                success: exit::done
        """
        )
        (project_dir / "transition_graphs" / "other_20250125130000.yml").write_text(
            yaml2
        )

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--all"])

        assert result.exit_code == 0

        # Both files should be generated
        assert (project_dir / "_railway" / "generated" / "top2_transitions.py").exists()
        assert (
            project_dir / "_railway" / "generated" / "other_transitions.py"
        ).exists()

    def test_sync_validation_error(self, project_dir: Path, monkeypatch):
        """Should report validation errors."""
        from railway.cli.main import app

        # Create invalid YAML (missing start node)
        invalid_yaml = dedent(
            """
            version: "1.0"
            entrypoint: invalid
            description: ""
            nodes:
              a:
                module: nodes.a
                function: func_a
                description: ""
            exits: {}
            start: nonexistent
            transitions: {}
        """
        )
        (project_dir / "transition_graphs" / "invalid_20250125140000.yml").write_text(
            invalid_yaml
        )

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--entry", "invalid"])

        assert result.exit_code != 0
        # Error may be in stdout or combined output
        output = result.output if result.output else ""
        assert "エラー" in output or "error" in output.lower()


class TestFindLatestYaml:
    """Test YAML file discovery."""

    def test_find_latest_yaml(self, tmp_path: Path):
        """Should find the latest YAML by timestamp."""
        from railway.cli.sync import find_latest_yaml

        graphs_dir = tmp_path / "transition_graphs"
        graphs_dir.mkdir()

        # Create files with different timestamps
        (graphs_dir / "top2_20250101000000.yml").write_text("old")
        (graphs_dir / "top2_20250125120000.yml").write_text("new")
        (graphs_dir / "top2_20250115000000.yml").write_text("middle")

        latest = find_latest_yaml(graphs_dir, "top2")

        assert latest is not None
        assert latest.name == "top2_20250125120000.yml"

    def test_find_latest_yaml_none(self, tmp_path: Path):
        """Should return None when no matching YAML exists."""
        from railway.cli.sync import find_latest_yaml

        graphs_dir = tmp_path / "transition_graphs"
        graphs_dir.mkdir()

        latest = find_latest_yaml(graphs_dir, "nonexistent")

        assert latest is None

    def test_find_all_entrypoints(self, tmp_path: Path):
        """Should find all unique entrypoints."""
        from railway.cli.sync import find_all_entrypoints

        graphs_dir = tmp_path / "transition_graphs"
        graphs_dir.mkdir()

        (graphs_dir / "top2_20250101.yml").write_text("")
        (graphs_dir / "top2_20250102.yml").write_text("")
        (graphs_dir / "other_20250101.yml").write_text("")

        entries = find_all_entrypoints(graphs_dir)

        assert set(entries) == {"top2", "other"}


class TestSyncOutput:
    """Test sync command output formatting."""

    def test_success_message(self, project_dir: Path, monkeypatch):
        """Should show success message with details."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--entry", "top2"])

        assert (
            "✓" in result.stdout
            or "成功" in result.stdout
            or "Success" in result.stdout
        )

    def test_shows_generated_path(self, project_dir: Path, monkeypatch):
        """Should show path to generated file."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--entry", "top2"])

        assert "_railway/generated/top2_transitions.py" in result.stdout
