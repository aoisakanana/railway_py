"""バックアップ機能のテスト。

TDD Red Phase: まずテストを書き、失敗を確認する。
"""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from railway.migrations.backup import (
    generate_backup_name,
    compute_checksum,
    create_backup,
    list_backups,
    restore_backup,
    clean_backups,
)


class TestPureFunctions:
    """純粋関数のテスト。"""

    def test_compute_checksum_is_deterministic(self):
        """同じ入力には同じチェックサム。"""
        content = b"Hello, World!"

        checksum1 = compute_checksum(content)
        checksum2 = compute_checksum(content)

        assert checksum1 == checksum2
        assert checksum1.startswith("sha256:")

    def test_compute_checksum_different_for_different_content(self):
        """異なる入力には異なるチェックサム。"""
        checksum1 = compute_checksum(b"Hello")
        checksum2 = compute_checksum(b"World")

        assert checksum1 != checksum2

    def test_generate_backup_name_format(self):
        """バックアップ名のフォーマット。"""
        dt = datetime(2026, 1, 23, 10, 30, 0, tzinfo=timezone.utc)

        name = generate_backup_name("0.9.0", dt)

        assert name == "0.9.0_20260123_103000"


class TestBackupOperations:
    """バックアップ操作のテスト。"""

    def test_create_backup_success(self, tmp_path: Path):
        """バックアップ作成が成功する。"""
        # テストファイル作成
        (tmp_path / "TUTORIAL.md").write_text("Tutorial content")

        backup_path = create_backup(tmp_path, "0.9.0", "Test backup")

        assert backup_path.exists()
        assert (backup_path / "TUTORIAL.md").exists()

    def test_list_backups_returns_sorted(self, tmp_path: Path):
        """バックアップが作成日時降順でソートされる。"""
        # 複数のバックアップを作成
        create_backup(tmp_path, "0.7.0", "First")
        create_backup(tmp_path, "0.8.0", "Second")
        create_backup(tmp_path, "0.9.0", "Third")

        backups = list_backups(tmp_path)

        assert len(backups) == 3
        # 最新が最初
        assert backups[0].version == "0.9.0"
        assert backups[2].version == "0.7.0"

    def test_restore_backup(self, tmp_path: Path):
        """バックアップから復元できる。"""
        # オリジナルファイル作成
        tutorial = tmp_path / "TUTORIAL.md"
        tutorial.write_text("Original content")

        # バックアップ作成
        backup_path = create_backup(tmp_path, "0.9.0", "Before change")

        # ファイル変更
        tutorial.write_text("Modified content")
        assert tutorial.read_text() == "Modified content"

        # バックアップ情報を取得
        backups = list_backups(tmp_path)
        backup = backups[0]

        # 復元
        result = restore_backup(tmp_path, backup)

        assert result.success
        assert tutorial.read_text() == "Original content"

    def test_clean_backups_keeps_recent(self, tmp_path: Path):
        """指定数のバックアップを保持する。"""
        # 5個のバックアップを作成
        for i in range(5):
            create_backup(tmp_path, f"0.{i}.0", f"Backup {i}")

        removed_count, _ = clean_backups(tmp_path, keep=2)

        assert removed_count == 3
        assert len(list_backups(tmp_path)) == 2
