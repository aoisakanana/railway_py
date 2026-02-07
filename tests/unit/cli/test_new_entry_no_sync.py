"""railway new entry --no-sync のテスト。

BUG: --no-sync でエントリポイントがコメントアウト状態で生成される問題の修正。
"""
import pytest
from pathlib import Path


class TestNewEntryNoSync:
    """--no-sync オプションのテスト。"""

    def test_pending_sync_template_has_entry_point_decorator(self) -> None:
        """生成されるテンプレートに @entry_point デコレータがある。"""
        from railway.cli.new import _get_dag_entry_template_pending_sync

        content = _get_dag_entry_template_pending_sync("my_workflow")

        # @entry_point がコメントアウトされていない
        assert "@entry_point" in content
        # コメントアウトされた @entry_point は含まない
        assert "# @entry_point" not in content

    def test_pending_sync_template_has_main_function(self) -> None:
        """生成されるテンプレートに main 関数がある。"""
        from railway.cli.new import _get_dag_entry_template_pending_sync

        content = _get_dag_entry_template_pending_sync("my_workflow")

        # def main がコメントアウトされていない
        assert "def main" in content
        # コメントアウトされた def main は含まない
        lines = content.split("\n")
        main_lines = [l for l in lines if "def main" in l]
        assert len(main_lines) > 0
        for line in main_lines:
            stripped = line.lstrip()
            assert not stripped.startswith("#"), f"main is commented out: {line}"

    def test_pending_sync_template_is_valid_python(self) -> None:
        """生成されるテンプレートは有効な Python コードである。"""
        from railway.cli.new import _get_dag_entry_template_pending_sync

        content = _get_dag_entry_template_pending_sync("my_workflow")

        # 構文エラーがなければ compile が成功
        compile(content, "<string>", "exec")

    def test_pending_sync_template_has_helpful_message(self) -> None:
        """生成されるテンプレートに次のステップの案内がある。"""
        from railway.cli.new import _get_dag_entry_template_pending_sync

        content = _get_dag_entry_template_pending_sync("my_workflow")

        # 次のステップの案内がある
        assert "railway sync transition" in content

    def test_pending_sync_template_raises_on_missing_transitions(self) -> None:
        """transitions がない場合、実行時に分かりやすいエラーを出す。"""
        from railway.cli.new import _get_dag_entry_template_pending_sync

        content = _get_dag_entry_template_pending_sync("my_workflow")

        # ImportError をキャッチして案内するコードがある
        assert "ModuleNotFoundError" in content or "ImportError" in content
        # または、存在確認のコードがある
        # 何らかの形で「sync が必要」というメッセージを出す
        assert "sync" in content.lower()

    def test_pending_sync_template_not_all_commented(self) -> None:
        """テンプレートの大部分がコメントアウトされていない。"""
        from railway.cli.new import _get_dag_entry_template_pending_sync

        content = _get_dag_entry_template_pending_sync("my_workflow")

        lines = content.split("\n")
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith("#") and not l.strip().startswith('"""')]

        # 実際のコード行が十分にある（最低10行）
        assert len(code_lines) >= 10, f"Too few code lines: {len(code_lines)}"
