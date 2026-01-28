"""マイグレーション実行のテスト。

TDD Red Phase: まずテストを書き、失敗を確認する。
"""
from pathlib import Path

import pytest
import yaml

from railway.migrations.types import MigrationPlan
from railway.migrations.changes import (
    MigrationDefinition,
    FileChange,
    ChangeType,
    YamlTransform,
)
from railway.migrations.executor import (
    apply_file_change,
    apply_yaml_transform,
    execute_migration_plan,
    initialize_project,
)
from railway.core.project_metadata import load_metadata, save_metadata, create_metadata
from railway.migrations.yaml_converter import convert_yaml_structure


class TestApplyFileChange:
    """ファイル変更適用のテスト。"""

    def test_create_file(self, tmp_path: Path):
        """ファイル作成アクション。"""
        change = FileChange.create(
            path="src/py.typed",
            content="",
            description="型マーカー",
        )

        apply_file_change(tmp_path, change)

        assert (tmp_path / "src" / "py.typed").exists()

    def test_create_file_with_content(self, tmp_path: Path):
        """コンテンツ付きファイル作成。"""
        change = FileChange.create(
            path="test.txt",
            content="Hello, World!",
            description="テストファイル",
        )

        apply_file_change(tmp_path, change)

        assert (tmp_path / "test.txt").read_text() == "Hello, World!"

    def test_delete_file(self, tmp_path: Path):
        """ファイル削除アクション。"""
        # ファイルを事前作成
        test_file = tmp_path / "to_delete.txt"
        test_file.write_text("delete me")

        change = FileChange.delete(
            path="to_delete.txt",
            description="削除",
        )

        apply_file_change(tmp_path, change)

        assert not test_file.exists()

    def test_delete_nonexistent_file_is_ok(self, tmp_path: Path):
        """存在しないファイルの削除は成功する。"""
        change = FileChange.delete(
            path="nonexistent.txt",
            description="削除",
        )

        # エラーにならない
        apply_file_change(tmp_path, change)


class TestExecuteMigrationPlan:
    """マイグレーション計画実行のテスト。"""

    def test_empty_plan_succeeds(self, tmp_path: Path):
        """空の計画は成功する。"""
        plan = MigrationPlan(
            from_version="0.9.0",
            to_version="0.9.0",
            migrations=(),
        )

        result = execute_migration_plan(tmp_path, plan)

        assert result.success
        assert result.from_version == "0.9.0"
        assert result.to_version == "0.9.0"

    def test_creates_backup_by_default(self, tmp_path: Path):
        """デフォルトでバックアップを作成する。"""
        # メタデータを事前作成
        metadata = create_metadata("test", "0.8.0")
        save_metadata(tmp_path, metadata)

        migration = MigrationDefinition(
            from_version="0.8.0",
            to_version="0.9.0",
            description="テスト",
            file_changes=(
                FileChange.create(
                    path="new_file.txt",
                    content="",
                    description="新規",
                ),
            ),
        )
        plan = MigrationPlan(
            from_version="0.8.0",
            to_version="0.9.0",
            migrations=(migration,),
        )

        result = execute_migration_plan(tmp_path, plan)

        assert result.success
        assert result.backup_path is not None
        assert result.backup_path.exists()

    def test_updates_metadata_on_success(self, tmp_path: Path):
        """成功時にメタデータを更新する。"""
        metadata = create_metadata("test", "0.8.0")
        save_metadata(tmp_path, metadata)

        migration = MigrationDefinition(
            from_version="0.8.0",
            to_version="0.9.0",
            description="テスト",
        )
        plan = MigrationPlan(
            from_version="0.8.0",
            to_version="0.9.0",
            migrations=(migration,),
        )

        result = execute_migration_plan(tmp_path, plan, create_backup_flag=False)

        assert result.success
        updated = load_metadata(tmp_path)
        assert updated is not None
        assert updated.railway.version == "0.9.0"

    def test_result_is_immutable(self, tmp_path: Path):
        """結果はイミュータブル。"""
        plan = MigrationPlan(
            from_version="0.9.0",
            to_version="0.9.0",
            migrations=(),
        )

        result = execute_migration_plan(tmp_path, plan)

        with pytest.raises(Exception):
            result.success = False


class TestInitializeProject:
    """プロジェクト初期化のテスト。"""

    def test_creates_metadata_file(self, tmp_path: Path):
        """メタデータファイルを作成する。"""
        result = initialize_project(tmp_path)

        assert result.success
        assert (tmp_path / ".railway" / "project.yaml").exists()

    def test_uses_directory_name_as_project_name(self, tmp_path: Path):
        """ディレクトリ名をプロジェクト名として使用する。"""
        initialize_project(tmp_path)

        metadata = load_metadata(tmp_path)
        assert metadata is not None
        assert metadata.project.name == tmp_path.name


class TestApplyYamlTransform:
    """YAML 変換適用のテスト（Issue #34）。"""

    def test_applies_yaml_transform(self, tmp_path: Path) -> None:
        """yaml_transforms が適用される。"""
        yaml_dir = tmp_path / "transition_graphs"
        yaml_dir.mkdir()
        (yaml_dir / "test.yml").write_text(
            """version: "1.0"
exits:
  green_done:
    code: 0
    description: "done"
nodes:
  start: {}
transitions:
  start:
    success::done: exit::green_done
"""
        )

        transform = YamlTransform(
            pattern="transition_graphs/**/*.yml",
            transform=convert_yaml_structure,
            description="test",
        )

        apply_yaml_transform(tmp_path, transform)

        result = yaml.safe_load((yaml_dir / "test.yml").read_text())
        assert "exits" not in result
        assert "exit" in result.get("nodes", {})
        assert "success" in result["nodes"]["exit"]

    def test_does_not_modify_file_without_changes(self, tmp_path: Path) -> None:
        """変換不要なファイルは変更しない。"""
        yaml_dir = tmp_path / "transition_graphs"
        yaml_dir.mkdir()
        original_content = """version: "1.0"
nodes:
  start: {}
  exit:
    success:
      done: {}
"""
        (yaml_dir / "test.yml").write_text(original_content)

        transform = YamlTransform(
            pattern="transition_graphs/**/*.yml",
            transform=convert_yaml_structure,
            description="test",
        )

        apply_yaml_transform(tmp_path, transform)

        # ファイルは変更されない（同一内容）
        result_content = (yaml_dir / "test.yml").read_text()
        result = yaml.safe_load(result_content)
        assert "exits" not in result
        assert "exit" in result.get("nodes", {})

    def test_handles_empty_yaml(self, tmp_path: Path) -> None:
        """空の YAML ファイルを正しく処理する。"""
        yaml_dir = tmp_path / "transition_graphs"
        yaml_dir.mkdir()
        (yaml_dir / "empty.yml").write_text("")

        transform = YamlTransform(
            pattern="transition_graphs/**/*.yml",
            transform=convert_yaml_structure,
            description="test",
        )

        # エラーにならない
        apply_yaml_transform(tmp_path, transform)

    def test_matches_glob_pattern(self, tmp_path: Path) -> None:
        """glob パターンでファイルをマッチする。"""
        # マッチするディレクトリ
        yaml_dir = tmp_path / "transition_graphs"
        yaml_dir.mkdir()
        (yaml_dir / "test.yml").write_text(
            """version: "1.0"
exits:
  green_done: {code: 0}
"""
        )

        # マッチしないディレクトリ
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        (other_dir / "test.yml").write_text(
            """version: "1.0"
exits:
  green_done: {code: 0}
"""
        )

        transform = YamlTransform(
            pattern="transition_graphs/**/*.yml",
            transform=convert_yaml_structure,
            description="test",
        )

        apply_yaml_transform(tmp_path, transform)

        # マッチしたファイルは変換される
        matched = yaml.safe_load((yaml_dir / "test.yml").read_text())
        assert "exits" not in matched

        # マッチしないファイルは変換されない
        not_matched = yaml.safe_load((other_dir / "test.yml").read_text())
        assert "exits" in not_matched


class TestApplyMigrationWithYamlTransform:
    """apply_migration が yaml_transforms を適用することのテスト（Issue #34）。"""

    def test_apply_migration_applies_yaml_transforms(self, tmp_path: Path) -> None:
        """apply_migration が yaml_transforms を適用する。"""
        yaml_dir = tmp_path / "transition_graphs"
        yaml_dir.mkdir()
        (yaml_dir / "test.yml").write_text(
            """version: "1.0"
exits:
  green_done: {code: 0, description: "done"}
"""
        )

        migration = MigrationDefinition(
            from_version="0.11.0",
            to_version="0.12.0",
            description="test",
            yaml_transforms=(
                YamlTransform(
                    pattern="transition_graphs/**/*.yml",
                    transform=convert_yaml_structure,
                    description="YAML 構造変換",
                ),
            ),
        )

        from railway.migrations.executor import apply_migration

        apply_migration(tmp_path, migration)

        result = yaml.safe_load((yaml_dir / "test.yml").read_text())
        assert "exits" not in result
        assert "exit" in result.get("nodes", {})
