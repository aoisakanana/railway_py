"""遷移グラフ依存バリデーションテスト。

TDD Red Phase: このテストは最初は失敗する（モジュールが存在しない）
"""

import pytest

from railway import Contract, node
from railway.core.dag import Outcome
from railway.core.dag.field_dependency import FieldDependency, AvailableFields


class WorkflowContext(Contract):
    """テスト用 Contract。"""

    incident_id: str
    severity: str
    hostname: str | None = None


class TestFindAllPaths:
    """経路探索テスト。"""

    def test_finds_single_path(self) -> None:
        """単一経路を発見する。"""
        from railway.core.dag.dependency_validator import find_all_paths

        transitions = {
            "start": {"success::done": "end"},
        }
        paths = find_all_paths("start", transitions, exit_nodes={"end"})
        assert paths == [("start", "end")]

    def test_finds_branching_paths(self) -> None:
        """分岐する経路をすべて発見する。"""
        from railway.core.dag.dependency_validator import find_all_paths

        transitions = {
            "check_severity": {
                "success::critical": "escalate",
                "success::normal": "log_only",
            },
            "escalate": {"success::done": "exit.success.done"},
            "log_only": {"success::done": "exit.success.done"},
        }
        paths = find_all_paths(
            "check_severity",
            transitions,
            exit_nodes={"exit.success.done"},
        )
        assert len(paths) == 2
        assert ("check_severity", "escalate", "exit.success.done") in paths
        assert ("check_severity", "log_only", "exit.success.done") in paths

    def test_finds_convergent_paths(self) -> None:
        """合流する経路を発見する。"""
        from railway.core.dag.dependency_validator import find_all_paths

        transitions = {
            "start": {
                "success::a": "process_a",
                "success::b": "process_b",
            },
            "process_a": {"success::done": "merge"},
            "process_b": {"success::done": "merge"},
            "merge": {"success::done": "exit.success.done"},
        }
        paths = find_all_paths(
            "start",
            transitions,
            exit_nodes={"exit.success.done"},
        )
        assert len(paths) == 2

    def test_handles_loop_by_limiting_visits(self) -> None:
        """ループを含むグラフでも安全に探索する。"""
        from railway.core.dag.dependency_validator import find_all_paths

        transitions = {
            "start": {"success::next": "process"},
            "process": {
                "success::retry": "process",  # ループ
                "success::done": "exit.success.done",
            },
        }
        # ループを含むグラフでも終了できる
        paths = find_all_paths(
            "start",
            transitions,
            exit_nodes={"exit.success.done"},
        )
        # ループを辿らない経路のみ返す
        assert len(paths) >= 1


class TestValidatePathDependencies:
    """単一経路の依存検証テスト。"""

    def test_valid_path_with_satisfied_dependencies(self) -> None:
        """依存が満たされる経路は有効。"""
        from railway.core.dag.dependency_validator import (
            validate_path_dependencies,
            DependencyValidationResult,
        )

        path = ("check_host", "escalate")
        dependencies = {
            "check_host": FieldDependency(
                requires=frozenset(["incident_id"]),
                optional=frozenset(),
                provides=frozenset(["hostname"]),
            ),
            "escalate": FieldDependency(
                requires=frozenset(["incident_id", "hostname"]),
                optional=frozenset(),
                provides=frozenset(["escalated"]),
            ),
        }
        initial_fields = AvailableFields(frozenset(["incident_id", "severity"]))

        result = validate_path_dependencies(path, dependencies, initial_fields)
        assert result.is_valid

    def test_invalid_path_with_missing_dependency(self) -> None:
        """依存が満たされない経路は無効。"""
        from railway.core.dag.dependency_validator import (
            validate_path_dependencies,
            DependencyValidationResult,
        )

        path = ("check_severity", "escalate")  # check_host をスキップ
        dependencies = {
            "check_severity": FieldDependency(
                requires=frozenset(["incident_id"]),
                optional=frozenset(),
                provides=frozenset(["severity_level"]),
            ),
            "escalate": FieldDependency(
                requires=frozenset(["hostname"]),  # hostname が必要
                optional=frozenset(),
                provides=frozenset(["escalated"]),
            ),
        }
        initial_fields = AvailableFields(frozenset(["incident_id", "severity"]))

        result = validate_path_dependencies(path, dependencies, initial_fields)
        assert not result.is_valid
        assert "hostname" in result.errors[0]

    def test_optional_does_not_fail_validation(self) -> None:
        """optional フィールドがなくても検証は通過する。"""
        from railway.core.dag.dependency_validator import (
            validate_path_dependencies,
            DependencyValidationResult,
        )

        path = ("check_severity", "escalate")
        dependencies = {
            "check_severity": FieldDependency(
                requires=frozenset(["incident_id"]),
                optional=frozenset(),
                provides=frozenset(),
            ),
            "escalate": FieldDependency(
                requires=frozenset(["incident_id"]),
                optional=frozenset(["hostname"]),  # optional なので OK
                provides=frozenset(["escalated"]),
            ),
        }
        initial_fields = AvailableFields(frozenset(["incident_id", "severity"]))

        result = validate_path_dependencies(path, dependencies, initial_fields)
        assert result.is_valid
        # 警告は出る
        assert len(result.warnings) > 0
        assert "hostname" in result.warnings[0]

    def test_handles_exit_nodes(self) -> None:
        """終端ノードも検証する。"""
        from railway.core.dag.dependency_validator import (
            validate_path_dependencies,
            DependencyValidationResult,
        )

        path = ("process", "exit.success.done")
        dependencies = {
            "process": FieldDependency(
                requires=frozenset(["incident_id"]),
                optional=frozenset(),
                provides=frozenset(["result"]),
            ),
            "exit.success.done": FieldDependency(
                requires=frozenset(["result"]),
                optional=frozenset(),
                provides=frozenset(),
            ),
        }
        initial_fields = AvailableFields(frozenset(["incident_id"]))

        result = validate_path_dependencies(path, dependencies, initial_fields)
        assert result.is_valid


class TestValidateAllPaths:
    """全経路の依存検証テスト。"""

    def test_all_paths_valid(self) -> None:
        """すべての経路が有効な場合は成功。"""
        from railway.core.dag.dependency_validator import (
            validate_all_paths,
            DependencyValidationResult,
        )

        transitions = {
            "check_host": {"success::found": "escalate"},
            "escalate": {"success::done": "exit.success.done"},
        }
        dependencies = {
            "check_host": FieldDependency(
                requires=frozenset(["incident_id"]),
                optional=frozenset(),
                provides=frozenset(["hostname"]),
            ),
            "escalate": FieldDependency(
                requires=frozenset(["incident_id", "hostname"]),
                optional=frozenset(),
                provides=frozenset(["escalated"]),
            ),
        }
        initial_fields = AvailableFields(frozenset(["incident_id"]))

        result = validate_all_paths(
            start="check_host",
            transitions=transitions,
            dependencies=dependencies,
            initial_fields=initial_fields,
        )
        assert result.is_valid

    def test_one_invalid_path_fails(self) -> None:
        """1つでも無効な経路があれば失敗。"""
        from railway.core.dag.dependency_validator import (
            validate_all_paths,
            DependencyValidationResult,
        )

        transitions = {
            "check_severity": {
                "success::critical": "check_host",
                "success::normal": "escalate",  # check_host をスキップ
            },
            "check_host": {"success::found": "escalate"},
            "escalate": {"success::done": "exit.success.done"},
        }
        dependencies = {
            "check_severity": FieldDependency(
                requires=frozenset(["incident_id"]),
                optional=frozenset(),
                provides=frozenset(),
            ),
            "check_host": FieldDependency(
                requires=frozenset(["incident_id"]),
                optional=frozenset(),
                provides=frozenset(["hostname"]),
            ),
            "escalate": FieldDependency(
                requires=frozenset(["hostname"]),  # hostname が必要
                optional=frozenset(),
                provides=frozenset(["escalated"]),
            ),
        }
        initial_fields = AvailableFields(frozenset(["incident_id"]))

        result = validate_all_paths(
            start="check_severity",
            transitions=transitions,
            dependencies=dependencies,
            initial_fields=initial_fields,
        )
        assert not result.is_valid
        # 無効な経路が報告される
        assert any("escalate" in e for e in result.errors)

    def test_collects_all_warnings(self) -> None:
        """すべてのパスからの警告を収集する。"""
        from railway.core.dag.dependency_validator import (
            validate_all_paths,
            DependencyValidationResult,
        )

        transitions = {
            "process": {"success::done": "exit.success.done"},
        }
        dependencies = {
            "process": FieldDependency(
                requires=frozenset(["incident_id"]),
                optional=frozenset(["extra_data"]),  # optional で利用不可
                provides=frozenset(),
            ),
        }
        initial_fields = AvailableFields(frozenset(["incident_id"]))

        result = validate_all_paths(
            start="process",
            transitions=transitions,
            dependencies=dependencies,
            initial_fields=initial_fields,
        )
        assert result.is_valid
        assert len(result.warnings) > 0


class TestValidateRequiresAgainstContract:
    """requires と Contract の整合性チェックテスト。"""

    def test_valid_when_requires_matches_contract(self) -> None:
        """requires が Contract フィールドに存在する場合は有効。"""
        from railway.core.dag.dependency_validator import (
            validate_requires_against_contract,
        )

        class Ctx(Contract):
            incident_id: str
            hostname: str | None = None

        @node(requires=["incident_id"], optional=["hostname"])
        def my_node(ctx: Ctx) -> tuple[Ctx, Outcome]:
            return ctx, Outcome.success("done")

        result = validate_requires_against_contract(my_node, "my_node")
        assert result.is_valid

    def test_invalid_when_requires_not_in_contract(self) -> None:
        """requires に Contract にないフィールドがある場合は無効。"""
        from railway.core.dag.dependency_validator import (
            validate_requires_against_contract,
        )

        class Ctx(Contract):
            incident_id: str

        @node(requires=["incident_id", "non_existent_field"])
        def my_node(ctx: Ctx) -> tuple[Ctx, Outcome]:
            return ctx, Outcome.success("done")

        result = validate_requires_against_contract(my_node, "my_node")
        assert not result.is_valid
        assert "non_existent_field" in str(result.errors)

    def test_warning_when_optional_not_in_contract(self) -> None:
        """optional に Contract にないフィールドがある場合は警告。"""
        from railway.core.dag.dependency_validator import (
            validate_requires_against_contract,
        )

        class Ctx(Contract):
            incident_id: str

        @node(requires=["incident_id"], optional=["unknown_optional"])
        def my_node(ctx: Ctx) -> tuple[Ctx, Outcome]:
            return ctx, Outcome.success("done")

        result = validate_requires_against_contract(my_node, "my_node")
        # optional の不整合は警告のみ
        assert result.is_valid
        assert "unknown_optional" in str(result.warnings)

    def test_valid_for_node_without_contract_type_hint(self) -> None:
        """型ヒントがないノードは検証をスキップ。"""
        from railway.core.dag.dependency_validator import (
            validate_requires_against_contract,
        )

        @node(requires=["incident_id"])
        def my_node(ctx):  # 型ヒントなし
            return ctx, Outcome.success("done")

        result = validate_requires_against_contract(my_node, "my_node")
        # 型情報がないので検証スキップ
        assert result.is_valid

    def test_valid_for_undecorated_function(self) -> None:
        """@node デコレータがない関数は検証をスキップ。"""
        from railway.core.dag.dependency_validator import (
            validate_requires_against_contract,
        )

        def plain_function(ctx):
            return ctx

        result = validate_requires_against_contract(plain_function, "plain_function")
        assert result.is_valid
