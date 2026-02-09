"""マイグレーション実行。

関数型パラダイム:
- ロジック（計画生成）と実行（IO）を分離
- 実行結果はイミュータブルなResultで返す

Note:
    変更定義型は railway/migrations/changes.py からインポート。
"""
import glob as glob_module
from collections.abc import Callable
from pathlib import Path

import yaml

from railway import __version__
from railway.core.project_metadata import (
    create_metadata,
    load_metadata,
    save_metadata,
    update_metadata_version,
)
from railway.migrations.backup import create_backup
from railway.migrations.changes import (
    ChangeType,
    ConfigChange,
    FileChange,
    InteractiveMode,
    MigrationDefinition,
    YamlTransform,
    should_confirm_change,
)
from railway.migrations.config_merger import merge_config
from railway.migrations.types import ConfirmCallback, MigrationPlan, MigrationResult

# ============================================================
# ファイル変更アクション（IO）
# ============================================================

def apply_file_change(
    project_path: Path,
    change: FileChange,
    *,
    on_confirm: ConfirmCallback | None = None,
    mode: InteractiveMode = "auto",
) -> bool:
    """ファイル変更を適用する。

    Args:
        project_path: プロジェクトルートパス
        change: 適用するファイル変更
        on_confirm: ユーザー確認コールバック（省略時は確認なし）
        mode: インタラクティブモード（"auto", "interactive", "lazy"）

    Returns:
        True if applied, False if skipped

    Raises:
        IOError: ファイル操作失敗時
    """
    if should_confirm_change(change.path, mode) and on_confirm is not None:
        if not on_confirm(change.path, change.description):
            return False

    file_path = project_path / change.path

    match change.change_type:
        case ChangeType.FILE_CREATE:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if not file_path.exists():
                file_path.write_text(change.content or "", encoding="utf-8")

        case ChangeType.FILE_DELETE:
            if file_path.exists():
                file_path.unlink()

        case ChangeType.FILE_UPDATE:
            # テンプレートから再生成（簡略化版）
            # TODO: 実際のテンプレートレンダリング実装
            if change.content:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(change.content, encoding="utf-8")

    return True


def apply_config_change(project_path: Path, change: ConfigChange) -> None:
    """設定変更を適用する。

    Args:
        project_path: プロジェクトルートパス
        change: 適用する設定変更
    """
    config_path = project_path / change.path
    if not config_path.exists():
        return

    with open(config_path, encoding="utf-8") as f:
        original = yaml.safe_load(f) or {}

    result, _ = merge_config(original, change)

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(result, f, default_flow_style=False, allow_unicode=True)


def apply_yaml_transform(project_path: Path, transform: YamlTransform) -> None:
    """YAML 変換を適用する。

    glob パターンにマッチするファイルに対して変換関数を実行する。

    Args:
        project_path: プロジェクトルートパス
        transform: 適用する YAML 変換定義
    """
    pattern = str(project_path / transform.pattern)
    for file_path_str in glob_module.glob(pattern, recursive=True):
        file_path = Path(file_path_str)
        if not file_path.is_file():
            continue

        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None:
            continue

        result = transform.transform(data)
        # ConversionResult または dict を処理
        converted = result.data if hasattr(result, "data") else result

        if converted != data and converted is not None:
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    converted,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )


def apply_migration(
    project_path: Path,
    migration: MigrationDefinition,
    *,
    on_confirm: ConfirmCallback | None = None,
    mode: InteractiveMode = "auto",
) -> None:
    """マイグレーションを適用する。

    Args:
        project_path: プロジェクトルートパス
        migration: 適用するマイグレーション定義
        on_confirm: ユーザー確認コールバック（省略時は確認なし）
        mode: インタラクティブモード
    """
    # ファイル変更を適用
    for change in migration.file_changes:
        apply_file_change(project_path, change, on_confirm=on_confirm, mode=mode)

    # 設定変更を適用
    for config_change in migration.config_changes:
        apply_config_change(project_path, config_change)

    # YAML 変換を適用
    for transform in migration.yaml_transforms:
        apply_yaml_transform(project_path, transform)


# ============================================================
# 高レベル実行関数
# ============================================================

def execute_migration_plan(
    project_path: Path,
    plan: MigrationPlan,
    create_backup_flag: bool = True,
    on_progress: Callable[[str], None] | None = None,
    on_confirm: ConfirmCallback | None = None,
    mode: InteractiveMode = "auto",
) -> MigrationResult:
    """マイグレーション計画を実行する。

    Args:
        project_path: プロジェクトルートパス
        plan: 実行するマイグレーション計画
        create_backup_flag: バックアップを作成するか
        on_progress: 進捗コールバック
        on_confirm: ユーザー確認コールバック（省略時は確認なし）
        mode: インタラクティブモード

    Returns:
        MigrationResult with success status and details
    """
    if plan.is_empty:
        return MigrationResult(
            success=True,
            from_version=plan.from_version,
            to_version=plan.to_version,
        )

    backup_path: Path | None = None
    current_version = plan.from_version

    try:
        # バックアップ作成
        if create_backup_flag:
            backup_path = create_backup(project_path, plan.from_version)
            if on_progress:
                on_progress(f"💾 バックアップ作成: {backup_path}")

        # マイグレーション実行
        for migration in plan.migrations:
            if on_progress:
                on_progress(f"⏳ {migration.description}...")

            apply_migration(
                project_path, migration, on_confirm=on_confirm, mode=mode,
            )
            current_version = migration.to_version

        # メタデータ更新
        metadata = load_metadata(project_path)
        if metadata:
            updated = update_metadata_version(metadata, plan.to_version)
            save_metadata(project_path, updated)

        return MigrationResult(
            success=True,
            from_version=plan.from_version,
            to_version=plan.to_version,
            backup_path=backup_path,
        )

    except Exception as e:
        return MigrationResult(
            success=False,
            from_version=plan.from_version,
            to_version=current_version,
            backup_path=backup_path,
            error=str(e),
        )


def initialize_project(project_path: Path) -> MigrationResult:
    """バージョン情報のないプロジェクトを初期化する。

    Args:
        project_path: プロジェクトルートパス

    Returns:
        MigrationResult
    """
    try:
        # プロジェクト名を推定
        project_name = project_path.name

        metadata = create_metadata(project_name, __version__)
        save_metadata(project_path, metadata)

        return MigrationResult(
            success=True,
            from_version="unknown",
            to_version=__version__,
        )
    except Exception as e:
        return MigrationResult(
            success=False,
            from_version="unknown",
            to_version="unknown",
            error=str(e),
        )
