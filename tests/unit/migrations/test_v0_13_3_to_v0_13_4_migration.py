"""v0.13.3 to v0.13.4 migration tests."""

import pytest

from railway.migrations.definitions.v0_13_3_to_v0_13_4 import MIGRATION_0_13_3_TO_0_13_4
from railway.migrations.registry import MIGRATIONS


class TestMigrationExists:
    """マイグレーション定義の存在確認。"""

    def test_migration_exists(self) -> None:
        """マイグレーション定義が存在する。"""
        assert MIGRATION_0_13_3_TO_0_13_4 is not None

    def test_migration_has_correct_versions(self) -> None:
        """バージョンが正しい。"""
        assert MIGRATION_0_13_3_TO_0_13_4.from_version == "0.13.3"
        assert MIGRATION_0_13_3_TO_0_13_4.to_version == "0.13.4"

    def test_migration_is_in_registry(self) -> None:
        """レジストリに登録されている。"""
        assert MIGRATION_0_13_3_TO_0_13_4 in MIGRATIONS

    def test_migration_has_description(self) -> None:
        """説明がある。"""
        assert MIGRATION_0_13_3_TO_0_13_4.description
        assert "モジュールパス" in MIGRATION_0_13_3_TO_0_13_4.description

    def test_migration_has_code_guidance(self) -> None:
        """コードガイダンスがある。"""
        assert len(MIGRATION_0_13_3_TO_0_13_4.code_guidance) > 0

    def test_migration_has_warnings(self) -> None:
        """警告メッセージがある。"""
        assert len(MIGRATION_0_13_3_TO_0_13_4.warnings) > 0
        # entrypoint に関する警告
        warning_text = " ".join(MIGRATION_0_13_3_TO_0_13_4.warnings)
        assert "entrypoint" in warning_text

    def test_migration_has_post_commands(self) -> None:
        """事後コマンドがある。"""
        assert len(MIGRATION_0_13_3_TO_0_13_4.post_migration_commands) > 0
        assert any(
            "sync" in cmd
            for cmd in MIGRATION_0_13_3_TO_0_13_4.post_migration_commands
        )
