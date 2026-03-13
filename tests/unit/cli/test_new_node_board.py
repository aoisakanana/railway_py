"""Tests for railway new node Board mode template generation (Issue 26-01).

Board モードがデフォルトで生成されることを保証する:
1. デフォルト (dag) で Board テンプレートが生成される
2. Board テンプレートでは Contract ファイルが生成されない
3. テストテンプレートが BoardBase を使う
4. 階層ノードでも Board テンプレートが生成される
"""

import pytest
from pathlib import Path
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def project_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Board テンプレートテスト用のプロジェクト構造をセットアップ。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "src" / "nodes").mkdir(parents=True)
    (tmp_path / "src" / "contracts").mkdir(parents=True)
    (tmp_path / "src" / "contracts" / "__init__.py").write_text('"""Contracts."""\n')
    (tmp_path / "tests" / "nodes").mkdir(parents=True)
    return tmp_path


class TestNewNodeBoardTemplate:
    """デフォルト (dag) モードで Board テンプレートが生成されることのテスト。"""

    def test_default_generates_board_template(self, project_dir: Path) -> None:
        """デフォルトで Board テンプレートが生成されること。

        Board テンプレートの特徴:
        - 引数が board（Contract ではない）
        - Outcome を返す
        - Contract の import がない
        """
        from railway.cli.main import app

        result = runner.invoke(app, ["new", "node", "process"])
        assert result.exit_code == 0

        node_content = (project_dir / "src" / "nodes" / "process.py").read_text()
        assert "def process(board)" in node_content
        assert "Outcome" in node_content
        assert "Contract" not in node_content

    def test_board_template_returns_outcome_only(self, project_dir: Path) -> None:
        """Board テンプレートは Outcome のみを返す（tuple ではない）。"""
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "check_status"])
        node_content = (project_dir / "src" / "nodes" / "check_status.py").read_text()

        # tuple[..., Outcome] ではなく、 -> Outcome のみ
        assert "-> Outcome:" in node_content
        assert "tuple[" not in node_content

    def test_board_template_has_no_contract_file(self, project_dir: Path) -> None:
        """Board モードでは Contract ファイルが生成されないこと。"""
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "process"])

        contract_file = project_dir / "src" / "contracts" / "process_context.py"
        assert not contract_file.exists()

    def test_board_template_is_valid_python(self, project_dir: Path) -> None:
        """生成されたコードが有効な Python であること。"""
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "check_data"])
        node_content = (project_dir / "src" / "nodes" / "check_data.py").read_text()

        # 構文チェック
        compile(node_content, "<string>", "exec")

    def test_board_test_template_uses_board_base(self, project_dir: Path) -> None:
        """テストテンプレートが BoardBase を使うこと。"""
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "process"])
        test_content = (project_dir / "tests" / "nodes" / "test_process.py").read_text()

        assert "BoardBase" in test_content
        assert "Outcome" in test_content

    def test_board_test_template_no_tuple_unpacking(self, project_dir: Path) -> None:
        """Board モードのテストに tuple アンパックがないこと。"""
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "process"])
        test_content = (project_dir / "tests" / "nodes" / "test_process.py").read_text()

        assert "result_ctx, outcome" not in test_content
        assert "ctx, outcome" not in test_content

    def test_board_test_template_is_valid_python(self, project_dir: Path) -> None:
        """テストテンプレートが有効な Python であること。"""
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "check_data"])
        test_content = (
            project_dir / "tests" / "nodes" / "test_check_data.py"
        ).read_text()

        compile(test_content, "<string>", "exec")


class TestNewNodeBoardHierarchical:
    """ドット区切り階層ノードでも Board テンプレートが生成されること。"""

    def test_hierarchical_board_node(self, project_dir: Path) -> None:
        """ドット区切りノード名で階層ディレクトリが生成されること。"""
        from railway.cli.main import app

        result = runner.invoke(app, ["new", "node", "processing.validate"])
        assert result.exit_code == 0

        node_path = (
            project_dir / "src" / "nodes" / "processing" / "validate.py"
        )
        content = node_path.read_text()
        assert "def validate(board)" in content
        assert "Outcome" in content
        assert "Contract" not in content

    def test_hierarchical_board_node_no_contract(self, project_dir: Path) -> None:
        """階層ノードでも Contract ファイルが生成されないこと。"""
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "processing.validate"])

        contract_path = (
            project_dir / "src" / "contracts" / "processing" / "validate_context.py"
        )
        assert not contract_path.exists()

    def test_hierarchical_board_node_test(self, project_dir: Path) -> None:
        """階層ノードのテストが BoardBase を使うこと。"""
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "processing.validate"])

        test_path = (
            project_dir / "tests" / "nodes" / "processing" / "test_validate.py"
        )
        assert test_path.exists()
        content = test_path.read_text()
        assert "BoardBase" in content


class TestNewNodeBoardCliOutput:
    """Board モードの CLI 出力テスト。"""

    def test_no_contract_in_output(self, project_dir: Path) -> None:
        """Board モードでは Contract ファイルが出力に表示されないこと。"""
        from railway.cli.main import app

        result = runner.invoke(app, ["new", "node", "process"])

        assert "src/nodes/process.py" in result.output
        assert "contracts" not in result.output.lower() or "contract" not in result.output.lower()

    def test_shows_test_file(self, project_dir: Path) -> None:
        """テストファイルが出力に表示されること。"""
        from railway.cli.main import app

        result = runner.invoke(app, ["new", "node", "check_data"])
        assert "tests/nodes/test_check_data.py" in result.output
