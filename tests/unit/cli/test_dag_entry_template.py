"""Tests for entry point template generation (Issue #61).

TDD: Red -> Green -> Refactor
"""

import pytest

from railway.cli.new import (
    _get_dag_entry_template,
    _get_dag_entry_template_pending_sync,
)


class TestGetDagEntryTemplate:
    """sync 後のエントリポイントテンプレートのテスト。"""

    def test_uses_run_helper(self) -> None:
        """run() ヘルパーを使用する。"""
        py_content = _get_dag_entry_template("greeting")

        assert "from _railway.generated.greeting_transitions import run" in py_content
        # dag_runner を直接使用しない
        assert "dag_runner" not in py_content

    def test_handles_result_success(self) -> None:
        """result.is_success を確認する。"""
        py_content = _get_dag_entry_template("greeting")

        assert "result.is_success" in py_content
        assert "result.exit_state" in py_content

    def test_handles_result_failure(self) -> None:
        """失敗時に exit code を返す。"""
        py_content = _get_dag_entry_template("greeting")

        assert "SystemExit(result.exit_code)" in py_content

    def test_includes_main_block(self) -> None:
        """if __name__ == '__main__' ブロックがある。"""
        py_content = _get_dag_entry_template("greeting")

        assert 'if __name__ == "__main__":' in py_content

    def test_generated_code_is_valid_python(self) -> None:
        """生成されたコードは構文的に正しい。"""
        py_content = _get_dag_entry_template("greeting")

        compile(py_content, "<string>", "exec")

    @pytest.mark.parametrize("name", ["greeting", "my_workflow", "alert_handler"])
    def test_works_with_various_names(self, name: str) -> None:
        """様々な名前で動作する。"""
        py_content = _get_dag_entry_template(name)

        assert f"from _railway.generated.{name}_transitions import run" in py_content


class TestGetDagEntryTemplatePendingSync:
    """sync 前のエントリポイントテンプレートのテスト。"""

    def test_includes_guidance_message(self) -> None:
        """次のステップを案内するメッセージがある。"""
        py_content = _get_dag_entry_template_pending_sync("greeting")

        assert "railway sync transition" in py_content

    def test_suggests_no_sync_alternative(self) -> None:
        """--no-sync オプションについて言及する。"""
        py_content = _get_dag_entry_template_pending_sync("greeting")

        assert "--no-sync" in py_content

    def test_raises_not_implemented_error(self) -> None:
        """NotImplementedError を raise する。"""
        py_content = _get_dag_entry_template_pending_sync("greeting")

        assert "NotImplementedError" in py_content

    def test_generated_code_is_valid_python(self) -> None:
        """生成されたコードは構文的に正しい。"""
        py_content = _get_dag_entry_template_pending_sync("greeting")

        compile(py_content, "<string>", "exec")

    def test_commented_code_shows_expected_structure(self) -> None:
        """コメントアウトされたコードが期待される構造を示す。"""
        py_content = _get_dag_entry_template_pending_sync("greeting")

        assert "# from _railway.generated.greeting_transitions import run" in py_content
