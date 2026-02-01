"""railway new command implementation."""

import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import typer

if TYPE_CHECKING:
    from railway.cli.sync import SyncResult


class ComponentType(str, Enum):
    """Type of component to create."""

    entry = "entry"
    node = "node"
    contract = "contract"


class EntryMode(str, Enum):
    """Entry point execution mode."""

    dag = "dag"
    linear = "linear"


class NodeMode(str, Enum):
    """Node template mode."""

    dag = "dag"
    linear = "linear"


def _is_railway_project() -> bool:
    """Check if current directory is a Railway project."""
    return (Path.cwd() / "src").exists()


def _write_file(path: Path, content: str) -> None:
    """Write content to a file."""
    path.write_text(content)


def _camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case."""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


# =============================================================================
# Contract Templates
# =============================================================================


def _get_contract_template(name: str) -> str:
    """Get basic Contract template."""
    return f'''"""{name} contract."""

from railway import Contract


class {name}(Contract):
    """
    Output contract for a node.

    TODO: Define the fields for this contract.
    """
    # Example fields (modify as needed):
    # items: list[dict]
    # total: int
    # fetched_at: datetime
    pass
'''


def _get_entity_contract_template(name: str) -> str:
    """Get entity Contract template."""
    return f'''"""{name} entity contract."""

from railway import Contract


class {name}(Contract):
    """
    Entity contract representing a {name.lower()}.

    TODO: Define the fields for this entity.
    """
    id: int
    # name: str
    # email: str
'''


def _get_params_contract_template(name: str) -> str:
    """Get Params contract template."""
    return f'''"""{name} parameters."""

from railway import Params


class {name}(Params):
    """
    Parameters for an entry point.

    TODO: Define the parameters.
    """
    # user_id: int
    # include_details: bool = False
    pass
'''


# =============================================================================
# Typed Node Templates
# =============================================================================


def _get_typed_node_template(
    name: str,
    output_type: str,
    inputs: list[tuple[str, str]],
) -> str:
    """Get typed node template with input/output contracts."""
    # Build imports
    import_lines = ["from railway import node"]
    output_snake = _camel_to_snake(output_type)
    import_lines.append(f"from contracts.{output_snake} import {output_type}")

    for param_name, type_name in inputs:
        type_snake = _camel_to_snake(type_name)
        import_line = f"from contracts.{type_snake} import {type_name}"
        if import_line not in import_lines:
            import_lines.append(import_line)

    imports = "\n".join(import_lines)

    # Build decorator
    if inputs:
        inputs_dict = ", ".join(f'"{pn}": {tn}' for pn, tn in inputs)
        decorator = f'@node(\n    inputs={{{inputs_dict}}},\n    output={output_type},\n)'
    else:
        decorator = f"@node(output={output_type})"

    # Build function signature
    if inputs:
        params = ", ".join(f"{pn}: {tn}" for pn, tn in inputs)
        signature = f"def {name}({params}) -> {output_type}:"
    else:
        signature = f"def {name}() -> {output_type}:"

    # Build docstring
    if inputs:
        args_doc = "\n".join(f"        {pn}: Input from a node that outputs {tn}." for pn, tn in inputs)
        docstring = f'''"""
    Process data.

    Args:
{args_doc}

    Returns:
        {output_type}: The result of this node.
    """'''
    else:
        docstring = f'''"""
    TODO: Implement this node.

    Returns:
        {output_type}: The result of this node.
    """'''

    return f'''"""{name} node."""

{imports}


{decorator}
{signature}
    {docstring}
    # TODO: Implement the logic
    return {output_type}(
        # Fill in the required fields
    )
'''


def _get_typed_node_test_template(
    name: str,
    output_type: str,
    inputs: list[tuple[str, str]],
) -> str:
    """Get typed node test template.

    Generates tests that use pytest.skip() by default to follow TDD workflow:
    1. Run tests (skip)
    2. Implement the test data
    3. Run tests (pass)
    """
    class_name = "".join(word.title() for word in name.split("_"))

    # Build imports
    import_lines = []
    output_snake = _camel_to_snake(output_type)
    import_lines.append(f"from contracts.{output_snake} import {output_type}")

    for param_name, type_name in inputs:
        type_snake = _camel_to_snake(type_name)
        import_line = f"from contracts.{type_snake} import {type_name}"
        if import_line not in import_lines:
            import_lines.append(import_line)

    import_lines.append(f"from nodes.{name} import {name}")
    imports = "\n".join(import_lines)

    # Build input hints for documentation
    if inputs:
        input_hints = "\n".join(
            f"    #     {pn} = {tn}(...)"
            for pn, tn in inputs
        )
        call_hint = ", ".join(pn for pn, _ in inputs)
        call_example = f"    #     result = {name}({call_hint})"
    else:
        input_hints = ""
        call_example = f"    #     result = {name}()"

    return f'''"""Tests for {name} node."""

import pytest

{imports}


class Test{class_name}:
    """Test suite for {name} node.

    TDD Workflow:
    1. Run tests (expect skip)
    2. Fill in test data and assertions
    3. Run tests (expect pass)
    """

    def test_{name}_returns_correct_type(self):
        """Node should return {output_type}.

        Example:
{input_hints}
{call_example}
            assert isinstance(result, {output_type})
        """
        pytest.skip("TODO: Fill in test data for {name}")

    def test_{name}_basic(self):
        """Basic functionality test."""
        pytest.skip("TODO: Implement this test")
'''


# =============================================================================
# Entry Templates
# =============================================================================


def _get_entry_template(name: str) -> str:
    """Get basic entry point template (legacy - pipeline style)."""
    return f'''"""{name} entry point."""

from railway import entry_point, node, pipeline
from loguru import logger


@node
def process(data: str) -> str:
    """
    Process data (pure function).

    Args:
        data: Input data

    Returns:
        Processed data
    """
    logger.info(f"Processing: {{data}}")
    # TODO: Add implementation
    return data


@entry_point
def main(input_data: str = "default"):
    """
    {name} entry point.

    Args:
        input_data: Input data to process
    """
    result = pipeline(
        input_data,
        process,
    )
    logger.info(f"Result: {{result}}")
    return result


# Export Typer app for testing with CliRunner
app = main._typer_app


if __name__ == "__main__":
    main()
'''


def _get_dag_entry_template(name: str) -> str:
    """Get dag_runner style entry point template (sync 後用).

    純粋関数: name -> Python コード文字列

    Args:
        name: エントリーポイント名

    Returns:
        Python コード文字列（run() を使用）
    """
    class_name = _to_pascal_case(name)
    return f'''"""
{name} エントリーポイント

Usage:
    railway run {name}
    # または
    python -m src.{name}
"""
from _railway.generated.{name}_transitions import run


def main() -> None:
    """ワークフローを実行する。"""
    # TODO: 初期コンテキストを設定してください
    # from contracts.{name}_context import {class_name}Context
    # initial_context = {class_name}Context(...)

    result = run({{}})

    if result.is_success:
        print(f"完了: {{result.exit_state}}")
    else:
        print(f"失敗: {{result.exit_state}}")
        raise SystemExit(result.exit_code)


if __name__ == "__main__":
    main()
'''


def _get_dag_entry_template_pending_sync(name: str) -> str:
    """Get dag_runner style entry point template (sync 前用).

    純粋関数: name -> Python コード文字列

    Args:
        name: エントリーポイント名

    Returns:
        Python コード文字列（次のステップを案内）
    """
    return f'''"""
{name} エントリーポイント

このファイルは `railway new entry {name}` で --no-sync オプションを
使用したため、まだ実行できません。

次のステップ:
    railway sync transition --entry {name}
    railway run {name}
"""

# TODO: sync 実行後、以下のコメントを解除してください
# from _railway.generated.{name}_transitions import run
#
# def main() -> None:
#     result = run({{}})
#     if result.is_success:
#         print(f"完了: {{result.exit_state}}")
#     else:
#         raise SystemExit(result.exit_code)
#
# if __name__ == "__main__":
#     main()

raise NotImplementedError(
    "先に `railway sync transition --entry {name}` を実行してください。"
)
'''


def _get_dag_node_template(name: str) -> str:
    """Get dag_runner style node template (returns Outcome)."""
    class_name = _to_pascal_case(name)
    return f'''"""
{name} 開始ノード
"""
from railway import Contract, node
from railway.core.dag.outcome import Outcome


class {class_name}Context(Contract):
    """ワークフローコンテキスト"""
    initialized: bool = False


@node
def start() -> tuple[{class_name}Context, Outcome]:
    """
    ワークフロー開始ノード。

    Returns:
        (context, outcome): コンテキストと状態
    """
    ctx = {class_name}Context(initialized=True)
    return ctx, Outcome.success("done")
'''


def _get_dag_yaml_template(name: str) -> str:
    """Get transition graph YAML template (v0.13.0+ 新形式).

    純粋関数: name -> YAML テンプレート文字列

    Args:
        name: エントリーポイント名

    Returns:
        YAML テンプレート文字列
    """
    return f'''version: "1.0"
entrypoint: {name}
description: "{name} ワークフロー"

nodes:
  start:
    module: nodes.{name}.start
    function: start
    description: "開始ノード"

  exit:
    success:
      done:
        description: "正常終了"
    failure:
      error:
        description: "エラー終了"

start: start

transitions:
  start:
    success::done: exit.success.done
    failure::error: exit.failure.error

options:
  max_iterations: 100
'''


def _get_linear_entry_template(name: str) -> str:
    """Get typed_pipeline style entry point template."""
    return f'''"""
{name} エントリーポイント

実行モード: typed_pipeline（線形パイプライン）
"""
from railway import entry_point, typed_pipeline

from nodes.{name}.step1 import step1
from nodes.{name}.step2 import step2


@entry_point
def main():
    """
    {name} パイプラインを実行する。

    処理順序: step1 → step2
    """
    result = typed_pipeline(
        step1,
        step2,
    )

    print(f"完了: {{result}}")
    return result


if __name__ == "__main__":
    main()
'''


def _get_linear_node_template(name: str, step_num: int) -> str:
    """Get typed_pipeline style node template (returns Contract)."""
    return f'''"""
{name} ステップ{step_num}
"""
from railway import Contract, node


class Step{step_num}Output(Contract):
    """ステップ{step_num}の出力"""
    value: str


@node
def step{step_num}() -> Step{step_num}Output:
    """
    ステップ{step_num}の処理。

    Returns:
        Step{step_num}Output: 処理結果
    """
    return Step{step_num}Output(value="processed")
'''


def _to_pascal_case(name: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in name.split("_"))


def _generate_exit_nodes_from_yaml(
    yaml_content: str,
    project_root: Path,
) -> "SyncResult":
    """YAML コンテンツから終端ノードを生成する。

    Args:
        yaml_content: YAML テンプレート文字列
        project_root: プロジェクトルート

    Returns:
        SyncResult: 生成結果

    Note:
        この関数は副作用を持つ（ファイル書き込み）。
        内部で純粋関数（parse_transition_graph）と
        副作用関数（sync_exit_nodes）を組み合わせる。
    """
    from railway.cli.sync import sync_exit_nodes
    from railway.core.dag.parser import parse_transition_graph

    graph = parse_transition_graph(yaml_content)
    return sync_exit_nodes(graph, project_root)


def _get_entry_example_template(name: str) -> str:
    """Get example entry point template."""
    return f'''"""{name} entry point with example implementation."""

from datetime import datetime

from railway import entry_point, node, pipeline
from loguru import logger


@node
def fetch_data(date: str) -> dict:
    """Fetch data for the specified date (pure function)."""
    logger.info(f"Fetching data for {{date}}")
    # TODO: Replace with actual API call
    return {{"date": date, "records": [1, 2, 3]}}


@node
def process_data(data: dict) -> dict:
    """Process fetched data (pure function)."""
    logger.info(f"Processing {{len(data['records'])}} records")
    return {{
        "date": data["date"],
        "summary": {{
            "total": len(data["records"]),
            "sum": sum(data["records"]),
        }}
    }}


@entry_point
def main(date: str | None = None):
    """
    {name} entry point.

    Args:
        date: Target date (YYYY-MM-DD), defaults to today
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    result = pipeline(
        fetch_data(date),
        process_data,
    )

    logger.info(f"Result: {{result}}")
    return result


# Export Typer app for testing with CliRunner
app = main._typer_app


if __name__ == "__main__":
    main()
'''


# =============================================================================
# Node Templates (dag mode - standalone)
# =============================================================================


def _get_dag_node_standalone_template(name: str) -> str:
    """Get dag-style node template that returns tuple[Contract, Outcome].

    純粋関数: name -> template string
    副作用なし、テスト容易
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


# =============================================================================
# Node Templates (linear mode - standalone)
# =============================================================================


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


# =============================================================================
# Node Test Templates (dag/linear mode)
# =============================================================================


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


# =============================================================================
# Node Templates (basic - legacy)
# =============================================================================


def _get_node_template(name: str) -> str:
    """Get basic node template."""
    return f'''"""{name} node."""

from railway import node
from loguru import logger


@node
def {name}(data: dict) -> dict:
    """
    {name} node (pure function).

    Args:
        data: Input data

    Returns:
        Processed data
    """
    logger.info(f"Processing in {name}")
    # TODO: Add implementation
    return data
'''


def _get_node_example_template(name: str) -> str:
    """Get example node template."""
    return f'''"""{name} node with example implementation."""

from railway import node
from loguru import logger


@node
def {name}(data: dict) -> dict:
    """
    {name} node (pure function).

    Features:
    - Type annotations
    - Logging
    - Error handling (via @node decorator)
    - Immutable transformation

    Args:
        data: Input data dictionary

    Returns:
        Processed data dictionary
    """
    logger.info(f"Starting {name} with {{len(data)}} fields")

    # Immutable transformation (original data unchanged)
    result = {{
        **data,
        "processed_by": "{name}",
        "status": "completed",
    }}

    logger.debug(f"Processed result: {{result}}")
    return result
'''


# =============================================================================
# Test Templates
# =============================================================================


def _get_entry_test_template(name: str) -> str:
    """Get test template for an entry point.

    Uses CliRunner with main._typer_app to avoid sys.argv pollution
    and ensure tests work even after user rewrites the entry point.
    """
    class_name = "".join(word.title() for word in name.split("_"))
    return f'''"""Tests for {name} entry point."""

import pytest
from typer.testing import CliRunner

from {name} import main

runner = CliRunner()


class Test{class_name}:
    """Test suite for {name} entry point.

    Uses CliRunner with main._typer_app to isolate from pytest's sys.argv.
    This pattern works regardless of whether 'app' is exported.
    """

    def test_{name}_runs_successfully(self):
        """Entry point should complete without error."""
        result = runner.invoke(main._typer_app, [])
        assert result.exit_code == 0, f"Failed with: {{result.stdout}}"

    def test_{name}_with_help(self):
        """Entry point should show help."""
        result = runner.invoke(main._typer_app, ["--help"])
        assert result.exit_code == 0
'''


def _get_node_test_template(name: str) -> str:
    """Get test template for a node (TDD-style skeleton)."""
    class_name = "".join(word.title() for word in name.split("_"))
    return f'''"""Tests for {name} node."""

import pytest

from nodes.{name} import {name}


class Test{class_name}:
    """Test suite for {name} node.

    TDD Workflow:
    1. Edit this file to define expected behavior
    2. Run: uv run pytest tests/nodes/test_{name}.py -v (expect failure)
    3. Implement src/nodes/{name}.py
    4. Run tests again (expect success)
    """

    def test_{name}_basic(self):
        """TODO: Define expected behavior and implement test.

        Example:
            # Arrange
            input_data = your_input_here

            # Act
            result = {name}(input_data)

            # Assert
            assert result == expected_output
        """
        pytest.skip("Implement this test based on your node's specification")

    def test_{name}_edge_case(self):
        """TODO: Test edge cases and error handling."""
        pytest.skip("Implement edge case tests")
'''


# =============================================================================
# Create Functions
# =============================================================================


def _create_contract(
    name: str,
    entity: bool,
    params: bool,
    force: bool,
) -> None:
    """Create a new Contract."""
    contracts_dir = Path.cwd() / "src" / "contracts"
    if not contracts_dir.exists():
        contracts_dir.mkdir(parents=True)
        (contracts_dir / "__init__.py").write_text('"""Contract modules."""\n')

    file_name = _camel_to_snake(name)
    file_path = contracts_dir / f"{file_name}.py"

    if file_path.exists() and not force:
        typer.echo(f"Error: {file_path} already exists. Use --force to overwrite.", err=True)
        raise typer.Exit(1)

    if params:
        content = _get_params_contract_template(name)
    elif entity:
        content = _get_entity_contract_template(name)
    else:
        content = _get_contract_template(name)

    _write_file(file_path, content)

    typer.echo(f"Created contract: src/contracts/{file_name}.py")
    typer.echo(f"\nTo use in a node:")
    typer.echo(f"  from contracts.{file_name} import {name}")


def _create_entry_test(name: str) -> None:
    """Create test file for entry point."""
    tests_dir = Path.cwd() / "tests"
    if not tests_dir.exists():
        tests_dir.mkdir(parents=True)

    test_file = tests_dir / f"test_{name}.py"
    if test_file.exists():
        return  # Don't overwrite existing tests

    content = _get_entry_test_template(name)
    _write_file(test_file, content)


def _create_entry(
    name: str,
    example: bool,
    force: bool,
    mode: EntryMode = EntryMode.dag,
    sync: bool = True,
) -> None:
    """Create a new entry point.

    Args:
        name: エントリポイント名
        example: サンプルコードを含めるか
        force: 既存ファイルを上書きするか
        mode: 実行モード（dag or linear）
        sync: sync を実行するか（dag モードのみ）
    """
    file_path = Path.cwd() / "src" / f"{name}.py"

    if file_path.exists() and not force:
        typer.echo(
            f"Error: {file_path} already exists. Use --force to overwrite.", err=True
        )
        raise typer.Exit(1)

    if mode == EntryMode.dag:
        _create_dag_entry(name, sync=sync)
    else:
        _create_linear_entry(name)

    # Create test file
    _create_entry_test(name)


def _create_dag_entry(name: str, sync: bool = True) -> None:
    """Create dag_runner style entry point with nodes and YAML.

    Args:
        name: エントリポイント名
        sync: sync を実行するか（デフォルト True）

    Issue #64: デフォルトで sync を実行し、1コマンドで動作するプロジェクトを生成
    """
    cwd = Path.cwd()
    src_dir = cwd / "src"
    nodes_dir = src_dir / "nodes" / name
    graphs_dir = cwd / "transition_graphs"
    output_dir = cwd / "_railway" / "generated"

    # Create directories
    nodes_dir.mkdir(parents=True, exist_ok=True)

    # 1. Create YAML (pure function → side effect)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    yaml_content = _get_dag_yaml_template(name)
    _write_file(graphs_dir / f"{name}_{timestamp}.yml", yaml_content)

    # 2. Create start node
    node_content = _get_dag_node_template(name)
    (nodes_dir / "__init__.py").touch()
    _write_file(nodes_dir / "start.py", node_content)

    # 3. Generate exit nodes from YAML (side effect)
    exit_result = _generate_exit_nodes_from_yaml(yaml_content, cwd)

    # 4. Sync transition (if enabled)
    if sync:
        output_dir.mkdir(parents=True, exist_ok=True)
        _run_sync_for_entry(name, graphs_dir, output_dir)

    # 5. Create entrypoint (depends on sync state)
    if sync:
        entry_content = _get_dag_entry_template(name)
    else:
        entry_content = _get_dag_entry_template_pending_sync(name)

    _write_file(src_dir / f"{name}.py", entry_content)

    # Output messages
    _print_dag_entry_created(name, timestamp, exit_result, sync)


def _run_sync_for_entry(
    name: str,
    graphs_dir: Path,
    output_dir: Path,
) -> None:
    """sync transition を実行する（副作用あり）。

    Note:
        subprocess ではなく、直接 Python 関数を呼び出す。
    """
    from railway.cli.sync import find_latest_yaml, _sync_entry, SyncError

    yaml_path = find_latest_yaml(graphs_dir, name)
    if yaml_path is None:
        return

    try:
        _sync_entry(
            entry_name=name,
            graphs_dir=graphs_dir,
            output_dir=output_dir,
            dry_run=False,
            validate_only=False,
            force=True,
        )
    except SyncError as e:
        typer.echo(f"警告: sync 中にエラーが発生しました: {e}", err=True)


def _print_dag_entry_created(
    name: str,
    timestamp: str,
    exit_result: "SyncResult",
    sync: bool,
) -> None:
    """生成結果を表示する（副作用あり: 標準出力）。"""
    typer.echo(f"✓ エントリーポイント '{name}' を作成しました（モード: dag）\n")
    typer.echo(f"  作成: src/{name}.py")
    typer.echo(f"  作成: src/nodes/{name}/start.py")
    typer.echo(f"  作成: transition_graphs/{name}_{timestamp}.yml")

    cwd = Path.cwd()
    for path in exit_result.generated:
        relative = path.relative_to(cwd)
        typer.echo(f"  作成: {relative}")

    if sync:
        typer.echo(f"  作成: _railway/generated/{name}_transitions.py")

    typer.echo("")
    if sync:
        typer.echo("次のステップ:")
        typer.echo(f"  railway run {name}")
    else:
        typer.echo("次のステップ:")
        typer.echo(f"  1. transition_graphs/{name}_*.yml を編集（オプション）")
        typer.echo(f"  2. railway sync transition --entry {name}")
        typer.echo(f"  3. railway run {name}")


def _create_linear_entry(name: str) -> None:
    """Create typed_pipeline style entry point with nodes."""
    cwd = Path.cwd()
    src_dir = cwd / "src"
    nodes_dir = src_dir / "nodes" / name

    # Create directories
    nodes_dir.mkdir(parents=True, exist_ok=True)

    # Create entry point file
    entry_content = _get_linear_entry_template(name)
    _write_file(src_dir / f"{name}.py", entry_content)

    # Create step nodes
    (nodes_dir / "__init__.py").touch()
    for i in [1, 2]:
        node_content = _get_linear_node_template(name, i)
        _write_file(nodes_dir / f"step{i}.py", node_content)

    typer.echo(f"✓ エントリーポイント '{name}' を作成しました（モード: linear）\n")
    typer.echo(f"  作成: src/{name}.py")
    typer.echo(f"  作成: src/nodes/{name}/step1.py")
    typer.echo(f"  作成: src/nodes/{name}/step2.py")
    typer.echo("")
    typer.echo("次のステップ:")
    typer.echo(f"  1. src/nodes/{name}/ のノードを実装")
    typer.echo(f"  2. railway run {name}")


def _create_node_contract(name: str, mode: NodeMode, force: bool = False) -> None:
    """Create Contract(s) for node based on mode.

    副作用あり: src/contracts/ にファイルを作成
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
            force,
        )
    else:
        _create_single_contract(
            contracts_dir,
            f"{name}_input",
            _get_linear_node_input_template(name),
            force,
        )
        _create_single_contract(
            contracts_dir,
            f"{name}_output",
            _get_linear_node_output_template(name),
            force,
        )


def _create_single_contract(
    contracts_dir: Path,
    file_name: str,
    content: str,
    force: bool,
) -> None:
    """Create a single contract file.

    Side effects: Creates or overwrites file
    """
    file_path = contracts_dir / f"{file_name}.py"
    if not file_path.exists() or force:
        _write_file(file_path, content)


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


def _parse_input_spec(input_spec: str) -> tuple[str, str]:
    """Parse input specification 'param_name:TypeName'.

    Args:
        input_spec: Input in format 'param_name:TypeName'

    Returns:
        Tuple of (param_name, type_name)

    Raises:
        typer.Exit: If format is invalid
    """
    if ":" not in input_spec:
        typer.echo(
            f"Error: Invalid input format '{input_spec}'. "
            "Expected 'param_name:TypeName'.",
            err=True,
        )
        raise typer.Exit(1)

    parts = input_spec.split(":", 1)
    return (parts[0].strip(), parts[1].strip())


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

    if output_type:
        typer.echo("To use in a typed pipeline:")
        typer.echo(f"  from nodes.{name} import {name}")
        typer.echo(f"  result = typed_pipeline({name})")
    else:
        typer.echo("TDD style workflow:")
        typer.echo(f"   1. Define tests in tests/nodes/test_{name}.py")
        typer.echo(f"   2. Run: uv run pytest tests/nodes/test_{name}.py -v")
        typer.echo(f"   3. Implement src/nodes/{name}.py")
        typer.echo("   4. Run tests again\n")
        typer.echo("To use in an entry point:")
        typer.echo(f"  from nodes.{name} import {name}")


# =============================================================================
# Main Command
# =============================================================================


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
    no_sync: bool = typer.Option(
        False,
        "--no-sync",
        help="sync を実行しない（上級者向け）。デフォルトでは sync を実行し、すぐに run 可能にする",
    ),
) -> None:
    """
    Create a new entry point, node, or contract.

    Entry points are CLI-accessible functions decorated with @entry_point.
    Nodes are pure functions decorated with @node for use in pipelines.
    Contracts are type-safe data structures for node inputs/outputs.

    Examples:
        railway new entry my_workflow              # dag_runner 型、sync 実行（デフォルト）
        railway new entry my_workflow --no-sync    # sync をスキップ
        railway new entry my_workflow --mode linear  # typed_pipeline 型
        railway new node fetch_data                # dag 形式（デフォルト）
        railway new node transform --mode linear   # linear 形式
        railway new contract UsersFetchResult
        railway new contract User --entity
        railway new contract ReportParams --params
        railway new node fetch_users --output UsersFetchResult
        railway new node process --input users:UsersFetchResult --output Result

    Documentation: https://pypi.org/project/railway-framework/
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

    # Validate mode
    if mode not in ("dag", "linear"):
        typer.echo(f"Error: Invalid mode '{mode}'. Must be 'dag' or 'linear'.", err=True)
        raise typer.Exit(1)

    if component_type == ComponentType.contract:
        _create_contract(name, entity, params, force)
    elif component_type == ComponentType.entry:
        entry_mode = EntryMode.dag if mode == "dag" else EntryMode.linear
        _create_entry(name, example, force, entry_mode, sync=not no_sync)
    else:  # node
        node_mode = NodeMode.dag if mode == "dag" else NodeMode.linear
        _create_node(name, example, force, output, input_specs, node_mode)
