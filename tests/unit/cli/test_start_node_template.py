"""Tests for start node template generation.

Issue #66: 開始ノードの引数整合性問題
- 開始ノードは optional な context を受け取る形式で生成される
- run() 関数から初期コンテキストを渡せる
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from railway.cli.main import app

runner = CliRunner()


def _init_project(parent_path: Path, project_name: str) -> Path:
    """テスト用プロジェクト初期化ヘルパー。

    Returns:
        作成されたプロジェクトのパス
    """
    result = runner.invoke(app, ["init", project_name], catch_exceptions=False)
    assert result.exit_code == 0, f"init failed: {result.output}"
    return parent_path / project_name


class TestStartNodeTemplate:
    """開始ノードテンプレートのテスト。"""

    def test_start_node_uses_board_argument(self, tmp_path: Path, monkeypatch):
        """開始ノードは board 引数を受け取る（Board モード）。"""
        monkeypatch.chdir(tmp_path)
        project_path = _init_project(tmp_path, "myproject")
        monkeypatch.chdir(project_path)

        result = runner.invoke(app, ["new", "entry", "greeting"])
        assert result.exit_code == 0

        start_file = project_path / "src" / "nodes" / "greeting" / "start.py"
        assert start_file.exists(), f"start.py not found at {start_file}"

        content = start_file.read_text()
        assert "def start(board)" in content
        assert "Outcome" in content

    def test_start_node_returns_outcome(self, tmp_path: Path, monkeypatch):
        """開始ノードは Outcome を返す（Board モード）。"""
        monkeypatch.chdir(tmp_path)
        project_path = _init_project(tmp_path, "myproject")
        monkeypatch.chdir(project_path)

        runner.invoke(app, ["new", "entry", "greeting"])

        start_file = project_path / "src" / "nodes" / "greeting" / "start.py"
        content = start_file.read_text()

        assert "Outcome.success" in content


class TestStartNodeExecution:
    """開始ノード実行のテスト。"""

    def test_generated_workflow_can_run(self, tmp_path: Path, monkeypatch):
        """生成されたワークフローが実行できる。"""
        monkeypatch.chdir(tmp_path)
        project_path = _init_project(tmp_path, "myproject")
        monkeypatch.chdir(project_path)

        result = runner.invoke(app, ["new", "entry", "greeting"])
        assert result.exit_code == 0

        # run コマンドで実行
        run_result = runner.invoke(app, ["run", "greeting"])
        # TypeError が発生しないことを確認
        assert "TypeError" not in (run_result.output or "")
        assert "takes 0 positional arguments" not in (run_result.output or "")
