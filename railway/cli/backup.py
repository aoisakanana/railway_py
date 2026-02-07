"""railway backup コマンド。

バックアップの一覧表示、復元、クリーンアップを提供する。
"""

import typer

from railway.core.project_discovery import find_project_root
from railway.migrations.backup import (
    clean_backups,
    list_backups,
    restore_backup,
)

app = typer.Typer(help="バックアップ管理コマンド")


@app.command(name="list")
def list_cmd(
    verbose: bool = typer.Option(False, "-v", "--verbose", help="詳細表示"),
) -> None:
    """バックアップ一覧を表示する。"""
    project_path = find_project_root()
    if project_path is None:
        typer.echo("❌ Railwayプロジェクトが見つかりません", err=True)
        raise typer.Exit(1)

    backups = list_backups(project_path)

    if not backups:
        typer.echo("バックアップはありません")
        raise typer.Exit(0)

    typer.echo(f"\n📦 バックアップ一覧 ({len(backups)}件)\n")

    for i, backup in enumerate(backups, 1):
        created = backup.created_at.strftime("%Y-%m-%d %H:%M:%S")
        size_kb = backup.size_bytes / 1024

        typer.echo(f"  {i}. {backup.name}")
        typer.echo(f"     バージョン: {backup.version}")
        typer.echo(f"     作成日時:   {created}")
        typer.echo(f"     理由:       {backup.reason}")

        if verbose:
            typer.echo(f"     サイズ:     {size_kb:.1f} KB")
            typer.echo(f"     ファイル数: {backup.manifest.file_count}")
            typer.echo(f"     パス:       {backup.path}")

        typer.echo("")


@app.command()
def restore(
    backup_name: str | None = typer.Argument(
        None,
        help="復元するバックアップ名（省略時は最新）",
    ),
    force: bool = typer.Option(False, "-f", "--force", help="確認なしで復元"),
) -> None:
    """バックアップから復元する。"""
    project_path = find_project_root()
    if project_path is None:
        typer.echo("❌ Railwayプロジェクトが見つかりません", err=True)
        raise typer.Exit(1)

    backups = list_backups(project_path)

    if not backups:
        typer.echo("❌ バックアップがありません", err=True)
        raise typer.Exit(1)

    # バックアップを選択
    if backup_name is None:
        backup = backups[0]
        typer.echo(f"📦 最新のバックアップを使用: {backup.name}")
    else:
        matching = [b for b in backups if b.name == backup_name]
        if not matching:
            typer.echo(f"❌ バックアップが見つかりません: {backup_name}", err=True)
            typer.echo("\n利用可能なバックアップ:")
            for b in backups:
                typer.echo(f"  - {b.name}")
            raise typer.Exit(1)
        backup = matching[0]

    # 復元内容を表示
    typer.echo("\n🔄 復元内容:")
    typer.echo(f"   バージョン: {backup.version}")
    typer.echo(f"   作成日時:   {backup.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    typer.echo(f"   ファイル数: {backup.manifest.file_count}")

    if backup.manifest.files:
        typer.echo("\n   ファイル:")
        for f in backup.manifest.files:
            typer.echo(f"     - {f.path}")

    # 確認
    if not force:
        typer.echo("\n⚠️  現在のファイルが上書きされます")
        if not typer.confirm("復元しますか?"):
            typer.echo("中止しました")
            raise typer.Exit(0)

    # 復元実行
    result = restore_backup(project_path, backup)

    if result.success:
        typer.echo("\n✅ 復元完了")
        typer.echo(f"   復元ファイル数: {len(result.restored_files)}")
    else:
        typer.echo(f"\n❌ 復元に失敗しました: {result.error}", err=True)
        raise typer.Exit(1)


@app.command()
def clean(
    keep: int = typer.Option(5, "--keep", "-k", help="保持するバックアップ数"),
    force: bool = typer.Option(False, "-f", "--force", help="確認なしで削除"),
) -> None:
    """古いバックアップを削除する。"""
    project_path = find_project_root()
    if project_path is None:
        typer.echo("❌ Railwayプロジェクトが見つかりません", err=True)
        raise typer.Exit(1)

    backups = list_backups(project_path)

    if len(backups) <= keep:
        typer.echo(f"✅ 削除対象のバックアップはありません（現在: {len(backups)}件）")
        raise typer.Exit(0)

    to_remove = backups[keep:]
    typer.echo(f"\n🗑️  削除対象 ({len(to_remove)}件):")
    for backup in to_remove:
        typer.echo(f"   - {backup.name}")

    if not force:
        if not typer.confirm("\nこれらのバックアップを削除しますか?"):
            typer.echo("中止しました")
            raise typer.Exit(0)

    removed_count, removed_names = clean_backups(project_path, keep)

    typer.echo(f"\n✅ {removed_count}件のバックアップを削除しました")
