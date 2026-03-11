"""v0.13.22 → v0.14.0 マイグレーション定義のテスト。"""

import pytest

from railway.migrations.definitions.v0_13_22_to_v0_14_0 import (
    MIGRATION_0_13_22_TO_0_14_0,
)
from railway.migrations.registry import (
    MIGRATIONS,
    calculate_migration_path,
    find_migration,
    find_next_migration,
)


class TestMigrationDefinition:
    """マイグレーション定義の基本プロパティテスト。"""

    def test_version_range(self) -> None:
        """バージョン範囲が正しい。"""
        assert MIGRATION_0_13_22_TO_0_14_0.from_version == "0.13.22"
        assert MIGRATION_0_13_22_TO_0_14_0.to_version == "0.14.0"

    def test_has_description(self) -> None:
        """説明がある。"""
        assert "Riverboard" in MIGRATION_0_13_22_TO_0_14_0.description

    def test_has_file_changes(self) -> None:
        """ファイル変更がある。"""
        assert len(MIGRATION_0_13_22_TO_0_14_0.file_changes) >= 1
        # _railway/cache/.gitkeep の作成
        paths = [fc.path for fc in MIGRATION_0_13_22_TO_0_14_0.file_changes]
        assert "_railway/cache/.gitkeep" in paths

    def test_has_code_guidance(self) -> None:
        """コードガイダンスがある。"""
        assert len(MIGRATION_0_13_22_TO_0_14_0.code_guidance) >= 3

    def test_model_copy_guidance(self) -> None:
        """model_copy() のガイダンスがある。"""
        patterns = [cg.pattern for cg in MIGRATION_0_13_22_TO_0_14_0.code_guidance]
        assert any("model_copy" in p for p in patterns)

    def test_requires_provides_guidance(self) -> None:
        """requires/provides のガイダンスがある。"""
        descriptions = [cg.description for cg in MIGRATION_0_13_22_TO_0_14_0.code_guidance]
        assert any("requires" in d for d in descriptions)

    def test_tuple_outcome_guidance(self) -> None:
        """tuple[Context, Outcome] のガイダンスがある。"""
        patterns = [cg.pattern for cg in MIGRATION_0_13_22_TO_0_14_0.code_guidance]
        assert any("tuple" in p for p in patterns)

    def test_exit_contract_guidance(self) -> None:
        """ExitContract のガイダンスがある。"""
        patterns = [cg.pattern for cg in MIGRATION_0_13_22_TO_0_14_0.code_guidance]
        assert any("ExitContract" in p for p in patterns)

    def test_has_warnings(self) -> None:
        """警告メッセージがある。"""
        assert len(MIGRATION_0_13_22_TO_0_14_0.warnings) > 0
        warnings_text = " ".join(MIGRATION_0_13_22_TO_0_14_0.warnings)
        assert "Riverboard" in warnings_text

    def test_has_post_migration_commands(self) -> None:
        """マイグレーション後コマンドがある。"""
        assert "railway sync transition --all" in MIGRATION_0_13_22_TO_0_14_0.post_migration_commands

    def test_has_breaking_changes(self) -> None:
        """破壊的変更フラグがTrue。"""
        assert MIGRATION_0_13_22_TO_0_14_0.has_breaking_changes


class TestRegistryIntegration:
    """レジストリ統合テスト。"""

    def test_migration_registered(self) -> None:
        """マイグレーションがレジストリに登録されている。"""
        assert MIGRATION_0_13_22_TO_0_14_0 in MIGRATIONS

    def test_find_migration_exact(self) -> None:
        """完全一致で検索できる。"""
        result = find_migration("0.13.22", "0.14.0")
        assert result is not None
        assert result.to_version == "0.14.0"

    def test_find_next_migration_from_0_13_22(self) -> None:
        """0.13.22 から次のマイグレーションを検索できる。"""
        result = find_next_migration("0.13.22", "0.14.0")
        assert result is not None
        assert result.to_version == "0.14.0"

    def test_calculate_path_from_0_13_22(self) -> None:
        """0.13.22 → 0.14.0 のパスを計算できる。"""
        plan = calculate_migration_path("0.13.22", "0.14.0")
        assert len(plan.migrations) == 1
        assert plan.migrations[0].to_version == "0.14.0"

    def test_calculate_path_from_0_13_15(self) -> None:
        """0.13.15 → 0.14.0 は2ステップ。"""
        plan = calculate_migration_path("0.13.15", "0.14.0")
        assert len(plan.migrations) == 2
        versions = [m.to_version for m in plan.migrations]
        assert "0.13.22" in versions
        assert "0.14.0" in versions


class TestCodeGuidanceMatching:
    """コードガイダンスのパターンマッチングテスト。"""

    def test_model_copy_pattern_matches(self) -> None:
        """model_copy パターンがマッチする。"""
        guidance = [
            cg for cg in MIGRATION_0_13_22_TO_0_14_0.code_guidance
            if "model_copy" in cg.pattern
        ][0]

        code = '''
def check_host(ctx: AlertContext) -> tuple[AlertContext, Outcome]:
    new_ctx = ctx.model_copy(update={"hostname": "server-01"})
    return new_ctx, Outcome.success("found")
'''
        matches = guidance.matches(code)
        assert len(matches) == 1
        assert matches[0][0] == 3  # line number

    def test_tuple_outcome_pattern_matches(self) -> None:
        """tuple[Context, Outcome] パターンがマッチする。"""
        guidance = [
            cg for cg in MIGRATION_0_13_22_TO_0_14_0.code_guidance
            if "tuple" in cg.pattern
        ][0]

        code = "def check(ctx: MyContext) -> tuple[MyContext, Outcome]:"
        matches = guidance.matches(code)
        assert len(matches) == 1

    def test_exit_contract_pattern_matches(self) -> None:
        """ExitContract サブクラスパターンがマッチする。"""
        guidance = [
            cg for cg in MIGRATION_0_13_22_TO_0_14_0.code_guidance
            if "ExitContract" in cg.pattern
        ][0]

        code = "class DoneResult(ExitContract):"
        matches = guidance.matches(code)
        assert len(matches) == 1
