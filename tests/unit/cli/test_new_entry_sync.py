"""Tests for railway new entry sync default behavior (Issue #64).

TDD: Red -> Green -> Refactor
"""

import pytest
from pathlib import Path
from typer.testing import CliRunner


class TestNewEntrySyncDefault:
    """railway new entry のデフォルト動作（sync 実行）のテスト。"""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_default_generates_transitions(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """デフォルトで _railway/generated/ が生成される。"""
        from railway.cli.main import app
        import os

        # プロジェクト構造をセットアップ
        (tmp_path / "src").mkdir()
        (tmp_path / "transition_graphs").mkdir()
        (tmp_path / "_railway/generated").mkdir(parents=True)

        # カレントディレクトリを一時ディレクトリに変更
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["new", "entry", "greeting"])

            assert result.exit_code == 0, f"Failed: {result.stdout}"
            assert (tmp_path / "_railway/generated/greeting_transitions.py").exists()
        finally:
            os.chdir(old_cwd)

    def test_default_uses_run_helper_in_entrypoint(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """デフォルトでエントリポイントは run() を使用する。"""
        from railway.cli.main import app
        import os

        (tmp_path / "src").mkdir()
        (tmp_path / "transition_graphs").mkdir()
        (tmp_path / "_railway/generated").mkdir(parents=True)

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["new", "entry", "greeting"])

            assert result.exit_code == 0, f"Failed: {result.stdout}"
            entrypoint = (tmp_path / "src/greeting.py").read_text()
            assert "from _railway.generated.greeting_transitions import run" in entrypoint
        finally:
            os.chdir(old_cwd)

    def test_default_generates_exit_nodes(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """デフォルトで終端ノードが生成される。"""
        from railway.cli.main import app
        import os

        (tmp_path / "src").mkdir()
        (tmp_path / "transition_graphs").mkdir()
        (tmp_path / "_railway/generated").mkdir(parents=True)

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["new", "entry", "greeting"])

            assert result.exit_code == 0, f"Failed: {result.stdout}"
            assert (tmp_path / "src/nodes/exit/success/done.py").exists()
            assert (tmp_path / "src/nodes/exit/failure/error.py").exists()
        finally:
            os.chdir(old_cwd)


class TestNewEntryNoSyncOption:
    """railway new entry --no-sync のテスト。"""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_no_sync_skips_transitions(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """--no-sync で _railway/generated/ を生成しない。"""
        from railway.cli.main import app
        import os

        (tmp_path / "src").mkdir()
        (tmp_path / "transition_graphs").mkdir()

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["new", "entry", "greeting", "--no-sync"])

            assert result.exit_code == 0, f"Failed: {result.stdout}"
            assert not (tmp_path / "_railway/generated/greeting_transitions.py").exists()
        finally:
            os.chdir(old_cwd)

    def test_no_sync_uses_pending_template(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """--no-sync でエントリポイントは pending 状態。"""
        from railway.cli.main import app
        import os

        (tmp_path / "src").mkdir()
        (tmp_path / "transition_graphs").mkdir()

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["new", "entry", "greeting", "--no-sync"])

            assert result.exit_code == 0, f"Failed: {result.stdout}"
            entrypoint = (tmp_path / "src/greeting.py").read_text()
            assert "NotImplementedError" in entrypoint
            assert "railway sync transition" in entrypoint
        finally:
            os.chdir(old_cwd)

    def test_no_sync_still_generates_exit_nodes(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """--no-sync でも終端ノードは生成される。"""
        from railway.cli.main import app
        import os

        (tmp_path / "src").mkdir()
        (tmp_path / "transition_graphs").mkdir()

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["new", "entry", "greeting", "--no-sync"])

            assert result.exit_code == 0, f"Failed: {result.stdout}"
            # 終端ノードは sync 有無にかかわらず生成される
            assert (tmp_path / "src/nodes/exit/success/done.py").exists()
            assert (tmp_path / "src/nodes/exit/failure/error.py").exists()
        finally:
            os.chdir(old_cwd)
