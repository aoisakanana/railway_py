"""Tests for v0.11 to v0.12 migration definition."""

import pytest

from railway.migrations.definitions.v0_11_to_v0_12 import MIGRATION_0_11_TO_0_12
from railway.migrations.registry import MIGRATIONS, find_migration


class TestMigrationExists:
    """マイグレーション定義の存在テスト。"""

    def test_migration_0_11_to_0_12_exists(self) -> None:
        """v0.11 → v0.12 マイグレーションが定義されている。"""
        assert MIGRATION_0_11_TO_0_12 is not None

    def test_migration_has_correct_versions(self) -> None:
        """バージョンが正しい。"""
        assert MIGRATION_0_11_TO_0_12.from_version == "0.11.0"
        assert MIGRATION_0_11_TO_0_12.to_version == "0.12.0"

    def test_migration_has_description(self) -> None:
        """説明がある。"""
        assert MIGRATION_0_11_TO_0_12.description
        assert "exit" in MIGRATION_0_11_TO_0_12.description.lower()

    def test_migration_is_in_registry(self) -> None:
        """レジストリに登録されている。"""
        assert MIGRATION_0_11_TO_0_12 in MIGRATIONS

    def test_can_find_migration(self) -> None:
        """find_migration で取得できる。"""
        migration = find_migration("0.11.0", "0.12.0")
        assert migration is not None
        assert migration.to_version == "0.12.0"


class TestMigrationYamlTransforms:
    """YAML 変換定義のテスト。"""

    def test_has_yaml_transforms(self) -> None:
        """YAML 変換が定義されている。"""
        assert len(MIGRATION_0_11_TO_0_12.yaml_transforms) > 0

    def test_transforms_target_transition_graphs(self) -> None:
        """transition_graphs ディレクトリを対象にしている。"""
        transform = MIGRATION_0_11_TO_0_12.yaml_transforms[0]
        assert "transition_graphs" in transform.pattern


class TestMigrationCodeGuidance:
    """コードガイダンスのテスト。"""

    def test_has_exit_node_guidance(self) -> None:
        """終端ノードに関するガイダンスがある。"""
        guidance_texts = [g.description for g in MIGRATION_0_11_TO_0_12.code_guidance]
        assert any("終端" in text or "exit" in text.lower() for text in guidance_texts)

    def test_has_sync_guidance(self) -> None:
        """sync コマンドに関するガイダンスがある。"""
        guidance_texts = [g.description for g in MIGRATION_0_11_TO_0_12.code_guidance]
        assert any("sync" in text.lower() or "再生成" in text for text in guidance_texts)


class TestMigrationWarnings:
    """警告メッセージのテスト。"""

    def test_has_warnings(self) -> None:
        """警告メッセージがある。"""
        assert len(MIGRATION_0_11_TO_0_12.warnings) > 0

    def test_warns_about_yaml_changes(self) -> None:
        """YAML 変更について警告している。"""
        warnings_text = " ".join(MIGRATION_0_11_TO_0_12.warnings)
        assert "YAML" in warnings_text or "yaml" in warnings_text.lower()

    def test_warns_about_backup(self) -> None:
        """バックアップについて警告している。"""
        warnings_text = " ".join(MIGRATION_0_11_TO_0_12.warnings)
        assert "バックアップ" in warnings_text or "backup" in warnings_text.lower()


class TestMigrationPostCommands:
    """マイグレーション後コマンドのテスト。"""

    def test_has_post_migration_commands(self) -> None:
        """マイグレーション後コマンドが定義されている。"""
        assert len(MIGRATION_0_11_TO_0_12.post_migration_commands) > 0

    def test_includes_sync_command(self) -> None:
        """sync コマンドが含まれている。"""
        commands = MIGRATION_0_11_TO_0_12.post_migration_commands
        assert any("sync" in cmd for cmd in commands)
