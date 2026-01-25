"""
Sync command for transition graph code generation.

This module is the IO boundary - it handles file operations
and delegates to pure functions for parsing, validation, and generation.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import typer

from railway.core.dag.codegen import generate_transition_code
from railway.core.dag.parser import ParseError, load_transition_graph
from railway.core.dag.validator import validate_graph

app = typer.Typer(help="同期コマンド")


class SyncError(Exception):
    """Error during sync operation."""

    pass


@app.command("transition")
def sync_transition(
    entry: Optional[str] = typer.Option(
        None,
        "--entry",
        "-e",
        help="同期するエントリーポイント名",
    ),
    all_entries: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="すべてのエントリーポイントを同期",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="プレビューのみ（ファイル生成なし）",
    ),
    validate_only: bool = typer.Option(
        False,
        "--validate-only",
        "-v",
        help="検証のみ（コード生成なし）",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
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
        typer.echo(
            f"エラー: transition_graphs ディレクトリが見つかりません: {graphs_dir}",
            err=True,
        )
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
        entries = [entry] if entry else []

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
        typer.echo(
            f"  ファイルが既に存在します。--force で上書き可能です: {output_path}"
        )

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
