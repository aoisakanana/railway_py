"""プレビュー型定義。

関数型パラダイム:
- 全てのデータ型はイミュータブル (frozen=True)
- 変更の種類を Enum で表現
"""
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class PreviewChangeType(Enum):
    """変更の種類。"""
    ADD = "add"           # ファイル追加
    UPDATE = "update"     # ファイル更新
    DELETE = "delete"     # ファイル削除
    GUIDANCE = "guidance" # 手動変更ガイダンス


class LineDiff(BaseModel):
    """行差分情報（イミュータブル）。"""
    model_config = ConfigDict(frozen=True)

    added: int
    removed: int

    @property
    def net_change(self) -> int:
        """純増減。"""
        return self.added - self.removed

    def format(self) -> str:
        """表示用フォーマット。"""
        return f"+{self.added}/-{self.removed}"


class ChangePreview(BaseModel):
    """個別の変更プレビュー（イミュータブル）。"""
    model_config = ConfigDict(frozen=True)

    change_type: PreviewChangeType
    path: str
    description: str
    details: tuple[str, ...] = Field(default_factory=tuple)
    line_diff: LineDiff | None = None

    @property
    def is_file_change(self) -> bool:
        """ファイル変更かどうか。"""
        return self.change_type in (
            PreviewChangeType.ADD,
            PreviewChangeType.UPDATE,
            PreviewChangeType.DELETE,
        )

    @property
    def is_guidance(self) -> bool:
        """ガイダンスかどうか。"""
        return self.change_type == PreviewChangeType.GUIDANCE


class MigrationPreview(BaseModel):
    """マイグレーション全体のプレビュー（イミュータブル）。"""
    model_config = ConfigDict(frozen=True)

    from_version: str
    to_version: str
    changes: tuple[ChangePreview, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)

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
