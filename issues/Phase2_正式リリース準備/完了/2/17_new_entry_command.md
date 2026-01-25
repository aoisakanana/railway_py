# Issue #17: `railway new entry` コマンド変更

**Phase:** 2d
**優先度:** 高
**依存関係:** #09, #12, #15
**見積もり:** 0.5日

---

## 概要

`railway new entry` コマンドのデフォルト挙動を `dag_runner()` 型に変更する。
旧来の `typed_pipeline()` 型は `--mode linear` オプションで生成可能とする。

---

## コマンド仕様

### 変更後

```bash
# デフォルト: dag_runner 型（推奨）
railway new entry my_workflow

# オプション: typed_pipeline 型（線形パイプライン）
railway new entry my_workflow --mode linear
```

### 生成されるファイル

#### dag_runner 型（デフォルト）

```
src/
├── my_workflow.py              # @entry_point + dag_runner()
└── nodes/
    └── my_workflow/
        └── start.py            # @node + Outcome 返却

transition_graphs/
└── my_workflow_{timestamp}.yml # 遷移グラフ定義
```

#### typed_pipeline 型（--mode linear）

```
src/
├── my_workflow.py              # @entry_point + typed_pipeline()
└── nodes/
    └── my_workflow/
        ├── step1.py            # @node（Contract返却）
        └── step2.py
```

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/cli/test_new_entry.py
"""Tests for railway new entry command."""
import pytest
from pathlib import Path
from typer.testing import CliRunner


runner = CliRunner()


class TestNewEntryDefault:
    """Test default (dag_runner) mode."""

    def test_creates_dag_entry_by_default(self, tmp_path, monkeypatch):
        """Should create dag_runner style entry by default."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(app, ["new", "entry", "my_workflow"])

        assert result.exit_code == 0

        # Check entry file contains dag_runner
        entry_file = tmp_path / "src" / "my_workflow.py"
        assert entry_file.exists()
        content = entry_file.read_text()
        assert "dag_runner" in content
        assert "TRANSITION_TABLE" in content
        assert "typed_pipeline" not in content

    def test_creates_transition_yaml(self, tmp_path, monkeypatch):
        """Should create transition graph YAML."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(app, ["new", "entry", "my_workflow"])

        assert result.exit_code == 0

        # Check YAML exists
        yamls = list((tmp_path / "transition_graphs").glob("my_workflow_*.yml"))
        assert len(yamls) == 1

    def test_creates_node_with_outcome(self, tmp_path, monkeypatch):
        """Should create node returning Outcome."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(app, ["new", "entry", "my_workflow"])

        assert result.exit_code == 0

        # Check node file
        node_file = tmp_path / "src" / "nodes" / "my_workflow" / "start.py"
        assert node_file.exists()
        content = node_file.read_text()
        assert "Outcome" in content
        assert "tuple[" in content


class TestNewEntryLinearMode:
    """Test linear (typed_pipeline) mode."""

    def test_creates_pipeline_entry_with_linear_flag(self, tmp_path, monkeypatch):
        """Should create typed_pipeline style entry with --mode linear."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(app, ["new", "entry", "my_workflow", "--mode", "linear"])

        assert result.exit_code == 0

        # Check entry file contains typed_pipeline
        entry_file = tmp_path / "src" / "my_workflow.py"
        content = entry_file.read_text()
        assert "typed_pipeline" in content
        assert "dag_runner" not in content

    def test_no_transition_yaml_in_linear_mode(self, tmp_path, monkeypatch):
        """Should NOT create transition YAML in linear mode."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(app, ["new", "entry", "my_workflow", "--mode", "linear"])

        assert result.exit_code == 0

        # No YAML should be created
        yamls = list((tmp_path / "transition_graphs").glob("my_workflow_*.yml"))
        assert len(yamls) == 0

    def test_creates_node_returning_contract(self, tmp_path, monkeypatch):
        """Should create node returning Contract only."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(app, ["new", "entry", "my_workflow", "--mode", "linear"])

        assert result.exit_code == 0

        # Check node file
        node_files = list((tmp_path / "src" / "nodes" / "my_workflow").glob("*.py"))
        assert len(node_files) >= 1

        content = node_files[0].read_text()
        assert "Contract" in content
        assert "Outcome" not in content


class TestNewEntryValidation:
    """Test command validation."""

    def test_invalid_mode_error(self, tmp_path, monkeypatch):
        """Should error on invalid mode."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(app, ["new", "entry", "my_workflow", "--mode", "invalid"])

        assert result.exit_code != 0
        assert "invalid" in result.stdout.lower() or "error" in result.stdout.lower()


def _init_project(path: Path):
    """Initialize a minimal project structure."""
    (path / "src").mkdir()
    (path / "src" / "nodes").mkdir()
    (path / "transition_graphs").mkdir()
    (path / "_railway" / "generated").mkdir(parents=True)
    (path / "pyproject.toml").write_text('[project]\nname = "test"')
```

### Step 2: Green（最小限の実装）

```python
# railway/cli/new.py
"""New command for creating project components."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(help="新規コンポーネント作成")


class EntryMode(str, Enum):
    """Entry point execution mode."""
    DAG = "dag"
    LINEAR = "linear"


@app.command("entry")
def new_entry(
    name: str = typer.Argument(..., help="エントリーポイント名"),
    mode: EntryMode = typer.Option(
        EntryMode.DAG,
        "--mode", "-m",
        help="実行モード: dag (デフォルト) または linear",
    ),
) -> None:
    """
    新しいエントリーポイントを作成する。

    デフォルトでは dag_runner 型（条件分岐対応）を生成。
    --mode linear で typed_pipeline 型（線形パイプライン）を生成。

    Examples:
        railway new entry my_workflow           # dag_runner 型
        railway new entry my_workflow --mode linear  # typed_pipeline 型
    """
    cwd = Path.cwd()

    if mode == EntryMode.DAG:
        _create_dag_entry(cwd, name)
    else:
        _create_linear_entry(cwd, name)

    typer.echo(f"✓ エントリーポイント '{name}' を作成しました（モード: {mode.value}）")


def _create_dag_entry(project_dir: Path, name: str) -> None:
    """Create dag_runner style entry point."""
    src_dir = project_dir / "src"
    nodes_dir = src_dir / "nodes" / name
    graphs_dir = project_dir / "transition_graphs"

    nodes_dir.mkdir(parents=True, exist_ok=True)

    # Create entry point file
    entry_content = f'''"""
{name} エントリーポイント

実行モード: dag_runner（条件分岐対応）
"""
from railway import entry_point
from railway.core.dag.runner import dag_runner
from railway.core.dag.callbacks import StepRecorder

from _railway.generated.{name}_transitions import (
    TRANSITION_TABLE,
    GRAPH_METADATA,
)
from nodes.{name}.start import start


@entry_point
def main():
    """
    {name} ワークフローを実行する。

    遷移ロジックは transition_graphs/{name}_*.yml で定義。
    コード生成: railway sync transition --entry {name}
    """
    recorder = StepRecorder()

    result = dag_runner(
        start=start,
        transitions=TRANSITION_TABLE,
        max_iterations=GRAPH_METADATA["max_iterations"],
        on_step=recorder,
    )

    if result.is_success:
        print(f"✓ 完了: {{result.exit_code}}")
    else:
        print(f"✗ 失敗: {{result.exit_code}}")

    return result
'''
    (src_dir / f"{name}.py").write_text(entry_content)

    # Create start node
    node_content = f'''"""
{name} 開始ノード
"""
from railway import Contract, node
from railway.core.dag.outcome import Outcome


class {_to_class_name(name)}Context(Contract):
    """ワークフローコンテキスト"""
    initialized: bool = False


@node
def start() -> tuple[{_to_class_name(name)}Context, Outcome]:
    """
    ワークフロー開始ノード。

    Returns:
        (context, outcome): コンテキストと状態
    """
    ctx = {_to_class_name(name)}Context(initialized=True)
    return ctx, Outcome.success("done")
'''
    (nodes_dir / "__init__.py").touch()
    (nodes_dir / "start.py").write_text(node_content)

    # Create transition YAML
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    yaml_content = f'''version: "1.0"
entrypoint: {name}
description: "{name} ワークフロー"

nodes:
  start:
    module: nodes.{name}.start
    function: start
    description: "開始ノード"

exits:
  success:
    code: 0
    description: "正常終了"
  error:
    code: 1
    description: "異常終了"

start: start

transitions:
  start:
    success::done: exit::success
    failure::error: exit::error

options:
  max_iterations: 100
'''
    (graphs_dir / f"{name}_{timestamp}.yml").write_text(yaml_content)

    typer.echo(f"  作成: src/{name}.py")
    typer.echo(f"  作成: src/nodes/{name}/start.py")
    typer.echo(f"  作成: transition_graphs/{name}_{timestamp}.yml")
    typer.echo("")
    typer.echo("次のステップ:")
    typer.echo(f"  1. transition_graphs/{name}_*.yml を編集")
    typer.echo(f"  2. railway sync transition --entry {name}")
    typer.echo(f"  3. railway run {name}")


def _create_linear_entry(project_dir: Path, name: str) -> None:
    """Create typed_pipeline style entry point."""
    src_dir = project_dir / "src"
    nodes_dir = src_dir / "nodes" / name

    nodes_dir.mkdir(parents=True, exist_ok=True)

    # Create entry point file
    entry_content = f'''"""
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
    result = typed_pipeline([
        step1,
        step2,
    ])

    print(f"完了: {{result}}")
    return result
'''
    (src_dir / f"{name}.py").write_text(entry_content)

    # Create step nodes
    for i, step_name in enumerate(["step1", "step2"], 1):
        node_content = f'''"""
{name} ステップ{i}
"""
from railway import Contract, node


class Step{i}Output(Contract):
    """ステップ{i}の出力"""
    value: str


@node
def {step_name}() -> Step{i}Output:
    """
    ステップ{i}の処理。

    Returns:
        Step{i}Output: 処理結果
    """
    return Step{i}Output(value="processed")
'''
        (nodes_dir / f"{step_name}.py").write_text(node_content)

    (nodes_dir / "__init__.py").touch()

    typer.echo(f"  作成: src/{name}.py")
    typer.echo(f"  作成: src/nodes/{name}/step1.py")
    typer.echo(f"  作成: src/nodes/{name}/step2.py")


def _to_class_name(name: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in name.split("_"))
```

---

## 完了条件

- [ ] `railway new entry <name>` がデフォルトで dag_runner 型を生成
- [ ] `--mode linear` オプションで typed_pipeline 型を生成
- [ ] dag_runner 型で transition YAML を自動生成
- [ ] dag_runner 型で @node(Outcome) スタイルのノードを生成
- [ ] linear 型で @node(Contract) スタイルのノードを生成
- [ ] 不正なモードでエラー
- [ ] テストカバレッジ90%以上

---

## 次のIssue

- #18: README.md 更新（dag_runner 型デフォルト）
- #19: TUTORIAL.md 更新（dag_runner 型デフォルト）
