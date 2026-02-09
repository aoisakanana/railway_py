"""マイグレーションレジストリのテスト。

TDD Red Phase: まずテストを書き、失敗を確認する。
"""
import pytest

from railway.migrations.types import MigrationPlan
from railway.migrations.changes import MigrationDefinition
from railway.migrations.registry import (
    _base_release,
    calculate_migration_path,
    find_next_migration,
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


class TestBaseRelease:
    """_base_release ヘルパーのテスト。"""

    def test_final_release(self) -> None:
        assert _base_release("0.13.10") == (0, 13, 10)

    def test_rc_release(self) -> None:
        assert _base_release("0.13.10rc2") == (0, 13, 10)

    def test_dev_release(self) -> None:
        assert _base_release("0.13.11.dev1") == (0, 13, 11)

    def test_post_release(self) -> None:
        assert _base_release("0.13.10.post1") == (0, 13, 10)

    def test_two_segment_version(self) -> None:
        assert _base_release("0.10") == (0, 10)


class TestFindNextMigrationRangeMatch:
    """find_next_migration の範囲マッチテスト。"""

    def test_prerelease_matches_migration_range(self) -> None:
        """0.13.10rc2 が 0.13.4→0.13.11 マイグレーションにマッチする。"""
        result = find_next_migration("0.13.10rc2", "0.13.11")
        assert result is not None
        assert result.to_version == "0.13.11"

    def test_exact_from_version_matches(self) -> None:
        """0.13.4 が 0.13.4→0.13.11 マイグレーションにマッチする。"""
        result = find_next_migration("0.13.4", "0.13.11")
        assert result is not None
        assert result.to_version == "0.13.11"

    def test_intermediate_version_matches(self) -> None:
        """0.13.7 が 0.13.4→0.13.11 マイグレーションにマッチする。"""
        result = find_next_migration("0.13.7", "0.13.11")
        assert result is not None
        assert result.to_version == "0.13.11"

    def test_prerelease_target_matches(self) -> None:
        """ターゲットが 0.13.11rc1 でも to_version=0.13.11 がマッチする。"""
        result = find_next_migration("0.13.10rc2", "0.13.11rc1")
        assert result is not None
        assert result.to_version == "0.13.11"

    def test_version_at_to_version_does_not_match(self) -> None:
        """0.13.11 は 0.13.4→0.13.11 の範囲外（to_version と同じ）。"""
        result = find_next_migration("0.13.11", "0.13.12")
        # 0.13.11 は [0.13.4, 0.13.11) の外
        # 別のマイグレーションがあれば返るが、なければ None
        # ここでは 0.13.4→0.13.11 にはマッチしないことを確認
        if result is not None:
            assert result.from_version != "0.13.4"

    def test_version_before_range_does_not_match(self) -> None:
        """0.13.3 は 0.13.4→0.13.11 の範囲外。"""
        # 0.13.3 は 0.13.3→0.13.4 にマッチするはず
        result = find_next_migration("0.13.3", "0.13.11")
        assert result is not None
        assert result.to_version == "0.13.4"  # 0.13.3→0.13.4 にマッチ


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

    def test_prerelease_to_prerelease(self) -> None:
        """0.13.10rc2 → 0.13.11rc1 でマイグレーションが実行される。"""
        plan = calculate_migration_path("0.13.10rc2", "0.13.11rc1")
        assert not plan.is_empty
        assert len(plan.migrations) >= 1

    def test_same_base_release_returns_empty(self) -> None:
        """0.13.11 → 0.13.11rc1 は同じベースリリースなので空。"""
        plan = calculate_migration_path("0.13.11", "0.13.11rc1")
        assert plan.is_empty

    def test_prerelease_same_base_returns_empty(self) -> None:
        """0.13.11rc1 → 0.13.11rc2 は同じベースリリースなので空。"""
        plan = calculate_migration_path("0.13.11rc1", "0.13.11rc2")
        assert plan.is_empty

    def test_chain_from_0_13_3(self) -> None:
        """0.13.3 → 0.13.11rc1 は 2 ステップ（0.13.3→0.13.4, 0.13.4→0.13.11）。"""
        plan = calculate_migration_path("0.13.3", "0.13.11rc1")
        assert len(plan.migrations) == 2

    def test_from_0_13_5_to_0_13_11(self) -> None:
        """0.13.5 → 0.13.11 で 0.13.4→0.13.11 マイグレーションが適用される。"""
        plan = calculate_migration_path("0.13.5", "0.13.11")
        assert len(plan.migrations) == 1
        assert plan.migrations[0].to_version == "0.13.11"
