"""プレビュー型定義のテスト。

TDD Red Phase: まずテストを書き、失敗を確認する。
"""
import pytest

from railway.migrations.preview_types import (
    PreviewChangeType,
    LineDiff,
    ChangePreview,
    MigrationPreview,
)


class TestPreviewChangeType:
    """PreviewChangeType列挙型のテスト。"""

    def test_has_all_change_types(self):
        """必要な変更タイプが定義されている。"""
        assert PreviewChangeType.ADD.value == "add"
        assert PreviewChangeType.UPDATE.value == "update"
        assert PreviewChangeType.DELETE.value == "delete"
        assert PreviewChangeType.GUIDANCE.value == "guidance"


class TestLineDiff:
    """LineDiff型のテスト。"""

    def test_is_immutable(self):
        """LineDiffは変更不可。"""
        diff = LineDiff(added=10, removed=5)

        with pytest.raises(Exception):
            diff.added = 20

    def test_net_change_positive(self):
        """純増減が正しく計算される（追加多い）。"""
        diff = LineDiff(added=10, removed=3)

        assert diff.net_change == 7

    def test_net_change_negative(self):
        """純増減が正しく計算される（削除多い）。"""
        diff = LineDiff(added=2, removed=8)

        assert diff.net_change == -6

    def test_format(self):
        """フォーマットが正しい。"""
        diff = LineDiff(added=10, removed=5)

        assert diff.format() == "+10/-5"


class TestChangePreview:
    """ChangePreview型のテスト。"""

    def test_is_immutable(self):
        """ChangePreviewは変更不可。"""
        preview = ChangePreview(
            change_type=PreviewChangeType.ADD,
            path="new_file.txt",
            description="新規ファイル",
        )

        with pytest.raises(Exception):
            preview.path = "other.txt"

    def test_is_file_change_for_add(self):
        """ADDはファイル変更。"""
        preview = ChangePreview(
            change_type=PreviewChangeType.ADD,
            path="new_file.txt",
            description="追加",
        )

        assert preview.is_file_change
        assert not preview.is_guidance

    def test_is_file_change_for_update(self):
        """UPDATEはファイル変更。"""
        preview = ChangePreview(
            change_type=PreviewChangeType.UPDATE,
            path="file.txt",
            description="更新",
        )

        assert preview.is_file_change
        assert not preview.is_guidance

    def test_is_file_change_for_delete(self):
        """DELETEはファイル変更。"""
        preview = ChangePreview(
            change_type=PreviewChangeType.DELETE,
            path="old_file.txt",
            description="削除",
        )

        assert preview.is_file_change
        assert not preview.is_guidance

    def test_is_guidance(self):
        """GUIDANCEはガイダンス。"""
        preview = ChangePreview(
            change_type=PreviewChangeType.GUIDANCE,
            path="src/file.py:10",
            description="手動対応",
        )

        assert preview.is_guidance
        assert not preview.is_file_change


class TestMigrationPreview:
    """MigrationPreview型のテスト。"""

    def test_is_immutable(self):
        """MigrationPreviewは変更不可。"""
        preview = MigrationPreview(
            from_version="0.8.0",
            to_version="0.9.0",
            changes=(),
        )

        with pytest.raises(Exception):
            preview.from_version = "0.7.0"

    def test_additions_filter(self):
        """追加のみをフィルタリングできる。"""
        preview = MigrationPreview(
            from_version="0.8.0",
            to_version="0.9.0",
            changes=(
                ChangePreview(change_type=PreviewChangeType.ADD, path="new.txt", description="追加"),
                ChangePreview(change_type=PreviewChangeType.ADD, path="another.txt", description="追加2"),
                ChangePreview(change_type=PreviewChangeType.UPDATE, path="old.txt", description="更新"),
            ),
        )

        assert len(preview.additions) == 2
        assert all(c.change_type == PreviewChangeType.ADD for c in preview.additions)

    def test_updates_filter(self):
        """更新のみをフィルタリングできる。"""
        preview = MigrationPreview(
            from_version="0.8.0",
            to_version="0.9.0",
            changes=(
                ChangePreview(change_type=PreviewChangeType.ADD, path="new.txt", description="追加"),
                ChangePreview(change_type=PreviewChangeType.UPDATE, path="file1.txt", description="更新1"),
                ChangePreview(change_type=PreviewChangeType.UPDATE, path="file2.txt", description="更新2"),
            ),
        )

        assert len(preview.updates) == 2

    def test_deletions_filter(self):
        """削除のみをフィルタリングできる。"""
        preview = MigrationPreview(
            from_version="0.8.0",
            to_version="0.9.0",
            changes=(
                ChangePreview(change_type=PreviewChangeType.DELETE, path="del1.txt", description="削除"),
                ChangePreview(change_type=PreviewChangeType.ADD, path="new.txt", description="追加"),
            ),
        )

        assert len(preview.deletions) == 1

    def test_guidance_items_filter(self):
        """ガイダンスのみをフィルタリングできる。"""
        preview = MigrationPreview(
            from_version="0.8.0",
            to_version="0.9.0",
            changes=(
                ChangePreview(change_type=PreviewChangeType.GUIDANCE, path="src/a.py:10", description="手動"),
                ChangePreview(change_type=PreviewChangeType.GUIDANCE, path="src/b.py:20", description="手動"),
                ChangePreview(change_type=PreviewChangeType.ADD, path="new.txt", description="追加"),
            ),
        )

        assert len(preview.guidance_items) == 2

    def test_total_changes(self):
        """変更総数を取得できる。"""
        preview = MigrationPreview(
            from_version="0.8.0",
            to_version="0.9.0",
            changes=(
                ChangePreview(change_type=PreviewChangeType.ADD, path="new.txt", description="追加"),
                ChangePreview(change_type=PreviewChangeType.UPDATE, path="old.txt", description="更新"),
                ChangePreview(change_type=PreviewChangeType.DELETE, path="del.txt", description="削除"),
            ),
        )

        assert preview.total_changes == 3

    def test_has_warnings_true(self):
        """警告がある場合。"""
        preview = MigrationPreview(
            from_version="0.8.0",
            to_version="0.9.0",
            changes=(),
            warnings=("注意事項",),
        )

        assert preview.has_warnings

    def test_has_warnings_false(self):
        """警告がない場合。"""
        preview = MigrationPreview(
            from_version="0.8.0",
            to_version="0.9.0",
            changes=(),
        )

        assert not preview.has_warnings

    def test_has_guidance_true(self):
        """ガイダンスがある場合。"""
        preview = MigrationPreview(
            from_version="0.8.0",
            to_version="0.9.0",
            changes=(
                ChangePreview(change_type=PreviewChangeType.GUIDANCE, path="src/a.py:10", description="手動"),
            ),
        )

        assert preview.has_guidance

    def test_has_guidance_false(self):
        """ガイダンスがない場合。"""
        preview = MigrationPreview(
            from_version="0.8.0",
            to_version="0.9.0",
            changes=(
                ChangePreview(change_type=PreviewChangeType.ADD, path="new.txt", description="追加"),
            ),
        )

        assert not preview.has_guidance
