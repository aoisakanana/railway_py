# Issue #64: `railway new entry` に sync を統合（デフォルト化）

**優先度**: P0
**依存**: #60, #61, #62
**ブロック**: なし

---

## 概要

`railway new entry` のデフォルト動作を変更し、**1コマンドで動作するプロジェクト**を生成できるようにする。

## 背景

現在のフローでは `railway new entry` 後に手動で `railway sync transition` を実行する必要がある。
これは3ステップ（new → sync → run）となり、初心者にとって障壁となる。

**現在の問題**:
```bash
railway new entry greeting
# → greeting.py で _railway/generated/greeting_transitions を import しているが、
#   _railway/ ディレクトリはまだ存在しない

railway run greeting
# → ImportError: No module named '_railway.generated.greeting_transitions'

railway sync transition --entry greeting
# → _railway/generated/greeting_transitions.py が生成される

railway run greeting
# → 正常動作
```

**期待される体験**:
```bash
railway new entry greeting
# → YAML、ノード、終端ノード、_railway/ すべて生成

railway run greeting
# → 正常動作（1コマンドで準備完了）
```

---

## 設計方針

### デフォルト動作の変更

**sync をデフォルトで実行する理由**:

| 観点 | 理由 |
|------|------|
| 後方互換性 | `railway new entry` は新規作成なので影響なし |
| ユーザー体験 | 「1コマンドで動く」が直感的 |
| エラー削減 | sync 忘れによる ImportError を防止 |
| 初心者向け | 複雑なフローを隠蔽 |

### オプション設計

| オプション | 動作 |
|------------|------|
| （デフォルト） | YAML + ノード + sync + エントリポイント すべて生成 |
| `--no-sync` | YAML + ノード のみ生成、エントリポイントは pending 状態 |

### 処理フロー

```
railway new entry greeting
    │
    ├─1. YAML テンプレート生成（#60）
    │   └─ transition_graphs/greeting_*.yml
    │
    ├─2. 開始ノード生成
    │   └─ src/nodes/greeting/start.py
    │
    ├─3. 終端ノード生成（#62）
    │   ├─ src/nodes/exit/success/done.py
    │   └─ src/nodes/exit/failure/error.py
    │
    ├─4. YAML パース & コード生成（sync）
    │   └─ _railway/generated/greeting_transitions.py
    │
    └─5. エントリポイント生成（#61）
        └─ src/greeting.py（run() を import）
```

---

## TDD 実装フロー

### Phase 1: Red（失敗するテストを先に作成）

```python
# tests/unit/cli/test_new_entry_sync.py

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

        # プロジェクト構造をセットアップ
        (tmp_path / "src").mkdir()
        (tmp_path / "transition_graphs").mkdir()
        (tmp_path / "_railway/generated").mkdir(parents=True)

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["new", "entry", "greeting"])

            assert result.exit_code == 0
            assert (tmp_path / "_railway/generated/greeting_transitions.py").exists()

    def test_default_uses_run_helper_in_entrypoint(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """デフォルトでエントリポイントは run() を使用する。"""
        from railway.cli.main import app

        (tmp_path / "src").mkdir()
        (tmp_path / "transition_graphs").mkdir()
        (tmp_path / "_railway/generated").mkdir(parents=True)

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["new", "entry", "greeting"])

            assert result.exit_code == 0
            entrypoint = (tmp_path / "src/greeting.py").read_text()
            assert "from _railway.generated.greeting_transitions import run" in entrypoint


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

        (tmp_path / "src").mkdir()
        (tmp_path / "transition_graphs").mkdir()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["new", "entry", "greeting", "--no-sync"])

            assert result.exit_code == 0
            assert not (tmp_path / "_railway/generated/greeting_transitions.py").exists()

    def test_no_sync_uses_pending_template(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """--no-sync でエントリポイントは pending 状態。"""
        from railway.cli.main import app

        (tmp_path / "src").mkdir()
        (tmp_path / "transition_graphs").mkdir()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["new", "entry", "greeting", "--no-sync"])

            assert result.exit_code == 0
            entrypoint = (tmp_path / "src/greeting.py").read_text()
            assert "NotImplementedError" in entrypoint
            assert "railway sync transition" in entrypoint
```

### E2E テスト（subprocess 使用、並列安全）

```python
# tests/e2e/test_new_entry_workflow.py

import subprocess
from pathlib import Path

import pytest


class TestNewEntryE2E:
    """new entry の E2E 統合テスト。

    Note:
        subprocess.run() の cwd パラメータを使用し、
        os.chdir() を避けて並列テスト安全性を確保。
    """

    def test_full_workflow_default(self, tmp_path: Path) -> None:
        """new entry → run の完全フロー（デフォルト動作）。"""
        project_dir = tmp_path / "test_project"

        # railway init
        result = subprocess.run(
            ["railway", "init", "test_project"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"init failed: {result.stderr}"

        # railway new entry（デフォルト = sync 実行）
        result = subprocess.run(
            ["railway", "new", "entry", "greeting"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"new entry failed: {result.stderr}"

        # _railway/generated/ が存在する
        assert (project_dir / "_railway/generated/greeting_transitions.py").exists()

        # railway run
        result = subprocess.run(
            ["railway", "run", "greeting"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"run failed: {result.stderr}"

    def test_full_workflow_no_sync(self, tmp_path: Path) -> None:
        """new entry --no-sync → sync → run のフロー。"""
        project_dir = tmp_path / "test_project"

        # railway init
        subprocess.run(
            ["railway", "init", "test_project"],
            cwd=tmp_path,
            capture_output=True,
        )

        # railway new entry --no-sync
        result = subprocess.run(
            ["railway", "new", "entry", "greeting", "--no-sync"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        # _railway/generated/ はまだ存在しない
        assert not (project_dir / "_railway/generated/greeting_transitions.py").exists()

        # railway sync transition
        result = subprocess.run(
            ["railway", "sync", "transition", "--entry", "greeting"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        # railway run
        result = subprocess.run(
            ["railway", "run", "greeting"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_generated_code_passes_type_check(self, tmp_path: Path) -> None:
        """生成されたコードは mypy を通過する。"""
        project_dir = tmp_path / "test_project"

        subprocess.run(["railway", "init", "test_project"], cwd=tmp_path, capture_output=True)
        subprocess.run(["railway", "new", "entry", "greeting"], cwd=project_dir, capture_output=True)

        # mypy チェック
        result = subprocess.run(
            ["uv", "run", "mypy", "src/"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"mypy errors: {result.stdout}\n{result.stderr}"

    def test_generated_code_passes_lint(self, tmp_path: Path) -> None:
        """生成されたコードは ruff を通過する。"""
        project_dir = tmp_path / "test_project"

        subprocess.run(["railway", "init", "test_project"], cwd=tmp_path, capture_output=True)
        subprocess.run(["railway", "new", "entry", "greeting"], cwd=project_dir, capture_output=True)

        # ruff チェック
        result = subprocess.run(
            ["uv", "run", "ruff", "check", "src/"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"ruff errors: {result.stdout}\n{result.stderr}"
```

### Phase 2: Green（最小実装）

```python
# railway/cli/new.py の修正

import typer
from pathlib import Path

from railway.cli.sync import _sync_entry


def new(
    component_type: ComponentType = typer.Argument(...),
    name: str = typer.Argument(...),
    # ... 既存のオプション ...
    no_sync: bool = typer.Option(
        False,
        "--no-sync",
        help="sync を実行しない（上級者向け）",
    ),
) -> None:
    """Create a new entry point, node, or contract."""
    # ... 既存のバリデーション ...

    if component_type == ComponentType.entry:
        entry_mode = EntryMode.dag if mode == "dag" else EntryMode.linear
        _create_entry(name, example, force, entry_mode, sync=not no_sync)
    # ... 他の処理 ...


def _create_entry(
    name: str,
    example: bool,
    force: bool,
    mode: EntryMode = EntryMode.dag,
    sync: bool = True,  # デフォルト True
) -> None:
    """Create a new entry point."""
    # ... 既存のバリデーション ...

    if mode == EntryMode.dag:
        _create_dag_entry(name, sync=sync)
    else:
        _create_linear_entry(name)


def _create_dag_entry(name: str, sync: bool = True) -> None:
    """Create dag_runner style entry point with nodes and YAML."""
    cwd = Path.cwd()
    src_dir = cwd / "src"
    nodes_dir = src_dir / "nodes" / name
    graphs_dir = cwd / "transition_graphs"
    output_dir = cwd / "_railway" / "generated"

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

    # 5. Sync transition (if enabled)
    if sync:
        output_dir.mkdir(parents=True, exist_ok=True)
        _run_sync_for_entry(name, graphs_dir, output_dir)

    # 6. Create entrypoint (depends on sync state)
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
```

### Phase 3: Refactor

- 進捗表示の改善（spinnerなど）
- `--sync` オプションの追加（将来的にデフォルトを変更する場合の互換性）
- エラーハンドリングの強化

---

## 修正ファイル

| ファイル | 変更内容 |
|----------|----------|
| `railway/cli/new.py` | `--no-sync` オプション追加、`_create_dag_entry()` 修正 |
| `tests/unit/cli/test_new_entry_sync.py` | 新規テストファイル |
| `tests/e2e/test_new_entry_workflow.py` | 新規 E2E テストファイル |

---

## コマンド仕様

```bash
# デフォルト（sync 実行）
railway new entry <name>
# → YAML, 開始ノード, 終端ノード, _railway/generated/, エントリポイント を生成
# → すぐに railway run 可能

# 上級者向け（sync スキップ）
railway new entry <name> --no-sync
# → YAML, 開始ノード, 終端ノード を生成
# → _railway/generated/ は生成されない
# → エントリポイントは pending 状態
```

---

## 受け入れ条件

### 機能
- [ ] デフォルトで `_railway/generated/` が生成される
- [ ] `--no-sync` で `_railway/generated/` を生成しない
- [ ] デフォルト時のエントリポイントは `run()` を使用
- [ ] `--no-sync` 時のエントリポイントは pending 状態
- [ ] `railway new entry greeting && railway run greeting` が正常動作

### E2E テスト
- [ ] 生成されたコードが mypy を通過
- [ ] 生成されたコードが ruff を通過
- [ ] 完全なワークフロー（init → new entry → run）が動作
- [ ] subprocess の cwd パラメータを使用（並列テスト安全）

### TDD・関数型
- [ ] Red → Green → Refactor フェーズに従って実装
- [ ] 純粋関数（テンプレート生成）と副作用関数（ファイル書き込み）の分離
- [ ] 全テスト通過

---

*1コマンドで動作するプロジェクトを提供し、初心者の障壁を下げる*
