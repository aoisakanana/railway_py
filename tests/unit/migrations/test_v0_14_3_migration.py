"""v0.14.0 → v0.14.3 マイグレーション定義のテスト。

TDD Red Phase: マイグレーション定義とexecutor glob対応のテスト。
"""

import pytest


class TestMigration014To0143:
    """v0.14.0 → v0.14.3 マイグレーション定義のテスト。"""

    def test_migration_registered(self) -> None:
        """マイグレーションがレジストリに登録されていること。"""
        from railway.migrations.registry import find_migration

        m = find_migration("0.14.0", "0.14.3")
        assert m is not None

    def test_migration_path_from_0140(self) -> None:
        """v0.14.0 から v0.14.3 へのパスが計算できること。"""
        from railway.migrations.registry import calculate_migration_path

        plan = calculate_migration_path("0.14.0", "0.14.3")
        assert len(plan.migrations) == 1

    def test_migration_path_from_0141(self) -> None:
        """v0.14.1 から v0.14.3 へのパスが計算できること。"""
        from railway.migrations.registry import calculate_migration_path

        plan = calculate_migration_path("0.14.1", "0.14.3")
        assert len(plan.migrations) == 1

    def test_migration_path_from_0142(self) -> None:
        """v0.14.2 から v0.14.3 へのパスが計算できること。"""
        from railway.migrations.registry import calculate_migration_path

        plan = calculate_migration_path("0.14.2", "0.14.3")
        assert len(plan.migrations) == 1

    def test_file_changes_include_board_deletion(self) -> None:
        """ファイル変更に Board 型ファイル削除が含まれること。"""
        from railway.migrations.registry import find_migration

        m = find_migration("0.14.0", "0.14.3")
        assert m is not None
        paths = [fc.path for fc in m.file_changes]
        assert any("_board.py" in p for p in paths)

    def test_code_guidance_includes_linear_mode(self) -> None:
        """コードガイダンスに linear mode 移行の案内が含まれること。"""
        from railway.migrations.registry import find_migration

        m = find_migration("0.14.0", "0.14.3")
        assert m is not None
        descriptions = [cg.description for cg in m.code_guidance]
        assert any("typed_pipeline" in d for d in descriptions)

    def test_code_guidance_includes_node_output(self) -> None:
        """コードガイダンスに @node(output=) 移行の案内が含まれること。"""
        from railway.migrations.registry import find_migration

        m = find_migration("0.14.0", "0.14.3")
        assert m is not None
        descriptions = [cg.description for cg in m.code_guidance]
        assert any("@node(output=" in d for d in descriptions)

    def test_code_guidance_includes_node_inputs(self) -> None:
        """コードガイダンスに @node(inputs=) 移行の案内が含まれること。"""
        from railway.migrations.registry import find_migration

        m = find_migration("0.14.0", "0.14.3")
        assert m is not None
        descriptions = [cg.description for cg in m.code_guidance]
        assert any("@node(inputs=" in d for d in descriptions)

    def test_code_guidance_includes_exit_code(self) -> None:
        """コードガイダンスに exit code 修正の案内が含まれること。"""
        from railway.migrations.registry import find_migration

        m = find_migration("0.14.0", "0.14.3")
        assert m is not None
        descriptions = [cg.description for cg in m.code_guidance]
        assert any("sys.exit" in d for d in descriptions)

    def test_code_guidance_includes_handle_result(self) -> None:
        """コードガイダンスに handle_result 削除の案内が含まれること。"""
        from railway.migrations.registry import find_migration

        m = find_migration("0.14.0", "0.14.3")
        assert m is not None
        descriptions = [cg.description for cg in m.code_guidance]
        assert any("handle_result" in d for d in descriptions)

    def test_code_guidance_includes_version_update(self) -> None:
        """コードガイダンスにバージョン更新の案内が含まれること。"""
        from railway.migrations.registry import find_migration

        m = find_migration("0.14.0", "0.14.3")
        assert m is not None
        patterns = [cg.pattern for cg in m.code_guidance]
        assert any("railway-framework" in p for p in patterns)

    def test_post_migration_commands(self) -> None:
        """post_migration_commands に railway sync が含まれること。"""
        from railway.migrations.registry import find_migration

        m = find_migration("0.14.0", "0.14.3")
        assert m is not None
        assert "railway sync transition --all" in m.post_migration_commands

    def test_warnings_not_empty(self) -> None:
        """warnings が空でないこと。"""
        from railway.migrations.registry import find_migration

        m = find_migration("0.14.0", "0.14.3")
        assert m is not None
        assert len(m.warnings) > 0

    def test_has_breaking_changes(self) -> None:
        """破壊的変更ありと判定されること。"""
        from railway.migrations.registry import find_migration

        m = find_migration("0.14.0", "0.14.3")
        assert m is not None
        assert m.has_breaking_changes


class TestExecutorGlobDelete:
    """executor の glob 対応テスト。"""

    def test_glob_delete_matches_multiple_files(self, tmp_path: object) -> None:
        """glob パターンで複数ファイルが削除されること。"""
        from pathlib import Path

        from railway.migrations.changes import FileChange
        from railway.migrations.executor import apply_file_change

        tmp = Path(str(tmp_path))
        gen_dir = tmp / "_railway" / "generated"
        gen_dir.mkdir(parents=True)
        (gen_dir / "greeting_board.py").write_text("# generated")
        (gen_dir / "check_board.py").write_text("# generated")
        (gen_dir / "transitions.py").write_text("# keep")

        change = FileChange.delete(path="_railway/generated/*_board.py")
        apply_file_change(tmp, change)

        assert not (gen_dir / "greeting_board.py").exists()
        assert not (gen_dir / "check_board.py").exists()
        assert (gen_dir / "transitions.py").exists()

    def test_glob_delete_no_match_is_noop(self, tmp_path: object) -> None:
        """glob パターンにマッチなしでもエラーにならないこと。"""
        from pathlib import Path

        from railway.migrations.changes import FileChange
        from railway.migrations.executor import apply_file_change

        tmp = Path(str(tmp_path))
        change = FileChange.delete(path="_railway/generated/*_board.py")
        apply_file_change(tmp, change)  # no error

    def test_literal_delete_unchanged(self, tmp_path: object) -> None:
        """glob を含まないパスの削除は従来通り動作すること。"""
        from pathlib import Path

        from railway.migrations.changes import FileChange
        from railway.migrations.executor import apply_file_change

        tmp = Path(str(tmp_path))
        target = tmp / "some_file.txt"
        target.write_text("content")

        change = FileChange.delete(path="some_file.txt")
        apply_file_change(tmp, change)

        assert not target.exists()
