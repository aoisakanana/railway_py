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
        entrypoint: entry2
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
    (graphs_dir / "entry2_20250125120000.yml").write_text(yaml_content)

    return tmp_path


class TestSyncTransitionCommand:
    """Test railway sync transition command."""

    def test_sync_single_entry(self, project_dir: Path, monkeypatch):
        """Should sync a single entrypoint."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--entry", "entry2"])

        assert result.exit_code == 0
        assert "entry2" in result.stdout

        # Check generated file exists
        generated = project_dir / "_railway" / "generated" / "entry2_transitions.py"
        assert generated.exists()

    def test_sync_dry_run(self, project_dir: Path, monkeypatch):
        """Should show preview without writing files."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(
            app, ["sync", "transition", "--entry", "entry2", "--dry-run"]
        )

        assert result.exit_code == 0
        assert "プレビュー" in result.stdout or "dry-run" in result.stdout.lower()

        # Should NOT create file
        generated = project_dir / "_railway" / "generated" / "entry2_transitions.py"
        assert not generated.exists()

    def test_sync_validate_only(self, project_dir: Path, monkeypatch):
        """Should validate without generating code."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(
            app, ["sync", "transition", "--entry", "entry2", "--validate-only"]
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
        assert (project_dir / "_railway" / "generated" / "entry2_transitions.py").exists()
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
        (graphs_dir / "entry2_20250101000000.yml").write_text("old")
        (graphs_dir / "entry2_20250125120000.yml").write_text("new")
        (graphs_dir / "entry2_20250115000000.yml").write_text("middle")

        latest = find_latest_yaml(graphs_dir, "entry2")

        assert latest is not None
        assert latest.name == "entry2_20250125120000.yml"

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

        (graphs_dir / "entry2_20250101.yml").write_text("")
        (graphs_dir / "entry2_20250102.yml").write_text("")
        (graphs_dir / "other_20250101.yml").write_text("")

        entries = find_all_entrypoints(graphs_dir)

        assert set(entries) == {"entry2", "other"}


class TestConvertYamlIfOldFormat:
    """Test _convert_yaml_if_old_format function."""

    def test_new_format_valid_shows_message(self, tmp_path: Path, capsys):
        """新形式かつスキーマ検証成功時は「既に新形式」を表示。"""
        from railway.cli.sync import _convert_yaml_if_old_format

        yaml_content = """\
version: "1.0"
entrypoint: test
description: ""
nodes:
  start:
    module: nodes.start
    function: start
    description: ""
  exit:
    success:
      done:
        description: ""
start: start
transitions:
  start:
    success::done: exit.success.done
"""
        yaml_path = tmp_path / "test.yml"
        yaml_path.write_text(yaml_content)

        result = _convert_yaml_if_old_format(yaml_path)

        assert result.converted is False
        captured = capsys.readouterr()
        assert "既に新形式" in captured.out

    def test_new_format_invalid_no_message(self, tmp_path: Path, capsys):
        """新形式だがスキーマエラー時は「既に新形式」を表示しない。"""
        from railway.cli.sync import _convert_yaml_if_old_format

        # version がない不完全な YAML（exits もないので新形式扱い）
        yaml_content = """\
entrypoint: test
description: ""
nodes:
  start:
    description: ""
start: start
transitions: {}
"""
        yaml_path = tmp_path / "invalid.yml"
        yaml_path.write_text(yaml_content)

        result = _convert_yaml_if_old_format(yaml_path)

        assert result.converted is False
        captured = capsys.readouterr()
        # スキーマエラーがあるので「既に新形式」は表示されない
        assert "既に新形式" not in captured.out


class TestSyncOutput:
    """Test sync command output formatting."""

    def test_success_message(self, project_dir: Path, monkeypatch):
        """Should show success message with details."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--entry", "entry2"])

        assert (
            "✓" in result.stdout
            or "成功" in result.stdout
            or "Success" in result.stdout
        )

    def test_shows_generated_path(self, project_dir: Path, monkeypatch):
        """Should show path to generated file."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--entry", "entry2"])

        assert "_railway/generated/entry2_transitions.py" in result.stdout


class TestSyncPyTyped:
    """sync で py.typed が生成されるかのテスト（mypy 対応）"""

    def test_creates_py_typed_in_generated(self, project_dir: Path, monkeypatch):
        """sync で _railway/generated/py.typed が生成される"""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        runner.invoke(app, ["sync", "transition", "--entry", "entry2"])

        py_typed = project_dir / "_railway" / "generated" / "py.typed"
        assert py_typed.exists(), "py.typed should be created in _railway/generated/"

    def test_py_typed_is_empty(self, project_dir: Path, monkeypatch):
        """py.typed は空ファイル"""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        runner.invoke(app, ["sync", "transition", "--entry", "entry2"])

        py_typed = project_dir / "_railway" / "generated" / "py.typed"
        assert py_typed.read_text() == "", "py.typed should be empty"

    def test_py_typed_not_recreated_if_exists(self, project_dir: Path, monkeypatch):
        """py.typed が既に存在する場合は再作成しない"""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        # 先に py.typed を作成
        py_typed = project_dir / "_railway" / "generated" / "py.typed"
        py_typed.write_text("existing")

        runner.invoke(app, ["sync", "transition", "--entry", "entry2"])

        # 上書きされていないことを確認
        assert py_typed.read_text() == "existing"
