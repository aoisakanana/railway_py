# Issue #62: 終端ノードスケルトン自動生成の統合

**優先度**: P1
**依存**: #60
**ブロック**: #64

---

## 概要

終端ノードスケルトンの自動生成を以下の両方で動作するようにする：
1. `railway new entry` 実行時
2. `railway sync transition` 実行時（**現在未実装 - バグ修正**）

既存の `sync_exit_nodes()` を活用し、コードの重複を避ける。

## 背景

### 問題 1: `railway new entry` で終端ノードが生成されない

現在、`railway new entry` で YAML に終端ノード（`exit.success.done` 等）を定義しても、
対応する Python ファイルは生成されない。

### 問題 2: `railway sync transition` でも終端ノードが生成されない（バグ）

`sync_exit_nodes()` 関数は存在するが、`_sync_entry()` 内で呼び出されていない。
そのため、YAML を編集して新しい終端ノードを追加しても、スケルトンが生成されない。

**現在のコード（sync.py:247-307）**:
```python
def _sync_entry(...) -> None:
    # YAML パース
    graph = load_transition_graph(yaml_path)

    # 検証
    result = validate_graph(graph)

    # 遷移コード生成
    code = generate_transition_code(graph, ...)

    # 書き込み
    output_path.write_text(code)

    # ← sync_exit_nodes() が呼ばれていない！
```

**期待される動作**:
```bash
# YAML に新しい終端ノードを追加
# exit.failure.timeout を追加

railway sync transition --entry greeting
# → _railway/generated/greeting_transitions.py が生成
# → src/nodes/exit/failure/timeout.py も自動生成 ← これが動かない
```

---

## 既存コードの確認

`railway/cli/sync.py` に既存の `sync_exit_nodes()` 関数がある:

```python
# 既存の関数（活用する）
def sync_exit_nodes(graph: TransitionGraph, project_root: Path) -> SyncResult:
    """未実装の終端ノードにスケルトンを生成（副作用あり）。"""
    ...
```

この関数は `TransitionGraph` を引数に取るため、YAML のパース後に呼び出す必要がある。

**問題**: この関数は存在するが、`_sync_entry()` 内で呼び出されていない。

---

## 修正内容

### 1. `_sync_entry()` 内で `sync_exit_nodes()` を呼び出す（バグ修正）

```python
def _sync_entry(...) -> None:
    # ... 既存の処理 ...

    # 終端ノードスケルトン生成を追加
    if not dry_run and not validate_only:
        cwd = Path.cwd()
        exit_result = sync_exit_nodes(graph, cwd)
        for path in exit_result.generated:
            typer.echo(f"  終端ノード生成: {path.relative_to(cwd)}")

    # 遷移コード生成（既存）
    ...
```

### 2. `railway new entry` でも `sync_exit_nodes()` を呼び出す

`_create_dag_entry()` で YAML 生成後に呼び出す。

---

## 設計方針

既存の `sync_exit_nodes()` を両方の場所で再利用:

| 呼び出し元 | タイミング | 効果 |
|------------|------------|------|
| `_sync_entry()` | `railway sync transition` 時 | YAML 更新後に新しい終端ノードを生成 |
| `_create_dag_entry()` | `railway new entry` 時 | 初期終端ノードを生成 |

**利点**:
- コード重複なし
- 既存の `sync_exit_nodes()` のテストを活用
- カスタム終端ノード（`exit.failure.ssh.handshake` など）にも対応

---

## TDD 実装フロー

### Phase 1: Red（失敗するテストを先に作成）

#### 1-A: `railway sync transition` での終端ノード生成テスト

```python
# tests/unit/cli/test_sync_exit_nodes.py

import pytest
from pathlib import Path


class TestSyncTransitionExitNodes:
    """railway sync transition での終端ノード生成テスト（バグ修正）。"""

    def test_sync_generates_new_exit_nodes(self, tmp_path: Path) -> None:
        """sync 時に新しい終端ノードが生成される。"""
        from railway.cli.sync import _sync_entry

        # YAML を作成
        graphs_dir = tmp_path / "transition_graphs"
        graphs_dir.mkdir()
        yaml_content = '''
version: "1.0"
entrypoint: test
nodes:
  start:
    module: nodes.test.start
    function: start
  exit:
    success:
      done:
        description: "正常終了"
    failure:
      timeout:
        description: "タイムアウト"
start: start
transitions:
  start:
    success::done: exit.success.done
    failure::timeout: exit.failure.timeout
'''
        (graphs_dir / "test_20260201000000.yml").write_text(yaml_content)

        # sync 実行
        output_dir = tmp_path / "_railway" / "generated"
        output_dir.mkdir(parents=True)
        (tmp_path / "src").mkdir()

        _sync_entry(
            entry_name="test",
            graphs_dir=graphs_dir,
            output_dir=output_dir,
            dry_run=False,
            validate_only=False,
            force=True,
        )

        # 終端ノードが生成されている
        assert (tmp_path / "src/nodes/exit/success/done.py").exists()
        assert (tmp_path / "src/nodes/exit/failure/timeout.py").exists()

    def test_sync_skips_existing_exit_nodes(self, tmp_path: Path) -> None:
        """既存の終端ノードは上書きされない。"""
        from railway.cli.sync import _sync_entry

        graphs_dir = tmp_path / "transition_graphs"
        graphs_dir.mkdir()
        yaml_content = '''
version: "1.0"
entrypoint: test
nodes:
  start:
    module: nodes.test.start
    function: start
  exit:
    success:
      done:
        description: "正常終了"
start: start
transitions:
  start:
    success::done: exit.success.done
'''
        (graphs_dir / "test_20260201000000.yml").write_text(yaml_content)

        # 既存ファイルを作成
        exit_path = tmp_path / "src/nodes/exit/success/done.py"
        exit_path.parent.mkdir(parents=True)
        exit_path.write_text("# custom implementation")

        output_dir = tmp_path / "_railway" / "generated"
        output_dir.mkdir(parents=True)

        _sync_entry(
            entry_name="test",
            graphs_dir=graphs_dir,
            output_dir=output_dir,
            dry_run=False,
            validate_only=False,
            force=True,
        )

        # 上書きされていない
        assert exit_path.read_text() == "# custom implementation"
```

#### 1-B: `railway new entry` での終端ノード生成テスト

```python
# tests/unit/cli/test_new_entry_exit_nodes.py

import pytest
from pathlib import Path
from unittest.mock import patch


class TestNewEntryExitNodes:
    """railway new entry での終端ノード生成テスト。"""

    def test_generates_success_exit_node(self, tmp_path: Path) -> None:
        """成功終端ノードが生成される。"""
        from railway.cli.new import _create_dag_entry

        # src ディレクトリを作成（プロジェクト構造をシミュレート）
        (tmp_path / "src").mkdir()
        (tmp_path / "transition_graphs").mkdir()

        with patch("railway.cli.new.Path.cwd", return_value=tmp_path):
            _create_dag_entry("greeting")

        exit_node_path = tmp_path / "src/nodes/exit/success/done.py"
        assert exit_node_path.exists()

    def test_generates_failure_exit_node(self, tmp_path: Path) -> None:
        """失敗終端ノードが生成される。"""
        from railway.cli.new import _create_dag_entry

        (tmp_path / "src").mkdir()
        (tmp_path / "transition_graphs").mkdir()

        with patch("railway.cli.new.Path.cwd", return_value=tmp_path):
            _create_dag_entry("greeting")

        exit_node_path = tmp_path / "src/nodes/exit/failure/error.py"
        assert exit_node_path.exists()

    def test_exit_node_returns_exit_contract(self, tmp_path: Path) -> None:
        """生成された終端ノードは ExitContract を返す。"""
        from railway.cli.new import _create_dag_entry

        (tmp_path / "src").mkdir()
        (tmp_path / "transition_graphs").mkdir()

        with patch("railway.cli.new.Path.cwd", return_value=tmp_path):
            _create_dag_entry("greeting")

        exit_node_path = tmp_path / "src/nodes/exit/success/done.py"
        content = exit_node_path.read_text()

        assert "ExitContract" in content
        assert "class SuccessDoneResult" in content

    def test_creates_init_files(self, tmp_path: Path) -> None:
        """__init__.py が各階層に生成される。"""
        from railway.cli.new import _create_dag_entry

        (tmp_path / "src").mkdir()
        (tmp_path / "transition_graphs").mkdir()

        with patch("railway.cli.new.Path.cwd", return_value=tmp_path):
            _create_dag_entry("greeting")

        assert (tmp_path / "src/nodes/exit/__init__.py").exists()
        assert (tmp_path / "src/nodes/exit/success/__init__.py").exists()

    def test_does_not_overwrite_existing_exit_node(self, tmp_path: Path) -> None:
        """既存の終端ノードは上書きしない。"""
        from railway.cli.new import _create_dag_entry

        (tmp_path / "src").mkdir()
        (tmp_path / "transition_graphs").mkdir()

        # 既存ファイルを作成
        exit_node_path = tmp_path / "src/nodes/exit/success/done.py"
        exit_node_path.parent.mkdir(parents=True, exist_ok=True)
        exit_node_path.write_text("# custom implementation")

        with patch("railway.cli.new.Path.cwd", return_value=tmp_path):
            _create_dag_entry("greeting")

        # 上書きされていない
        assert exit_node_path.read_text() == "# custom implementation"


class TestSyncExitNodesFromYamlContent:
    """YAML コンテンツからの終端ノード生成テスト。"""

    def test_generates_from_yaml_content(self, tmp_path: Path) -> None:
        """YAML コンテンツから終端ノードを生成する。"""
        from railway.cli.new import _generate_exit_nodes_from_yaml

        yaml_content = '''
nodes:
  exit:
    success:
      done:
        description: "正常終了"
'''
        (tmp_path / "src").mkdir()

        result = _generate_exit_nodes_from_yaml(yaml_content, tmp_path)

        assert len(result.generated) == 1
        assert (tmp_path / "src/nodes/exit/success/done.py").exists()
```

### Phase 2: Green（最小実装）

#### 2-A: `_sync_entry()` の修正（バグ修正）

```python
# railway/cli/sync.py の _sync_entry() を修正

def _sync_entry(
    entry_name: str,
    graphs_dir: Path,
    output_dir: Path,
    dry_run: bool,
    validate_only: bool,
    force: bool,
) -> None:
    """Sync a single entrypoint."""
    # Find latest YAML
    yaml_path = find_latest_yaml(graphs_dir, entry_name)
    if yaml_path is None:
        raise SyncError(f"遷移グラフが見つかりません: {entry_name}_*.yml")

    typer.echo(f"処理中: {yaml_path.name}")

    # Parse YAML
    try:
        graph = load_transition_graph(yaml_path)
    except ParseError as e:
        raise SyncError(f"パースエラー: {e}")

    # Validate graph
    result = validate_graph(graph)
    if not result.is_valid:
        error_msgs = "\n  ".join(f"[{e.code}] {e.message}" for e in result.errors)
        raise SyncError(f"検証エラー:\n  {error_msgs}")

    # Show warnings
    for warning in result.warnings:
        typer.echo(f"  警告 [{warning.code}]: {warning.message}")

    if validate_only:
        typer.echo(f"✓ {entry_name}: 検証成功")
        return

    # ★ 終端ノードスケルトン生成を追加（バグ修正）
    if not dry_run:
        cwd = Path.cwd()
        exit_result = sync_exit_nodes(graph, cwd)
        for path in exit_result.generated:
            typer.echo(f"  終端ノード生成: {path.relative_to(cwd)}")
        for path in exit_result.skipped:
            # 既存ファイルはスキップ（情報表示は省略）
            pass

    # Generate code (pure function)
    relative_yaml = yaml_path.relative_to(graphs_dir.parent)
    code = generate_transition_code(graph, str(relative_yaml))

    if dry_run:
        typer.echo(f"\n--- プレビュー: {entry_name}_transitions.py ---")
        lines = code.split("\n")[:50]
        typer.echo("\n".join(lines))
        if len(code.split("\n")) > 50:
            typer.echo("... (省略)")
        typer.echo("--- プレビュー終了 ---\n")
        return

    # Write generated code
    output_path = output_dir / f"{entry_name}_transitions.py"
    if output_path.exists() and not force:
        typer.echo(
            f"  ファイルが既に存在します。--force で上書き可能です: {output_path}"
        )

    output_path.write_text(code, encoding="utf-8")

    typer.echo(f"✓ {entry_name}: 生成完了")
    typer.echo(f"  出力: _railway/generated/{entry_name}_transitions.py")
```

#### 2-B: `railway/cli/new.py` に追加

```python
# railway/cli/new.py に追加

import yaml
from railway.core.dag.parser import parse_transition_graph
from railway.cli.sync import sync_exit_nodes, SyncResult


def _generate_exit_nodes_from_yaml(
    yaml_content: str,
    project_root: Path,
) -> SyncResult:
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
    parsed = yaml.safe_load(yaml_content)
    graph = parse_transition_graph(parsed)
    return sync_exit_nodes(graph, project_root)


def _create_dag_entry(name: str) -> None:
    """Create dag_runner style entry point with nodes and YAML."""
    cwd = Path.cwd()
    src_dir = cwd / "src"
    nodes_dir = src_dir / "nodes" / name
    graphs_dir = cwd / "transition_graphs"

    # Create directories
    nodes_dir.mkdir(parents=True, exist_ok=True)

    # 1. Create YAML (pure function)
    yaml_content = _get_dag_yaml_template(name)

    # 2. Write YAML (side effect)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    yaml_path = graphs_dir / f"{name}_{timestamp}.yml"
    _write_file(yaml_path, yaml_content)

    # 3. Generate exit nodes from YAML (side effect)
    exit_result = _generate_exit_nodes_from_yaml(yaml_content, cwd)

    # 4. Create start node (side effect)
    node_content = _get_dag_node_template(name)
    (nodes_dir / "__init__.py").touch()
    _write_file(nodes_dir / "start.py", node_content)

    # Output messages
    typer.echo(f"✓ エントリーポイント '{name}' を作成しました（モード: dag）\n")
    typer.echo(f"  作成: src/{name}.py")
    typer.echo(f"  作成: src/nodes/{name}/start.py")
    typer.echo(f"  作成: transition_graphs/{name}_{timestamp}.yml")

    for path in exit_result.generated:
        relative = path.relative_to(cwd)
        typer.echo(f"  作成: {relative}")

    typer.echo("")
    typer.echo("次のステップ:")
    typer.echo(f"  railway run {name}")
```

### Phase 3: Refactor

- カスタム終端ノードのオプション追加
- 終端ノード生成のスキップオプション（`--skip-exit-nodes`）

---

## 修正ファイル

| ファイル | 変更内容 |
|----------|----------|
| `railway/cli/sync.py` | `_sync_entry()` 内で `sync_exit_nodes()` を呼び出す（**バグ修正**） |
| `railway/cli/new.py` | `_generate_exit_nodes_from_yaml()` 追加、`_create_dag_entry()` 修正 |
| `tests/unit/cli/test_sync_exit_nodes.py` | 新規テストファイル（sync 時の終端ノード生成） |
| `tests/unit/cli/test_new_entry_exit_nodes.py` | 新規テストファイル（new entry 時の終端ノード生成） |

---

## 生成されるファイル構造

```
project/
├── src/
│   ├── greeting.py              # エントリポイント
│   └── nodes/
│       ├── greeting/
│       │   ├── __init__.py
│       │   └── start.py         # 開始ノード
│       └── exit/
│           ├── __init__.py
│           ├── success/
│           │   ├── __init__.py
│           │   └── done.py      # ← 自動生成
│           └── failure/
│               ├── __init__.py
│               └── error.py     # ← 自動生成
└── transition_graphs/
    └── greeting_*.yml
```

---

## 関数型パラダイムの観点

### 純粋関数と副作用の分離

| 関数 | 純粋/副作用 | 説明 |
|------|-------------|------|
| `_get_dag_yaml_template()` | 純粋 | YAML 文字列を生成 |
| `parse_transition_graph()` | 純粋 | YAML を TransitionGraph に変換 |
| `generate_exit_node_skeleton()` | 純粋 | コード文字列を生成 |
| `sync_exit_nodes()` | 副作用 | ファイルを書き込む |
| `_generate_exit_nodes_from_yaml()` | 副作用 | 上記を組み合わせる |

### `_ensure_package_directory()` の改善

既存の `while` ループを関数型スタイルに修正:

```python
# Before (手続き型)
def _ensure_package_directory(directory: Path) -> None:
    current = directory
    while current.name and current.name != "src":
        init_file = current / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Auto-generated package."""\n')
        current = current.parent

# After (関数型)
def _get_package_directories(directory: Path) -> tuple[Path, ...]:
    """src までのディレクトリパスを取得（純粋関数）。"""
    dirs: list[Path] = []
    current = directory
    while current.name and current.name != "src":
        dirs.append(current)
        current = current.parent
    return tuple(dirs)


def _ensure_package_directory(directory: Path) -> None:
    """ディレクトリに __init__.py を生成（副作用あり）。"""
    directory.mkdir(parents=True, exist_ok=True)
    for d in _get_package_directories(directory):
        init_file = d / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Auto-generated package."""\n')
```

---

## 受け入れ条件

### 機能
- [ ] `railway sync transition` で終端ノードファイルが生成される（**バグ修正**）
- [ ] `railway new entry` で終端ノードファイルが生成される
- [ ] 生成された終端ノードは `ExitContract` サブクラスを返す
- [ ] `__init__.py` が各階層に生成される
- [ ] 既存の終端ノードは上書きされない
- [ ] YAML 更新後の `sync` で新しい終端ノードのみ生成される

### TDD・関数型
- [ ] Red → Green → Refactor フェーズに従って実装
- [ ] 既存の `sync_exit_nodes()` を両方の場所で再利用
- [ ] 純粋関数と副作用関数の明確な分離
- [ ] 全テスト通過

---

*railway sync transition と railway new entry の両方で終端ノードを自動生成*
