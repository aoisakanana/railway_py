"""プレビュー生成機能のテスト。

TDD Red Phase: まずテストを書き、失敗を確認する。
"""
from pathlib import Path

import pytest

from railway.migrations.preview_types import (
    PreviewChangeType,
    MigrationPreview,
)
from railway.migrations.preview import (
    preview_file_change,
    preview_config_change,
    generate_migration_preview,
)
from railway.migrations.changes import (
    FileChange,
    ConfigChange,
    MigrationDefinition,
)


class TestPreviewFileChange:
    """preview_file_change関数のテスト。"""

    def test_create_file_preview(self, tmp_path: Path):
        """ファイル作成のプレビュー。"""
        change = FileChange.create(
            path="new_file.txt",
            content="Hello, World!",
            description="新規ファイル",
        )

        preview = preview_file_change(change, tmp_path)

        assert preview.change_type == PreviewChangeType.ADD
        assert preview.path == "new_file.txt"
        assert "13 bytes" in preview.details[0]

    def test_delete_file_preview(self, tmp_path: Path):
        """ファイル削除のプレビュー。"""
        change = FileChange.delete(
            path="old_file.txt",
            description="削除",
        )

        preview = preview_file_change(change, tmp_path)

        assert preview.change_type == PreviewChangeType.DELETE
        assert preview.path == "old_file.txt"


class TestPreviewConfigChange:
    """preview_config_change関数のテスト。"""

    def test_shows_additions(self):
        """追加キーが表示される。"""
        change = ConfigChange(
            path="config.yaml",
            additions={"new_key": "value"},
        )

        preview = preview_config_change(change)

        assert preview.change_type == PreviewChangeType.UPDATE
        assert any("新規キー: new_key" in d for d in preview.details)

    def test_shows_renames(self):
        """リネームキーが表示される。"""
        change = ConfigChange(
            path="config.yaml",
            renames={"old_key": "new_key"},
        )

        preview = preview_config_change(change)

        assert any("old_key → new_key" in d for d in preview.details)

    def test_shows_deletions(self):
        """削除キーが表示される。"""
        change = ConfigChange(
            path="config.yaml",
            deletions=["deprecated_key"],
        )

        preview = preview_config_change(change)

        assert any("削除" in d and "deprecated_key" in d for d in preview.details)


class TestGenerateMigrationPreview:
    """generate_migration_preview関数のテスト。"""

    def test_empty_migrations_returns_empty_preview(self, tmp_path: Path):
        """空のマイグレーションは空のプレビュー。"""
        preview = generate_migration_preview([], tmp_path)

        assert preview.from_version == ""
        assert preview.to_version == ""
        assert len(preview.changes) == 0

    def test_includes_file_changes(self, tmp_path: Path):
        """ファイル変更が含まれる。"""
        migration = MigrationDefinition(
            from_version="0.8.0",
            to_version="0.9.0",
            description="テスト",
            file_changes=(
                FileChange.create("new.txt", "content", "追加"),
                FileChange.delete("old.txt", "削除"),
            ),
        )

        preview = generate_migration_preview([migration], tmp_path)

        assert len(preview.additions) == 1
        assert len(preview.deletions) == 1

    def test_includes_config_changes(self, tmp_path: Path):
        """設定変更が含まれる。"""
        migration = MigrationDefinition(
            from_version="0.8.0",
            to_version="0.9.0",
            description="テスト",
            config_changes=(
                ConfigChange(
                    path="config.yaml",
                    description="設定",
                    additions={"key": "value"},
                ),
            ),
        )

        preview = generate_migration_preview([migration], tmp_path)

        assert len(preview.updates) == 1

    def test_includes_warnings(self, tmp_path: Path):
        """警告が含まれる。"""
        migration = MigrationDefinition(
            from_version="0.8.0",
            to_version="0.9.0",
            description="テスト",
            warnings=("注意: 手動対応が必要",),
        )

        preview = generate_migration_preview([migration], tmp_path)

        assert preview.has_warnings
        assert "手動対応" in preview.warnings[0]

    def test_versions_from_migration_range(self, tmp_path: Path):
        """バージョンはマイグレーション範囲から取得。"""
        migrations = [
            MigrationDefinition(
                from_version="0.7.0",
                to_version="0.8.0",
                description="First",
            ),
            MigrationDefinition(
                from_version="0.8.0",
                to_version="0.9.0",
                description="Second",
            ),
        ]

        preview = generate_migration_preview(migrations, tmp_path)

        assert preview.from_version == "0.7.0"
        assert preview.to_version == "0.9.0"


class TestDryRunBehavior:
    """dry-runモードの動作テスト。"""

    def test_dry_run_does_not_modify_files(self, tmp_path: Path):
        """dry-runはファイルを変更しない。"""
        # ファイル作成
        test_file = tmp_path / "existing.txt"
        test_file.write_text("Original content")
        original_content = test_file.read_text()

        # プレビュー生成（ファイルを変更しない）
        migration = MigrationDefinition(
            from_version="0.8.0",
            to_version="0.9.0",
            description="Test",
            file_changes=(
                FileChange.create("new_file.txt", "new content", "追加"),
            ),
        )

        preview = generate_migration_preview([migration], tmp_path)

        # 既存ファイルは変更されていない
        assert test_file.read_text() == original_content
        # 新規ファイルは作成されていない
        assert not (tmp_path / "new_file.txt").exists()

    def test_preview_is_immutable(self, tmp_path: Path):
        """プレビュー結果はイミュータブル。"""
        migration = MigrationDefinition(
            from_version="0.8.0",
            to_version="0.9.0",
            description="Test",
        )

        preview = generate_migration_preview([migration], tmp_path)

        with pytest.raises(Exception):
            preview.from_version = "0.7.0"
