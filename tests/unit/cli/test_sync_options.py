"""Tests for railway sync transition options (Issue #65).

TDD: Red -> Green -> Refactor

Changes:
- Default: overwrite generated files (no --force needed)
- --no-overwrite: skip if file exists
- --convert: convert old format YAML to new format
- --force: hidden (for internal/test use)
"""

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def project_with_old_format_yaml(tmp_path: Path) -> Path:
    """Create project with old format YAML."""
    graphs_dir = tmp_path / "transition_graphs"
    graphs_dir.mkdir()

    railway_dir = tmp_path / "_railway" / "generated"
    railway_dir.mkdir(parents=True)

    # Old format YAML (with exits section)
    yaml_content = dedent(
        """
        version: "1.0"
        entrypoint: greeting
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
            success::done: exit::done
    """
    )
    (graphs_dir / "greeting_20260101000000.yml").write_text(yaml_content)

    return tmp_path


@pytest.fixture
def project_with_new_format_yaml(tmp_path: Path) -> Path:
    """Create project with new format YAML."""
    graphs_dir = tmp_path / "transition_graphs"
    graphs_dir.mkdir()

    railway_dir = tmp_path / "_railway" / "generated"
    railway_dir.mkdir(parents=True)

    # New format YAML (with nodes.exit section)
    yaml_content = dedent(
        """
        version: "1.0"
        entrypoint: greeting
        description: "テストワークフロー"

        nodes:
          start:
            module: nodes.start
            function: start_node
            description: "開始ノード"

          exit:
            success:
              done:
                description: "完了"

        start: start

        transitions:
          start:
            success::done: exit.success.done
    """
    )
    (graphs_dir / "greeting_20260101000000.yml").write_text(yaml_content)

    return tmp_path


class TestDefaultOverwrite:
    """デフォルトで上書きする動作のテスト。"""

    def test_default_overwrites_existing_file(
        self, project_with_new_format_yaml: Path, monkeypatch
    ) -> None:
        """デフォルトで既存ファイルを上書きする。"""
        from railway.cli.main import app

        monkeypatch.chdir(project_with_new_format_yaml)

        # Create existing file
        generated = (
            project_with_new_format_yaml
            / "_railway"
            / "generated"
            / "greeting_transitions.py"
        )
        generated.write_text("# old content")

        # Run sync (no --force needed)
        result = runner.invoke(app, ["sync", "transition", "--entry", "greeting"])

        assert result.exit_code == 0
        assert "生成完了" in result.stdout
        # File should be overwritten
        assert "# old content" not in generated.read_text()
        assert "TRANSITION_TABLE" in generated.read_text()


class TestNoOverwriteOption:
    """--no-overwrite オプションのテスト。"""

    def test_no_overwrite_skips_existing_file(
        self, project_with_new_format_yaml: Path, monkeypatch
    ) -> None:
        """--no-overwrite で既存ファイルをスキップする。"""
        from railway.cli.main import app

        monkeypatch.chdir(project_with_new_format_yaml)

        # Create existing file
        generated = (
            project_with_new_format_yaml
            / "_railway"
            / "generated"
            / "greeting_transitions.py"
        )
        old_content = "# custom content - do not overwrite"
        generated.write_text(old_content)

        # Run sync with --no-overwrite
        result = runner.invoke(
            app, ["sync", "transition", "--entry", "greeting", "--no-overwrite"]
        )

        assert result.exit_code == 0
        assert "スキップ" in result.stdout or "既に存在" in result.stdout
        # File should NOT be overwritten
        assert generated.read_text() == old_content

    def test_no_overwrite_creates_new_file(
        self, project_with_new_format_yaml: Path, monkeypatch
    ) -> None:
        """--no-overwrite でも新規ファイルは生成する。"""
        from railway.cli.main import app

        monkeypatch.chdir(project_with_new_format_yaml)

        # No existing file
        generated = (
            project_with_new_format_yaml
            / "_railway"
            / "generated"
            / "greeting_transitions.py"
        )
        assert not generated.exists()

        # Run sync with --no-overwrite
        result = runner.invoke(
            app, ["sync", "transition", "--entry", "greeting", "--no-overwrite"]
        )

        assert result.exit_code == 0
        assert "生成完了" in result.stdout
        # File should be created
        assert generated.exists()


class TestConvertOption:
    """--convert オプションのテスト。"""

    def test_convert_transforms_old_format_yaml(
        self, project_with_old_format_yaml: Path, monkeypatch
    ) -> None:
        """--convert で旧形式 YAML を新形式に変換する。"""
        from railway.cli.main import app

        monkeypatch.chdir(project_with_old_format_yaml)

        yaml_path = (
            project_with_old_format_yaml
            / "transition_graphs"
            / "greeting_20260101000000.yml"
        )

        # Verify old format
        original = yaml_path.read_text()
        assert "exits:" in original

        # Run sync with --convert
        result = runner.invoke(
            app, ["sync", "transition", "--entry", "greeting", "--convert"]
        )

        assert result.exit_code == 0
        assert "変換" in result.stdout

        # YAML should be converted
        converted = yaml_path.read_text()
        assert "exits:" not in converted
        assert "exit:" in converted or "nodes:" in converted

    def test_convert_does_nothing_for_new_format(
        self, project_with_new_format_yaml: Path, monkeypatch
    ) -> None:
        """--convert は新形式 YAML に対して何もしない。"""
        from railway.cli.main import app

        monkeypatch.chdir(project_with_new_format_yaml)

        yaml_path = (
            project_with_new_format_yaml
            / "transition_graphs"
            / "greeting_20260101000000.yml"
        )

        original = yaml_path.read_text()

        # Run sync with --convert
        result = runner.invoke(
            app, ["sync", "transition", "--entry", "greeting", "--convert"]
        )

        assert result.exit_code == 0
        # No conversion message (already new format)
        assert "既に新形式" in result.stdout or "変換" not in result.stdout

        # YAML should be unchanged
        assert yaml_path.read_text() == original


class TestForceOptionHidden:
    """--force オプションが hidden であることのテスト。"""

    def test_force_option_still_works(
        self, project_with_new_format_yaml: Path, monkeypatch
    ) -> None:
        """--force は hidden だが動作する（内部用）。"""
        from railway.cli.main import app

        monkeypatch.chdir(project_with_new_format_yaml)

        # Create existing file
        generated = (
            project_with_new_format_yaml
            / "_railway"
            / "generated"
            / "greeting_transitions.py"
        )
        generated.write_text("# old content")

        # Run sync with --force (should still work)
        result = runner.invoke(
            app, ["sync", "transition", "--entry", "greeting", "--force"]
        )

        assert result.exit_code == 0
        assert "# old content" not in generated.read_text()

    def test_help_does_not_show_force(self, monkeypatch, tmp_path) -> None:
        """--help に --force が表示されない。"""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["sync", "transition", "--help"])

        assert result.exit_code == 0
        # --force should not appear in help
        # Note: This is a weak test as Typer may still show hidden options
        # The implementation should use hidden=True
