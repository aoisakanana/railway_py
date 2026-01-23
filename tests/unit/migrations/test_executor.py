"""マイグレーション実行のテスト。

TDD Red Phase: まずテストを書き、失敗を確認する。
"""
from pathlib import Path

import pytest

from railway.migrations.types import MigrationPlan
from railway.migrations.changes import (
    MigrationDefinition,
    FileChange,
    ChangeType,
)
from railway.migrations.executor import (
    apply_file_change,
    execute_migration_plan,
    initialize_project,
)
from railway.core.project_metadata import load_metadata, save_metadata, create_metadata


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
