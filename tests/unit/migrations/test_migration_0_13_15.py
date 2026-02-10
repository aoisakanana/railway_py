"""v0.13.11 -> v0.13.15 マイグレーションテスト."""
from pathlib import Path

import pytest

from railway.migrations.definitions.v0_13_11_to_v0_13_15 import (
    MIGRATION_0_13_11_TO_0_13_15,
)
from railway.migrations.registry import calculate_migration_path, find_migration


class TestMigrationDefinition:
    """マイグレーション定義の基本テスト."""

    def test_migration_is_registered(self) -> None:
        migration = find_migration("0.13.11", "0.13.15")
        assert migration is not None

    def test_migration_versions(self) -> None:
        assert MIGRATION_0_13_11_TO_0_13_15.from_version == "0.13.11"
        assert MIGRATION_0_13_11_TO_0_13_15.to_version == "0.13.15"

    def test_migration_path_from_0_13_11(self) -> None:
        """0.13.11 からのマイグレーションパス."""
        plan = calculate_migration_path("0.13.11", "0.13.15")
        assert not plan.is_empty
        assert len(plan.migrations) == 1

    def test_migration_path_from_0_13_12(self) -> None:
        """0.13.12 からのマイグレーションパス（中間バージョン範囲マッチ）."""
        plan = calculate_migration_path("0.13.12", "0.13.15")
        assert not plan.is_empty
        assert len(plan.migrations) == 1

    def test_migration_path_from_0_13_14(self) -> None:
        """0.13.14 からのマイグレーションパス（直近バージョン範囲マッチ）."""
        plan = calculate_migration_path("0.13.14", "0.13.15")
        assert not plan.is_empty
        assert len(plan.migrations) == 1

    def test_chained_path_from_0_13_4(self) -> None:
        """0.13.4 からの連鎖マイグレーション（0.13.4→0.13.11→0.13.15）."""
        plan = calculate_migration_path("0.13.4", "0.13.15")
        assert len(plan.migrations) == 2

    def test_post_migration_includes_sync(self) -> None:
        assert any(
            "sync" in cmd
            for cmd in MIGRATION_0_13_11_TO_0_13_15.post_migration_commands
        )

    def test_code_guidance_mentions_tutorial(self) -> None:
        assert any(
            "TUTORIAL" in g.description
            for g in MIGRATION_0_13_11_TO_0_13_15.code_guidance
        )

    def test_code_guidance_mentions_version_constraint(self) -> None:
        assert any(
            "railway-framework" in g.description
            for g in MIGRATION_0_13_11_TO_0_13_15.code_guidance
        )
