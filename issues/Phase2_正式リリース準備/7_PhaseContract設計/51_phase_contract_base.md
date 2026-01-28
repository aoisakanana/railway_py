# Issue #51: FieldDependency 型システム

## 概要

フィールドベース依存関係の型システム基盤を構築する。

## 設計

### データ型

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class FieldDependency:
    """ノードのフィールド依存関係。"""
    requires: frozenset[str]   # 必須フィールド
    optional: frozenset[str]   # オプションフィールド
    provides: frozenset[str]   # 提供するフィールド


@dataclass(frozen=True)
class AvailableFields:
    """ある時点で利用可能なフィールド。"""
    fields: frozenset[str]

    def satisfies(self, dependency: FieldDependency) -> bool:
        """依存関係を満たすか判定。"""
        return dependency.requires.issubset(self.fields)

    def after(self, dependency: FieldDependency) -> "AvailableFields":
        """ノード実行後の利用可能フィールド。"""
        return AvailableFields(self.fields | dependency.provides)
```

### バリデーション関数

```python
def validate_transition_dependencies(
    from_available: AvailableFields,
    to_dependency: FieldDependency,
) -> ValidationResult:
    """遷移の依存関係を検証する。

    Args:
        from_available: 遷移元で利用可能なフィールド
        to_dependency: 遷移先が必要とする依存関係

    Returns:
        ValidationResult
    """
    missing = to_dependency.requires - from_available.fields
    if missing:
        return ValidationResult(
            is_valid=False,
            errors=(f"必須フィールドが不足: {missing}",),
        )
    return ValidationResult(is_valid=True, errors=())
```

## タスク

### 1. Red Phase: 失敗するテストを作成

`tests/unit/core/dag/test_field_dependency.py`:

```python
"""フィールド依存関係の型システムテスト。"""

import pytest
from railway.core.dag.field_dependency import (
    FieldDependency,
    AvailableFields,
    validate_transition_dependencies,
)


class TestFieldDependency:
    """FieldDependency のテスト。"""

    def test_creates_immutable_dependency(self) -> None:
        """イミュータブルな依存関係を作成する。"""
        dep = FieldDependency(
            requires=frozenset(["a", "b"]),
            optional=frozenset(["c"]),
            provides=frozenset(["d"]),
        )
        assert dep.requires == frozenset(["a", "b"])
        assert dep.optional == frozenset(["c"])
        assert dep.provides == frozenset(["d"])

    def test_empty_dependency(self) -> None:
        """空の依存関係を作成できる。"""
        dep = FieldDependency(
            requires=frozenset(),
            optional=frozenset(),
            provides=frozenset(),
        )
        assert len(dep.requires) == 0


class TestAvailableFields:
    """AvailableFields のテスト。"""

    def test_satisfies_when_all_required_present(self) -> None:
        """すべての必須フィールドがある場合は満たす。"""
        available = AvailableFields(frozenset(["a", "b", "c"]))
        dep = FieldDependency(
            requires=frozenset(["a", "b"]),
            optional=frozenset(),
            provides=frozenset(),
        )
        assert available.satisfies(dep) is True

    def test_not_satisfies_when_required_missing(self) -> None:
        """必須フィールドが欠けている場合は満たさない。"""
        available = AvailableFields(frozenset(["a"]))
        dep = FieldDependency(
            requires=frozenset(["a", "b"]),
            optional=frozenset(),
            provides=frozenset(),
        )
        assert available.satisfies(dep) is False

    def test_optional_does_not_affect_satisfies(self) -> None:
        """オプションフィールドは満たす判定に影響しない。"""
        available = AvailableFields(frozenset(["a"]))
        dep = FieldDependency(
            requires=frozenset(["a"]),
            optional=frozenset(["b"]),  # b はなくても OK
            provides=frozenset(),
        )
        assert available.satisfies(dep) is True

    def test_after_adds_provided_fields(self) -> None:
        """after() で提供フィールドが追加される。"""
        available = AvailableFields(frozenset(["a"]))
        dep = FieldDependency(
            requires=frozenset(["a"]),
            optional=frozenset(),
            provides=frozenset(["b", "c"]),
        )
        new_available = available.after(dep)
        assert new_available.fields == frozenset(["a", "b", "c"])

    def test_after_preserves_existing_fields(self) -> None:
        """after() は既存フィールドを保持する。"""
        available = AvailableFields(frozenset(["a", "b"]))
        dep = FieldDependency(
            requires=frozenset(),
            optional=frozenset(),
            provides=frozenset(["c"]),
        )
        new_available = available.after(dep)
        assert "a" in new_available.fields
        assert "b" in new_available.fields
        assert "c" in new_available.fields


class TestValidateTransitionDependencies:
    """遷移依存関係バリデーションのテスト。"""

    def test_valid_when_requirements_satisfied(self) -> None:
        """必須フィールドが満たされている場合は有効。"""
        available = AvailableFields(frozenset(["incident_id", "severity"]))
        dep = FieldDependency(
            requires=frozenset(["incident_id"]),
            optional=frozenset(),
            provides=frozenset(),
        )
        result = validate_transition_dependencies(available, dep)
        assert result.is_valid is True

    def test_invalid_when_requirements_not_satisfied(self) -> None:
        """必須フィールドが不足している場合は無効。"""
        available = AvailableFields(frozenset(["incident_id"]))
        dep = FieldDependency(
            requires=frozenset(["incident_id", "hostname"]),
            optional=frozenset(),
            provides=frozenset(),
        )
        result = validate_transition_dependencies(available, dep)
        assert result.is_valid is False
        assert "hostname" in result.errors[0]

    def test_reports_all_missing_fields(self) -> None:
        """不足しているすべてのフィールドを報告する。"""
        available = AvailableFields(frozenset())
        dep = FieldDependency(
            requires=frozenset(["a", "b", "c"]),
            optional=frozenset(),
            provides=frozenset(),
        )
        result = validate_transition_dependencies(available, dep)
        assert result.is_valid is False
        # すべての不足フィールドが報告される
        assert "a" in str(result.errors)
        assert "b" in str(result.errors)
        assert "c" in str(result.errors)


class TestFieldDependencyFromDict:
    """dict からの FieldDependency 作成テスト。"""

    def test_creates_from_dict(self) -> None:
        """dict から FieldDependency を作成する。"""
        from railway.core.dag.field_dependency import field_dependency_from_dict

        data = {
            "requires": ["a", "b"],
            "optional": ["c"],
            "provides": ["d"],
        }
        dep = field_dependency_from_dict(data)
        assert dep.requires == frozenset(["a", "b"])
        assert dep.optional == frozenset(["c"])
        assert dep.provides == frozenset(["d"])

    def test_handles_missing_keys(self) -> None:
        """キーが欠けている場合は空の frozenset。"""
        from railway.core.dag.field_dependency import field_dependency_from_dict

        data = {"requires": ["a"]}
        dep = field_dependency_from_dict(data)
        assert dep.requires == frozenset(["a"])
        assert dep.optional == frozenset()
        assert dep.provides == frozenset()
```

### 2. Green Phase: 最小限の実装

`railway/core/dag/field_dependency.py`:

```python
"""フィールドベース依存関係の型システム。

ノード間のデータ依存を requires/optional/provides で明示する。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FieldDependency:
    """ノードのフィールド依存関係。

    Attributes:
        requires: 必須フィールド（なければ実行不可）
        optional: オプションフィールド（あれば使用）
        provides: このノードが提供するフィールド
    """
    requires: frozenset[str]
    optional: frozenset[str]
    provides: frozenset[str]


@dataclass(frozen=True)
class AvailableFields:
    """ある時点で利用可能なフィールド。

    ワークフロー実行中に累積されるフィールドを追跡する。
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


@dataclass(frozen=True)
class ValidationResult:
    """バリデーション結果。"""
    is_valid: bool
    errors: tuple[str, ...]


def validate_transition_dependencies(
    from_available: AvailableFields,
    to_dependency: FieldDependency,
) -> ValidationResult:
    """遷移の依存関係を検証する。

    Args:
        from_available: 遷移元で利用可能なフィールド
        to_dependency: 遷移先が必要とする依存関係

    Returns:
        ValidationResult
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
    """
    return FieldDependency(
        requires=frozenset(data.get("requires", [])),
        optional=frozenset(data.get("optional", [])),
        provides=frozenset(data.get("provides", [])),
    )
```

### 3. Refactor Phase

- エラーメッセージの改善
- ドキュメンテーション追加
- エッジケースのテスト追加

## 完了条件

- [ ] `railway/core/dag/field_dependency.py` が作成されている
- [ ] `FieldDependency` データクラスが実装されている
- [ ] `AvailableFields` データクラスが実装されている
- [ ] `validate_transition_dependencies()` 関数が実装されている
- [ ] `field_dependency_from_dict()` 関数が実装されている
- [ ] すべてのテストが通過

## 依存関係

- Issue #50 (ADR) が完了していること

## 関連ファイル

- `railway/core/dag/field_dependency.py` (新規)
- `tests/unit/core/dag/test_field_dependency.py` (新規)
- `railway/core/dag/__init__.py` (エクスポート追加)
