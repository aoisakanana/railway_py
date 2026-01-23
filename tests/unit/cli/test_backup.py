"""バックアップCLIコマンドのテスト。"""
from pathlib import Path

import pytest
from typer.testing import CliRunner

from railway.cli.backup import app
from railway.migrations.backup import create_backup


runner = CliRunner()


class TestBackupListCommand:
    """backup list コマンドのテスト。"""

    def test_list_no_backups(self, tmp_path: Path, monkeypatch):
        """バックアップがない場合のメッセージ。"""
        # プロジェクトルートを設定
        (tmp_path / ".railway").mkdir()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "バックアップはありません" in result.output

    def test_list_shows_backups(self, tmp_path: Path, monkeypatch):
        """バックアップ一覧が表示される。"""
        (tmp_path / ".railway").mkdir()
        (tmp_path / "TUTORIAL.md").write_text("content")
        create_backup(tmp_path, "0.9.0", "Test backup")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "バックアップ一覧" in result.output
        assert "0.9.0" in result.output

    def test_list_verbose_shows_details(self, tmp_path: Path, monkeypatch):
        """詳細表示オプション。"""
        (tmp_path / ".railway").mkdir()
        (tmp_path / "TUTORIAL.md").write_text("content")
        create_backup(tmp_path, "0.9.0", "Test backup")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["list", "-v"])

        assert result.exit_code == 0
        assert "サイズ" in result.output
        assert "ファイル数" in result.output


class TestBackupRestoreCommand:
    """backup restore コマンドのテスト。"""

    def test_restore_no_backups(self, tmp_path: Path, monkeypatch):
        """バックアップがない場合のエラー。"""
        (tmp_path / ".railway").mkdir()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["restore"])

        assert result.exit_code == 1
        assert "バックアップがありません" in result.output

    def test_restore_latest_with_force(self, tmp_path: Path, monkeypatch):
        """最新バックアップから強制復元。"""
        (tmp_path / ".railway").mkdir()
        tutorial = tmp_path / "TUTORIAL.md"
        tutorial.write_text("original")
        create_backup(tmp_path, "0.9.0", "Before change")
        tutorial.write_text("modified")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["restore", "-f"])

        assert result.exit_code == 0
        assert "復元完了" in result.output
        assert tutorial.read_text() == "original"

    def test_restore_specific_backup(self, tmp_path: Path, monkeypatch):
        """指定したバックアップから復元。"""
        (tmp_path / ".railway").mkdir()
        tutorial = tmp_path / "TUTORIAL.md"
        tutorial.write_text("v1")
        create_backup(tmp_path, "0.8.0", "V1 backup")

        tutorial.write_text("v2")
        create_backup(tmp_path, "0.9.0", "V2 backup")

        tutorial.write_text("v3")
        monkeypatch.chdir(tmp_path)

        # 最初のバックアップを取得
        from railway.migrations.backup import list_backups
        backups = list_backups(tmp_path)
        # 古い方（0.8.0）を選択
        old_backup = [b for b in backups if b.version == "0.8.0"][0]

        result = runner.invoke(app, ["restore", old_backup.name, "-f"])

        assert result.exit_code == 0
        assert tutorial.read_text() == "v1"


class TestBackupCleanCommand:
    """backup clean コマンドのテスト。"""

    def test_clean_nothing_to_delete(self, tmp_path: Path, monkeypatch):
        """削除対象がない場合。"""
        (tmp_path / ".railway").mkdir()
        create_backup(tmp_path, "0.9.0", "Test")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["clean", "--keep", "5"])

        assert result.exit_code == 0
        assert "削除対象のバックアップはありません" in result.output

    def test_clean_removes_old_backups(self, tmp_path: Path, monkeypatch):
        """古いバックアップを削除。"""
        (tmp_path / ".railway").mkdir()
        for i in range(5):
            create_backup(tmp_path, f"0.{i}.0", f"Backup {i}")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["clean", "--keep", "2", "-f"])

        assert result.exit_code == 0
        assert "3件のバックアップを削除しました" in result.output
