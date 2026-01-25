# Issue #06: Dry-run モード実装

## 概要

`railway update --dry-run` で実際の変更を行わずに、適用される変更をプレビューする機能を実装する。

## 現状

マイグレーション前に何が変更されるか確認する手段がない。

## 目標

```bash
$ railway update --dry-run

🔍 プロジェクトを分析中...

   プロジェクト名:      my_project
   現在のバージョン:    0.8.0
   ターゲットバージョン: 0.9.0

📋 適用される変更:

   [ファイル追加]
   + src/py.typed (0 bytes)

   [ファイル更新]
   ~ TUTORIAL.md
     - Step 8 セクションを追加 (+150 lines)
     - FAQ セクションを追加 (+50 lines)

   ~ config/development.yaml
     - 新規キー: error_handling.on_error_default
     - キー名変更: log_level → logging.level

   [ファイル削除]
   - deprecated_config.yaml

   [コード変更ガイダンス（手動対応推奨）]
   ! src/nodes/fetch_data.py:15
     @node(log_input=True)  →  @node(log_inputs=True)

   ! src/nodes/process.py:8
     @node(log_input=True)  →  @node(log_inputs=True)

[dry-run] 実際の変更は行われませんでした。
実行するには: railway update
```

## 設計原則

### 関数型パラダイム準拠

1. **イミュータブルなプレビュー結果**: frozen dataclass で表現
2. **純粋関数によるプレビュー生成**: 副作用なしでプレビューを計算
3. **差分計算の分離**: difflib を使った純粋関数による差分計算
4. **表示ロジックの分離**: データ生成と表示フォーマットを分離

## 実装

### 1. プレビュー型定義（イミュータブル）

```python
# railway/migrations/preview_types.py
"""プレビュー型定義。

関数型パラダイム:
- 全てのデータ型はイミュータブル (frozen=True)
- 変更の種類を Enum で表現
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Sequence


class PreviewChangeType(Enum):
    """変更の種類。"""
    ADD = "add"           # ファイル追加
    UPDATE = "update"     # ファイル更新
    DELETE = "delete"     # ファイル削除
    GUIDANCE = "guidance" # 手動変更ガイダンス


@dataclass(frozen=True)
class LineDiff:
    """行差分情報（イミュータブル）。"""
    added: int
    removed: int

    @property
    def net_change(self) -> int:
        """純増減。"""
        return self.added - self.removed

    def format(self) -> str:
        """表示用フォーマット。"""
        return f"+{self.added}/-{self.removed}"


@dataclass(frozen=True)
class ChangePreview:
    """個別の変更プレビュー（イミュータブル）。"""
    change_type: PreviewChangeType
    path: str
    description: str
    details: tuple[str, ...] = field(default_factory=tuple)
    line_diff: Optional[LineDiff] = None

    @property
    def is_file_change(self) -> bool:
        """ファイル変更かどうか。"""
        return self.change_type in (PreviewChangeType.ADD, PreviewChangeType.UPDATE, PreviewChangeType.DELETE)

    @property
    def is_guidance(self) -> bool:
        """ガイダンスかどうか。"""
        return self.change_type == PreviewChangeType.GUIDANCE


@dataclass(frozen=True)
class MigrationPreview:
    """マイグレーション全体のプレビュー（イミュータブル）。"""
    from_version: str
    to_version: str
    changes: tuple[ChangePreview, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def additions(self) -> tuple[ChangePreview, ...]:
        """追加変更のみ。"""
        return tuple(c for c in self.changes if c.change_type == PreviewChangeType.ADD)

    @property
    def updates(self) -> tuple[ChangePreview, ...]:
        """更新変更のみ。"""
        return tuple(c for c in self.changes if c.change_type == PreviewChangeType.UPDATE)

    @property
    def deletions(self) -> tuple[ChangePreview, ...]:
        """削除変更のみ。"""
        return tuple(c for c in self.changes if c.change_type == PreviewChangeType.DELETE)

    @property
    def guidance_items(self) -> tuple[ChangePreview, ...]:
        """ガイダンス項目のみ。"""
        return tuple(c for c in self.changes if c.change_type == PreviewChangeType.GUIDANCE)

    @property
    def total_changes(self) -> int:
        """変更の総数。"""
        return len(self.changes)

    @property
    def has_warnings(self) -> bool:
        """警告があるか。"""
        return len(self.warnings) > 0

    @property
    def has_guidance(self) -> bool:
        """ガイダンス項目があるか。"""
        return len(self.guidance_items) > 0
```

### 2. 差分計算（純粋関数）

```python
# railway/migrations/diff.py
"""差分計算機能。

関数型パラダイム:
- 全ての関数は純粋関数
- 入力を変更せず、新しい値を返す
"""
import difflib
from typing import Sequence

from railway.migrations.preview_types import LineDiff


def count_diff_lines(original: str, new: str) -> LineDiff:
    """2つのテキスト間の行差分をカウントする純粋関数。

    Args:
        original: 元のテキスト
        new: 新しいテキスト

    Returns:
        LineDiff with added and removed counts
    """
    diff = difflib.unified_diff(
        original.splitlines(),
        new.splitlines(),
    )

    added = 0
    removed = 0

    for line in diff:
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1

    return LineDiff(added=added, removed=removed)


def generate_unified_diff(
    original: str,
    new: str,
    original_name: str = "before",
    new_name: str = "after",
    context_lines: int = 3,
) -> str:
    """unified diff 形式の差分を生成する純粋関数。

    Args:
        original: 元のテキスト
        new: 新しいテキスト
        original_name: 元ファイル名
        new_name: 新ファイル名
        context_lines: コンテキスト行数

    Returns:
        unified diff 形式の文字列
    """
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=original_name,
        tofile=new_name,
        n=context_lines,
    )
    return "".join(diff)


def summarize_changes(original: str, new: str) -> list[str]:
    """変更内容を人間が読みやすい形式で要約する純粋関数。

    Args:
        original: 元のテキスト
        new: 新しいテキスト

    Returns:
        変更の説明リスト
    """
    summaries: list[str] = []

    original_lines = original.splitlines()
    new_lines = new.splitlines()

    diff = count_diff_lines(original, new)

    if diff.added > 0 and diff.removed == 0:
        summaries.append(f"{diff.added}行を追加")
    elif diff.removed > 0 and diff.added == 0:
        summaries.append(f"{diff.removed}行を削除")
    elif diff.added > 0 and diff.removed > 0:
        summaries.append(f"{diff.added}行を追加、{diff.removed}行を削除")

    # セクションの追加を検出
    for line in new_lines:
        if line.startswith("## ") and line not in original_lines:
            section_name = line[3:].strip()
            summaries.append(f"セクション「{section_name}」を追加")

    return summaries


def find_added_sections(original: str, new: str, marker: str = "## ") -> list[str]:
    """追加されたセクションを検出する純粋関数。

    Args:
        original: 元のテキスト
        new: 新しいテキスト
        marker: セクションマーカー

    Returns:
        追加されたセクション名のリスト
    """
    original_sections = {
        line[len(marker):].strip()
        for line in original.splitlines()
        if line.startswith(marker)
    }
    new_sections = {
        line[len(marker):].strip()
        for line in new.splitlines()
        if line.startswith(marker)
    }

    return sorted(new_sections - original_sections)
```

### 3. プレビュー生成（純粋関数）

```python
# railway/migrations/preview.py
"""プレビュー生成機能。

関数型パラダイム:
- プレビュー生成は純粋関数
- IOは別レイヤーで分離
"""
from pathlib import Path
from typing import Sequence

from railway.migrations.changes import (
    MigrationDefinition,
    FileChange,
    ConfigChange,
    CodeGuidance,
    ChangeType as MigChangeType,
)
from railway.migrations.preview_types import (
    ChangePreview,
    PreviewChangeType,
    LineDiff,
    MigrationPreview,
)
from railway.migrations.diff import count_diff_lines, summarize_changes
from railway.migrations.scanner import scan_project


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
    file_path = project_path / change.path

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
            if not file_path.exists():
                return ChangePreview(
                    change_type=PreviewChangeType.ADD,
                    path=change.path,
                    description="テンプレートから生成",
                )

            # 既存ファイルとの差分を計算
            try:
                original = file_path.read_text(encoding="utf-8")
                # テンプレートレンダリング（実装は省略）
                new_content = ""  # render_template(change.template, project_path)
                diff = count_diff_lines(original, new_content)
                details = tuple(summarize_changes(original, new_content))

                return ChangePreview(
                    change_type=PreviewChangeType.UPDATE,
                    path=change.path,
                    description="テンプレート更新",
                    details=details,
                    line_diff=diff,
                )
            except (OSError, UnicodeDecodeError):
                return ChangePreview(
                    change_type=PreviewChangeType.UPDATE,
                    path=change.path,
                    description="テンプレート更新",
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


def preview_code_guidance(
    guidance: CodeGuidance,
    project_path: Path,
) -> list[ChangePreview]:
    """コードガイダンスのプレビューを生成する。

    Args:
        guidance: コードガイダンス定義
        project_path: プロジェクトパス

    Returns:
        ChangePreviewのリスト
    """
    scan_result = scan_project(project_path, [guidance])
    previews: list[ChangePreview] = []

    for match in scan_result.matches:
        previews.append(ChangePreview(
            change_type=PreviewChangeType.GUIDANCE,
            path=match.file_path,
            description=match.guidance.description,
            details=(
                f"現在: {match.original_line.strip()}",
                f"推奨: {match.suggested_line.strip()}",
            ),
        ))

    return previews


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

        # コードガイダンス
        for cg in migration.code_guidance:
            changes.extend(preview_code_guidance(cg, project_path))

        # 警告
        warnings.extend(migration.warnings)

    return MigrationPreview(
        from_version=migrations[0].from_version,
        to_version=migrations[-1].to_version,
        changes=tuple(changes),
        warnings=tuple(warnings),
    )
```

### 4. プレビュー表示（表示ロジック分離）

```python
# railway/cli/preview_display.py
"""プレビュー表示機能。

関数型パラダイム:
- 表示フォーマットは純粋関数
- 実際の出力はIO層で行う
"""
from typing import Callable

from railway.migrations.preview_types import (
    ChangePreview,
    PreviewChangeType,
    MigrationPreview,
)


def format_change_type_header(change_type: PreviewChangeType) -> str:
    """変更タイプのヘッダーをフォーマットする純粋関数。"""
    headers = {
        PreviewChangeType.ADD: "[ファイル追加]",
        PreviewChangeType.UPDATE: "[ファイル更新]",
        PreviewChangeType.DELETE: "[ファイル削除]",
        PreviewChangeType.GUIDANCE: "[コード変更ガイダンス（手動対応推奨）]",
    }
    return headers[change_type]


def format_change_symbol(change_type: PreviewChangeType) -> str:
    """変更タイプのシンボルをフォーマットする純粋関数。"""
    symbols = {
        PreviewChangeType.ADD: "+",
        PreviewChangeType.UPDATE: "~",
        PreviewChangeType.DELETE: "-",
        PreviewChangeType.GUIDANCE: "!",
    }
    return symbols[change_type]


def format_change_preview(
    change: ChangePreview,
    verbose: bool = False,
) -> list[str]:
    """個別変更のプレビューをフォーマットする純粋関数。

    Args:
        change: 変更プレビュー
        verbose: 詳細表示

    Returns:
        フォーマット済み行のリスト
    """
    lines: list[str] = []
    symbol = format_change_symbol(change.change_type)

    # メイン行
    diff_str = ""
    if change.line_diff:
        diff_str = f" ({change.line_diff.format()})"
    lines.append(f"   {symbol} {change.path}{diff_str}")

    # 詳細
    if change.change_type == PreviewChangeType.GUIDANCE:
        lines.append(f"     {change.description}")

    if verbose or change.change_type != PreviewChangeType.ADD:
        for detail in change.details:
            lines.append(f"     - {detail}")

    return lines


def format_migration_preview(
    preview: MigrationPreview,
    verbose: bool = False,
) -> list[str]:
    """マイグレーションプレビュー全体をフォーマットする純粋関数。

    Args:
        preview: マイグレーションプレビュー
        verbose: 詳細表示

    Returns:
        フォーマット済み行のリスト
    """
    lines: list[str] = ["", "📋 適用される変更:", ""]

    # タイプごとにグループ化して表示
    for change_type in (PreviewChangeType.ADD, PreviewChangeType.UPDATE, PreviewChangeType.DELETE, PreviewChangeType.GUIDANCE):
        changes = [c for c in preview.changes if c.change_type == change_type]
        if changes:
            lines.append(f"   {format_change_type_header(change_type)}")
            for change in changes:
                lines.extend(format_change_preview(change, verbose))
            lines.append("")

    # 警告
    if preview.warnings:
        lines.append("   ⚠️  警告:")
        for warning in preview.warnings:
            lines.append(f"   - {warning}")
        lines.append("")

    return lines


def display_preview(
    preview: MigrationPreview,
    output: Callable[[str], None],
    verbose: bool = False,
) -> None:
    """プレビューを表示する。

    Args:
        preview: マイグレーションプレビュー
        output: 出力関数（typer.echo など）
        verbose: 詳細表示
    """
    lines = format_migration_preview(preview, verbose)
    for line in lines:
        output(line)
```

## テスト（TDD: Red → Green → Refactor）

### テストファイル構成

```
tests/unit/migrations/
├── test_preview_types.py
├── test_diff.py
└── test_preview.py
```

### Red Phase: テストを先に書く

```python
# tests/unit/migrations/test_preview.py
"""プレビュー機能のテスト。

TDD Red Phase: まずテストを書き、失敗を確認する。
"""
from pathlib import Path

import pytest

from railway.migrations.preview_types import (
    ChangePreview,
    PreviewChangeType,
    LineDiff,
    MigrationPreview,
)
from railway.migrations.diff import (
    count_diff_lines,
    generate_unified_diff,
    summarize_changes,
    find_added_sections,
)
from railway.migrations.preview import (
    preview_config_change,
    generate_migration_preview,
)
from railway.migrations.changes import ConfigChange


class TestLineDiff:
    """LineDiff型のテスト。"""

    def test_is_immutable(self):
        """LineDiffは変更不可。"""
        diff = LineDiff(added=10, removed=5)

        with pytest.raises(Exception):
            diff.added = 20

    def test_net_change(self):
        """純増減が正しく計算される。"""
        diff = LineDiff(added=10, removed=3)

        assert diff.net_change == 7

    def test_format(self):
        """フォーマットが正しい。"""
        diff = LineDiff(added=10, removed=5)

        assert diff.format() == "+10/-5"


class TestCountDiffLines:
    """count_diff_lines関数のテスト。"""

    def test_no_changes(self):
        """変更なしの場合。"""
        text = "Hello\nWorld"

        diff = count_diff_lines(text, text)

        assert diff.added == 0
        assert diff.removed == 0

    def test_additions_only(self):
        """追加のみの場合。"""
        original = "Hello"
        new = "Hello\nWorld"

        diff = count_diff_lines(original, new)

        assert diff.added == 1
        assert diff.removed == 0

    def test_deletions_only(self):
        """削除のみの場合。"""
        original = "Hello\nWorld"
        new = "Hello"

        diff = count_diff_lines(original, new)

        assert diff.added == 0
        assert diff.removed == 1

    def test_mixed_changes(self):
        """追加と削除の両方。"""
        original = "Hello\nWorld"
        new = "Hi\nWorld\nNew"

        diff = count_diff_lines(original, new)

        assert diff.added >= 1
        assert diff.removed >= 1


class TestFindAddedSections:
    """find_added_sections関数のテスト。"""

    def test_finds_new_sections(self):
        """追加されたセクションを検出する。"""
        original = "## Introduction\n\nContent"
        new = "## Introduction\n\nContent\n\n## New Section\n\nMore"

        sections = find_added_sections(original, new)

        assert "New Section" in sections

    def test_returns_empty_for_no_new_sections(self):
        """新しいセクションがない場合は空。"""
        original = "## Section\n\nContent"
        new = "## Section\n\nUpdated content"

        sections = find_added_sections(original, new)

        assert sections == []


class TestPreviewConfigChange:
    """preview_config_change関数のテスト。"""

    def test_shows_additions(self):
        """追加キーが表示される。"""
        change = ConfigChange(
            path="config.yaml",
            additions={"new_key": "value"},
        )

        preview = preview_config_change(change)

        assert any("新規キー: new_key" in d for d in preview.details)

    def test_shows_renames(self):
        """リネームキーが表示される。"""
        change = ConfigChange(
            path="config.yaml",
            renames={"old": "new"},
        )

        preview = preview_config_change(change)

        assert any("old → new" in d for d in preview.details)

    def test_shows_deletions(self):
        """削除キーが表示される。"""
        change = ConfigChange(
            path="config.yaml",
            deletions=["deprecated"],
        )

        preview = preview_config_change(change)

        assert any("削除" in d and "deprecated" in d for d in preview.details)


class TestMigrationPreview:
    """MigrationPreview型のテスト。"""

    def test_is_immutable(self):
        """MigrationPreviewは変更不可。"""
        preview = MigrationPreview(
            from_version="0.8.0",
            to_version="0.9.0",
            changes=(),
        )

        with pytest.raises(Exception):
            preview.from_version = "0.7.0"

    def test_filters_by_type(self):
        """タイプ別にフィルタリングできる。"""
        preview = MigrationPreview(
            from_version="0.8.0",
            to_version="0.9.0",
            changes=(
                ChangePreview(PreviewChangeType.ADD, "new.txt", "追加"),
                ChangePreview(PreviewChangeType.UPDATE, "old.txt", "更新"),
                ChangePreview(PreviewChangeType.DELETE, "del.txt", "削除"),
            ),
        )

        assert len(preview.additions) == 1
        assert len(preview.updates) == 1
        assert len(preview.deletions) == 1

    def test_has_warnings(self):
        """警告の有無を判定できる。"""
        preview_with = MigrationPreview(
            from_version="0.8.0",
            to_version="0.9.0",
            changes=(),
            warnings=("注意",),
        )
        preview_without = MigrationPreview(
            from_version="0.8.0",
            to_version="0.9.0",
            changes=(),
        )

        assert preview_with.has_warnings
        assert not preview_without.has_warnings


class TestDryRunBehavior:
    """dry-run モードの動作テスト。"""

    def test_dry_run_does_not_modify_files(self, tmp_path: Path):
        """dry-runはファイルを変更しない。"""
        # ファイル作成
        test_file = tmp_path / "test.txt"
        test_file.write_text("Original content")
        original_content = test_file.read_text()

        # プレビュー生成（ファイルを変更しない）
        from railway.migrations.preview import generate_migration_preview
        from railway.migrations.changes import MigrationDefinition, FileChange

        migration = MigrationDefinition(
            from_version="0.8.0",
            to_version="0.9.0",
            description="Test",
            file_changes=(
                FileChange.update("test.txt", "template.j2", "更新"),
            ),
        )

        preview = generate_migration_preview([migration], tmp_path)

        # ファイルは変更されていない
        assert test_file.read_text() == original_content
```

### Green Phase: 最小限の実装

上記「実装」セクションのコードを実装し、テストを通す。

### Refactor Phase: 改善

1. カラー出力のサポート
2. JSON/YAML形式での出力オプション
3. インタラクティブな差分表示

## 依存関係

- #03 railway update コマンド基本実装（`MigrationPlan`, `MigrationResult` 型）
- #04 マイグレーション戦略設計（`MigrationDefinition`, `FileChange`, `ConfigChange`, `CodeGuidance` を使用）

## 優先度

**低** - 基本機能完成後に追加
