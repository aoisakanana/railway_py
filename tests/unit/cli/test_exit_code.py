"""Tests for exit code propagation in railway run."""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from railway.cli import new as new_module
from railway.cli.main import app

runner = CliRunner()


class TestExitCodePropagation:
    """exit code が正しく伝播されることを検証する。"""

    def test_dag_template_calls_sys_exit_on_failure(self) -> None:
        """失敗時に sys.exit が呼ばれるテンプレートであること。"""
        template = new_module._get_dag_entry_template("test")
        assert "sys.exit" in template

    def test_dag_template_imports_sys(self) -> None:
        """テンプレートに import sys が含まれること。"""
        template = new_module._get_dag_entry_template("test")
        assert "import sys" in template

    def test_dag_template_no_sys_exit_on_success_path(self) -> None:
        """成功パスでは sys.exit が呼ばれないこと。"""
        template = new_module._get_dag_entry_template("test")
        lines = template.split("\n")
        for i, line in enumerate(lines):
            if "sys.exit" in line:
                # sys.exit は失敗パス（✗ の後）にのみ存在すべき
                preceding = "\n".join(lines[max(0, i - 3) : i])
                assert "\u2717" in preceding or "else" in preceding

    def test_pending_sync_template_already_exits(self) -> None:
        """pending_sync テンプレートは既に SystemExit を含むこと。"""
        template = new_module._get_dag_entry_template_pending_sync("test")
        assert "SystemExit" in template

    def test_run_catches_system_exit(self, tmp_path: pytest.TempPathFactory) -> None:
        """SystemExit が typer.Exit に変換されること。"""
        entry_file = tmp_path / "src" / "fail_test.py"
        entry_file.parent.mkdir(parents=True)
        entry_file.write_text("# dummy")

        with patch("railway.cli.run._execute_entry", side_effect=SystemExit(1)):
            result = runner.invoke(
                app, ["run", "fail_test", "--project", str(tmp_path)]
            )
        assert result.exit_code == 1

    def test_run_propagates_exit_code(self, tmp_path: pytest.TempPathFactory) -> None:
        """SystemExit の code が正しく伝播されること。"""
        entry_file = tmp_path / "src" / "fail_test.py"
        entry_file.parent.mkdir(parents=True)
        entry_file.write_text("# dummy")

        with patch("railway.cli.run._execute_entry", side_effect=SystemExit(42)):
            result = runner.invoke(
                app, ["run", "fail_test", "--project", str(tmp_path)]
            )
        assert result.exit_code == 42
