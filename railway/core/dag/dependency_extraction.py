"""依存情報の自動抽出モジュール。

ノード関数やContract型から依存情報を抽出する純粋関数群。

設計原則:
- 純粋関数: 副作用なし、同じ入力に同じ出力
- エラーハンドリング: None / 空の結果で安全に失敗
- 関心の分離: 抽出ロジックのみを担当
"""

from __future__ import annotations

import importlib
import inspect
from typing import Any, Callable, get_type_hints

from railway.core.dag.field_dependency import (
    AvailableFields,
    EMPTY_FIELD_DEPENDENCY,
    FieldDependency,
)
from railway.core.dag.types import TransitionGraph


def extract_field_dependency(node_func: Callable[..., Any]) -> FieldDependency | None:
    """ノード関数から FieldDependency を抽出する。

    @node デコレータで宣言された依存情報を取得する。
    デコレータなしの関数は None を返す。

    Args:
        node_func: ノード関数

    Returns:
        FieldDependency または None

    Example:
        >>> @node(requires=["a"], provides=["b"])
        ... def my_node(ctx): ...
        >>> dep = extract_field_dependency(my_node)
        >>> dep.requires
        frozenset({'a'})
    """
    # _field_dependency 属性があれば直接返す
    if hasattr(node_func, "_field_dependency"):
        return node_func._field_dependency

    # _requires, _optional, _provides 属性から構築
    if hasattr(node_func, "_requires"):
        return FieldDependency(
            requires=getattr(node_func, "_requires", frozenset()),
            optional=getattr(node_func, "_optional", frozenset()),
            provides=getattr(node_func, "_provides", frozenset()),
        )

    # @node デコレータなしの関数
    return None


def import_node_function(module_path: str, function_name: str) -> Callable[..., Any]:
    """ノード関数を動的にインポートする。

    Args:
        module_path: モジュールパス（例: "nodes.check_host"）
        function_name: 関数名（例: "check_host"）

    Returns:
        インポートされた関数

    Raises:
        ImportError: モジュールまたは関数が見つからない場合

    Example:
        >>> func = import_node_function("nodes.start", "start")
        >>> callable(func)
        True
    """
    # キャッシュを無効化（テスト時の動的モジュール作成に対応）
    importlib.invalidate_caches()

    module = importlib.import_module(module_path)
    if not hasattr(module, function_name):
        raise ImportError(
            f"関数 '{function_name}' がモジュール '{module_path}' に見つかりません"
        )
    return getattr(module, function_name)


def load_node_dependencies(
    graph: TransitionGraph,
) -> dict[str, FieldDependency]:
    """遷移グラフの全ノードから依存情報をロードする。

    未実装のノードやデコレータなしのノードはスキップされる。

    Args:
        graph: 遷移グラフ

    Returns:
        ノード名から FieldDependency へのマッピング

    Example:
        >>> deps = load_node_dependencies(graph)
        >>> deps["check_host"].requires
        frozenset({'incident_id'})
    """
    result: dict[str, FieldDependency] = {}

    for node_def in graph.nodes:
        try:
            func = import_node_function(node_def.module, node_def.function)
            dep = extract_field_dependency(func)
            if dep is not None:
                result[node_def.name] = dep
        except ImportError:
            # 未実装のノードはスキップ
            continue
        except Exception:
            # その他のエラーもスキップ（堅牢性）
            continue

    return result


def extract_initial_fields_from_start_node(graph: TransitionGraph) -> AvailableFields:
    """開始ノードの Contract 型から初期フィールドを抽出する。

    Contract の必須フィールド（デフォルト値なし）を初期フィールドとして返す。

    Args:
        graph: 遷移グラフ

    Returns:
        初期フィールドを含む AvailableFields

    Example:
        >>> class MyContext(Contract):
        ...     required_field: str
        ...     optional_field: str | None = None
        >>> initial = extract_initial_fields_from_start_node(graph)
        >>> "required_field" in initial.fields
        True
        >>> "optional_field" in initial.fields
        False
    """
    # 開始ノードを取得
    start_node_def = graph.get_node(graph.start_node)
    if start_node_def is None:
        return AvailableFields(frozenset())

    # 関数をインポート
    try:
        func = import_node_function(start_node_def.module, start_node_def.function)
    except ImportError:
        return AvailableFields(frozenset())

    # 型ヒントを取得
    try:
        hints = get_type_hints(func)
    except Exception:
        return AvailableFields(frozenset())

    # 第一引数の型を取得（ctx パラメータ）
    sig = inspect.signature(func)
    params = list(sig.parameters.keys())
    if not params:
        return AvailableFields(frozenset())

    first_param = params[0]
    if first_param not in hints:
        return AvailableFields(frozenset())

    contract_type = hints[first_param]

    # Contract の必須フィールドを抽出
    return _extract_required_fields_from_contract(contract_type)


def _extract_required_fields_from_contract(contract_type: type) -> AvailableFields:
    """Contract クラスから必須フィールドを抽出する。

    Pydantic BaseModel のフィールド情報を解析し、
    デフォルト値がないフィールドを必須フィールドとして返す。

    Args:
        contract_type: Contract クラス

    Returns:
        必須フィールドを含む AvailableFields
    """
    # Pydantic モデルのフィールド情報を取得
    if not hasattr(contract_type, "model_fields"):
        return AvailableFields(frozenset())

    required_fields: set[str] = set()

    for field_name, field_info in contract_type.model_fields.items():
        # デフォルト値がないフィールドが必須
        if field_info.is_required():
            required_fields.add(field_name)

    return AvailableFields(frozenset(required_fields))
