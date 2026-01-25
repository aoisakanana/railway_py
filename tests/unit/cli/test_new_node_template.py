"""Tests for railway new node template generation.

このテストスイートは以下を保証する：
1. 生成されるコードがdag_runner形式に準拠している
2. Contractが自動生成される
3. TDDワークフローを促進するテストテンプレートが生成される
4. 既存オプションとの後方互換性
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
    """Test railway new node generates dag-style template by default.

    DAG形式がデフォルトである理由：
    - 条件分岐を含むワークフローに対応（運用自動化の多くのケース）
    - Outcome による遷移制御で複雑なフローを表現可能
    - YAML遷移グラフとの親和性が高い
    """

    def test_node_returns_tuple_contract_outcome(self, project_dir):
        """Node should return tuple[Contract, Outcome] by default.

        重要性: dag_runnerは tuple[Contract, Outcome] を期待する。
        これにより遷移先をOutcomeで制御できる。
        """
        from railway.cli.main import app

        result = runner.invoke(app, ["new", "node", "check_status"])

        assert result.exit_code == 0

        node_content = (project_dir / "src" / "nodes" / "check_status.py").read_text()

        # Should import Outcome
        assert "from railway.core.dag.outcome import Outcome" in node_content
        # Should return tuple with Contract and Outcome
        assert "tuple[CheckStatusContext, Outcome]" in node_content
        assert "Outcome.success" in node_content

    def test_node_creates_context_contract(self, project_dir):
        """Should create a Context Contract for the node.

        重要性: Contractを自動生成することで：
        - 型安全がすぐに有効になる
        - IDE補完が効く
        - 手動でファイルを作成する手間を省く
        """
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "validate_input"])

        contract_path = project_dir / "src" / "contracts" / "validate_input_context.py"
        assert contract_path.exists(), "Should create context contract"

        contract_content = contract_path.read_text()
        assert "class ValidateInputContext(Contract):" in contract_content
        assert "from railway import Contract" in contract_content

    def test_node_imports_context_contract(self, project_dir):
        """Node should import its Context Contract.

        重要性: import文が正しく設定されていることで、
        生成直後からコードが動作する。
        """
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "process_data"])

        node_content = (project_dir / "src" / "nodes" / "process_data.py").read_text()

        assert "from contracts.process_data_context import ProcessDataContext" in node_content

    def test_node_shows_immutable_update_pattern(self, project_dir):
        """Node template should demonstrate immutable update with model_copy.

        重要性: イミュータブル更新パターンを例示することで：
        - 予期せぬ副作用によるバグを防止
        - テストが簡単になる（入力を与えて出力を確認するだけ）
        - 並行処理での安全性確保
        """
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "update_status"])

        node_content = (project_dir / "src" / "nodes" / "update_status.py").read_text()

        # Should show model_copy pattern for immutable updates
        assert "model_copy" in node_content or "# ctx.model_copy" in node_content

    def test_dag_mode_explicit(self, project_dir):
        """Should accept --mode dag explicitly.

        重要性: 明示的に指定できることで、
        スクリプトやCIでの利用時に意図を明確化できる。
        """
        from railway.cli.main import app

        result = runner.invoke(app, ["new", "node", "explicit_dag", "--mode", "dag"])

        assert result.exit_code == 0
        node_content = (project_dir / "src" / "nodes" / "explicit_dag.py").read_text()
        assert "Outcome" in node_content


class TestNewNodeLinearMode:
    """Test railway new node --mode linear generates typed_pipeline style.

    linear形式が存在する理由：
    - ETL、データ変換パイプラインに最適
    - Outcome不要でシンプル
    - typed_pipeline との親和性
    """

    def test_linear_node_returns_contract(self, project_dir):
        """Linear node should return Contract (not tuple).

        重要性: linear形式ではOutcomeを使用しないため、
        シンプルなContract返却のみで良い。
        """
        from railway.cli.main import app

        result = runner.invoke(app, ["new", "node", "transform", "--mode", "linear"])

        assert result.exit_code == 0

        node_content = (project_dir / "src" / "nodes" / "transform.py").read_text()

        # Should NOT use Outcome
        assert "Outcome" not in node_content
        # Should return Contract directly
        assert "-> TransformOutput:" in node_content

    def test_linear_node_has_optional_input_parameter(self, project_dir):
        """Linear node should have optional input Contract parameter.

        重要性: Optional にすることで、パイプラインの最初のノードとしても
        途中のノードとしても使用可能になる。
        """
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "process", "--mode", "linear"])

        node_content = (project_dir / "src" / "nodes" / "process.py").read_text()

        # Should have optional input parameter (first node may not have input)
        assert "Optional[ProcessInput]" in node_content
        assert "input_data" in node_content

    def test_linear_node_creates_both_contracts(self, project_dir):
        """Linear node should create both Input and Output Contracts.

        重要性: Input/Outputの両方を生成することで、
        型安全なパイプラインをすぐに構築できる。
        """
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "aggregate", "--mode", "linear"])

        # Should create input contract
        input_path = project_dir / "src" / "contracts" / "aggregate_input.py"
        assert input_path.exists(), "Should create input contract"

        # Should create output contract
        output_path = project_dir / "src" / "contracts" / "aggregate_output.py"
        assert output_path.exists(), "Should create output contract"


class TestNewNodeTestTemplate:
    """Test that node test templates match the new node style.

    テストテンプレートが重要な理由：
    - TDDワークフローをすぐに開始できる
    - テストの書き方のお手本を提供
    - 「テストを書く」心理的ハードルを下げる
    """

    def test_dag_node_test_imports_outcome(self, project_dir):
        """Test template for dag node should import and test Outcome.

        重要性: Outcome検証の例を示すことで、
        正しい遷移制御のテスト方法を学べる。
        """
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "check_health"])

        test_content = (project_dir / "tests" / "nodes" / "test_check_health.py").read_text()

        # Test should import from correct paths
        assert "from nodes.check_health import check_health" in test_content
        assert "from contracts.check_health_context import CheckHealthContext" in test_content
        # Test should verify outcome
        assert "outcome.is_success" in test_content or "Outcome" in test_content

    def test_linear_node_test_imports_contracts(self, project_dir):
        """Test template for linear node should import both contracts.

        重要性: Input/Outputの両方をテストで使用する例を示す。
        """
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "format_output", "--mode", "linear"])

        test_content = (project_dir / "tests" / "nodes" / "test_format_output.py").read_text()

        # Test should reference input and output Contracts
        assert "FormatOutputInput" in test_content or "FormatOutputOutput" in test_content

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


class TestNewNodeContractIntegration:
    """Test integration between node and contract generation.

    ノードとContractの整合性が重要な理由：
    - 生成直後からコードが動作する
    - import文のタイポによるエラーを防止
    - IDE補完が即座に効く
    """

    def test_node_and_contract_are_consistent(self, project_dir):
        """Node signature should match generated contract.

        重要性: クラス名が一致していないとimportエラーになる。
        この整合性テストで回帰を防止。
        """
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "validate"])

        node_content = (project_dir / "src" / "nodes" / "validate.py").read_text()
        contract_content = (project_dir / "src" / "contracts" / "validate_context.py").read_text()

        # Contract class name should match import in node
        assert "ValidateContext" in contract_content
        assert "ValidateContext" in node_content

    def test_existing_contract_not_overwritten(self, project_dir):
        """Should not overwrite existing contract file but still create node.

        重要性: ユーザーが既に作成したContractを誤って上書きしない。
        安全性のための重要なガード。
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

        # But node should still be created
        node_path = project_dir / "src" / "nodes" / "my_node.py"
        assert node_path.exists(), "Node should be created even if contract exists"


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
        assert "src/contracts/show_files_context.py" in result.output
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

    def test_linear_mode_shows_both_contracts(self, project_dir):
        """Linear mode should show both input and output contracts.

        重要性: linear モードでは2つのContractが生成されることを
        明示的に伝える。
        """
        from railway.cli.main import app

        result = runner.invoke(app, ["new", "node", "both_contracts", "--mode", "linear"])

        assert "both_contracts_input.py" in result.output
        assert "both_contracts_output.py" in result.output


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

    def test_mode_ignored_when_output_specified(self, project_dir):
        """--mode should be ignored when --output is specified.

        重要性: --output 指定時は既存のテンプレートを使用し、
        予期せぬ動作変更を防止する。
        """
        from railway.cli.main import app

        runner.invoke(app, ["new", "contract", "CustomOutput"])

        result = runner.invoke(
            app,
            ["new", "node", "custom", "--output", "CustomOutput", "--mode", "dag"],
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

    def test_force_overwrites_contract(self, project_dir):
        """--force should overwrite existing contract.

        重要性: Contractも含めて上書きできることで、
        完全な再生成が可能になる。
        """
        from railway.cli.main import app

        # Create contract
        contract_path = project_dir / "src" / "contracts" / "force_test_context.py"
        contract_path.write_text("# Old contract")

        # Create node with force (should overwrite contract too)
        result = runner.invoke(app, ["new", "node", "force_test", "--force"])

        assert result.exit_code == 0
        content = contract_path.read_text()
        assert "ForceTestContext" in content
