# Issue #54: 遷移グラフ依存バリデータ

## 概要

`railway sync transition` 実行時に、遷移グラフの全経路でフィールド依存関係を検証する。
**YAML には依存情報を書かない** - ノードコードから依存を抽出して検証する。

## 設計

### 検証の流れ

```
1. YAML パース        → 遷移グラフ取得
2. ノードロード       → 各ノードの FieldDependency 抽出
3. 経路解析           → 開始ノードから終端ノードまでの全経路を探索
4. 依存検証           → 各経路で requires が満たされるか確認
5. エラー報告         → 不整合を分かりやすく報告
```

### 検証ルール

```
遷移 A → B が有効であるためには:
  - A の provides + A 実行前の AvailableFields ⊇ B の requires
```

### エラー例

```
$ railway sync transition --entry alert_workflow

❌ 依存関係エラー: 遷移 'check_severity → escalate' が無効です

  escalate が必要とするフィールド:
    requires: [incident_id]  ✅ 利用可能
    optional: [hostname]     ⚠️ 利用不可（check_host をスキップしたため）

  この時点で利用可能なフィールド:
    [incident_id, severity]

  提案:
    - escalate の optional から hostname を使用する処理を確認してください
    - または check_host を経由する遷移に変更してください
```

## タスク

### 1. Red Phase: 失敗するテストを作成

`tests/unit/core/dag/test_dependency_validator.py`:

```python
"""遷移グラフ依存バリデーションテスト。"""

import pytest
from railway import Contract, node
from railway.core.dag import Outcome
from railway.core.dag.field_dependency import FieldDependency, AvailableFields
from railway.core.dag.dependency_validator import (
    validate_all_paths,
    validate_path_dependencies,
    find_all_paths,
    DependencyValidationResult,
)


class WorkflowContext(Contract):
    incident_id: str
    hostname: str | None = None


class TestFindAllPaths:
    """経路探索テスト。"""

    def test_finds_single_path(self) -> None:
        """単一経路を発見する。"""
        transitions = {
            "start": {"success::done": "end"},
        }
        paths = find_all_paths("start", transitions, exit_nodes={"end"})
        assert paths == [("start", "end")]

    def test_finds_branching_paths(self) -> None:
        """分岐する経路をすべて発見する。"""
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


class TestValidatePathDependencies:
    """単一経路の依存検証テスト。"""

    def test_valid_path_with_satisfied_dependencies(self) -> None:
        """依存が満たされる経路は有効。"""
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


class TestValidateAllPaths:
    """全経路の依存検証テスト。"""

    def test_all_paths_valid(self) -> None:
        """すべての経路が有効な場合は成功。"""
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
        assert "check_severity → escalate" in str(result.errors)
```

### 2. Green Phase: バリデータ実装

`railway/core/dag/dependency_validator.py`:

```python
"""遷移グラフの依存関係バリデーション。

ノードコードから抽出した依存情報を使用して、
遷移グラフの全経路でフィールド依存関係を検証する。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from railway.core.dag.field_dependency import (
    FieldDependency,
    AvailableFields,
)


@dataclass(frozen=True)
class DependencyValidationResult:
    """依存関係バリデーションの結果。"""
    is_valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


def find_all_paths(
    start: str,
    transitions: dict[str, dict[str, str]],
    exit_nodes: set[str],
) -> list[tuple[str, ...]]:
    """開始ノードから終端ノードまでの全経路を探索する。

    Args:
        start: 開始ノード名
        transitions: 遷移グラフ
        exit_nodes: 終端ノード名のセット

    Returns:
        経路のリスト（各経路はノード名のタプル）
    """
    paths: list[tuple[str, ...]] = []

    def dfs(current: str, path: list[str]) -> None:
        path.append(current)

        if current in exit_nodes:
            paths.append(tuple(path))
            path.pop()
            return

        if current not in transitions:
            # 遷移先がない（終端でないのに遷移がない）
            path.pop()
            return

        for target in transitions[current].values():
            dfs(target, path)

        path.pop()

    dfs(start, [])
    return paths


def validate_path_dependencies(
    path: tuple[str, ...],
    dependencies: dict[str, FieldDependency],
    initial_fields: AvailableFields,
) -> DependencyValidationResult:
    """単一経路の依存関係を検証する。

    Args:
        path: ノード名のタプル
        dependencies: ノード名 → FieldDependency のマッピング
        initial_fields: 開始時に利用可能なフィールド

    Returns:
        DependencyValidationResult
    """
    errors: list[str] = []
    warnings: list[str] = []
    available = initial_fields

    for i, node_name in enumerate(path):
        if node_name.startswith("exit."):
            # 終端ノード
            dep = dependencies.get(node_name)
            if dep is not None:
                missing = dep.requires - available.fields
                if missing:
                    errors.append(
                        f"終端ノード '{node_name}' の必須フィールドが不足: {sorted(missing)}"
                    )
            continue

        dep = dependencies.get(node_name)
        if dep is None:
            # 依存宣言がないノードはスキップ
            continue

        # requires チェック
        missing_requires = dep.requires - available.fields
        if missing_requires:
            prev_node = path[i - 1] if i > 0 else "開始"
            errors.append(
                f"遷移 '{prev_node} → {node_name}' が無効です。\n"
                f"  必須フィールドが不足: {sorted(missing_requires)}\n"
                f"  利用可能なフィールド: {sorted(available.fields)}"
            )

        # optional チェック（警告のみ）
        missing_optional = dep.optional - available.fields
        if missing_optional:
            warnings.append(
                f"ノード '{node_name}' の optional フィールドが利用不可: {sorted(missing_optional)}"
            )

        # provides を追加
        available = available.after(dep)

    return DependencyValidationResult(
        is_valid=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def validate_all_paths(
    start: str,
    transitions: dict[str, dict[str, str]],
    dependencies: dict[str, FieldDependency],
    initial_fields: AvailableFields,
) -> DependencyValidationResult:
    """遷移グラフの全経路で依存関係を検証する。

    Args:
        start: 開始ノード名
        transitions: 遷移グラフ
        dependencies: ノード名 → FieldDependency のマッピング
        initial_fields: 開始時に利用可能なフィールド

    Returns:
        DependencyValidationResult
    """
    # 終端ノードを特定
    exit_nodes: set[str] = set()
    for targets in transitions.values():
        for target in targets.values():
            if target.startswith("exit."):
                exit_nodes.add(target)

    # 全経路を探索
    paths = find_all_paths(start, transitions, exit_nodes)

    # 各経路を検証
    all_errors: list[str] = []
    all_warnings: list[str] = []

    for path in paths:
        result = validate_path_dependencies(path, dependencies, initial_fields)
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)

    return DependencyValidationResult(
        is_valid=len(all_errors) == 0,
        errors=tuple(all_errors),
        warnings=tuple(all_warnings),
    )
```

### 3. sync コマンドへの統合

`railway/cli/commands/sync.py` を更新:

```python
from railway.core.dag.dependency_extraction import (
    load_node_dependencies,
    extract_initial_fields_from_start_node,
)

def sync_transition(entry: str) -> None:
    """遷移コードを生成する。"""
    # 1. YAML パース
    graph = parse_transition_graph(yaml_path)

    # 2. ノードから依存を抽出
    dependencies = load_node_dependencies(graph)

    # 3. 初期フィールドを自動導出（YAML には書かない）
    # 開始ノードの Contract の必須フィールドから導出
    initial_fields = extract_initial_fields_from_start_node(graph)

    logger.debug(f"初期フィールド（自動導出）: {initial_fields.fields}")

    # 4. 全経路の依存を検証
    result = validate_all_paths(
        start=graph.start,
        transitions=graph.transitions,
        dependencies=dependencies,
        initial_fields=initial_fields,
    )

    if not result.is_valid:
        print("❌ 依存関係エラー:")
        for error in result.errors:
            print(f"  {error}")
        raise SystemExit(1)

    if result.warnings:
        print("⚠️ 警告:")
        for warning in result.warnings:
            print(f"  {warning}")

    # 5. コード生成
    generate_transition_code(graph)
```

**設計判断:**
- `initial_fields` は YAML に書かない
- 開始ノードの Contract 型から自動導出（Issue #53 で実装）
- 型ヒントがない場合は空の `AvailableFields` を使用（すべての requires チェックが厳密になる）

### 4. requires と Contract フィールドの整合性チェック

`@node(requires=["field_x"])` と宣言しても、Contract に `field_x` が存在しない場合を検出:

```python
def validate_requires_against_contract(
    node_func: Callable,
    node_name: str,
) -> ValidationResult:
    """requires が Contract のフィールドに存在するか検証する。

    Args:
        node_func: ノード関数
        node_name: ノード名（エラーメッセージ用）

    Returns:
        ValidationResult
    """
    from typing import get_type_hints
    from railway.core.dag.dependency_extraction import extract_field_dependency

    dep = extract_field_dependency(node_func)
    if dep is None:
        return ValidationResult(is_valid=True, errors=(), warnings=())

    try:
        hints = get_type_hints(node_func)
        ctx_type = hints.get("ctx")

        if ctx_type and hasattr(ctx_type, "model_fields"):
            contract_fields = set(ctx_type.model_fields.keys())
            unknown_requires = dep.requires - contract_fields
            unknown_optional = dep.optional - contract_fields

            errors = []
            warnings = []

            if unknown_requires:
                errors.append(
                    f"ノード '{node_name}' の requires に Contract にないフィールドがあります: {sorted(unknown_requires)}"
                )
            if unknown_optional:
                warnings.append(
                    f"ノード '{node_name}' の optional に Contract にないフィールドがあります: {sorted(unknown_optional)}"
                )

            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=tuple(errors),
                warnings=tuple(warnings),
            )

    except (TypeError, AttributeError):
        pass

    return ValidationResult(is_valid=True, errors=(), warnings=())
```

**テストケース:**

```python
class TestValidateRequiresAgainstContract:
    """requires と Contract の整合性チェックテスト。"""

    def test_valid_when_requires_matches_contract(self) -> None:
        """requires が Contract フィールドに存在する場合は有効。"""
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
        class Ctx(Contract):
            incident_id: str

        @node(requires=["incident_id", "non_existent_field"])
        def my_node(ctx: Ctx) -> tuple[Ctx, Outcome]:
            return ctx, Outcome.success("done")

        result = validate_requires_against_contract(my_node, "my_node")
        assert not result.is_valid
        assert "non_existent_field" in str(result.errors)
```

### 5. Refactor Phase

- エラーメッセージの改善（修正提案を含める）
- 循環検出の追加
- パフォーマンス最適化（大きなグラフ対応）

## 完了条件

- [ ] `find_all_paths()` が全経路を探索できる
- [ ] `validate_path_dependencies()` が依存を検証できる
- [ ] `validate_all_paths()` が全経路を検証できる
- [ ] `validate_requires_against_contract()` が Contract との整合性を検証できる
- [ ] `extract_initial_fields_from_start_node()` が初期フィールドを自動導出できる
- [ ] optional フィールドの不足は警告のみ
- [ ] `railway sync transition` に統合されている
- [ ] すべてのテストが通過

## 依存関係

- Issue #51 (FieldDependency 型システム) が完了していること
- Issue #52 (Node 依存宣言拡張) が完了していること
- Issue #53 (依存情報の自動抽出) が完了していること

## 関連ファイル

- `railway/core/dag/dependency_validator.py` (新規)
- `railway/cli/commands/sync.py` (更新)
- `tests/unit/core/dag/test_dependency_validator.py` (新規)
