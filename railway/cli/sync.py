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
from typing import Any

import typer

from railway.core.dag.board_analyzer import NodeAnalysis
from railway.core.dag.codegen import generate_exit_node_skeleton, generate_transition_code
from railway.core.dag.parser import ParseError, load_transition_graph, parse_transition_graph
from railway.core.dag.path_validator import PathIssue, PathValidationResult
from railway.core.dag.schema import validate_yaml_schema
from railway.core.dag.skeleton import (
    SkeletonSpec,
    compute_file_path,
    compute_skeleton_specs,
    filter_regular_nodes,
    generate_regular_node_content,
)
from railway.core.dag.types import NodeDefinition, TransitionGraph
from railway.core.dag.validator import validate_graph
from railway.migrations.yaml_converter import convert_yaml_structure

# =============================================================================
# Issue #44: Exit Node Skeleton Generation
# =============================================================================


# =============================================================================
# Issue #65: YAML Format Conversion
# =============================================================================


@dataclass(frozen=True)
class ConvertFileResult:
    """YAML変換結果（イミュータブル）。

    Attributes:
        converted: 変換が行われた（またはプレビュー成功）場合 True
        data: 変換後のデータ（変換成功時のみ）
    """

    converted: bool
    data: dict[str, Any] | None = None


def _convert_yaml_if_old_format(
    yaml_path: Path, *, dry_run: bool = False
) -> ConvertFileResult:
    """旧形式 YAML を新形式に変換（副作用あり）。

    変換後にスキーマ検証を行い、検証成功時のみファイルに書き込む。
    例外発生時は元の内容に復元する。

    フロー:
    1. 元の内容をバックアップ（read）
    2. 変換（純粋関数）
    3. スキーマ検証（純粋関数）
    4. ファイル書き込み（副作用 - 検証成功時のみ、dry_run=False の場合）

    Args:
        yaml_path: YAML ファイルパス
        dry_run: True の場合、変換結果をプレビューのみ（ファイル変更なし）

    Returns:
        ConvertFileResult: 変換結果（converted=True/False, data=変換後データ or None）
    """
    import yaml

    # 元の内容をバックアップ
    original_content = yaml_path.read_text()
    data = yaml.safe_load(original_content)

    if "exits" not in data:
        # 新形式だが、スキーマ検証が成功した場合のみメッセージ表示
        validation = validate_yaml_schema(data)
        if validation.is_valid:
            typer.echo(f"  既に新形式: {yaml_path.name}")
        return ConvertFileResult(converted=False)

    try:
        result = convert_yaml_structure(data)

        if not result.success:
            typer.echo(
                f"  警告: YAML 変換に失敗しました: {result.error}",
                err=True,
            )
            return ConvertFileResult(converted=False)

        # 変換結果のスキーマ検証（書き込み前に検証）
        assert result.data is not None  # success=True なら data は non-None
        validation = validate_yaml_schema(result.data)
        if not validation.is_valid:
            errors = ", ".join(validation.errors)
            typer.echo(
                f"  警告: 変換結果が無効なためロールバックしました: {errors}",
                err=True,
            )
            return ConvertFileResult(converted=False)

        # 検証成功
        if dry_run:
            typer.echo(
                f"  プレビュー: {yaml_path.name}（旧形式 → 新形式に変換可能）"
            )
            return ConvertFileResult(converted=True, data=result.data)

        # ファイルに書き込み
        new_content = yaml.safe_dump(
            result.data, allow_unicode=True, sort_keys=False
        )
        yaml_path.write_text(new_content)
        typer.echo(f"  変換: {yaml_path.name}（旧形式 → 新形式）")
        return ConvertFileResult(converted=True, data=result.data)

    except Exception as e:
        # 例外発生時は元の内容に復元
        yaml_path.write_text(original_content)
        typer.echo(
            f"  エラー: 変換中に例外が発生しました: {e}", err=True
        )
        return ConvertFileResult(converted=False)


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


# =============================================================================
# BUG-001: Regular Node Skeleton Generation
# =============================================================================


def _has_explicit_module(node_def: NodeDefinition, entrypoint: str) -> bool:
    """ノードが明示的な module 指定を持つかどうかを判定する（純粋関数）。

    デフォルトの module パス（nodes.{entrypoint}.{node_name}）と異なる場合、
    明示的に module が指定されていると判定する。

    Args:
        node_def: ノード定義
        entrypoint: エントリーポイント名

    Returns:
        明示的な module 指定がある場合 True
    """
    default_module = f"nodes.{entrypoint}.{node_def.name}"
    return node_def.module != default_module


def sync_regular_nodes(graph: TransitionGraph, project_root: Path) -> SyncResult:
    """未実装の通常ノードにスケルトンを生成（副作用あり）。

    純粋関数（skeleton.py）と副作用（ファイル操作）を分離:
    1. filter_regular_nodes: 通常ノードのフィルタ（純粋）
    2. compute_skeleton_specs: 仕様生成（純粋）
    3. compute_file_path: パス計算（純粋）
    4. generate_regular_node_content: コード生成（純粋）
    5. _write_skeleton_file: ファイル書き込み（副作用）

    Args:
        graph: 遷移グラフ
        project_root: プロジェクトルート

    Returns:
        SyncResult: 同期結果
    """
    src_dir = project_root / "src"

    generated: list[Path] = []
    skipped: list[Path] = []

    # Step 1: 明示 module ノードとデフォルトノードを分離
    explicit_module_nodes: list[NodeDefinition] = []
    default_node_names: list[str] = []
    for node_def in graph.nodes:
        if node_def.is_exit:
            continue
        if _has_explicit_module(node_def, graph.entrypoint):
            explicit_module_nodes.append(node_def)
        else:
            default_node_names.append(node_def.name)

    # Step 2: 明示 module ノード - module パスからファイルパスを直接計算
    for node_def in explicit_module_nodes:
        module_file_path = src_dir / (node_def.module.replace(".", "/") + ".py")
        if module_file_path.exists():
            skipped.append(module_file_path)
            continue
        explicit_spec = SkeletonSpec(
            node_name=node_def.name,
            module_path=node_def.module,
            entrypoint=graph.entrypoint,
            is_exit_node=False,
        )
        content = generate_regular_node_content(explicit_spec)
        _write_skeleton_file(module_file_path, content)
        generated.append(module_file_path)

    # Step 3: デフォルトノード - 既存ロジック
    regular_nodes = filter_regular_nodes(tuple(default_node_names))
    specs = compute_skeleton_specs(regular_nodes, graph.entrypoint)

    for spec in specs:
        file_path = compute_file_path(spec, src_dir)

        if file_path.exists():
            skipped.append(file_path)
            continue

        content = generate_regular_node_content(spec)
        _write_skeleton_file(file_path, content)
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
    entry: str | None = typer.Option(
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
        railway sync transition --entry entry2
        railway sync transition --all
        railway sync transition --entry entry2 --dry-run
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
    convert_result = ConvertFileResult(converted=False)
    if convert:
        convert_result = _convert_yaml_if_old_format(yaml_path, dry_run=dry_run)

    # Parse YAML (pure function via IO boundary)
    try:
        if dry_run and convert_result.converted and convert_result.data is not None:
            import yaml as yaml_mod

            yaml_str = yaml_mod.safe_dump(
                convert_result.data, allow_unicode=True, sort_keys=False
            )
            graph = parse_transition_graph(yaml_str)
        else:
            graph = load_transition_graph(yaml_path)
    except ParseError as e:
        raise SyncError(f"パースエラー:\n  {e}")

    # Validate graph (pure function)
    result = validate_graph(graph)
    if not result.is_valid:
        error_msgs = "\n  ".join(f"[{e.code}] {e.message}" for e in result.errors)
        raise SyncError(f"検証エラー:\n  {error_msgs}")

    # Show warnings
    for warning in result.warnings:
        typer.echo(f"  警告 [{warning.code}]: {warning.message}")

    # === Board Analysis Pipeline (v0.14.0) ===
    # Board 解析は読み取りのみ（副作用なし）なので dry-run/validate_only の前に実行。
    # これにより dry-run や validate_only でも Board モード判定とエラー検出の恩恵を受ける。
    src_dir = graphs_dir.parent / "src"
    board_analyses: dict[str, NodeAnalysis] = {}
    if src_dir.exists():
        board_analyses = _analyze_board_nodes(graph, src_dir)
        if board_analyses:
            entry_fields = _detect_entry_fields(graph, board_analyses)

            # Path validation
            from railway.core.dag.path_validator import validate_paths

            path_result = validate_paths(graph, board_analyses, entry_fields)

            # Display results
            _display_board_analysis_result(
                board_analyses, path_result, entry_fields
            )

            # Stop on errors (E010 path errors + E012-E015 node violations)
            if _has_analysis_errors(board_analyses, path_result):
                error_count = len(path_result.errors) + sum(
                    len(
                        [
                            v
                            for v in a.violations
                            if v.code in {"E012", "E013", "E014", "E015"}
                        ]
                    )
                    for a in board_analyses.values()
                )
                raise SyncError(
                    f"Board 解析で {error_count} 件のエラーが検出されました"
                )

    is_board_mode = bool(board_analyses)

    # === 早期 return ゾーン ===
    if validate_only:
        typer.echo(f"✓ {entry_name}: 検証成功")
        return

    if dry_run:
        # Generate code (pure function) for preview - Board モード反映済み
        relative_yaml = yaml_path.relative_to(graphs_dir.parent)
        code = generate_transition_code(
            graph, str(relative_yaml), board_mode=is_board_mode
        )
        typer.echo(f"\n--- プレビュー: {entry_name}_transitions.py ---")
        # Show first 50 lines
        lines = code.split("\n")[:50]
        typer.echo("\n".join(lines))
        if len(code.split("\n")) > 50:
            typer.echo("... (省略)")
        typer.echo("--- プレビュー終了 ---\n")
        return

    # === ファイル I/O ゾーン ===

    # Issue #62: 終端ノードスケルトン生成（副作用あり）
    cwd = graphs_dir.parent  # プロジェクトルート
    exit_result = sync_exit_nodes(graph, cwd)
    for path in exit_result.generated:
        typer.echo(f"  終端ノード生成: {path.relative_to(cwd)}")

    # BUG-001: 通常ノードスケルトン生成（副作用あり）
    regular_result = sync_regular_nodes(graph, cwd)
    for path in regular_result.generated:
        typer.echo(f"  通常ノード生成: {path.relative_to(cwd)}")

    # Generate code (pure function) - Board モード反映済み
    relative_yaml = yaml_path.relative_to(graphs_dir.parent)
    code = generate_transition_code(
        graph, str(relative_yaml), board_mode=is_board_mode
    )

    # Write generated code (IO operation)
    output_path = output_dir / f"{entry_name}_transitions.py"
    if output_path.exists() and no_overwrite:
        typer.echo(f"  スキップ: {output_path.name}（既に存在、--no-overwrite）")
        return

    output_path.write_text(code, encoding="utf-8")

    # py.typed マーカー生成（mypy 対応）
    py_typed_path = output_dir / "py.typed"
    if not py_typed_path.exists():
        py_typed_path.touch()

    typer.echo(f"✓ {entry_name}: 生成完了")
    typer.echo(f"  出力: _railway/generated/{entry_name}_transitions.py")


# =============================================================================
# Issue #24: Board Analysis Pipeline Integration
# =============================================================================


def _is_linear_mode_node(source_code: str) -> bool:
    """ソースコードが Linear/Contract モードのノードか判定する（純粋関数）。

    @node(output=...) または @node(inputs=...) が指定されていれば
    Linear mode として判定し、Board 解析をスキップする。

    Args:
        source_code: ノードのソースコード

    Returns:
        Linear mode の場合 True
    """
    import ast as _ast

    try:
        tree = _ast.parse(source_code)
    except SyntaxError:
        return False

    for node in _ast.walk(tree):
        if not isinstance(node, _ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            if isinstance(decorator, _ast.Call):
                func = decorator.func
                if isinstance(func, _ast.Name) and func.id == "node":
                    kw_names = {kw.arg for kw in decorator.keywords}
                    if "output" in kw_names or "inputs" in kw_names:
                        return True
    return False


def _analyze_board_nodes(
    graph: TransitionGraph,
    src_dir: Path,
) -> dict[str, NodeAnalysis]:
    """グラフのノードファイルを AST 解析する（副作用: ファイル読み込み）。

    Board mode ノードのみ解析する。以下はスキップ:
    - is_exit のノード
    - Linear mode ノード（@node(output=...) / @node(inputs=...)）
    - ファイルが存在しないノード

    Args:
        graph: 遷移グラフ
        src_dir: src ディレクトリパス

    Returns:
        ノード名 → NodeAnalysis のマッピング
    """
    from railway.core.dag.board_analyzer import analyze_node_file

    analyses: dict[str, NodeAnalysis] = {}
    for node_def in graph.nodes:
        if node_def.is_exit:
            continue
        # node の module からファイルパスを計算
        module_path = node_def.module.replace(".", "/") + ".py"
        file_path = src_dir / module_path
        if not file_path.exists():
            continue
        source_code = file_path.read_text()
        # Linear mode ノードはスキップ（Board 解析対象外）
        if _is_linear_mode_node(source_code):
            continue
        analysis = analyze_node_file(str(file_path), source_code, node_def.name)
        analyses[node_def.name] = analysis
    return analyses


def _detect_entry_fields(
    graph: TransitionGraph,
    analyses: dict[str, NodeAnalysis],
) -> frozenset[str]:
    """開始ノードの reads から entry_fields を抽出する（純粋関数）。

    Entry fields = start node の reads（required + optional）。
    これはワークフロー実行時に呼び出し元が提供すべきフィールド。

    Args:
        graph: 遷移グラフ
        analyses: ノード名 → NodeAnalysis のマッピング

    Returns:
        entry_fields の frozenset
    """
    start_analysis = analyses.get(graph.start_node)
    if start_analysis is None:
        return frozenset()
    return start_analysis.reads_all


def _has_analysis_errors(
    board_analyses: dict[str, NodeAnalysis],
    path_result: PathValidationResult,
) -> bool:
    """Board 解析結果にエラーレベルの問題があるか判定する（純粋関数）。

    E010（経路依存エラー）と E012〜E015（ノード解析違反）を統合的に判定。

    Args:
        board_analyses: ノード名 → NodeAnalysis のマッピング
        path_result: 経路検証結果

    Returns:
        エラーレベルの問題がある場合 True
    """
    # E010: 経路依存エラー
    if path_result.has_errors:
        return True
    # E012-E015: ノード解析の違反
    error_codes = {"E012", "E013", "E014", "E015"}
    for analysis in board_analyses.values():
        if any(v.code in error_codes for v in analysis.violations):
            return True
    return False


def _display_board_analysis_result(
    analyses: dict[str, NodeAnalysis],
    path_result: PathValidationResult,
    entry_fields: frozenset[str],
) -> None:
    """Board 解析結果を表示する（副作用: typer.echo）。

    Args:
        analyses: ノード名 → NodeAnalysis のマッピング
        path_result: 経路検証結果
        entry_fields: エントリーポイントのフィールド
    """
    # Analysis summary
    typer.echo(f"  Board解析: {len(analyses)} ノード解析済み")
    if entry_fields:
        typer.echo(f"  entry_fields: {', '.join(sorted(entry_fields))}")

    # Violations
    for name, analysis in sorted(analyses.items()):
        for v in analysis.violations:
            typer.echo(
                f"  [{v.code}] {v.file_path}:{v.line} {v.message}", err=True
            )

    # Path issues
    for issue in path_result.errors:
        typer.echo(f"  [{issue.code}] {issue.message}", err=True)
    for issue in path_result.warnings:
        typer.echo(f"  [{issue.code}] {issue.message}")
    for issue in path_result.infos:
        typer.echo(f"  [{issue.code}] {issue.message}")


def _format_analysis_summary(analysis: NodeAnalysis) -> str:
    """ノード解析のサマリーをフォーマットする（純粋関数）。

    Args:
        analysis: ノード解析結果

    Returns:
        フォーマット済み文字列
    """
    parts: list[str] = [f"  {analysis.node_name}:"]

    if analysis.reads_required:
        parts.append(
            f"    reads: {', '.join(sorted(analysis.reads_required))}"
        )
    if analysis.reads_optional:
        parts.append(
            f"    reads(optional): {', '.join(sorted(analysis.reads_optional))}"
        )
    if analysis.all_writes:
        parts.append(
            f"    writes: {', '.join(sorted(analysis.all_writes))}"
        )

    for bw in analysis.branch_writes:
        if bw.writes:
            parts.append(
                f"    [{bw.outcome}]: writes {', '.join(sorted(bw.writes))}"
            )

    return "\n".join(parts)


def _format_path_issue(issue: PathIssue) -> str:
    """PathIssue をフォーマットする（純粋関数）。

    Args:
        issue: 経路検証の問題

    Returns:
        フォーマット済み文字列
    """
    severity_mark = {"error": "\u2717", "warning": "\u26a0", "info": "\u2139"}.get(
        issue.severity, "?"
    )
    return f"  {severity_mark} [{issue.code}] {issue.message}"


def _matches_entry_yaml(filename: str, entry_name: str) -> bool:
    """エントリ名に正確にマッチするYAMLファイル名か判定（純粋関数）。

    ファイル名は {entry_name}_{数値}.yml の形式でなければならない。
    プレフィックス部分一致（例: "qsol" が "qsol_hoge_*.yml" にマッチ）を防止する。

    Args:
        filename: ファイル名
        entry_name: エントリポイント名

    Returns:
        マッチする場合 True
    """
    pattern = re.compile(rf"^{re.escape(entry_name)}_(\d+)\.yml$")
    return pattern.match(filename) is not None


def find_latest_yaml(graphs_dir: Path, entry_name: str) -> Path | None:
    """
    Find the latest YAML file for an entrypoint.

    Files are expected to be named: {entry_name}_{timestamp}.yml
    Returns the one with the latest timestamp (numeric sort).

    Args:
        graphs_dir: Directory containing YAML files
        entry_name: Entrypoint name

    Returns:
        Path to latest YAML, or None if not found
    """
    pattern = re.compile(rf"^{re.escape(entry_name)}_(\d+)\.yml$")
    matches: list[tuple[int, Path]] = []

    for p in graphs_dir.glob("*.yml"):
        m = pattern.match(p.name)
        if m:
            matches.append((int(m.group(1)), p))

    if not matches:
        return None

    # Sort by numeric suffix descending
    matches.sort(key=lambda x: x[0], reverse=True)
    return matches[0][1]


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
