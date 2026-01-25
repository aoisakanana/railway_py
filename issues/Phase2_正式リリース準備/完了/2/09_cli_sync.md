# Issue #09: CLI `railway sync transition`

**Phase:** 2b
**優先度:** 高
**依存関係:** #03.1（フィクスチャ）, #05, #06, #08
**見積もり:** 1日

---

## 概要

遷移グラフYAMLからPythonコードを生成するCLIコマンドを実装する。
このコマンドはIO境界として機能し、内部では純粋関数を呼び出す。

---

## コマンド仕様

```bash
# 基本使用法
railway sync transition --entry <entrypoint_name>

# 全エントリーポイントを同期
railway sync transition --all

# ドライラン（プレビュー）
railway sync transition --entry top2 --dry-run

# 検証のみ
railway sync transition --entry top2 --validate-only

# 強制上書き
railway sync transition --entry top2 --force
```

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/cli/test_sync.py
"""Tests for railway sync transition CLI command."""
import pytest
from pathlib import Path
from typer.testing import CliRunner
from textwrap import dedent


runner = CliRunner()


@pytest.fixture
def project_dir(tmp_path):
    """Create a minimal project structure."""
    # Create transition_graphs directory
    graphs_dir = tmp_path / "transition_graphs"
    graphs_dir.mkdir()

    # Create _railway/generated directory
    railway_dir = tmp_path / "_railway" / "generated"
    railway_dir.mkdir(parents=True)

    # Create a sample YAML
    yaml_content = dedent("""
        version: "1.0"
        entrypoint: top2
        description: "テストワークフロー"

        nodes:
          start:
            module: nodes.start
            function: start_node
            description: "開始ノード"

        exits:
          done:
            code: 0
            description: "完了"

        start: start

        transitions:
          start:
            success: exit::done
    """)
    (graphs_dir / "top2_20250125120000.yml").write_text(yaml_content)

    return tmp_path


class TestSyncTransitionCommand:
    """Test railway sync transition command."""

    def test_sync_single_entry(self, project_dir, monkeypatch):
        """Should sync a single entrypoint."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--entry", "top2"])

        assert result.exit_code == 0
        assert "top2" in result.stdout

        # Check generated file exists
        generated = project_dir / "_railway" / "generated" / "top2_transitions.py"
        assert generated.exists()

    def test_sync_dry_run(self, project_dir, monkeypatch):
        """Should show preview without writing files."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--entry", "top2", "--dry-run"])

        assert result.exit_code == 0
        assert "プレビュー" in result.stdout or "dry-run" in result.stdout.lower()

        # Should NOT create file
        generated = project_dir / "_railway" / "generated" / "top2_transitions.py"
        assert not generated.exists()

    def test_sync_validate_only(self, project_dir, monkeypatch):
        """Should validate without generating code."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--entry", "top2", "--validate-only"])

        assert result.exit_code == 0
        assert "検証" in result.stdout or "valid" in result.stdout.lower()

    def test_sync_entry_not_found(self, project_dir, monkeypatch):
        """Should error when entrypoint YAML not found."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--entry", "nonexistent"])

        assert result.exit_code != 0
        assert "見つかりません" in result.stdout or "not found" in result.stdout.lower()

    def test_sync_all_entries(self, project_dir, monkeypatch):
        """Should sync all entrypoints with --all flag."""
        from railway.cli.main import app

        # Add another YAML
        yaml2 = dedent("""
            version: "1.0"
            entrypoint: other
            description: ""
            nodes:
              a:
                module: nodes.a
                function: func_a
                description: ""
            exits:
              done:
                code: 0
                description: ""
            start: a
            transitions:
              a:
                success: exit::done
        """)
        (project_dir / "transition_graphs" / "other_20250125130000.yml").write_text(yaml2)

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--all"])

        assert result.exit_code == 0

        # Both files should be generated
        assert (project_dir / "_railway" / "generated" / "top2_transitions.py").exists()
        assert (project_dir / "_railway" / "generated" / "other_transitions.py").exists()

    def test_sync_validation_error(self, project_dir, monkeypatch):
        """Should report validation errors."""
        from railway.cli.main import app

        # Create invalid YAML (missing start node)
        invalid_yaml = dedent("""
            version: "1.0"
            entrypoint: invalid
            description: ""
            nodes:
              a:
                module: nodes.a
                function: func_a
                description: ""
            exits: {}
            start: nonexistent
            transitions: {}
        """)
        (project_dir / "transition_graphs" / "invalid_20250125140000.yml").write_text(invalid_yaml)

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--entry", "invalid"])

        assert result.exit_code != 0
        assert "エラー" in result.stdout or "error" in result.stdout.lower()


class TestFindLatestYaml:
    """Test YAML file discovery."""

    def test_find_latest_yaml(self, tmp_path):
        """Should find the latest YAML by timestamp."""
        from railway.cli.sync import find_latest_yaml

        graphs_dir = tmp_path / "transition_graphs"
        graphs_dir.mkdir()

        # Create files with different timestamps
        (graphs_dir / "top2_20250101000000.yml").write_text("old")
        (graphs_dir / "top2_20250125120000.yml").write_text("new")
        (graphs_dir / "top2_20250115000000.yml").write_text("middle")

        latest = find_latest_yaml(graphs_dir, "top2")

        assert latest is not None
        assert latest.name == "top2_20250125120000.yml"

    def test_find_latest_yaml_none(self, tmp_path):
        """Should return None when no matching YAML exists."""
        from railway.cli.sync import find_latest_yaml

        graphs_dir = tmp_path / "transition_graphs"
        graphs_dir.mkdir()

        latest = find_latest_yaml(graphs_dir, "nonexistent")

        assert latest is None

    def test_find_all_entrypoints(self, tmp_path):
        """Should find all unique entrypoints."""
        from railway.cli.sync import find_all_entrypoints

        graphs_dir = tmp_path / "transition_graphs"
        graphs_dir.mkdir()

        (graphs_dir / "top2_20250101.yml").write_text("")
        (graphs_dir / "top2_20250102.yml").write_text("")
        (graphs_dir / "other_20250101.yml").write_text("")

        entries = find_all_entrypoints(graphs_dir)

        assert set(entries) == {"top2", "other"}


class TestSyncOutput:
    """Test sync command output formatting."""

    def test_success_message(self, project_dir, monkeypatch):
        """Should show success message with details."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--entry", "top2"])

        assert "✓" in result.stdout or "成功" in result.stdout or "Success" in result.stdout

    def test_shows_generated_path(self, project_dir, monkeypatch):
        """Should show path to generated file."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--entry", "top2"])

        assert "_railway/generated/top2_transitions.py" in result.stdout
```

```bash
pytest tests/unit/cli/test_sync.py -v
# Expected: FAILED (ImportError)
```

### Step 2: Green（最小限の実装）

```python
# railway/cli/sync.py
"""
Sync command for transition graph code generation.

This module is the IO boundary - it handles file operations
and delegates to pure functions for parsing, validation, and generation.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional
import re

import typer
from loguru import logger

from railway.core.dag.parser import load_transition_graph, ParseError
from railway.core.dag.validator import validate_graph
from railway.core.dag.codegen import generate_transition_code

app = typer.Typer(help="同期コマンド")


@app.command("transition")
def sync_transition(
    entry: Optional[str] = typer.Option(
        None,
        "--entry", "-e",
        help="同期するエントリーポイント名",
    ),
    all_entries: bool = typer.Option(
        False,
        "--all", "-a",
        help="すべてのエントリーポイントを同期",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run", "-n",
        help="プレビューのみ（ファイル生成なし）",
    ),
    validate_only: bool = typer.Option(
        False,
        "--validate-only", "-v",
        help="検証のみ（コード生成なし）",
    ),
    force: bool = typer.Option(
        False,
        "--force", "-f",
        help="既存ファイルを強制上書き",
    ),
) -> None:
    """
    遷移グラフYAMLからPythonコードを生成する。

    Usage:
        railway sync transition --entry top2
        railway sync transition --all
        railway sync transition --entry top2 --dry-run
    """
    if not entry and not all_entries:
        typer.echo("エラー: --entry または --all を指定してください", err=True)
        raise typer.Exit(1)

    cwd = Path.cwd()
    graphs_dir = cwd / "transition_graphs"
    output_dir = cwd / "_railway" / "generated"

    if not graphs_dir.exists():
        typer.echo(f"エラー: transition_graphs ディレクトリが見つかりません: {graphs_dir}", err=True)
        raise typer.Exit(1)

    # Ensure output directory exists
    if not dry_run and not validate_only:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Determine entries to process
    if all_entries:
        entries = find_all_entrypoints(graphs_dir)
        if not entries:
            typer.echo("警告: 同期対象のエントリーポイントが見つかりません")
            return
    else:
        entries = [entry]

    # Process each entry
    success_count = 0
    error_count = 0

    for entry_name in entries:
        try:
            _sync_entry(
                entry_name=entry_name,
                graphs_dir=graphs_dir,
                output_dir=output_dir,
                dry_run=dry_run,
                validate_only=validate_only,
                force=force,
            )
            success_count += 1
        except SyncError as e:
            typer.echo(f"✗ {entry_name}: {e}", err=True)
            error_count += 1

    # Summary
    if len(entries) > 1:
        typer.echo(f"\n完了: {success_count} 成功, {error_count} 失敗")

    if error_count > 0:
        raise typer.Exit(1)


class SyncError(Exception):
    """Error during sync operation."""
    pass


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

    # Parse YAML (pure function via IO boundary)
    try:
        graph = load_transition_graph(yaml_path)
    except ParseError as e:
        raise SyncError(f"パースエラー: {e}")

    # Validate graph (pure function)
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

    # Generate code (pure function)
    relative_yaml = yaml_path.relative_to(graphs_dir.parent)
    code = generate_transition_code(graph, str(relative_yaml))

    if dry_run:
        typer.echo(f"\n--- プレビュー: {entry_name}_transitions.py ---")
        # Show first 50 lines
        lines = code.split("\n")[:50]
        typer.echo("\n".join(lines))
        if len(code.split("\n")) > 50:
            typer.echo("... (省略)")
        typer.echo("--- プレビュー終了 ---\n")
        return

    # Write generated code (IO operation)
    output_path = output_dir / f"{entry_name}_transitions.py"
    if output_path.exists() and not force:
        # デフォルト動作: 既存ファイルがある場合は上書きしてスキップ
        # ただし警告を表示してユーザーに通知
        typer.echo(f"  スキップ: {output_path} は既に存在します。--force で上書き可能です")
        return  # 上書きせずに正常終了

    output_path.write_text(code, encoding="utf-8")

    typer.echo(f"✓ {entry_name}: 生成完了")
    typer.echo(f"  出力: _railway/generated/{entry_name}_transitions.py")


def find_latest_yaml(graphs_dir: Path, entry_name: str) -> Optional[Path]:
    """
    Find the latest YAML file for an entrypoint.

    Files are expected to be named: {entry_name}_{timestamp}.yml
    Returns the one with the latest timestamp.

    Args:
        graphs_dir: Directory containing YAML files
        entry_name: Entrypoint name

    Returns:
        Path to latest YAML, or None if not found
    """
    pattern = f"{entry_name}_*.yml"
    matches = list(graphs_dir.glob(pattern))

    if not matches:
        return None

    # Sort by filename (timestamp) descending
    matches.sort(key=lambda p: p.name, reverse=True)
    return matches[0]


def find_all_entrypoints(graphs_dir: Path) -> list[str]:
    """
    Find all unique entrypoints in the graphs directory.

    Args:
        graphs_dir: Directory containing YAML files

    Returns:
        List of unique entrypoint names
    """
    entries: set[str] = set()
    pattern = re.compile(r"^(.+?)_\d+\.yml$")

    for path in graphs_dir.glob("*.yml"):
        match = pattern.match(path.name)
        if match:
            entries.add(match.group(1))

    return sorted(entries)
```

```python
# railway/cli/main.py への追加
# 既存のファイルに以下を追加

from railway.cli.sync import app as sync_app

app.add_typer(sync_app, name="sync")
```

```bash
pytest tests/unit/cli/test_sync.py -v
# Expected: PASSED
```

### Step 3: Refactor

- プログレスバーの追加（複数ファイル処理時）
- 差分表示オプション
- エラーメッセージの改善

---

## 完了条件

- [ ] `railway sync transition --entry` が動作
- [ ] `railway sync transition --all` が動作
- [ ] `--dry-run` でプレビュー表示
- [ ] `--validate-only` で検証のみ
- [ ] 最新のYAMLファイルを自動検出
- [ ] 検証エラー時に適切なメッセージ
- [ ] 生成ファイルパスを表示
- [ ] テストカバレッジ90%以上

---

## 次のIssue

- #10: DAGランナー実装
