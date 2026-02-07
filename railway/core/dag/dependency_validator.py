"""遷移グラフの依存関係バリデーション。

ノードコードから抽出した依存情報を使用して、
遷移グラフの全経路でフィールド依存関係を検証する。

設計原則:
- 純粋関数: 副作用なし、同じ入力に同じ出力
- イミュータブル: frozen=True の dataclass
- 関心の分離: バリデーションロジックのみを担当
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, get_type_hints

from railway.core.dag.field_dependency import (
    AvailableFields,
    FieldDependency,
)


@dataclass(frozen=True)
class DependencyValidationResult:
    """依存関係バリデーションの結果。

    Attributes:
        is_valid: バリデーションが成功したか
        errors: エラーメッセージのタプル
        warnings: 警告メッセージのタプル
    """

    is_valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def find_all_paths(
    start: str,
    transitions: dict[str, dict[str, str]],
    exit_nodes: set[str],
    max_path_length: int = 100,
) -> list[tuple[str, ...]]:
    """開始ノードから終端ノードまでの全経路を探索する。

    深さ優先探索（DFS）で全経路を列挙する。
    ループを含むグラフでも安全に動作するよう、経路長を制限する。

    Args:
        start: 開始ノード名
        transitions: 遷移グラフ（ノード名 → {状態 → 遷移先}）
        exit_nodes: 終端ノード名のセット
        max_path_length: 経路の最大長（ループ防止）

    Returns:
        経路のリスト（各経路はノード名のタプル）

    Example:
        >>> transitions = {"start": {"success::done": "end"}}
        >>> paths = find_all_paths("start", transitions, {"end"})
        >>> paths
        [("start", "end")]
    """
    paths: list[tuple[str, ...]] = []

    def dfs(current: str, path: list[str], visited: set[str]) -> None:
        # ループ検出: 同じノードを2回訪問したら中止
        if current in visited:
            return

        # 経路長制限
        if len(path) >= max_path_length:
            return

        path.append(current)
        visited.add(current)

        if current in exit_nodes:
            paths.append(tuple(path))
            path.pop()
            visited.discard(current)
            return

        if current not in transitions:
            # 遷移先がない（終端でないのに遷移がない）
            path.pop()
            visited.discard(current)
            return

        for target in transitions[current].values():
            dfs(target, path, visited)

        path.pop()
        visited.discard(current)

    dfs(start, [], set())
    return paths


def validate_path_dependencies(
    path: tuple[str, ...],
    dependencies: dict[str, FieldDependency],
    initial_fields: AvailableFields,
) -> DependencyValidationResult:
    """単一経路の依存関係を検証する。

    経路上の各ノードについて、その時点で利用可能なフィールドが
    ノードの requires を満たすか検証する。

    Args:
        path: ノード名のタプル
        dependencies: ノード名 → FieldDependency のマッピング
        initial_fields: 開始時に利用可能なフィールド

    Returns:
        DependencyValidationResult

    Example:
        >>> path = ("check_host", "escalate")
        >>> deps = {...}
        >>> result = validate_path_dependencies(path, deps, initial_fields)
        >>> result.is_valid
        True
    """
    errors: list[str] = []
    warnings: list[str] = []
    available = initial_fields

    for i, node_name in enumerate(path):
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
                f"ノード '{node_name}' の optional フィールドが利用不可: "
                f"{sorted(missing_optional)}"
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

    すべての経路を探索し、各経路で依存関係を検証する。
    1つでもエラーがあれば全体として無効と判定する。

    Args:
        start: 開始ノード名
        transitions: 遷移グラフ
        dependencies: ノード名 → FieldDependency のマッピング
        initial_fields: 開始時に利用可能なフィールド

    Returns:
        DependencyValidationResult

    Example:
        >>> result = validate_all_paths("start", transitions, deps, initial)
        >>> if not result.is_valid:
        ...     print(result.errors)
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


def validate_requires_against_contract(
    node_func: Callable[..., Any],
    node_name: str,
) -> DependencyValidationResult:
    """requires が Contract のフィールドに存在するか検証する。

    @node(requires=["field"]) と宣言されたフィールドが、
    実際の Contract に存在するかチェックする。

    Args:
        node_func: ノード関数
        node_name: ノード名（エラーメッセージ用）

    Returns:
        DependencyValidationResult

    Example:
        >>> @node(requires=["incident_id"])
        ... def my_node(ctx: MyContext): ...
        >>> result = validate_requires_against_contract(my_node, "my_node")
        >>> result.is_valid
        True
    """
    from railway.core.dag.dependency_extraction import extract_field_dependency

    dep = extract_field_dependency(node_func)
    if dep is None:
        return DependencyValidationResult(is_valid=True)

    try:
        hints = get_type_hints(node_func)
    except (TypeError, NameError):
        # 型ヒントが取得できない場合はスキップ
        return DependencyValidationResult(is_valid=True)

    # 第一引数の型を取得（ctx パラメータ）
    sig = inspect.signature(node_func)
    params = list(sig.parameters.keys())
    if not params:
        return DependencyValidationResult(is_valid=True)

    first_param = params[0]
    if first_param not in hints:
        return DependencyValidationResult(is_valid=True)

    contract_type = hints[first_param]

    # Pydantic モデルのフィールド情報を取得
    if not hasattr(contract_type, "model_fields"):
        return DependencyValidationResult(is_valid=True)

    contract_fields = set(contract_type.model_fields.keys())
    unknown_requires = dep.requires - contract_fields
    unknown_optional = dep.optional - contract_fields

    errors: list[str] = []
    warnings: list[str] = []

    if unknown_requires:
        errors.append(
            f"ノード '{node_name}' の requires に Contract にない"
            f"フィールドがあります: {sorted(unknown_requires)}"
        )
    if unknown_optional:
        warnings.append(
            f"ノード '{node_name}' の optional に Contract にない"
            f"フィールドがあります: {sorted(unknown_optional)}"
        )

    return DependencyValidationResult(
        is_valid=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
