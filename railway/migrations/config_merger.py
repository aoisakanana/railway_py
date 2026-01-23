"""設定マージ機能。

関数型パラダイム:
- マージ操作は純粋関数
- 入力を変更せず、新しい辞書を返す
"""
from copy import deepcopy
from typing import Any

from railway.migrations.changes import ConfigChange


def deep_merge(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """辞書を深くマージする純粋関数。

    Args:
        base: ベース辞書
        updates: マージする辞書

    Returns:
        マージされた新しい辞書（元の辞書は変更されない）
    """
    result = deepcopy(base)

    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)

    return result


def apply_renames(data: dict[str, Any], renames: dict[str, str]) -> dict[str, Any]:
    """キー名変更を適用する純粋関数。

    Args:
        data: 対象辞書
        renames: {旧キー: 新キー} の辞書

    Returns:
        キー名変更後の新しい辞書
    """
    result = deepcopy(data)

    for old_key, new_key in renames.items():
        if old_key in result:
            result[new_key] = result.pop(old_key)

    return result


def apply_deletions(data: dict[str, Any], deletions: list[str]) -> dict[str, Any]:
    """キー削除を適用する純粋関数。

    Args:
        data: 対象辞書
        deletions: 削除するキーのリスト

    Returns:
        キー削除後の新しい辞書
    """
    result = deepcopy(data)

    for key in deletions:
        result.pop(key, None)

    return result


def merge_config(
    original: dict[str, Any],
    change: ConfigChange,
) -> tuple[dict[str, Any], list[str]]:
    """設定変更をマージする純粋関数。

    Args:
        original: 元の設定
        change: 適用する変更

    Returns:
        (マージ後の設定, 適用された変更の説明リスト)
    """
    applied: list[str] = []
    result = deepcopy(original)

    # 追加
    if change.additions:
        result = deep_merge(result, change.additions)
        applied.append(f"追加: {len(change.additions)}キー")

    # リネーム
    if change.renames:
        result = apply_renames(result, change.renames)
        applied.append(f"リネーム: {len(change.renames)}キー")

    # 削除
    if change.deletions:
        result = apply_deletions(result, change.deletions)
        applied.append(f"削除: {len(change.deletions)}キー")

    return result, applied
