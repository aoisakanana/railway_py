"""Tests for railway new node template generation.

このテストスイートは以下を保証する：
1. 生成されるコードがdag_runner形式に準拠している
2. TDDワークフローを促進するテストテンプレートが生成される
3. 既存オプションとの後方互換性
"""

import pytest
from pathlib import Path
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def project_dir(tmp_path, monkeypatch):
    """Set up minimal project structure for tests.

    純粋なテスト環境を用意し、他のテストからの影響を排除する。
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / "src" / "nodes").mkdir(parents=True)
    (tmp_path / "src" / "contracts").mkdir(parents=True)
    (tmp_path / "src" / "contracts" / "__init__.py").write_text('"""Contracts."""\n')
    (tmp_path / "tests" / "nodes").mkdir(parents=True)
    return tmp_path


class TestNewNodeDagMode:
    """Test railway new node generates Board mode template by default.

    Board モードがデフォルトである理由：
    - board を引数に取り Outcome を返すシンプルなインターフェース
    - Contract 定義不要で迅速にノード開発を開始できる
    - YAML遷移グラフとの親和性が高い
    """

    def test_node_returns_outcome(self, project_dir):
        """Node should return Outcome (Board mode) by default.

        重要性: Board モードでは board を引数に取り Outcome を返す。
        """
        from railway.cli.main import app

        result = runner.invoke(app, ["new", "node", "check_status"])

        assert result.exit_code == 0

        node_content = (project_dir / "src" / "nodes" / "check_status.py").read_text()

        # Should import Outcome
        assert "from railway.core.dag import Outcome" in node_content
        # Board mode: board argument, returns Outcome
        assert "def check_status(board)" in node_content
        assert "-> Outcome:" in node_content
        assert "Outcome.success" in node_content

    def test_node_does_not_create_contract(self, project_dir):
        """Board mode should NOT create a Contract file.

        重要性: Board モードでは Contract 不要。
        """
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "validate_input"])

        contract_path = project_dir / "src" / "contracts" / "validate_input_context.py"
        assert not contract_path.exists(), "Board mode should not create contract"

    def test_node_does_not_import_contract(self, project_dir):
        """Board mode node should not import Contract.

        重要性: Board モードではノードが Contract を使用しない。
        """
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "process_data"])

        node_content = (project_dir / "src" / "nodes" / "process_data.py").read_text()

        assert "Contract" not in node_content

    def test_node_uses_board_argument(self, project_dir):
        """Board mode node should use board argument.

        重要性: Board パターンにより mutable な共有状態を使用。
        """
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "update_status"])

        node_content = (project_dir / "src" / "nodes" / "update_status.py").read_text()

        assert "def update_status(board)" in node_content

    def test_dag_mode_is_only_mode(self, project_dir):
        """Board mode is always used (no --mode option).

        重要性: linear モードが削除されたため、dag のみ。
        """
        from railway.cli.main import app

        result = runner.invoke(app, ["new", "node", "explicit_dag"])

        assert result.exit_code == 0
        node_content = (project_dir / "src" / "nodes" / "explicit_dag.py").read_text()
        assert "Outcome" in node_content
        assert "def explicit_dag(board)" in node_content


class TestNewNodeTestTemplate:
    """Test that node test templates match the new node style.

    テストテンプレートが重要な理由：
    - TDDワークフローをすぐに開始できる
    - テストの書き方のお手本を提供
    - 「テストを書く」心理的ハードルを下げる
    """

    def test_dag_node_test_uses_board_base(self, project_dir):
        """Test template for Board mode node should use BoardBase.

        重要性: BoardBase を使ったテストパターンを示すことで、
        Board モードの正しいテスト方法を学べる。
        """
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "check_health"])

        test_content = (project_dir / "tests" / "nodes" / "test_check_health.py").read_text()

        # Test should import from correct paths
        assert "from nodes.check_health import check_health" in test_content
        assert "from railway.core.board import BoardBase" in test_content
        # Test should verify outcome
        assert "Outcome" in test_content
        # Board mode: no Contract import
        assert "CheckHealthContext" not in test_content

    def test_test_has_tdd_workflow_comment(self, project_dir):
        """Test template should have TDD workflow comment.

        重要性: TDDワークフローの手順を示すことで、
        開発者がRed-Green-Refactorサイクルを実践できる。
        """
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "my_node"])

        test_content = (project_dir / "tests" / "nodes" / "test_my_node.py").read_text()

        assert "TDD Workflow" in test_content
        assert "uv run pytest" in test_content


class TestNewNodeBoardModeIntegration:
    """Test Board mode node generation integration.

    Board モードの統合テスト：
    - Contract ファイルが生成されない
    - ノードファイルが正しく生成される
    """

    def test_node_is_self_contained(self, project_dir):
        """Board mode node should be self-contained (no Contract dependency).

        重要性: Board モードでは Contract 不要。
        ノードファイルだけで動作する。
        """
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "validate"])

        node_content = (project_dir / "src" / "nodes" / "validate.py").read_text()

        # Board mode: no Contract import
        assert "Contract" not in node_content
        assert "def validate(board)" in node_content

    def test_existing_contract_not_affected(self, project_dir):
        """Board mode should not touch existing contract files.

        重要性: Board モードでは Contract を生成しないため、
        既存の Contract ファイルに影響しない。
        """
        from railway.cli.main import app

        # Create existing contract
        existing_content = '"""Existing contract."""\nclass CustomContext: pass\n'
        (project_dir / "src" / "contracts" / "my_node_context.py").write_text(existing_content)

        result = runner.invoke(app, ["new", "node", "my_node"])

        # Command should succeed
        assert result.exit_code == 0

        # Contract should not be overwritten
        contract_content = (project_dir / "src" / "contracts" / "my_node_context.py").read_text()
        assert "Existing contract" in contract_content

        # Node should still be created
        node_path = project_dir / "src" / "nodes" / "my_node.py"
        assert node_path.exists(), "Node should be created"


class TestNewNodeCliOutput:
    """Test CLI output messages.

    CLI出力が重要な理由：
    - ユーザーが何が生成されたかを即座に把握できる
    - 次のステップ（TDDワークフロー）を案内する
    - 発見可能性を高める
    """

    def test_shows_created_files(self, project_dir):
        """Should show list of created files.

        重要性: どのファイルが生成されたかを明示することで、
        ユーザーは次にどのファイルを編集すべきか分かる。
        """
        from railway.cli.main import app

        result = runner.invoke(app, ["new", "node", "show_files"])

        assert "src/nodes/show_files.py" in result.output
        # Board mode: no contract files
        assert "tests/nodes/test_show_files.py" in result.output

    def test_shows_tdd_workflow(self, project_dir):
        """Should show TDD workflow instructions.

        重要性: TDDワークフローを案内することで、
        テスト駆動開発の文化を促進する。
        """
        from railway.cli.main import app

        result = runner.invoke(app, ["new", "node", "tdd_test"])

        assert "TDD" in result.output or "tdd" in result.output.lower()
        assert "pytest" in result.output


class TestNewNodeBackwardsCompatibility:
    """Test that existing typed node options still work.

    後方互換性が重要な理由：
    - 既存ユーザーのスクリプトやワークフローを壊さない
    - 段階的な移行を可能にする
    - --output / --input オプションは特定のユースケースで有用
    """

    def test_output_option_still_works(self, project_dir):
        """--output option should still work for custom output types.

        重要性: 既存の typed_pipeline ユーザーが
        引き続き同じ方法でノードを生成できる。
        """
        from railway.cli.main import app

        # First create a contract
        runner.invoke(app, ["new", "contract", "UserList"])

        # Then create node with --output
        result = runner.invoke(app, ["new", "node", "fetch_users", "--output", "UserList"])

        assert result.exit_code == 0

        node_content = (project_dir / "src" / "nodes" / "fetch_users.py").read_text()
        assert "UserList" in node_content

    def test_input_option_still_works(self, project_dir):
        """--input option should still work.

        重要性: 入力型を明示的に指定するワークフローをサポート。
        """
        from railway.cli.main import app

        # Create contracts
        runner.invoke(app, ["new", "contract", "InputData"])
        runner.invoke(app, ["new", "contract", "OutputData"])

        # Create node with input/output
        result = runner.invoke(
            app,
            ["new", "node", "process", "--input", "data:InputData", "--output", "OutputData"],
        )

        assert result.exit_code == 0

    def test_output_uses_typed_template(self, project_dir):
        """--output should use typed template (not dag template).

        重要性: --output 指定時は既存のテンプレートを使用し、
        予期せぬ動作変更を防止する。
        """
        from railway.cli.main import app

        runner.invoke(app, ["new", "contract", "CustomOutput"])

        result = runner.invoke(
            app,
            ["new", "node", "custom", "--output", "CustomOutput"],
        )

        assert result.exit_code == 0

        # Should use typed template, not dag template
        node_content = (project_dir / "src" / "nodes" / "custom.py").read_text()
        assert "Outcome" not in node_content  # typed template doesn't use Outcome


class TestNewNodeForceOption:
    """Test --force option with new templates.

    --force オプションが重要な理由：
    - テンプレート更新後に再生成したい場合がある
    - 間違った内容を上書きで修正できる
    - CI/CDでの自動再生成に使用できる
    """

    def test_force_overwrites_node(self, project_dir):
        """--force should overwrite existing node.

        重要性: 意図的な上書きを可能にすることで、
        テンプレート更新後の再生成をサポート。
        """
        from railway.cli.main import app

        # Create initial node
        runner.invoke(app, ["new", "node", "overwrite_me"])

        # Modify the file
        node_path = project_dir / "src" / "nodes" / "overwrite_me.py"
        node_path.write_text("# Modified content")

        # Overwrite with force
        result = runner.invoke(app, ["new", "node", "overwrite_me", "--force"])

        assert result.exit_code == 0
        content = node_path.read_text()
        assert "# Modified content" not in content
        assert "@node" in content

    def test_force_overwrites_board_node(self, project_dir):
        """--force should overwrite existing Board mode node file.

        重要性: Board モードではノードファイルのみが上書きされる。
        Contract ファイルは生成されない。
        """
        from railway.cli.main import app

        # Create initial node
        node_path = project_dir / "src" / "nodes" / "force_test.py"
        node_path.parent.mkdir(parents=True, exist_ok=True)
        node_path.write_text("# Old node content")

        # Overwrite with force
        result = runner.invoke(app, ["new", "node", "force_test", "--force"])

        assert result.exit_code == 0
        content = node_path.read_text()
        assert "def force_test(board)" in content
