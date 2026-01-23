"""マイグレーションレジストリのテスト。

TDD Red Phase: まずテストを書き、失敗を確認する。
"""
import pytest

from railway.migrations.types import MigrationPlan
from railway.migrations.changes import MigrationDefinition
from railway.migrations.registry import (
    calculate_migration_path,
    normalize_version,
)


class TestNormalizeVersion:
    """バージョン正規化のテスト。"""

    def test_patch_version_is_zeroed(self):
        """パッチバージョンが0になる。"""
        assert normalize_version("0.9.5") == "0.9.0"

    def test_major_minor_preserved(self):
        """メジャー・マイナーは保持される。"""
        assert normalize_version("1.2.3") == "1.2.0"

    def test_already_normalized(self):
        """既に正規化済みの場合は変わらない。"""
        assert normalize_version("0.9.0") == "0.9.0"


class TestCalculateMigrationPath:
    """マイグレーションパス計算のテスト。"""

    def test_same_version_returns_empty_plan(self):
        """同じバージョンは空の計画を返す。"""
        plan = calculate_migration_path("0.9.0", "0.9.0")
        assert plan.is_empty
        assert plan.migrations == ()

    def test_downgrade_returns_empty_plan(self):
        """ダウングレードは空の計画を返す。"""
        plan = calculate_migration_path("0.10.0", "0.9.0")
        assert plan.is_empty

    def test_plan_is_immutable(self):
        """計画はイミュータブル。"""
        plan = calculate_migration_path("0.9.0", "0.9.0")
        with pytest.raises(Exception):
            plan.migrations = ()  # type: ignore
