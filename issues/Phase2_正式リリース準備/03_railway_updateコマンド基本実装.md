# Issue #03: railway update コマンド基本実装

## 概要

プロジェクトを最新の railway-framework バージョンにマイグレーションする `railway update` コマンドを実装する。

## 現状

```bash
$ pip install --upgrade railway-framework
# バージョン 0.7.0 → 0.9.0

$ cd my_project
$ railway new node fetch_data
# 問題: プロジェクトは 0.7.0 形式、テンプレートは 0.9.0 形式
# 手動でマイグレーションするしかない
```

## 目標

```bash
$ railway update

🔍 プロジェクトを分析中...

   プロジェクト名:     my_project
   現在のバージョン:   0.7.0
   ターゲットバージョン: 0.9.0

📋 適用される変更:

   [ファイル追加]
   + src/py.typed

   [ファイル更新]
   ~ TUTORIAL.md (Step 8 追加)
   ~ config/development.yaml (新形式)

   [変更なし]
   - src/nodes/* (ユーザーコードは変更しない)
   - tests/* (ユーザーコードは変更しない)

続行しますか? [y/N]: y

✅ 更新完了
   バックアップ: .railway/backups/0.7.0_20260123_103000/
   新バージョン: 0.9.0
```

## 設計

### コマンド構造

```bash
railway update [OPTIONS]

Options:
  --dry-run      変更をプレビューのみ（実行しない）
  --init         バージョン情報のないプロジェクトに .railway/project.yaml を追加
  --force        確認なしで実行
  --no-backup    バックアップを作成しない
  -v, --verbose  詳細出力
```

### 更新対象の分類

| カテゴリ | 対象 | 動作 |
|----------|------|------|
| フレームワークファイル | py.typed, TUTORIAL.md | 上書き更新 |
| 設定ファイル | config/*.yaml | マージ更新 |
| テンプレートファイル | .gitignore, pyproject.toml | マージ更新 |
| ユーザーコード | src/nodes/*, tests/* | **変更しない** |

## 設計原則

### 関数型パラダイム準拠

1. **イミュータブルなマイグレーション定義**: frozen dataclass で定義
2. **純粋関数によるパス計算**: マイグレーションパスの計算は純粋関数
3. **副作用の明示的分離**: 実際のファイル操作はIO層で明示的に分離
4. **Result型パターン**: 成功/失敗を明示的に表現

## 実装

### 1. マイグレーション定義（イミュータブル）

**注**: 詳細な変更定義型（`FileChange`, `ConfigChange`, `CodeGuidance`）は **#04 マイグレーション戦略設計** で定義。
本issueでは実行に必要な最小限の型のみ定義。

```python
# railway/migrations/types.py
"""マイグレーション実行に必要な基本型定義。

関数型パラダイム:
- 全てのデータ型はイミュータブル (frozen=True)
- 副作用のない値としてマイグレーションを表現

Note:
    詳細な変更定義（FileChange, ConfigChange, CodeGuidance）は
    railway/migrations/changes.py で定義される。
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from railway.migrations.changes import MigrationDefinition


@dataclass(frozen=True)
class MigrationPlan:
    """マイグレーション計画（イミュータブル）。

    Attributes:
        from_version: 元のバージョン
        to_version: 移行先バージョン
        migrations: 適用するマイグレーション定義のシーケンス
    """
    from_version: str
    to_version: str
    migrations: tuple["MigrationDefinition", ...]

    @property
    def is_empty(self) -> bool:
        """マイグレーションが不要かどうか。"""
        return len(self.migrations) == 0

    @property
    def total_changes(self) -> int:
        """変更の総数。"""
        return sum(m.total_changes for m in self.migrations)


@dataclass(frozen=True)
class MigrationResult:
    """マイグレーション実行結果（イミュータブル）。

    Attributes:
        success: 成功したかどうか
        from_version: 元のバージョン
        to_version: 移行先バージョン（成功時）または最後に成功したバージョン
        backup_path: バックアップパス（作成した場合）
        error: エラーメッセージ（失敗時）
    """
    success: bool
    from_version: str
    to_version: str
    backup_path: Optional[Path] = None
    error: Optional[str] = None
```

### 2. マイグレーションレジストリ（純粋関数）

```python
# railway/migrations/registry.py
"""マイグレーションレジストリ。

関数型パラダイム:
- レジストリは不変のタプルとして定義
- パス計算は純粋関数

Note:
    MigrationDefinition は railway/migrations/changes.py で定義。
    実際のマイグレーション定義は railway/migrations/definitions/ 以下に配置。
"""
from typing import Optional

from packaging.version import Version

from railway.migrations.types import MigrationPlan
from railway.migrations.changes import MigrationDefinition, FileChange, ConfigChange


# ============================================================
# マイグレーション定義（不変）
# 実際のプロジェクトでは definitions/ ディレクトリから動的にロード
# ============================================================

MIGRATIONS: tuple[MigrationDefinition, ...] = (
    MigrationDefinition(
        from_version="0.7.0",
        to_version="0.8.0",
        description="設定ファイル形式の更新",
        config_changes=(
            ConfigChange(
                path="config/development.yaml",
                additions={"logging": {"level": "DEBUG"}},
            ),
        ),
    ),
    MigrationDefinition(
        from_version="0.8.0",
        to_version="0.9.0",
        description="py.typed追加、TUTORIAL更新",
        file_changes=(
            FileChange.create(
                path="src/py.typed",
                content="",
                description="型チェック用マーカーファイル",
            ),
            FileChange.update(
                path="TUTORIAL.md",
                template="tutorial.md.j2",
                description="Step 8 セクション追加",
            ),
        ),
    ),
)


# ============================================================
# 純粋関数: マイグレーションパス計算
# ============================================================

def find_migration(from_ver: str, to_ver: str) -> Optional[MigrationDefinition]:
    """指定されたバージョン間の直接マイグレーションを探す純粋関数。

    Args:
        from_ver: 元のバージョン
        to_ver: 移行先バージョン

    Returns:
        MigrationDefinition if found, None otherwise
    """
    for migration in MIGRATIONS:
        if migration.from_version == from_ver and migration.to_version == to_ver:
            return migration
    return None


def find_next_migration(from_ver: str, target_ver: str) -> Optional[MigrationDefinition]:
    """次のマイグレーションステップを探す純粋関数。

    Args:
        from_ver: 現在のバージョン
        target_ver: 最終目標バージョン

    Returns:
        次のMigrationDefinition、または見つからない場合None
    """
    from_v = Version(from_ver)
    target_v = Version(target_ver)

    candidates = [
        m for m in MIGRATIONS
        if m.from_version == from_ver
        and Version(m.to_version) <= target_v
    ]

    if not candidates:
        return None

    # 最も大きなバージョンジャンプを優先
    return max(candidates, key=lambda m: Version(m.to_version))


def calculate_migration_path(from_ver: str, to_ver: str) -> MigrationPlan:
    """マイグレーションパスを計算する純粋関数。

    Args:
        from_ver: 元のバージョン
        to_ver: 移行先バージョン

    Returns:
        MigrationPlan with ordered migrations

    Raises:
        ValueError: パスが見つからない場合
    """
    from_v = Version(from_ver)
    to_v = Version(to_ver)

    # 同じバージョンまたはダウングレード
    if from_v >= to_v:
        return MigrationPlan(
            from_version=from_ver,
            to_version=to_ver,
            migrations=(),
        )

    # パスを構築
    path: list[MigrationDefinition] = []
    current = from_ver

    while Version(current) < to_v:
        next_migration = find_next_migration(current, to_ver)
        if next_migration is None:
            raise ValueError(
                f"{current} から {to_ver} へのマイグレーションパスが見つかりません"
            )
        path.append(next_migration)
        current = next_migration.to_version

    return MigrationPlan(
        from_version=from_ver,
        to_version=to_ver,
        migrations=tuple(path),
    )


def normalize_version(version: str) -> str:
    """バージョン文字列を正規化する純粋関数。

    Args:
        version: バージョン文字列

    Returns:
        MAJOR.MINOR.0 形式に正規化されたバージョン

    Examples:
        >>> normalize_version("0.9.5")
        "0.9.0"
        >>> normalize_version("1.2.3")
        "1.2.0"
    """
    v = Version(version)
    return f"{v.major}.{v.minor}.0"
```

### 3. マイグレーション実行（IO分離）

```python
# railway/migrations/executor.py
"""マイグレーション実行。

関数型パラダイム:
- ロジック（計画生成）と実行（IO）を分離
- 実行結果はイミュータブルなResultで返す

Note:
    変更定義型は railway/migrations/changes.py からインポート。
"""
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import yaml

from railway import __version__
from railway.core.project_discovery import find_project_root
from railway.core.project_metadata import (
    load_metadata,
    save_metadata,
    create_metadata,
    update_metadata_version,
)
from railway.migrations.backup import create_backup
from railway.migrations.registry import calculate_migration_path, normalize_version
from railway.migrations.types import MigrationPlan, MigrationResult
from railway.migrations.changes import (
    MigrationDefinition,
    FileChange,
    ConfigChange,
    ChangeType,
)
from railway.migrations.config_merger import merge_config


# ============================================================
# ファイル変更アクション（IO）
# ============================================================

def apply_file_change(project_path: Path, change: FileChange) -> None:
    """ファイル変更を適用する。

    Args:
        project_path: プロジェクトルートパス
        change: 適用するファイル変更

    Raises:
        IOError: ファイル操作失敗時
    """
    file_path = project_path / change.path

    match change.change_type:
        case ChangeType.FILE_CREATE:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(change.content or "", encoding="utf-8")

        case ChangeType.FILE_DELETE:
            if file_path.exists():
                file_path.unlink()

        case ChangeType.FILE_UPDATE:
            # テンプレートから再生成
            if change.template:
                content = render_template(change.template, project_path)
                file_path.write_text(content, encoding="utf-8")


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


def apply_migration(project_path: Path, migration: MigrationDefinition) -> None:
    """マイグレーションを適用する。

    Args:
        project_path: プロジェクトルートパス
        migration: 適用するマイグレーション定義
    """
    # ファイル変更を適用
    for change in migration.file_changes:
        apply_file_change(project_path, change)

    # 設定変更を適用
    for change in migration.config_changes:
        apply_config_change(project_path, change)


# ============================================================
# 高レベル実行関数
# ============================================================

def execute_migration_plan(
    project_path: Path,
    plan: MigrationPlan,
    create_backup_flag: bool = True,
    on_progress: Optional[Callable[[str], None]] = None,
) -> MigrationResult:
    """マイグレーション計画を実行する。

    Args:
        project_path: プロジェクトルートパス
        plan: 実行するマイグレーション計画
        create_backup_flag: バックアップを作成するか
        on_progress: 進捗コールバック

    Returns:
        MigrationResult with success status and details
    """
    if plan.is_empty:
        return MigrationResult(
            success=True,
            from_version=plan.from_version,
            to_version=plan.to_version,
        )

    backup_path: Optional[Path] = None
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

            apply_migration(project_path, migration)
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
```

### 4. update コマンド（CLI層）

```python
# railway/cli/update.py
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


app = typer.Typer()


@app.callback(invoke_without_command=True)
def update(
    dry_run: bool = typer.Option(False, "--dry-run", help="プレビューのみ"),
    init: bool = typer.Option(False, "--init", help="バージョン情報を初期化"),
    force: bool = typer.Option(False, "--force", "-f", help="確認なしで実行"),
    no_backup: bool = typer.Option(False, "--no-backup", help="バックアップを作成しない"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="詳細出力"),
):
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
```

## テスト（TDD: Red → Green → Refactor）

### テストファイル構成

```
tests/unit/migrations/
├── test_types.py
├── test_registry.py
└── test_executor.py
tests/unit/cli/
└── test_update_command.py
```

### Red Phase: テストを先に書く

```python
# tests/unit/migrations/test_registry.py
"""マイグレーションレジストリのテスト。

TDD Red Phase: まずテストを書き、失敗を確認する。
"""
import pytest
from packaging.version import Version

from railway.migrations.types import MigrationPlan
from railway.migrations.changes import MigrationDefinition
from railway.migrations.registry import (
    find_migration,
    find_next_migration,
    calculate_migration_path,
    normalize_version,
)


class TestNormalizeVersion:
    """バージョン正規化のテスト。"""

    def test_patch_version_is_zeroed(self):
        """パッチバージョンが0になる。"""
        assert normalize_version("0.9.5") == "0.9.0"

    def test_major_minor_preserved(self):
        """メジャー・マイナーは保持される。"""
        assert normalize_version("1.2.3") == "1.2.0"

    def test_already_normalized(self):
        """既に正規化済みの場合は変わらない。"""
        assert normalize_version("0.9.0") == "0.9.0"


class TestFindMigration:
    """直接マイグレーション検索のテスト。"""

    def test_find_existing_migration(self):
        """存在するマイグレーションを見つける。"""
        migration = find_migration("0.8.0", "0.9.0")
        assert migration is not None
        assert migration.from_version == "0.8.0"
        assert migration.to_version == "0.9.0"

    def test_find_nonexistent_migration_returns_none(self):
        """存在しないマイグレーションはNoneを返す。"""
        migration = find_migration("0.5.0", "0.6.0")
        assert migration is None


class TestCalculateMigrationPath:
    """マイグレーションパス計算のテスト。"""

    def test_same_version_returns_empty_plan(self):
        """同じバージョンは空の計画を返す。"""
        plan = calculate_migration_path("0.9.0", "0.9.0")
        assert plan.is_empty
        assert plan.migrations == ()

    def test_direct_migration(self):
        """直接マイグレーションを見つける。"""
        plan = calculate_migration_path("0.8.0", "0.9.0")
        assert len(plan.migrations) == 1
        assert plan.migrations[0].from_version == "0.8.0"
        assert plan.migrations[0].to_version == "0.9.0"

    def test_multi_step_migration(self):
        """複数ステップのマイグレーションパスを構築する。"""
        plan = calculate_migration_path("0.7.0", "0.9.0")
        assert len(plan.migrations) == 2
        assert plan.migrations[0].from_version == "0.7.0"
        assert plan.migrations[-1].to_version == "0.9.0"

    def test_no_path_raises_error(self):
        """パスがない場合はエラー。"""
        with pytest.raises(ValueError, match="マイグレーションパスが見つかりません"):
            calculate_migration_path("0.1.0", "0.9.0")

    def test_downgrade_returns_empty_plan(self):
        """ダウングレードは空の計画を返す。"""
        plan = calculate_migration_path("0.9.0", "0.8.0")
        assert plan.is_empty

    def test_plan_is_immutable(self):
        """計画はイミュータブル。"""
        plan = calculate_migration_path("0.8.0", "0.9.0")
        with pytest.raises(Exception):
            plan.migrations = ()  # type: ignore

    def test_total_changes_calculated_correctly(self):
        """変更数が正しく計算される。"""
        plan = calculate_migration_path("0.8.0", "0.9.0")
        # 0.8→0.9 には2つの変更がある
        assert plan.total_changes == 2


# tests/unit/migrations/test_executor.py
"""マイグレーション実行のテスト。"""
from pathlib import Path

import pytest

from railway.migrations.types import MigrationPlan
from railway.migrations.changes import (
    MigrationDefinition,
    FileChange,
    ChangeType,
)
from railway.migrations.executor import (
    apply_file_change,
    execute_migration_plan,
    initialize_project,
)
from railway.core.project_metadata import load_metadata, save_metadata, create_metadata


class TestApplyFileChange:
    """ファイル変更適用のテスト。"""

    def test_create_file(self, tmp_path: Path):
        """ファイル作成アクション。"""
        change = FileChange.create(
            path="src/py.typed",
            content="",
            description="型マーカー",
        )

        apply_file_change(tmp_path, change)

        assert (tmp_path / "src" / "py.typed").exists()

    def test_create_file_with_content(self, tmp_path: Path):
        """コンテンツ付きファイル作成。"""
        change = FileChange.create(
            path="test.txt",
            content="Hello, World!",
            description="テストファイル",
        )

        apply_file_change(tmp_path, change)

        assert (tmp_path / "test.txt").read_text() == "Hello, World!"

    def test_delete_file(self, tmp_path: Path):
        """ファイル削除アクション。"""
        # ファイルを事前作成
        test_file = tmp_path / "to_delete.txt"
        test_file.write_text("delete me")

        change = FileChange.delete(
            path="to_delete.txt",
            description="削除",
        )

        apply_file_change(tmp_path, change)

        assert not test_file.exists()

    def test_delete_nonexistent_file_is_ok(self, tmp_path: Path):
        """存在しないファイルの削除は成功する。"""
        change = FileChange.delete(
            path="nonexistent.txt",
            description="削除",
        )

        # エラーにならない
        apply_file_change(tmp_path, change)


class TestExecuteMigrationPlan:
    """マイグレーション計画実行のテスト。"""

    def test_empty_plan_succeeds(self, tmp_path: Path):
        """空の計画は成功する。"""
        plan = MigrationPlan(
            from_version="0.9.0",
            to_version="0.9.0",
            migrations=(),
        )

        result = execute_migration_plan(tmp_path, plan)

        assert result.success
        assert result.from_version == "0.9.0"
        assert result.to_version == "0.9.0"

    def test_creates_backup_by_default(self, tmp_path: Path):
        """デフォルトでバックアップを作成する。"""
        # メタデータを事前作成
        metadata = create_metadata("test", "0.8.0")
        save_metadata(tmp_path, metadata)

        migration = MigrationDefinition(
            from_version="0.8.0",
            to_version="0.9.0",
            description="テスト",
            file_changes=(
                FileChange.create(
                    path="new_file.txt",
                    content="",
                    description="新規",
                ),
            ),
        )
        plan = MigrationPlan(
            from_version="0.8.0",
            to_version="0.9.0",
            migrations=(migration,),
        )

        result = execute_migration_plan(tmp_path, plan)

        assert result.success
        assert result.backup_path is not None
        assert result.backup_path.exists()

    def test_updates_metadata_on_success(self, tmp_path: Path):
        """成功時にメタデータを更新する。"""
        metadata = create_metadata("test", "0.8.0")
        save_metadata(tmp_path, metadata)

        migration = MigrationDefinition(
            from_version="0.8.0",
            to_version="0.9.0",
            description="テスト",
        )
        plan = MigrationPlan(
            from_version="0.8.0",
            to_version="0.9.0",
            migrations=(migration,),
        )

        result = execute_migration_plan(tmp_path, plan, create_backup_flag=False)

        assert result.success
        updated = load_metadata(tmp_path)
        assert updated is not None
        assert updated.railway.version == "0.9.0"

    def test_result_is_immutable(self, tmp_path: Path):
        """結果はイミュータブル。"""
        plan = MigrationPlan(
            from_version="0.9.0",
            to_version="0.9.0",
            migrations=(),
        )

        result = execute_migration_plan(tmp_path, plan)

        with pytest.raises(Exception):
            result.success = False


class TestInitializeProject:
    """プロジェクト初期化のテスト。"""

    def test_creates_metadata_file(self, tmp_path: Path):
        """メタデータファイルを作成する。"""
        result = initialize_project(tmp_path)

        assert result.success
        assert (tmp_path / ".railway" / "project.yaml").exists()

    def test_uses_directory_name_as_project_name(self, tmp_path: Path):
        """ディレクトリ名をプロジェクト名として使用する。"""
        result = initialize_project(tmp_path)

        metadata = load_metadata(tmp_path)
        assert metadata is not None
        assert metadata.project.name == tmp_path.name
```

### Green Phase: 最小限の実装

上記「実装」セクションのコードを実装し、テストを通す。

### Refactor Phase: 改善

1. エラーハンドリングの強化
2. テンプレートレンダリング機能の実装
3. 設定マージ機能の実装（#04で詳細化）

## 依存関係

- #01 プロジェクトバージョン記録（メタデータの読み書き）
- #02 バージョン互換性チェック（互換性判定ロジック）
- #04 マイグレーション戦略設計（`MigrationDefinition`, `FileChange`, `ChangeType` 型を使用）

## 優先度

**高** - 継続的保守運用の核心機能
