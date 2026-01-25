"""Tests for v0.10.0 → v0.11.3 migration.

TDD Red Phase: テストを先に作成し、失敗することを確認。
"""

import pytest

from railway.migrations.registry import MIGRATIONS, find_migration
from railway.migrations.changes import ChangeType


class TestMigrationExists:
    """マイグレーション定義の存在テスト。"""

    def test_migration_0_10_to_0_12_exists(self):
        """0.10.0 → 0.11.3 マイグレーションが存在する。"""
        migration = find_migration("0.10.0", "0.11.3")
        assert migration is not None
        assert migration.from_version == "0.10.0"
        assert migration.to_version == "0.11.3"

    def test_migration_has_description(self):
        """マイグレーションに説明がある。"""
        migration = find_migration("0.10.0", "0.11.3")
        assert migration is not None
        assert "DAG" in migration.description or "dag" in migration.description.lower()

    def test_migration_is_in_registry(self):
        """マイグレーションがレジストリに登録されている。"""
        migration_versions = [(m.from_version, m.to_version) for m in MIGRATIONS]
        assert ("0.10.0", "0.11.3") in migration_versions


class TestMigrationFileChanges:
    """ファイル変更のテスト。"""

    @pytest.fixture
    def migration(self):
        """マイグレーション定義を取得。"""
        m = find_migration("0.10.0", "0.11.3")
        assert m is not None
        return m

    def test_creates_transition_graphs_dir(self, migration):
        """transition_graphs ディレクトリを作成する。"""
        paths = [fc.path for fc in migration.file_changes]
        assert any("transition_graphs" in p for p in paths)

    def test_creates_railway_generated_dir(self, migration):
        """_railway/generated ディレクトリを作成する。"""
        paths = [fc.path for fc in migration.file_changes]
        assert any("_railway/generated" in p for p in paths)

    def test_file_changes_are_create_type(self, migration):
        """ファイル変更は CREATE タイプである。"""
        for fc in migration.file_changes:
            assert fc.change_type == ChangeType.FILE_CREATE

    def test_transition_graphs_has_gitkeep(self, migration):
        """transition_graphs/.gitkeep が含まれる。"""
        paths = [fc.path for fc in migration.file_changes]
        assert "transition_graphs/.gitkeep" in paths

    def test_railway_generated_has_gitkeep(self, migration):
        """_railway/generated/.gitkeep が含まれる。"""
        paths = [fc.path for fc in migration.file_changes]
        assert "_railway/generated/.gitkeep" in paths


class TestMigrationCodeGuidance:
    """コードガイダンスのテスト。"""

    @pytest.fixture
    def migration(self):
        """マイグレーション定義を取得。"""
        m = find_migration("0.10.0", "0.11.3")
        assert m is not None
        return m

    def test_detects_dict_return_type(self, migration):
        """dict を返すノードを検出する。"""
        old_code = """
@node
def process(data: dict) -> dict:
    return data
"""
        # 少なくとも1つのガイダンスがマッチする
        matches = []
        for guidance in migration.code_guidance:
            matches.extend(guidance.matches(old_code))

        assert len(matches) > 0

    def test_detects_dict_parameter(self, migration):
        """data: dict パラメータを検出する。"""
        old_code = """
def fetch_data(data: dict):
    pass
"""
        matches = []
        for guidance in migration.code_guidance:
            matches.extend(guidance.matches(old_code))

        assert len(matches) > 0

    def test_detects_old_pipeline_import(self, migration):
        """旧 pipeline import を検出する。"""
        old_code = """
from railway import pipeline, node
"""
        matches = []
        for guidance in migration.code_guidance:
            matches.extend(guidance.matches(old_code))

        assert len(matches) > 0

    def test_does_not_match_new_format(self, migration):
        """新形式のコードにはマッチしない。"""
        new_code = """
from railway.core.dag import dag_runner

@node
def process(ctx: ProcessContext) -> tuple[ProcessContext, Outcome]:
    return ctx, Outcome.success("done")
"""
        # 旧形式検出パターンはマッチしない
        matches = []
        for guidance in migration.code_guidance:
            matches.extend(guidance.matches(new_code))

        # pipeline や dict -> dict: にはマッチしないはず
        assert len(matches) == 0

    def test_guidance_has_file_patterns(self, migration):
        """ガイダンスにファイルパターンが設定されている。"""
        for guidance in migration.code_guidance:
            assert len(guidance.file_patterns) > 0


class TestMigrationWarnings:
    """警告メッセージのテスト。"""

    @pytest.fixture
    def migration(self):
        """マイグレーション定義を取得。"""
        m = find_migration("0.10.0", "0.11.3")
        assert m is not None
        return m

    def test_has_warnings(self, migration):
        """警告メッセージが含まれる。"""
        assert len(migration.warnings) > 0

    def test_warnings_mention_node_format(self, migration):
        """ノード形式変更の警告がある。"""
        warnings_text = " ".join(migration.warnings)
        assert "ノード" in warnings_text or "node" in warnings_text.lower()

    def test_warnings_mention_pipeline_deprecation(self, migration):
        """pipeline非推奨の警告がある。"""
        warnings_text = " ".join(migration.warnings)
        assert "pipeline" in warnings_text.lower()

    def test_has_breaking_changes_flag(self, migration):
        """破壊的変更フラグがTrueになる。"""
        assert migration.has_breaking_changes is True
