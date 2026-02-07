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
        """--no-sync でエントリポイントは pending 状態（実行可能だが sync を促す）。"""
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
            # 実行可能なコード（コメントアウトされていない）
            assert "@entry_point" in entrypoint
            assert "# @entry_point" not in entrypoint
            # sync を促すメッセージがある
            assert "railway sync transition" in entrypoint
            # transitions がない場合のエラーハンドリング
            assert "ModuleNotFoundError" in entrypoint
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


class TestExistingYamlHandling:
    """既存 YAML ファイルの処理テスト。"""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_existing_new_format_yaml_is_not_overwritten(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """新形式の既存 YAML は上書きしない。"""
        from railway.cli.main import app
        import os

        (tmp_path / "src").mkdir()
        (tmp_path / "transition_graphs").mkdir()
        (tmp_path / "_railway/generated").mkdir(parents=True)

        # 既存の新形式 YAML を作成
        existing_yaml = tmp_path / "transition_graphs/greeting_20260101000000.yml"
        existing_content = '''version: "1.0"
entrypoint: greeting
description: "カスタム説明"

nodes:
  start:
    description: "開始"
  exit:
    success:
      done:
        description: "完了"

start: start

transitions:
  start:
    success::done: exit.success.done
'''
        existing_yaml.write_text(existing_content)

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["new", "entry", "greeting"])

            assert result.exit_code == 0, f"Failed: {result.stdout}"
            # 既存 YAML の内容が保持されている
            assert existing_yaml.read_text() == existing_content
            # 新しい YAML が作成されていない
            yamls = list((tmp_path / "transition_graphs").glob("greeting_*.yml"))
            assert len(yamls) == 1
            assert yamls[0].name == "greeting_20260101000000.yml"
        finally:
            os.chdir(old_cwd)

    def test_existing_old_format_yaml_is_converted(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """旧形式の既存 YAML は新形式に変換される。"""
        from railway.cli.main import app
        import os

        (tmp_path / "src").mkdir()
        (tmp_path / "transition_graphs").mkdir()
        (tmp_path / "_railway/generated").mkdir(parents=True)

        # 既存の旧形式 YAML を作成
        existing_yaml = tmp_path / "transition_graphs/greeting_20260101000000.yml"
        old_format_content = '''version: "1.0"
entrypoint: greeting
description: "テスト"

nodes:
  start:
    description: "開始"

exits:
  green_done:
    code: 0
    description: "正常終了"

start: start

transitions:
  start:
    success::done: exit::green_done
'''
        existing_yaml.write_text(old_format_content)

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["new", "entry", "greeting"])

            assert result.exit_code == 0, f"Failed: {result.stdout}"
            # YAML が変換されている
            converted = existing_yaml.read_text()
            assert "exits:" not in converted
            assert "exit:" in converted or "exit" in converted
        finally:
            os.chdir(old_cwd)

    def test_existing_entrypoint_is_not_overwritten(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """既存のエントリポイントは上書きしない。"""
        from railway.cli.main import app
        import os

        (tmp_path / "src").mkdir()
        (tmp_path / "transition_graphs").mkdir()
        (tmp_path / "_railway/generated").mkdir(parents=True)

        # 既存のエントリポイントを作成
        entry_file = tmp_path / "src/greeting.py"
        custom_content = "# Custom entrypoint\nprint('hello')\n"
        entry_file.write_text(custom_content)

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["new", "entry", "greeting"])

            assert result.exit_code == 0, f"Failed: {result.stdout}"
            # 既存のエントリポイントが保持されている
            assert entry_file.read_text() == custom_content
        finally:
            os.chdir(old_cwd)
