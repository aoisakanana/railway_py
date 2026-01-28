"""フィールドベース依存関係の型システム。

ノード間のデータ依存を requires/optional/provides で明示する。

設計原則:
- 純粋関数: 副作用なし、同じ入力に同じ出力
- イミュータブル: frozen=True の dataclass
- 関心の分離: YAML は遷移のみ、依存はノードコードで宣言
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FieldDependency:
    """ノードのフィールド依存関係。

    各ノードが必要とするフィールドと提供するフィールドを明示する。

    Attributes:
        requires: 必須フィールド（なければ実行不可）
        optional: オプションフィールド（あれば使用）
        provides: このノードが提供するフィールド

    Example:
        >>> dep = FieldDependency(
        ...     requires=frozenset(["incident_id"]),
        ...     optional=frozenset(["hostname"]),
        ...     provides=frozenset(["escalated"]),
        ... )
        >>> "incident_id" in dep.requires
        True
    """

    requires: frozenset[str]
    optional: frozenset[str]
    provides: frozenset[str]


# 空の依存関係を表す定数
EMPTY_FIELD_DEPENDENCY = FieldDependency(
    requires=frozenset(),
    optional=frozenset(),
    provides=frozenset(),
)


@dataclass(frozen=True)
class AvailableFields:
    """ある時点で利用可能なフィールド。

    ワークフロー実行中に累積されるフィールドを追跡する。

    Attributes:
        fields: 利用可能なフィールド名の集合

    Example:
        >>> available = AvailableFields(frozenset(["a", "b"]))
        >>> dep = FieldDependency(
        ...     requires=frozenset(["a"]),
        ...     optional=frozenset(),
        ...     provides=frozenset(["c"]),
        ... )
        >>> available.satisfies(dep)
        True
        >>> new_available = available.after(dep)
        >>> "c" in new_available.fields
        True
    """

    fields: frozenset[str]

    def satisfies(self, dependency: FieldDependency) -> bool:
        """依存関係を満たすか判定する。

        Args:
            dependency: 検証対象の依存関係

        Returns:
            requires のすべてのフィールドが利用可能なら True
        """
        return dependency.requires.issubset(self.fields)

    def after(self, dependency: FieldDependency) -> AvailableFields:
        """ノード実行後の利用可能フィールドを計算する。

        Args:
            dependency: 実行したノードの依存関係

        Returns:
            provides を追加した新しい AvailableFields
        """
        return AvailableFields(self.fields | dependency.provides)

    def missing_optional(self, dependency: FieldDependency) -> frozenset[str]:
        """不足している optional フィールドを取得する。

        Args:
            dependency: 検証対象の依存関係

        Returns:
            利用不可の optional フィールド
        """
        return dependency.optional - self.fields


@dataclass(frozen=True)
class ValidationResult:
    """バリデーション結果。

    Attributes:
        is_valid: バリデーションが成功したか
        errors: エラーメッセージのタプル
        warnings: 警告メッセージのタプル
    """

    is_valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def validate_transition_dependencies(
    from_available: AvailableFields,
    to_dependency: FieldDependency,
) -> ValidationResult:
    """遷移の依存関係を検証する。

    遷移元で利用可能なフィールドが、遷移先の requires を満たすか検証する。

    Args:
        from_available: 遷移元で利用可能なフィールド
        to_dependency: 遷移先が必要とする依存関係

    Returns:
        ValidationResult

    Example:
        >>> available = AvailableFields(frozenset(["a"]))
        >>> dep = FieldDependency(
        ...     requires=frozenset(["a", "b"]),
        ...     optional=frozenset(),
        ...     provides=frozenset(),
        ... )
        >>> result = validate_transition_dependencies(available, dep)
        >>> result.is_valid
        False
        >>> "b" in result.errors[0]
        True
    """
    missing = to_dependency.requires - from_available.fields
    if missing:
        return ValidationResult(
            is_valid=False,
            errors=(f"必須フィールドが不足: {sorted(missing)}",),
        )
    return ValidationResult(is_valid=True, errors=())


def field_dependency_from_dict(data: dict[str, Any]) -> FieldDependency:
    """dict から FieldDependency を作成する。

    Args:
        data: {"requires": [...], "optional": [...], "provides": [...]}

    Returns:
        FieldDependency

    Example:
        >>> dep = field_dependency_from_dict({"requires": ["a", "b"]})
        >>> dep.requires
        frozenset({'a', 'b'})
    """
    return FieldDependency(
        requires=frozenset(data.get("requires", [])),
        optional=frozenset(data.get("optional", [])),
        provides=frozenset(data.get("provides", [])),
    )
