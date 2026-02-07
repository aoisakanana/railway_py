"""プレビュー生成機能。

関数型パラダイム:
- プレビュー生成は純粋関数
- IOは別レイヤーで分離
"""
from collections.abc import Sequence
from pathlib import Path

from railway.migrations.changes import (
    ChangeType as MigChangeType,
)
from railway.migrations.changes import (
    ConfigChange,
    FileChange,
    MigrationDefinition,
)
from railway.migrations.preview_types import (
    ChangePreview,
    MigrationPreview,
    PreviewChangeType,
)


def preview_file_change(
    change: FileChange,
    project_path: Path,
) -> ChangePreview:
    """ファイル変更のプレビューを生成する。

    Args:
        change: ファイル変更定義
        project_path: プロジェクトパス

    Returns:
        ChangePreview
    """
    match change.change_type:
        case MigChangeType.FILE_CREATE:
            content_size = len(change.content or "")
            return ChangePreview(
                change_type=PreviewChangeType.ADD,
                path=change.path,
                description="新規ファイル作成",
                details=(f"サイズ: {content_size} bytes",),
            )

        case MigChangeType.FILE_DELETE:
            return ChangePreview(
                change_type=PreviewChangeType.DELETE,
                path=change.path,
                description="ファイル削除",
            )

        case MigChangeType.FILE_UPDATE:
            file_path = project_path / change.path
            if not file_path.exists():
                return ChangePreview(
                    change_type=PreviewChangeType.ADD,
                    path=change.path,
                    description="テンプレートから生成",
                )

            return ChangePreview(
                change_type=PreviewChangeType.UPDATE,
                path=change.path,
                description="テンプレート更新",
            )

        case _:
            return ChangePreview(
                change_type=PreviewChangeType.UPDATE,
                path=change.path,
                description=change.description,
            )


def preview_config_change(change: ConfigChange) -> ChangePreview:
    """設定変更のプレビューを生成する純粋関数。

    Args:
        change: 設定変更定義

    Returns:
        ChangePreview
    """
    details: list[str] = []

    for key in change.additions:
        details.append(f"新規キー: {key}")

    for old, new in change.renames.items():
        details.append(f"キー名変更: {old} → {new}")

    for key in change.deletions:
        details.append(f"キー削除: {key}")

    return ChangePreview(
        change_type=PreviewChangeType.UPDATE,
        path=change.path,
        description="設定ファイル更新",
        details=tuple(details),
    )


def generate_migration_preview(
    migrations: Sequence[MigrationDefinition],
    project_path: Path,
) -> MigrationPreview:
    """マイグレーションのプレビューを生成する。

    Args:
        migrations: マイグレーション定義のシーケンス
        project_path: プロジェクトパス

    Returns:
        MigrationPreview
    """
    if not migrations:
        return MigrationPreview(
            from_version="",
            to_version="",
            changes=(),
        )

    changes: list[ChangePreview] = []
    warnings: list[str] = []

    for migration in migrations:
        # ファイル変更
        for fc in migration.file_changes:
            changes.append(preview_file_change(fc, project_path))

        # 設定変更
        for cc in migration.config_changes:
            changes.append(preview_config_change(cc))

        # 警告
        warnings.extend(migration.warnings)

    return MigrationPreview(
        from_version=migrations[0].from_version,
        to_version=migrations[-1].to_version,
        changes=tuple(changes),
        warnings=tuple(warnings),
    )
