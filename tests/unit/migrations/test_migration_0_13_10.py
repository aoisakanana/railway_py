"""v0.13.4 -> v0.13.11 マイグレーションテスト."""
from pathlib import Path

import pytest

from railway.migrations.definitions.v0_13_4_to_v0_13_11 import (
    MIGRATION_0_13_4_TO_0_13_11,
)
from railway.migrations.executor import apply_file_change, execute_migration_plan
from railway.migrations.registry import calculate_migration_path, find_migration


class TestMigrationDefinition:
    """マイグレーション定義の基本テスト."""

    def test_migration_is_registered(self) -> None:
        migration = find_migration("0.13.4", "0.13.11")
        assert migration is not None

    def test_migration_versions(self) -> None:
        assert MIGRATION_0_13_4_TO_0_13_11.from_version == "0.13.4"
        assert MIGRATION_0_13_4_TO_0_13_11.to_version == "0.13.11"

    def test_migration_path_from_0_13_10(self) -> None:
        """0.13.10 からのマイグレーションパス（範囲マッチ）。"""
        plan = calculate_migration_path("0.13.10", "0.13.11")
        assert not plan.is_empty
        assert len(plan.migrations) == 1

    def test_migration_path_from_0_13_10rc2(self) -> None:
        """0.13.10rc2 からのマイグレーションパス（プレリリース範囲マッチ）。"""
        plan = calculate_migration_path("0.13.10rc2", "0.13.11rc1")
        assert not plan.is_empty
        assert len(plan.migrations) == 1

    def test_migration_path_from_0_13_5(self) -> None:
        """0.13.5 からのマイグレーションパス（中間バージョン範囲マッチ）。"""
        plan = calculate_migration_path("0.13.5", "0.13.11")
        assert not plan.is_empty
        assert len(plan.migrations) == 1

    def test_code_guidance_mentions_mypy(self) -> None:
        assert any(
            "mypy" in g.description
            for g in MIGRATION_0_13_4_TO_0_13_11.code_guidance
        )

    def test_post_migration_includes_sync(self) -> None:
        assert any(
            "sync" in cmd
            for cmd in MIGRATION_0_13_4_TO_0_13_11.post_migration_commands
        )

    def test_warnings_mention_nested_path_change(self) -> None:
        assert any(
            "sub.deep.process" in w or "ネスト" in w
            for w in MIGRATION_0_13_4_TO_0_13_11.warnings
        )

    def test_file_changes_include_init_py(self) -> None:
        paths = [c.path for c in MIGRATION_0_13_4_TO_0_13_11.file_changes]
        assert "tests/nodes/__init__.py" in paths


class TestMigrationExecution:
    """マイグレーション実行テスト."""

    def test_tests_nodes_init_py_created(self, tmp_path: Path) -> None:
        """tests/nodes/__init__.py が作成されること."""
        (tmp_path / "tests" / "nodes").mkdir(parents=True)
        for change in MIGRATION_0_13_4_TO_0_13_11.file_changes:
            apply_file_change(tmp_path, change)
        assert (tmp_path / "tests" / "nodes" / "__init__.py").exists()

    def test_existing_init_py_not_overwritten(self, tmp_path: Path) -> None:
        """既存の __init__.py を上書きしないこと."""
        init_py = tmp_path / "tests" / "nodes" / "__init__.py"
        init_py.parent.mkdir(parents=True)
        init_py.write_text("# custom content")
        for change in MIGRATION_0_13_4_TO_0_13_11.file_changes:
            apply_file_change(tmp_path, change)
        assert init_py.read_text() == "# custom content"
