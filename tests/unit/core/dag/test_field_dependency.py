"""フィールド依存関係の型システムテスト。

TDD Red Phase: このテストは最初は失敗する（モジュールが存在しない）
"""

import pytest


class TestFieldDependency:
    """FieldDependency のテスト。"""

    def test_creates_immutable_dependency(self) -> None:
        """イミュータブルな依存関係を作成する。"""
        from railway.core.dag.field_dependency import FieldDependency

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
        from railway.core.dag.field_dependency import FieldDependency

        dep = FieldDependency(
            requires=frozenset(),
            optional=frozenset(),
            provides=frozenset(),
        )
        assert len(dep.requires) == 0
        assert len(dep.optional) == 0
        assert len(dep.provides) == 0

    def test_is_frozen(self) -> None:
        """dataclass は frozen である。"""
        from railway.core.dag.field_dependency import FieldDependency

        dep = FieldDependency(
            requires=frozenset(["a"]),
            optional=frozenset(),
            provides=frozenset(),
        )
        with pytest.raises(AttributeError):
            dep.requires = frozenset(["b"])  # type: ignore


class TestAvailableFields:
    """AvailableFields のテスト。"""

    def test_satisfies_when_all_required_present(self) -> None:
        """すべての必須フィールドがある場合は満たす。"""
        from railway.core.dag.field_dependency import (
            FieldDependency,
            AvailableFields,
        )

        available = AvailableFields(frozenset(["a", "b", "c"]))
        dep = FieldDependency(
            requires=frozenset(["a", "b"]),
            optional=frozenset(),
            provides=frozenset(),
        )
        assert available.satisfies(dep) is True

    def test_not_satisfies_when_required_missing(self) -> None:
        """必須フィールドが欠けている場合は満たさない。"""
        from railway.core.dag.field_dependency import (
            FieldDependency,
            AvailableFields,
        )

        available = AvailableFields(frozenset(["a"]))
        dep = FieldDependency(
            requires=frozenset(["a", "b"]),
            optional=frozenset(),
            provides=frozenset(),
        )
        assert available.satisfies(dep) is False

    def test_optional_does_not_affect_satisfies(self) -> None:
        """オプションフィールドは満たす判定に影響しない。"""
        from railway.core.dag.field_dependency import (
            FieldDependency,
            AvailableFields,
        )

        available = AvailableFields(frozenset(["a"]))
        dep = FieldDependency(
            requires=frozenset(["a"]),
            optional=frozenset(["b"]),  # b はなくても OK
            provides=frozenset(),
        )
        assert available.satisfies(dep) is True

    def test_after_adds_provided_fields(self) -> None:
        """after() で提供フィールドが追加される。"""
        from railway.core.dag.field_dependency import (
            FieldDependency,
            AvailableFields,
        )

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
        from railway.core.dag.field_dependency import (
            FieldDependency,
            AvailableFields,
        )

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

    def test_missing_optional(self) -> None:
        """missing_optional() で不足している optional フィールドを取得する。"""
        from railway.core.dag.field_dependency import (
            FieldDependency,
            AvailableFields,
        )

        available = AvailableFields(frozenset(["a"]))
        dep = FieldDependency(
            requires=frozenset(["a"]),
            optional=frozenset(["b", "c"]),
            provides=frozenset(),
        )
        missing = available.missing_optional(dep)
        assert missing == frozenset(["b", "c"])


class TestValidateTransitionDependencies:
    """遷移依存関係バリデーションのテスト。"""

    def test_valid_when_requirements_satisfied(self) -> None:
        """必須フィールドが満たされている場合は有効。"""
        from railway.core.dag.field_dependency import (
            FieldDependency,
            AvailableFields,
            validate_transition_dependencies,
        )

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
        from railway.core.dag.field_dependency import (
            FieldDependency,
            AvailableFields,
            validate_transition_dependencies,
        )

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
        from railway.core.dag.field_dependency import (
            FieldDependency,
            AvailableFields,
            validate_transition_dependencies,
        )

        available = AvailableFields(frozenset())
        dep = FieldDependency(
            requires=frozenset(["a", "b", "c"]),
            optional=frozenset(),
            provides=frozenset(),
        )
        result = validate_transition_dependencies(available, dep)
        assert result.is_valid is False
        # すべての不足フィールドが報告される
        error_str = str(result.errors)
        assert "a" in error_str
        assert "b" in error_str
        assert "c" in error_str


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

    def test_handles_empty_dict(self) -> None:
        """空の dict でも動作する。"""
        from railway.core.dag.field_dependency import field_dependency_from_dict

        data: dict = {}
        dep = field_dependency_from_dict(data)
        assert dep.requires == frozenset()
        assert dep.optional == frozenset()
        assert dep.provides == frozenset()


class TestEmptyFieldDependency:
    """EMPTY_FIELD_DEPENDENCY 定数のテスト。"""

    def test_empty_constant_exists(self) -> None:
        """空の依存関係を表す定数が存在する。"""
        from railway.core.dag.field_dependency import EMPTY_FIELD_DEPENDENCY

        assert EMPTY_FIELD_DEPENDENCY.requires == frozenset()
        assert EMPTY_FIELD_DEPENDENCY.optional == frozenset()
        assert EMPTY_FIELD_DEPENDENCY.provides == frozenset()
