"""バージョン互換性チェック機能。

関数型パラダイム:
- 全ての関数は純粋関数（副作用なし）
- 入力のみに依存し、同じ入力には同じ出力
- Enumで状態を値として表現
"""
from enum import Enum

from packaging.version import Version
from pydantic import BaseModel, ConfigDict


class CompatibilityLevel(Enum):
    """バージョン互換性レベル（値として表現）。"""
    FULL = "full"           # 完全互換
    MINOR_DIFF = "minor"    # マイナーバージョン差
    MAJOR_DIFF = "major"    # メジャーバージョン差
    UNKNOWN = "unknown"     # メタデータなし


class CompatibilityResult(BaseModel):
    """互換性チェック結果（イミュータブル）。

    Attributes:
        level: 互換性レベル
        project_version: プロジェクトのバージョン（不明の場合None）
        current_version: 現在のrailway-frameworkバージョン
    """
    model_config = ConfigDict(frozen=True)

    level: CompatibilityLevel
    project_version: str | None
    current_version: str

    @property
    def is_compatible(self) -> bool:
        """完全互換かどうか。"""
        return self.level == CompatibilityLevel.FULL

    @property
    def requires_confirmation(self) -> bool:
        """ユーザー確認が必要かどうか。"""
        return self.level in (CompatibilityLevel.MINOR_DIFF, CompatibilityLevel.UNKNOWN)

    @property
    def is_blocked(self) -> bool:
        """実行がブロックされるかどうか。"""
        return self.level == CompatibilityLevel.MAJOR_DIFF


def check_compatibility(
    project_version: str | None,
    current_version: str,
) -> CompatibilityResult:
    """バージョン互換性をチェックする純粋関数。

    Args:
        project_version: プロジェクトのrailway-frameworkバージョン（None=不明）
        current_version: 現在のrailway-frameworkバージョン

    Returns:
        CompatibilityResult with level and versions

    Examples:
        >>> check_compatibility("0.9.0", "0.9.0").level
        CompatibilityLevel.FULL
        >>> check_compatibility("0.8.0", "0.9.0").level
        CompatibilityLevel.MINOR_DIFF
        >>> check_compatibility(None, "0.9.0").level
        CompatibilityLevel.UNKNOWN
    """
    if project_version is None:
        return CompatibilityResult(
            level=CompatibilityLevel.UNKNOWN,
            project_version=None,
            current_version=current_version,
        )

    proj = Version(project_version)
    curr = Version(current_version)

    if proj.major != curr.major:
        level = CompatibilityLevel.MAJOR_DIFF
    elif proj.minor != curr.minor:
        level = CompatibilityLevel.MINOR_DIFF
    else:
        level = CompatibilityLevel.FULL

    return CompatibilityResult(
        level=level,
        project_version=project_version,
        current_version=current_version,
    )


# ============================================================
# メッセージ生成（純粋関数）
# ============================================================

def get_compatibility_message(level: CompatibilityLevel) -> str | None:
    """互換性レベルに応じたメッセージを取得する純粋関数。

    Args:
        level: 互換性レベル

    Returns:
        ユーザー向けメッセージ、FULLの場合はNone
    """
    messages = {
        CompatibilityLevel.FULL: None,
        CompatibilityLevel.MINOR_DIFF: (
            "マイナーバージョンが異なります。\n"
            "テンプレートが更新されている可能性があります。"
        ),
        CompatibilityLevel.MAJOR_DIFF: (
            "メジャーバージョンが異なります。\n"
            "破壊的変更が含まれている可能性があります。"
        ),
        CompatibilityLevel.UNKNOWN: (
            "プロジェクトのバージョン情報がありません。\n"
            "古いバージョンで作成されたプロジェクトの可能性があります。"
        ),
    }
    return messages[level]


def format_compatibility_warning(result: CompatibilityResult) -> str:
    """互換性警告をフォーマットする純粋関数。

    Args:
        result: 互換性チェック結果

    Returns:
        フォーマット済み警告メッセージ
    """
    version_display = result.project_version or "不明"
    message = get_compatibility_message(result.level) or ""

    return (
        f"⚠️  バージョン不一致を検出\n"
        f"   プロジェクト: {version_display}\n"
        f"   現在:         {result.current_version}\n\n"
        f"{message}"
    )


def format_compatibility_error(result: CompatibilityResult) -> str:
    """互換性エラーをフォーマットする純粋関数。

    Args:
        result: 互換性チェック結果

    Returns:
        フォーマット済みエラーメッセージ
    """
    version_display = result.project_version or "不明"
    message = get_compatibility_message(result.level) or ""

    return (
        f"❌ バージョン互換性エラー\n"
        f"   プロジェクト: {version_display}\n"
        f"   現在:         {result.current_version}\n\n"
        f"{message}\n\n"
        f"'railway update' を実行してプロジェクトを更新してください。"
    )
