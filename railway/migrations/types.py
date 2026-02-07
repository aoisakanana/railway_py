"""マイグレーション実行に必要な基本型定義。

関数型パラダイム:
- 全てのデータ型はイミュータブル (frozen=True)
- 副作用のない値としてマイグレーションを表現

Note:
    詳細な変更定義（FileChange, ConfigChange, CodeGuidance）は
    railway/migrations/changes.py で定義される。
"""
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MigrationPlan(BaseModel):
    """マイグレーション計画（イミュータブル）。

    Attributes:
        from_version: 元のバージョン
        to_version: 移行先バージョン
        migrations: 適用するマイグレーション定義のシーケンス
    """
    model_config = ConfigDict(frozen=True)

    from_version: str
    to_version: str
    migrations: tuple[Any, ...] = Field(default_factory=tuple)

    @property
    def is_empty(self) -> bool:
        """マイグレーションが不要かどうか。"""
        return len(self.migrations) == 0

    @property
    def total_changes(self) -> int:
        """変更の総数。"""
        return sum(m.total_changes for m in self.migrations)


class MigrationResult(BaseModel):
    """マイグレーション実行結果（イミュータブル）。

    Attributes:
        success: 成功したかどうか
        from_version: 元のバージョン
        to_version: 移行先バージョン（成功時）または最後に成功したバージョン
        backup_path: バックアップパス（作成した場合）
        error: エラーメッセージ（失敗時）
    """
    model_config = ConfigDict(frozen=True)

    success: bool
    from_version: str
    to_version: str
    backup_path: Path | None = None
    error: str | None = None
