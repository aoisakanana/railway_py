# Issue #21: railway new node テンプレートの最新化

**Phase:** 2e
**優先度:** 高
**依存関係:** #17, #20
**見積もり:** 0.5日

---

## 概要

`railway new node <name>` コマンドが生成するスケルトンコードが、現在のフレームワーク実装と一致していない。

### 現状の問題

**生成されるコード（旧形式）:**
```python
@node
def fetch_data(data: dict) -> dict:
    """..."""
    return data
```

**期待されるコード（dag_runner形式）:**
```python
@node
def fetch_data(ctx: FetchDataContext) -> tuple[FetchDataContext, Outcome]:
    """..."""
    return ctx, Outcome.success("done")
```

README.md や TUTORIAL.md は Contract + Outcome パターンを使用しているが、`railway new node` は `dict` ベースのコードを生成している。

---

## 解決策

1. **`--mode` オプションの追加**: `railway new entry` と同様に `dag` / `linear` モードを追加
2. **デフォルトをdag形式に変更**: Contract + Outcome を返す形式
3. **Contract自動生成**: ノード名に基づいたContext/Output Contractを自動生成
4. **テストテンプレート更新**: 新形式に対応したテストスケルトン
5. **イミュータブル更新パターンの例示**: `model_copy()` を使用した例

---

## 成果物

### 修正後のコマンド

```bash
# dag 形式（デフォルト）: tuple[Contract, Outcome] を返す
railway new node check_status

# linear 形式: Contract を返す（入力Contract付き）
railway new node transform_data --mode linear

# 明示的にdag形式
railway new node validate --mode dag

# 既存オプション（後方互換性）
railway new node fetch_users --output UserList
railway new node process --input data:InputData --output OutputData
```

### 生成されるファイル構成

**dag モード:**
```
src/
├── nodes/
│   └── check_status.py        # ノード本体
└── contracts/
    └── check_status_context.py # Context Contract
tests/
└── nodes/
    └── test_check_status.py   # テスト
```

**linear モード:**
```
src/
├── nodes/
│   └── transform_data.py       # ノード本体
└── contracts/
    ├── transform_data_input.py  # Input Contract
    └── transform_data_output.py # Output Contract
tests/
└── nodes/
    └── test_transform_data.py  # テスト
```

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/cli/test_new_node_template.py
"""Tests for railway new node template generation."""

import pytest
from pathlib import Path
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def project_dir(tmp_path, monkeypatch):
    """Set up minimal project structure for tests."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "src" / "nodes").mkdir(parents=True)
    (tmp_path / "src" / "contracts").mkdir(parents=True)
    (tmp_path / "src" / "contracts" / "__init__.py").write_text('"""Contracts."""\n')
    (tmp_path / "tests" / "nodes").mkdir(parents=True)
    return tmp_path


class TestNewNodeDagMode:
    """Test railway new node generates dag-style template by default."""

    def test_node_returns_tuple_contract_outcome(self, project_dir):
        """Node should return tuple[Contract, Outcome] by default."""
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
        """Should create a Context Contract for the node."""
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "validate_input"])

        contract_path = project_dir / "src" / "contracts" / "validate_input_context.py"
        assert contract_path.exists(), "Should create context contract"

        contract_content = contract_path.read_text()
        assert "class ValidateInputContext(Contract):" in contract_content
        assert "from railway import Contract" in contract_content

    def test_node_imports_context_contract(self, project_dir):
        """Node should import its Context Contract."""
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "process_data"])

        node_content = (project_dir / "src" / "nodes" / "process_data.py").read_text()

        assert "from contracts.process_data_context import ProcessDataContext" in node_content

    def test_node_shows_immutable_update_pattern(self, project_dir):
        """Node template should demonstrate immutable update with model_copy."""
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "update_status"])

        node_content = (project_dir / "src" / "nodes" / "update_status.py").read_text()

        # Should show model_copy pattern for immutable updates
        assert "model_copy" in node_content or "# ctx.model_copy" in node_content

    def test_dag_mode_explicit(self, project_dir):
        """Should accept --mode dag explicitly."""
        from railway.cli.main import app

        result = runner.invoke(app, ["new", "node", "explicit_dag", "--mode", "dag"])

        assert result.exit_code == 0
        node_content = (project_dir / "src" / "nodes" / "explicit_dag.py").read_text()
        assert "Outcome" in node_content


class TestNewNodeLinearMode:
    """Test railway new node --mode linear generates typed_pipeline style."""

    def test_linear_node_returns_contract(self, project_dir):
        """Linear node should return Contract (not tuple)."""
        from railway.cli.main import app

        result = runner.invoke(app, ["new", "node", "transform", "--mode", "linear"])

        assert result.exit_code == 0

        node_content = (project_dir / "src" / "nodes" / "transform.py").read_text()

        # Should NOT use Outcome
        assert "Outcome" not in node_content
        # Should return Contract directly
        assert "-> TransformOutput:" in node_content

    def test_linear_node_has_optional_input_parameter(self, project_dir):
        """Linear node should have optional input Contract parameter."""
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "process", "--mode", "linear"])

        node_content = (project_dir / "src" / "nodes" / "process.py").read_text()

        # Should have optional input parameter (first node may not have input)
        assert "Optional[ProcessInput]" in node_content
        assert "input_data" in node_content

    def test_linear_node_creates_both_contracts(self, project_dir):
        """Linear node should create both Input and Output Contracts."""
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "aggregate", "--mode", "linear"])

        # Should create input contract
        input_path = project_dir / "src" / "contracts" / "aggregate_input.py"
        assert input_path.exists(), "Should create input contract"

        # Should create output contract
        output_path = project_dir / "src" / "contracts" / "aggregate_output.py"
        assert output_path.exists(), "Should create output contract"


class TestNewNodeTestTemplate:
    """Test that node test templates match the new node style."""

    def test_dag_node_test_imports_outcome(self, project_dir):
        """Test template for dag node should import and test Outcome."""
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "check_health"])

        test_content = (project_dir / "tests" / "nodes" / "test_check_health.py").read_text()

        # Test should import from correct paths
        assert "from nodes.check_health import check_health" in test_content
        assert "from contracts.check_health_context import CheckHealthContext" in test_content
        # Test should verify outcome
        assert "outcome.is_success" in test_content or "Outcome" in test_content

    def test_linear_node_test_imports_contracts(self, project_dir):
        """Test template for linear node should import both contracts."""
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "format_output", "--mode", "linear"])

        test_content = (project_dir / "tests" / "nodes" / "test_format_output.py").read_text()

        # Test should reference input and output Contracts
        assert "FormatOutputInput" in test_content or "FormatOutputOutput" in test_content

    def test_test_has_tdd_workflow_comment(self, project_dir):
        """Test template should have TDD workflow comment."""
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "my_node"])

        test_content = (project_dir / "tests" / "nodes" / "test_my_node.py").read_text()

        assert "TDD Workflow" in test_content
        assert "uv run pytest" in test_content


class TestNewNodeContractIntegration:
    """Test integration between node and contract generation."""

    def test_node_and_contract_are_consistent(self, project_dir):
        """Node signature should match generated contract."""
        from railway.cli.main import app

        runner.invoke(app, ["new", "node", "validate"])

        node_content = (project_dir / "src" / "nodes" / "validate.py").read_text()
        contract_content = (project_dir / "src" / "contracts" / "validate_context.py").read_text()

        # Contract class name should match import in node
        assert "ValidateContext" in contract_content
        assert "ValidateContext" in node_content

    def test_existing_contract_not_overwritten(self, project_dir):
        """Should not overwrite existing contract file but still create node."""
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
    """Test CLI output messages."""

    def test_shows_created_files(self, project_dir):
        """Should show list of created files."""
        from railway.cli.main import app

        result = runner.invoke(app, ["new", "node", "show_files"])

        assert "src/nodes/show_files.py" in result.output
        assert "src/contracts/show_files_context.py" in result.output
        assert "tests/nodes/test_show_files.py" in result.output

    def test_shows_tdd_workflow(self, project_dir):
        """Should show TDD workflow instructions."""
        from railway.cli.main import app

        result = runner.invoke(app, ["new", "node", "tdd_test"])

        assert "TDD" in result.output or "tdd" in result.output.lower()
        assert "pytest" in result.output

    def test_linear_mode_shows_both_contracts(self, project_dir):
        """Linear mode should show both input and output contracts."""
        from railway.cli.main import app

        result = runner.invoke(app, ["new", "node", "both_contracts", "--mode", "linear"])

        assert "both_contracts_input.py" in result.output
        assert "both_contracts_output.py" in result.output


class TestNewNodeBackwardsCompatibility:
    """Test that existing typed node options still work."""

    def test_output_option_still_works(self, project_dir):
        """--output option should still work for custom output types."""
        from railway.cli.main import app

        # First create a contract
        runner.invoke(app, ["new", "contract", "UserList"])

        # Then create node with --output
        result = runner.invoke(app, ["new", "node", "fetch_users", "--output", "UserList"])

        assert result.exit_code == 0

        node_content = (project_dir / "src" / "nodes" / "fetch_users.py").read_text()
        assert "UserList" in node_content

    def test_input_option_still_works(self, project_dir):
        """--input option should still work."""
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
        """--mode should be ignored when --output is specified."""
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
    """Test --force option with new templates."""

    def test_force_overwrites_node(self, project_dir):
        """--force should overwrite existing node."""
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
        """--force should overwrite existing contract."""
        from railway.cli.main import app

        # Create contract
        contract_path = project_dir / "src" / "contracts" / "force_test_context.py"
        contract_path.write_text("# Old contract")

        # Create node with force (should overwrite contract too)
        result = runner.invoke(app, ["new", "node", "force_test", "--force"])

        assert result.exit_code == 0
        content = contract_path.read_text()
        assert "ForceTestContext" in content
```

### Step 2: Green（実装）

`railway/cli/new.py` を修正：

```python
# 1. NodeMode Enum を追加（EntryMode の隣に）
class NodeMode(str, Enum):
    """Node template mode."""
    dag = "dag"
    linear = "linear"


# 2. 新しいテンプレート関数を追加

def _get_dag_node_standalone_template(name: str) -> str:
    """Get dag-style node template that returns tuple[Contract, Outcome].

    Pure function: name -> template string
    """
    class_name = _to_pascal_case(name)
    return f'''"""{name} ノード"""

from railway import node
from railway.core.dag.outcome import Outcome

from contracts.{name}_context import {class_name}Context


@node
def {name}(ctx: {class_name}Context) -> tuple[{class_name}Context, Outcome]:
    """
    {name} の処理を実行する。

    Args:
        ctx: ワークフローコンテキスト

    Returns:
        (context, outcome): 更新されたコンテキストと結果
    """
    # イミュータブル更新の例:
    # updated_ctx = ctx.model_copy(update={{"processed": True}})
    # return updated_ctx, Outcome.success("done")

    # TODO: 実装を追加
    return ctx, Outcome.success("done")
'''


def _get_dag_node_context_template(name: str) -> str:
    """Get Context Contract template for dag node.

    Pure function: name -> template string
    """
    class_name = _to_pascal_case(name)
    return f'''"""{class_name}Context - {name} ノードのコンテキスト"""

from railway import Contract


class {class_name}Context(Contract):
    """
    {name} ノードのコンテキスト。

    Contract は不変（イミュータブル）です。
    更新時は model_copy() を使用してください。

    Example:
        ctx = {class_name}Context(value="initial")
        updated = ctx.model_copy(update={{"value": "updated"}})
    """
    # TODO: 必要なフィールドを定義してください
    # value: str
    # processed: bool = False
    pass
'''


def _get_linear_node_standalone_template(name: str) -> str:
    """Get linear-style node template that returns Contract.

    Pure function: name -> template string
    """
    class_name = _to_pascal_case(name)
    return f'''"""{name} ノード"""

from typing import Optional

from railway import node

from contracts.{name}_input import {class_name}Input
from contracts.{name}_output import {class_name}Output


@node
def {name}(input_data: Optional[{class_name}Input] = None) -> {class_name}Output:
    """
    {name} の処理を実行する。

    Args:
        input_data: 入力データ（前段ノードからの出力、最初のノードでは None）

    Returns:
        {class_name}Output: 処理結果
    """
    # TODO: 実装を追加
    # input_data が None の場合は最初のノードとして動作
    return {class_name}Output()
'''


def _get_linear_node_input_template(name: str) -> str:
    """Get Input Contract template for linear node.

    Pure function: name -> template string
    """
    class_name = _to_pascal_case(name)
    return f'''"""{class_name}Input - {name} ノードの入力"""

from railway import Contract


class {class_name}Input(Contract):
    """
    {name} ノードの入力。

    前段のノードから渡されるデータを定義します。
    """
    # TODO: 必要なフィールドを定義してください
    # items: list[dict]
    pass
'''


def _get_linear_node_output_template(name: str) -> str:
    """Get Output Contract template for linear node.

    Pure function: name -> template string
    """
    class_name = _to_pascal_case(name)
    return f'''"""{class_name}Output - {name} ノードの出力"""

from railway import Contract


class {class_name}Output(Contract):
    """
    {name} ノードの出力。

    次段のノードまたは最終結果として使用されます。
    """
    # TODO: 必要なフィールドを定義してください
    # result: str
    # total: int = 0
    pass
'''


def _get_dag_node_test_standalone_template(name: str) -> str:
    """Get test template for dag-style node.

    Pure function: name -> template string
    """
    class_name = _to_pascal_case(name)
    return f'''"""Tests for {name} node."""

import pytest

from nodes.{name} import {name}
from contracts.{name}_context import {class_name}Context


class Test{class_name}:
    """Test suite for {name} node.

    TDD Workflow:
    1. Edit this file to define expected behavior
    2. Run: uv run pytest tests/nodes/test_{name}.py -v
    3. Implement src/nodes/{name}.py
    4. Run tests again
    """

    def test_{name}_returns_tuple(self):
        """Node should return tuple[Context, Outcome]."""
        ctx = {class_name}Context()
        result_ctx, outcome = {name}(ctx)

        assert isinstance(result_ctx, {class_name}Context)
        assert outcome.is_success

    def test_{name}_context_is_immutable(self):
        """Original context should not be modified."""
        original = {class_name}Context()
        result_ctx, _ = {name}(original)

        # Verify original is unchanged (immutability)
        # Add specific field checks here

    def test_{name}_success_case(self):
        """Test successful execution."""
        pytest.skip("TODO: Implement success case test")

    def test_{name}_failure_case(self):
        """Test failure handling."""
        pytest.skip("TODO: Implement failure case test")
'''


def _get_linear_node_test_standalone_template(name: str) -> str:
    """Get test template for linear-style node.

    Pure function: name -> template string
    """
    class_name = _to_pascal_case(name)
    return f'''"""Tests for {name} node."""

import pytest

from nodes.{name} import {name}
from contracts.{name}_input import {class_name}Input
from contracts.{name}_output import {class_name}Output


class Test{class_name}:
    """Test suite for {name} node.

    TDD Workflow:
    1. Edit this file to define expected behavior
    2. Run: uv run pytest tests/nodes/test_{name}.py -v
    3. Implement src/nodes/{name}.py
    4. Run tests again
    """

    def test_{name}_returns_output_without_input(self):
        """Node should return {class_name}Output even without input (first node)."""
        result = {name}()

        assert isinstance(result, {class_name}Output)

    def test_{name}_returns_output_with_input(self):
        """Node should return {class_name}Output when given input."""
        input_data = {class_name}Input()
        result = {name}(input_data)

        assert isinstance(result, {class_name}Output)

    def test_{name}_basic(self):
        """Test basic functionality."""
        pytest.skip("TODO: Implement basic test")
'''


# 3. Contract生成関数を更新

def _create_node_contract(name: str, mode: NodeMode, force: bool = False) -> None:
    """Create Contract(s) for node based on mode.

    Side effects: Creates contract file(s) in src/contracts/
    """
    contracts_dir = Path.cwd() / "src" / "contracts"
    if not contracts_dir.exists():
        contracts_dir.mkdir(parents=True)
        (contracts_dir / "__init__.py").write_text('"""Contract modules."""\n')

    if mode == NodeMode.dag:
        _create_single_contract(
            contracts_dir,
            f"{name}_context",
            _get_dag_node_context_template(name),
            force
        )
    else:
        _create_single_contract(
            contracts_dir,
            f"{name}_input",
            _get_linear_node_input_template(name),
            force
        )
        _create_single_contract(
            contracts_dir,
            f"{name}_output",
            _get_linear_node_output_template(name),
            force
        )


def _create_single_contract(
    contracts_dir: Path,
    file_name: str,
    content: str,
    force: bool
) -> None:
    """Create a single contract file.

    Side effects: Creates or overwrites file
    """
    file_path = contracts_dir / f"{file_name}.py"
    if not file_path.exists() or force:
        _write_file(file_path, content)


# 4. _create_node_test 関数を更新

def _create_node_test(
    name: str,
    output_type: Optional[str] = None,
    inputs: Optional[list[tuple[str, str]]] = None,
    mode: NodeMode = NodeMode.dag,
) -> None:
    """Create test file for node."""
    tests_dir = Path.cwd() / "tests" / "nodes"
    if not tests_dir.exists():
        tests_dir.mkdir(parents=True)

    test_file = tests_dir / f"test_{name}.py"
    if test_file.exists():
        return  # Don't overwrite existing tests

    if output_type:
        content = _get_typed_node_test_template(name, output_type, inputs or [])
    elif mode == NodeMode.dag:
        content = _get_dag_node_test_standalone_template(name)
    else:
        content = _get_linear_node_test_standalone_template(name)

    _write_file(test_file, content)


# 5. _create_node 関数を更新

def _create_node(
    name: str,
    example: bool,
    force: bool,
    output_type: Optional[str] = None,
    input_specs: Optional[list[str]] = None,
    mode: NodeMode = NodeMode.dag,
) -> None:
    """Create a new node with associated contracts and tests."""
    nodes_dir = Path.cwd() / "src" / "nodes"
    if not nodes_dir.exists():
        nodes_dir.mkdir(parents=True)
        (nodes_dir / "__init__.py").write_text('"""Node modules."""\n')

    file_path = nodes_dir / f"{name}.py"

    if file_path.exists() and not force:
        typer.echo(f"Error: {file_path} already exists. Use --force to overwrite.", err=True)
        raise typer.Exit(1)

    # Parse inputs (for --input option)
    inputs: list[tuple[str, str]] = []
    if input_specs:
        inputs = [_parse_input_spec(spec) for spec in input_specs]

    # Generate content based on mode and options
    if output_type:
        # 既存の --output オプション対応（後方互換性）
        content = _get_typed_node_template(name, output_type, inputs)
    elif mode == NodeMode.dag:
        content = _get_dag_node_standalone_template(name)
        _create_node_contract(name, mode, force)
    else:
        content = _get_linear_node_standalone_template(name)
        _create_node_contract(name, mode, force)

    _write_file(file_path, content)

    # Create test file
    _create_node_test(name, output_type, inputs, mode)

    # Output messages
    typer.echo(f"Created src/nodes/{name}.py")
    if not output_type:
        if mode == NodeMode.dag:
            typer.echo(f"Created src/contracts/{name}_context.py")
        else:
            typer.echo(f"Created src/contracts/{name}_input.py")
            typer.echo(f"Created src/contracts/{name}_output.py")
    typer.echo(f"Created tests/nodes/test_{name}.py\n")

    typer.echo("TDD style workflow:")
    typer.echo(f"   1. Define tests in tests/nodes/test_{name}.py")
    typer.echo(f"   2. Run: uv run pytest tests/nodes/test_{name}.py -v")
    typer.echo(f"   3. Implement src/nodes/{name}.py")
    typer.echo("   4. Run tests again")


# 6. new() コマンドを更新（mode パラメータを追加）

def new(
    component_type: ComponentType = typer.Argument(..., help="Type: entry, node, or contract"),
    name: str = typer.Argument(..., help="Name of the component"),
    example: bool = typer.Option(False, "--example", help="Generate with example code"),
    force: bool = typer.Option(False, "--force", help="Overwrite if exists"),
    entity: bool = typer.Option(False, "--entity", help="Create entity Contract (with id field)"),
    params: bool = typer.Option(False, "--params", help="Create Params Contract"),
    output: Optional[str] = typer.Option(None, "--output", help="Output Contract type for node"),
    input_specs: Optional[list[str]] = typer.Option(
        None, "--input", help="Input spec 'param_name:TypeName' (repeatable)"
    ),
    mode: str = typer.Option(
        "dag",
        "--mode",
        "-m",
        help="Mode: dag (default, 条件分岐) or linear (線形パイプライン)",
    ),
) -> None:
    """
    Create a new entry point, node, or contract.

    Examples:
        railway new entry my_workflow              # dag_runner 型（デフォルト）
        railway new entry my_workflow --mode linear  # typed_pipeline 型
        railway new node fetch_data                # dag 形式（デフォルト）
        railway new node transform --mode linear   # linear 形式
        railway new contract UsersFetchResult
    """
    # Validate we're in a project
    if not _is_railway_project():
        typer.echo("Error: Not in a Railway project (src/ directory not found)", err=True)
        raise typer.Exit(1)

    # Validate mutually exclusive options
    if entity and params:
        typer.echo("Error: --entity and --params are mutually exclusive.", err=True)
        raise typer.Exit(1)

    # Validate --input requires --output
    if input_specs and not output:
        typer.echo("Error: --input requires --output to be specified.", err=True)
        raise typer.Exit(1)

    if component_type == ComponentType.contract:
        _create_contract(name, entity, params, force)
    elif component_type == ComponentType.entry:
        entry_mode = EntryMode.dag if mode == "dag" else EntryMode.linear
        _create_entry(name, example, force, entry_mode)
    else:  # node
        node_mode = NodeMode.dag if mode == "dag" else NodeMode.linear
        _create_node(name, example, force, output, input_specs, node_mode)
```

### Step 3: Refactor

1. **純粋関数の維持**: 全テンプレート生成関数は純粋関数（引数 → 文字列）
2. **副作用の局所化**: ファイル書き込みは `_write_file`, `_create_single_contract` に集約
3. **イミュータブルパターンの促進**: テンプレートに `model_copy()` の例を含む
4. **既存コードとの整合性**: `EntryMode` と `NodeMode` で一貫したインターフェース

---

## 完了条件

- [ ] `railway new node <name>` がデフォルトで dag 形式（Contract + Outcome）を生成
- [ ] `railway new node <name> --mode linear` が linear 形式（Input/Output Contract）を生成
- [ ] ノード生成時に対応する Contract が自動生成される
- [ ] 生成されるテンプレートに `model_copy()` のイミュータブル更新例が含まれる
- [ ] テストテンプレートがイミュータビリティのテストを含む
- [ ] `--output` / `--input` オプションの後方互換性を維持
- [ ] `--force` オプションが Contract も含めて上書きできる
- [ ] 既存 Contract がある場合は上書きしない（`--force` なしの場合）
- [ ] 全テストが通過

---

## 関連ファイル

- `railway/cli/new.py` - new コマンド実装
- `tests/unit/cli/test_new.py` - 既存テスト
- `tests/unit/cli/test_new_node_template.py` - 新規テスト

---

## 備考

- `railway new entry` と `railway new node` で `--mode` オプションのインターフェースを統一
- ノード単独作成時は `nodes/` ディレクトリ直下に配置
- Contract は `contracts/` ディレクトリに自動生成
- dag モードは Context Contract を1つ生成、linear モードは Input/Output の2つを生成
- イミュータビリティは Railway Framework の重要な原則であり、テンプレートで明示する
- テストの import パス（`from nodes.{name} import {name}`）は Issue #20 で `src/` が `sys.path` に追加されるため動作する
- linear モードの入力は `Optional` にすることで、パイプラインの最初のノードとしても使用可能
