"""railway update コマンド。

関数型パラダイム:
- コマンドはIO/UIの統合層
- ロジックは executor/registry モジュールに分離
"""
import typer

from railway import __version__
from railway.core.project_discovery import find_project_root
from railway.core.project_metadata import load_metadata
from railway.migrations.registry import calculate_migration_path
from railway.migrations.executor import (
    execute_migration_plan,
    initialize_project,
)


app = typer.Typer(help="プロジェクト更新コマンド")


@app.callback(invoke_without_command=True)
def update(
    dry_run: bool = typer.Option(False, "--dry-run", help="プレビューのみ"),
    init: bool = typer.Option(False, "--init", help="バージョン情報を初期化"),
    force: bool = typer.Option(False, "--force", "-f", help="確認なしで実行"),
    no_backup: bool = typer.Option(False, "--no-backup", help="バックアップを作成しない"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="詳細出力"),
) -> None:
    """プロジェクトを最新バージョンに更新する。"""
    project_path = find_project_root()
    if project_path is None:
        typer.echo("❌ Railwayプロジェクトが見つかりません", err=True)
        raise typer.Exit(1)

    metadata = load_metadata(project_path)

    # --init: バージョン情報がない場合に初期化
    if init:
        if metadata is not None:
            typer.echo("ℹ️  このプロジェクトにはすでにバージョン情報があります")
            raise typer.Exit(0)

        result = initialize_project(project_path)
        if result.success:
            typer.echo(f"✅ バージョン情報を初期化しました: {__version__}")
        else:
            typer.echo(f"❌ 初期化に失敗しました: {result.error}", err=True)
            raise typer.Exit(1)
        raise typer.Exit(0)

    # バージョン情報がない場合
    if metadata is None:
        typer.echo(
            "⚠️  このプロジェクトにはバージョン情報がありません。\n"
            "   'railway update --init' で初期化してください。"
        )
        raise typer.Exit(1)

    from_version = metadata.railway.version

    # 既に最新の場合
    if from_version == __version__:
        typer.echo(f"✅ プロジェクトは最新です (v{__version__})")
        raise typer.Exit(0)

    # マイグレーション計画を計算
    try:
        plan = calculate_migration_path(from_version, __version__)
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1)

    # プレビュー表示
    typer.echo(f"\n🔍 プロジェクトを分析中...\n")
    typer.echo(f"   プロジェクト名:      {metadata.project.name}")
    typer.echo(f"   現在のバージョン:    {from_version}")
    typer.echo(f"   ターゲットバージョン: {__version__}\n")

    if plan.is_empty:
        typer.echo("📋 適用される変更はありません\n")
        # メタデータのみ更新
        if not dry_run:
            from railway.core.project_metadata import update_metadata_version, save_metadata
            updated = update_metadata_version(metadata, __version__)
            save_metadata(project_path, updated)
            typer.echo(f"✅ バージョン情報を更新しました: {__version__}")
        raise typer.Exit(0)

    typer.echo("📋 適用される変更:\n")
    for m in plan.migrations:
        typer.echo(f"   {m.from_version} → {m.to_version}: {m.description}")
        if verbose:
            for change in m.file_changes:
                typer.echo(f"      - {change.path}: {change.description}")
            for change in m.config_changes:
                typer.echo(f"      - {change.path}: {change.description}")

    if dry_run:
        typer.echo("\n[dry-run] 実際の変更は行われません")
        raise typer.Exit(0)

    # 確認
    if not force:
        if not typer.confirm("\n続行しますか?"):
            typer.echo("中止しました")
            raise typer.Exit(0)

    # マイグレーション実行
    def progress_callback(message: str) -> None:
        typer.echo(message)

    result = execute_migration_plan(
        project_path,
        plan,
        create_backup_flag=not no_backup,
        on_progress=progress_callback,
    )

    if result.success:
        typer.echo(f"\n✅ 更新完了")
        if result.backup_path:
            typer.echo(f"   バックアップ: {result.backup_path}")
        typer.echo(f"   新バージョン: {result.to_version}")
    else:
        typer.echo(f"\n❌ 更新に失敗しました: {result.error}", err=True)
        if result.backup_path:
            typer.echo(f"   バックアップから復元できます: {result.backup_path}")
        raise typer.Exit(1)
