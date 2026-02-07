"""マイグレーション変更定義。

関数型パラダイム:
- 全てのデータ型はイミュータブル (frozen=True)
- ファクトリメソッドで生成
- 状態変更なし
"""
import fnmatch
import re
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChangeType(Enum):
    """変更の種類。"""
    FILE_CREATE = "file_create"
    FILE_UPDATE = "file_update"
    FILE_DELETE = "file_delete"
    CONFIG_MERGE = "config_merge"
    CODE_GUIDANCE = "code_guidance"


class FileChange(BaseModel):
    """ファイル変更定義（イミュータブル）。

    ファクトリメソッド経由で生成することを推奨。
    """
    model_config = ConfigDict(frozen=True)

    change_type: ChangeType
    path: str
    description: str
    content: str | None = None
    template: str | None = None

    @classmethod
    def create(
        cls,
        path: str,
        content: str,
        description: str | None = None,
    ) -> "FileChange":
        """新規ファイル作成の変更を生成。

        Args:
            path: ファイルパス
            content: ファイル内容
            description: 変更説明

        Returns:
            FileChange インスタンス
        """
        return cls(
            change_type=ChangeType.FILE_CREATE,
            path=path,
            content=content,
            description=description or f"新規作成: {path}",
        )

    @classmethod
    def update(
        cls,
        path: str,
        template: str,
        description: str | None = None,
    ) -> "FileChange":
        """ファイル更新の変更を生成。

        Args:
            path: ファイルパス
            template: テンプレート名
            description: 変更説明

        Returns:
            FileChange インスタンス
        """
        return cls(
            change_type=ChangeType.FILE_UPDATE,
            path=path,
            template=template,
            description=description or f"更新: {path}",
        )

    @classmethod
    def delete(
        cls,
        path: str,
        description: str | None = None,
    ) -> "FileChange":
        """ファイル削除の変更を生成。

        Args:
            path: ファイルパス
            description: 変更説明

        Returns:
            FileChange インスタンス
        """
        return cls(
            change_type=ChangeType.FILE_DELETE,
            path=path,
            description=description or f"削除: {path}",
        )


class ConfigChange(BaseModel):
    """設定ファイル変更定義（イミュータブル）。"""
    model_config = ConfigDict(frozen=True)

    path: str
    additions: dict[str, Any] = Field(default_factory=dict)
    renames: dict[str, str] = Field(default_factory=dict)
    deletions: list[str] = Field(default_factory=list)

    @property
    def description(self) -> str:
        """変更の説明を生成。"""
        parts: list[str] = []
        if self.additions:
            parts.append(f"追加: {len(self.additions)}キー")
        if self.renames:
            parts.append(f"リネーム: {len(self.renames)}キー")
        if self.deletions:
            parts.append(f"削除: {len(self.deletions)}キー")
        return ", ".join(parts) if parts else "変更なし"


class CodeGuidance(BaseModel):
    """コードガイダンス定義（イミュータブル）。

    自動適用せず、ユーザーに推奨変更を表示。
    """
    model_config = ConfigDict(frozen=True)

    description: str
    pattern: str
    replacement: str
    file_patterns: tuple[str, ...] = ("src/**/*.py",)

    def matches(self, content: str) -> list[tuple[int, str, str]]:
        """コンテンツ内でパターンにマッチする行を見つける。

        Args:
            content: 検索対象のコンテンツ

        Returns:
            (行番号, 元の行, 推奨行) のリスト
        """
        result: list[tuple[int, str, str]] = []
        regex = re.compile(self.pattern)

        for i, line in enumerate(content.splitlines(), start=1):
            if regex.search(line):
                suggested = regex.sub(self.replacement, line)
                result.append((i, line, suggested))

        return result


class YamlTransform(BaseModel):
    """YAML ファイルの構造変換定義（イミュータブル）。

    YAML ファイルの構造を変換するための定義。
    transform 関数は ConversionResult を返す純粋関数。

    Attributes:
        pattern: glob パターン（例: "transition_graphs/**/*.yml"）
        transform: 変換関数 (dict -> ConversionResult)
        description: 変換の説明
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    pattern: str
    transform: Callable[[dict[str, Any]], Any]  # Returns ConversionResult
    description: str

    def matches(self, path: Path) -> bool:
        """パスがパターンにマッチするかどうか。

        Args:
            path: チェックするパス

        Returns:
            マッチすれば True
        """
        return fnmatch.fnmatch(str(path), self.pattern)


class MigrationDefinition(BaseModel):
    """マイグレーション定義（イミュータブル）。

    特定バージョン間の移行に必要な変更を定義。
    """
    model_config = ConfigDict(frozen=True)

    from_version: str
    to_version: str
    description: str
    file_changes: tuple[FileChange, ...] = Field(default_factory=tuple)
    config_changes: tuple[ConfigChange, ...] = Field(default_factory=tuple)
    yaml_transforms: tuple[YamlTransform, ...] = Field(default_factory=tuple)
    code_guidance: tuple[CodeGuidance, ...] = Field(default_factory=tuple)
    post_migration_commands: tuple[str, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)

    @property
    def total_changes(self) -> int:
        """変更の合計数。"""
        return (
            len(self.file_changes)
            + len(self.config_changes)
            + len(self.yaml_transforms)
        )

    @property
    def has_breaking_changes(self) -> bool:
        """破壊的変更があるかどうか。"""
        return len(self.warnings) > 0 or len(self.code_guidance) > 0
