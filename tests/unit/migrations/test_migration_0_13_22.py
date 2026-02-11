"""v0.13.15 -> v0.13.22 マイグレーションテスト."""

from railway.migrations.definitions.v0_13_15_to_v0_13_22 import (
    MIGRATION_0_13_15_TO_0_13_22,
)
from railway.migrations.registry import calculate_migration_path, find_migration


class TestMigrationDefinition:
    """マイグレーション定義の基本テスト."""

    def test_migration_is_registered(self) -> None:
        migration = find_migration("0.13.15", "0.13.22")
        assert migration is not None

    def test_migration_versions(self) -> None:
        assert MIGRATION_0_13_15_TO_0_13_22.from_version == "0.13.15"
        assert MIGRATION_0_13_15_TO_0_13_22.to_version == "0.13.22"

    def test_migration_has_description(self) -> None:
        assert MIGRATION_0_13_15_TO_0_13_22.description

    def test_post_migration_includes_sync(self) -> None:
        """sync --all が post_migration_commands に含まれること."""
        assert any(
            "sync" in cmd
            for cmd in MIGRATION_0_13_15_TO_0_13_22.post_migration_commands
        )

    def test_code_guidance_mentions_version_constraint(self) -> None:
        """バージョン制約更新のガイダンスがあること."""
        assert any(
            "railway-framework" in g.description
            for g in MIGRATION_0_13_15_TO_0_13_22.code_guidance
        )

    def test_warnings_mention_codegen(self) -> None:
        """codegen 変更に関する警告があること."""
        all_warnings = " ".join(MIGRATION_0_13_15_TO_0_13_22.warnings)
        assert "codegen" in all_warnings.lower() or "sync" in all_warnings.lower()


class TestMigrationPathChaining:
    """マイグレーションパスの連鎖テスト."""

    def test_migration_path_from_0_13_15(self) -> None:
        """0.13.15 からのマイグレーションパス."""
        plan = calculate_migration_path("0.13.15", "0.13.22")
        assert not plan.is_empty
        assert len(plan.migrations) == 1
        assert plan.migrations[0].to_version == "0.13.22"

    def test_migration_path_from_0_13_18(self) -> None:
        """0.13.18 からのマイグレーションパス（中間バージョン範囲マッチ）."""
        plan = calculate_migration_path("0.13.18", "0.13.22")
        assert not plan.is_empty
        assert len(plan.migrations) == 1
        assert plan.migrations[0].to_version == "0.13.22"

    def test_migration_path_from_0_13_21(self) -> None:
        """0.13.21 からのマイグレーションパス（直近バージョン範囲マッチ）."""
        plan = calculate_migration_path("0.13.21", "0.13.22")
        assert not plan.is_empty
        assert len(plan.migrations) == 1

    def test_chained_path_from_0_13_11(self) -> None:
        """0.13.11 からの連鎖（0.13.11→0.13.15→0.13.22）."""
        plan = calculate_migration_path("0.13.11", "0.13.22")
        assert len(plan.migrations) == 2
        assert plan.migrations[0].to_version == "0.13.15"
        assert plan.migrations[1].to_version == "0.13.22"

    def test_chained_path_from_0_13_4(self) -> None:
        """0.13.4 からの連鎖（0.13.4→0.13.11→0.13.15→0.13.22）."""
        plan = calculate_migration_path("0.13.4", "0.13.22")
        assert len(plan.migrations) == 3

    def test_chained_path_from_0_13_3(self) -> None:
        """0.13.3 からの全連鎖（0.13.3→0.13.4→0.13.11→0.13.15→0.13.22）."""
        plan = calculate_migration_path("0.13.3", "0.13.22")
        assert len(plan.migrations) == 4
        assert plan.migrations[-1].to_version == "0.13.22"
