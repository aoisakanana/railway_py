"""Tests for railway new entry Board mode template generation (Issue 26-02).

Board モードのエントリーポイント生成を保証する:
1. デフォルトで Board モードのエントリーポイントが生成される
2. 開始ノードが board 引数を使う
3. 終端ノードが board 引数を使い None を返す
4. テストテンプレートが BoardBase を使う
"""

import pytest
from pathlib import Path
from typer.testing import CliRunner

runner = CliRunner()


def _init_project(path: Path) -> None:
    """プロジェクト構造のセットアップ。"""
    (path / "src").mkdir()
    (path / "src" / "nodes").mkdir()
    (path / "transition_graphs").mkdir()
    (path / "_railway" / "generated").mkdir(parents=True)
    (path / "pyproject.toml").write_text('[project]\nname = "test"')


class TestNewEntryBoardStartNode:
    """開始ノードが Board テンプレートで生成されること。"""

    def test_start_node_uses_board(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """開始ノードが board 引数を使うこと。"""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(app, ["new", "entry", "my_workflow"])
        assert result.exit_code == 0, f"Failed: {result.stdout}"

        start_file = tmp_path / "src" / "nodes" / "my_workflow" / "start.py"
        assert start_file.exists()
        content = start_file.read_text()
        assert "def start(board)" in content
        assert "Outcome" in content
        # Contract クラスを使用していない
        assert "class " not in content or "Contract" not in content

    def test_start_node_returns_outcome(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """開始ノードが Outcome のみを返すこと（tuple ではない）。"""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        runner.invoke(app, ["new", "entry", "my_workflow"])

        start_file = tmp_path / "src" / "nodes" / "my_workflow" / "start.py"
        content = start_file.read_text()
        assert "-> Outcome:" in content or "Outcome.success" in content
        assert "tuple[" not in content

    def test_start_node_is_valid_python(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """開始ノードが有効な Python であること。"""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        runner.invoke(app, ["new", "entry", "my_workflow"])

        start_file = tmp_path / "src" / "nodes" / "my_workflow" / "start.py"
        content = start_file.read_text()
        compile(content, "<string>", "exec")


class TestNewEntryBoardExitNode:
    """終端ノードが Board テンプレートで生成されること。"""

    def test_exit_node_uses_board_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """終端ノードが board 引数を使い None を返すこと。"""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        runner.invoke(app, ["new", "entry", "my_workflow"])

        exit_file = tmp_path / "src" / "nodes" / "exit" / "success" / "done.py"
        assert exit_file.exists()
        content = exit_file.read_text()
        assert "def done(board)" in content
        assert "ExitContract" not in content
        assert "-> None:" in content

    def test_exit_node_is_valid_python(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """終端ノードが有効な Python であること。"""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        runner.invoke(app, ["new", "entry", "my_workflow"])

        exit_file = tmp_path / "src" / "nodes" / "exit" / "success" / "done.py"
        content = exit_file.read_text()
        compile(content, "<string>", "exec")

    def test_failure_exit_node_uses_board(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """failure 終端ノードも board を使うこと。"""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        runner.invoke(app, ["new", "entry", "my_workflow"])

        exit_file = tmp_path / "src" / "nodes" / "exit" / "failure" / "error.py"
        assert exit_file.exists()
        content = exit_file.read_text()
        assert "board" in content
        assert "ExitContract" not in content


class TestNewEntryBoardEntryPoint:
    """エントリーポイントが Board モードで生成されること。"""

    def test_entry_uses_run_helper(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """エントリーポイントが run() ヘルパーを使うこと。"""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        runner.invoke(app, ["new", "entry", "my_workflow"])

        entry_file = tmp_path / "src" / "my_workflow.py"
        content = entry_file.read_text()
        assert "from _railway.generated.my_workflow_transitions import run" in content
        assert "result = run(" in content

    def test_entry_checks_is_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """エントリーポイントが is_success を確認すること。"""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        runner.invoke(app, ["new", "entry", "my_workflow"])

        entry_file = tmp_path / "src" / "my_workflow.py"
        content = entry_file.read_text()
        assert "result.is_success" in content
        assert "result.exit_state" in content


class TestNewEntryBoardTestTemplate:
    """テストテンプレートが Board モードで生成されること (Issue 26-03)。"""

    def test_entry_test_uses_board_base(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """エントリーテストが BoardBase を使うこと。"""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        runner.invoke(app, ["new", "entry", "my_workflow"])

        test_file = tmp_path / "tests" / "test_my_workflow.py"
        assert test_file.exists()
        content = test_file.read_text()
        assert "BoardBase" in content
        assert "Outcome" in content

    def test_entry_test_imports_start_node(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """エントリーテストが開始ノードを import すること。"""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        runner.invoke(app, ["new", "entry", "my_workflow"])

        test_file = tmp_path / "tests" / "test_my_workflow.py"
        content = test_file.read_text()
        assert "from nodes.my_workflow.start import start" in content

    def test_entry_test_is_valid_python(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """エントリーテストが有効な Python であること。"""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        runner.invoke(app, ["new", "entry", "my_workflow"])

        test_file = tmp_path / "tests" / "test_my_workflow.py"
        content = test_file.read_text()
        compile(content, "<string>", "exec")

    def test_entry_test_no_tuple_unpacking(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """エントリーテストに tuple アンパックがないこと。"""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        runner.invoke(app, ["new", "entry", "my_workflow"])

        test_file = tmp_path / "tests" / "test_my_workflow.py"
        content = test_file.read_text()
        assert "result_ctx, outcome" not in content
