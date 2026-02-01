"""
Sync command for transition graph code generation.

This module is the IO boundary - it handles file operations
and delegates to pure functions for parsing, validation, and generation.

Issue #44: Exit node skeleton generation support added.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import typer

from railway.core.dag.codegen import generate_transition_code, generate_exit_node_skeleton
from railway.core.dag.parser import ParseError, load_transition_graph
from railway.core.dag.types import TransitionGraph, NodeDefinition
from railway.core.dag.validator import validate_graph


# =============================================================================
# Issue #44: Exit Node Skeleton Generation
# =============================================================================


# =============================================================================
# Issue #65: YAML Format Conversion
# =============================================================================


def _is_old_format_yaml(yaml_path: Path) -> bool:
    """YAML が旧形式（exits セクションあり）か判定（純粋関数）。"""
    import yaml

    content = yaml_path.read_text()
    data = yaml.safe_load(content)
    return "exits" in data


def _convert_yaml_if_old_format(yaml_path: Path) -> bool:
    """旧形式 YAML を新形式に変換（副作用あり）。

    Args:
        yaml_path: YAML ファイルパス

    Returns:
        変換した場合 True、既に新形式の場合 False
    """
    import yaml

    from railway.migrations.yaml_converter import convert_yaml_structure

    content = yaml_path.read_text()
    data = yaml.safe_load(content)

    if "exits" not in data:
        typer.echo(f"  既に新形式: {yaml_path.name}")
        return False

    result = convert_yaml_structure(data)

    if result.success:
        new_content = yaml.safe_dump(result.data, allow_unicode=True, sort_keys=False)
        yaml_path.write_text(new_content)
        typer.echo(f"  変換: {yaml_path.name}（旧形式 → 新形式）")
        return True
    else:
        typer.echo(f"  警告: YAML 変換に失敗しました: {result.error}", err=True)
        return False


@dataclass(frozen=True)
class SyncResult:
    """終端ノード同期の結果（イミュータブル）。

    Attributes:
        generated: 生成されたファイルパス
        skipped: スキップされたファイルパス（既存）
        warnings: 警告メッセージ

    Note:
        dataclass を採用した理由:
        - 内部処理用でユーザーに直接公開されない
        - シリアライズ不要
        - ValidationResult 等の既存内部型と一貫性がある
        - BaseModel より軽量
    """

    generated: tuple[Path, ...]
    skipped: tuple[Path, ...]
    warnings: tuple[str, ...] = ()


def sync_exit_nodes(graph: TransitionGraph, project_root: Path) -> SyncResult:
    """未実装の終端ノードにスケルトンを生成（副作用あり）。

    Args:
        graph: 遷移グラフ
        project_root: プロジェクトルート

    Returns:
        SyncResult: 同期結果

    Note:
        この関数は以下の副作用を持つ：
        - ファイル書き込み
        - ディレクトリ作成
    """
    generated: list[Path] = []
    skipped: list[Path] = []

    for node_def in graph.nodes:
        if not node_def.is_exit:
            continue

        file_path = _calculate_exit_node_file_path(node_def, project_root)

        if file_path.exists():
            skipped.append(file_path)
            continue

        # 純粋関数でコード生成
        code = generate_exit_node_skeleton(node_def)

        # 副作用: ファイル書き込み
        _write_skeleton_file(file_path, code)
        generated.append(file_path)

    return SyncResult(
        generated=tuple(generated),
        skipped=tuple(skipped),
    )


def _calculate_exit_node_file_path(node: NodeDefinition, project_root: Path) -> Path:
    """ノード定義からファイルパスを計算（純粋関数）。

    Args:
        node: ノード定義
        project_root: プロジェクトルート

    Returns:
        ファイルパス

    Examples:
        >>> _calculate_exit_node_file_path(NodeDefinition(module="nodes.exit.success.done", ...), Path("/project"))
        Path("/project/src/nodes/exit/success/done.py")
    """
    module_path = node.module.replace(".", "/") + ".py"
    return project_root / "src" / module_path


def _write_skeleton_file(file_path: Path, content: str) -> None:
    """スケルトンファイルを書き込み（副作用あり）。

    Args:
        file_path: 書き込み先パス
        content: ファイル内容
    """
    _ensure_package_directory(file_path.parent)
    file_path.write_text(content)


def _ensure_package_directory(directory: Path) -> None:
    """ディレクトリを作成し、__init__.py も生成する（副作用あり）。

    Args:
        directory: 作成するディレクトリ

    Note:
        src ディレクトリ自体には __init__.py を作成しない。
        src/nodes/ 以下の階層にのみ作成する。
    """
    directory.mkdir(parents=True, exist_ok=True)

    # src ディレクトリまでの各階層に __init__.py を作成
    # ただし src 自体には作成しない
    current = directory
    while current.name and current.name != "src":
        init_file = current / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Auto-generated package."""\n')
        current = current.parent

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
    no_overwrite: bool = typer.Option(
        False,
        "--no-overwrite",
        help="既存ファイルを上書きしない",
    ),
    convert: bool = typer.Option(
        False,
        "--convert",
        "-c",
        help="旧形式 YAML を新形式に変換",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        hidden=True,  # 内部用（後方互換のため残す）
        help="既存ファイルを強制上書き（非推奨: デフォルトで上書き）",
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
                no_overwrite=no_overwrite,
                convert=convert,
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
    no_overwrite: bool = False,
    convert: bool = False,
) -> None:
    """Sync a single entrypoint.

    Issue #62 修正: sync_exit_nodes() を呼び出すように変更。
    Issue #65 修正: デフォルトで上書き、--no-overwrite でスキップ、--convert で変換。

    Args:
        entry_name: エントリーポイント名
        graphs_dir: 遷移グラフディレクトリ
        output_dir: 出力ディレクトリ
        dry_run: プレビューのみ
        validate_only: 検証のみ
        no_overwrite: True の場合、既存ファイルをスキップ
        convert: True の場合、旧形式 YAML を新形式に変換
    """
    # Find latest YAML
    yaml_path = find_latest_yaml(graphs_dir, entry_name)
    if yaml_path is None:
        raise SyncError(f"遷移グラフが見つかりません: {entry_name}_*.yml")

    typer.echo(f"処理中: {yaml_path.name}")

    # Convert YAML if requested
    if convert:
        _convert_yaml_if_old_format(yaml_path)

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

    if dry_run:
        # Generate code (pure function) for preview
        relative_yaml = yaml_path.relative_to(graphs_dir.parent)
        code = generate_transition_code(graph, str(relative_yaml))
        typer.echo(f"\n--- プレビュー: {entry_name}_transitions.py ---")
        # Show first 50 lines
        lines = code.split("\n")[:50]
        typer.echo("\n".join(lines))
        if len(code.split("\n")) > 50:
            typer.echo("... (省略)")
        typer.echo("--- プレビュー終了 ---\n")
        return

    # Issue #62: 終端ノードスケルトン生成（副作用あり）
    cwd = graphs_dir.parent  # プロジェクトルート
    exit_result = sync_exit_nodes(graph, cwd)
    for path in exit_result.generated:
        typer.echo(f"  終端ノード生成: {path.relative_to(cwd)}")

    # Generate code (pure function)
    relative_yaml = yaml_path.relative_to(graphs_dir.parent)
    code = generate_transition_code(graph, str(relative_yaml))

    # Write generated code (IO operation)
    output_path = output_dir / f"{entry_name}_transitions.py"
    if output_path.exists() and no_overwrite:
        typer.echo(f"  スキップ: {output_path.name}（既に存在、--no-overwrite）")
        return

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
