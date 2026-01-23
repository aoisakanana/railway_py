"""マイグレーション基本型のテスト。

TDD Red Phase: まずテストを書き、失敗を確認する。
"""
import pytest

from railway.migrations.types import MigrationPlan, MigrationResult
from railway.migrations.changes import MigrationDefinition, FileChange


class TestMigrationPlanImmutability:
    """MigrationPlanのイミュータブル性テスト。"""

    def test_is_frozen(self):
        """MigrationPlanは変更不可。"""
        plan = MigrationPlan(
            from_version="0.8.0",
            to_version="0.9.0",
            migrations=(),
        )

        with pytest.raises(Exception):
            plan.from_version = "0.7.0"


class TestMigrationPlanProperties:
    """MigrationPlanのプロパティテスト。"""

    def test_is_empty_true_when_no_migrations(self):
        """マイグレーションがない場合is_empty=True。"""
        plan = MigrationPlan(
            from_version="0.9.0",
            to_version="0.9.0",
            migrations=(),
        )
        assert plan.is_empty is True

    def test_is_empty_false_when_has_migrations(self):
        """マイグレーションがある場合is_empty=False。"""
        migration = MigrationDefinition(
            from_version="0.8.0",
            to_version="0.9.0",
            description="test",
        )
        plan = MigrationPlan(
            from_version="0.8.0",
            to_version="0.9.0",
            migrations=(migration,),
        )
        assert plan.is_empty is False

    def test_total_changes_sums_all_migrations(self):
        """total_changesが全マイグレーションの変更数を合計する。"""
        m1 = MigrationDefinition(
            from_version="0.7.0",
            to_version="0.8.0",
            description="m1",
            file_changes=(
                FileChange.create("a.txt", ""),
                FileChange.create("b.txt", ""),
            ),
        )
        m2 = MigrationDefinition(
            from_version="0.8.0",
            to_version="0.9.0",
            description="m2",
            file_changes=(FileChange.create("c.txt", ""),),
        )
        plan = MigrationPlan(
            from_version="0.7.0",
            to_version="0.9.0",
            migrations=(m1, m2),
        )
        assert plan.total_changes == 3


class TestMigrationResultImmutability:
    """MigrationResultのイミュータブル性テスト。"""

    def test_is_frozen(self):
        """MigrationResultは変更不可。"""
        result = MigrationResult(
            success=True,
            from_version="0.8.0",
            to_version="0.9.0",
        )

        with pytest.raises(Exception):
            result.success = False
