# Issue #03: nodeデコレータ拡張

## 概要
nodeデコレータを拡張し、入力依存（inputs）と出力型（output）を宣言可能にする。

## 依存関係
- Issue #01: Output Model基本設計（先行）
- Issue #02: Contractベースクラス実装（先行）

## 現在の実装
```python
@node
def fetch_data(user_id: int) -> dict:
    return {"user": get_user(user_id)}
```

## 新しい実装

### nodeデコレータの新シグネチャ
```python
@node(
    inputs: dict[str, type[Contract]] = {},  # 入力依存の宣言
    output: type[Contract] = None,            # 出力型の宣言
)
```

### パターン別の使用方法

#### パターンA: 入力なし（起点ノード）
```python
from railway import node
from contracts.user_contracts import UsersFetchResult, User

@node(output=UsersFetchResult)
def fetch_users() -> UsersFetchResult:
    """ユーザー一覧を取得する"""
    users = api.get_users()
    return UsersFetchResult(
        users=[User(**u) for u in users],
        total=len(users),
        fetched_at=datetime.now(),
    )
```

#### パターンB: 単一入力
```python
from railway import node
from contracts.user_contracts import UsersFetchResult, UsersProcessResult

@node(
    inputs={"users": UsersFetchResult},
    output=UsersProcessResult,
)
def process_users(users: UsersFetchResult) -> UsersProcessResult:
    """ユーザーをアクティブ/非アクティブに分類"""
    active = [u for u in users.users if is_active(u)]
    inactive = [u for u in users.users if not is_active(u)]
    return UsersProcessResult(
        active_users=active,
        inactive_users=inactive,
    )
```

#### パターンC: 複数入力（DAG的依存）
```python
from railway import node
from contracts.user_contracts import UsersFetchResult
from contracts.order_contracts import OrdersFetchResult
from contracts.report_contracts import ReportResult

@node(
    inputs={
        "users": UsersFetchResult,
        "orders": OrdersFetchResult,
    },
    output=ReportResult,
)
def generate_report(
    users: UsersFetchResult,
    orders: OrdersFetchResult,
) -> ReportResult:
    """ユーザーと注文からレポートを生成"""
    return ReportResult(
        content=f"{users.total} users, {len(orders.orders)} orders",
        generated_at=datetime.now(),
    )
```

#### パターンD: パラメータ入力
```python
from railway import node
from contracts.params import ReportParams
from contracts.report_contracts import ReportResult

@node(
    inputs={"params": ReportParams},
    output=ReportResult,
)
def generate_custom_report(params: ReportParams) -> ReportResult:
    """パラメータに基づいてレポートを生成"""
    return ReportResult(
        user_id=params.user_id,
        include_details=params.include_details,
    )
```

## 実装詳細

### nodeデコレータの実装
```python
# railway/core/decorators.py
from typing import Callable, Type, Any, TypeVar
from functools import wraps
from loguru import logger
from railway.core.contract import Contract

T = TypeVar("T", bound=Contract)

def node(
    func: Callable = None,
    *,
    inputs: dict[str, Type[Contract]] = None,
    output: Type[Contract] = None,
):
    """
    Node decorator for typed execution.

    Args:
        func: The function to decorate (auto-provided when used without args)
        inputs: Dictionary mapping parameter names to expected Contract types
        output: Expected output Contract type

    Example:
        @node(output=UsersFetchResult)
        def fetch_users() -> UsersFetchResult:
            ...

        @node(inputs={"users": UsersFetchResult}, output=ProcessResult)
        def process(users: UsersFetchResult) -> ProcessResult:
            ...
    """
    inputs = inputs or {}

    def decorator(fn: Callable) -> Callable:
        node_name = fn.__name__

        @wraps(fn)
        def wrapper(*args, **kwargs):
            logger.info(f"[{node_name}] Starting...")
            try:
                result = fn(*args, **kwargs)

                # 出力型の検証
                if output is not None and not isinstance(result, output):
                    raise TypeError(
                        f"Node '{node_name}' expected to return {output.__name__}, "
                        f"got {type(result).__name__}"
                    )

                logger.info(f"[{node_name}] Completed")
                return result
            except Exception as e:
                logger.error(f"[{node_name}] Failed: {e}")
                raise

        # メタデータを付与
        wrapper._node_name = node_name
        wrapper._node_inputs = inputs
        wrapper._node_output = output
        wrapper._original_func = fn

        return wrapper

    # @node または @node() の両方に対応
    if func is not None:
        return decorator(func)
    return decorator
```

### 入力型の検証
```python
def validate_node_inputs(
    node_func: Callable,
    provided: dict[str, Any],
) -> dict[str, Contract]:
    """
    Validate and convert inputs for a node.

    Args:
        node_func: The decorated node function
        provided: Dictionary of provided input values

    Returns:
        Validated inputs as Contract instances
    """
    inputs_spec = getattr(node_func, "_node_inputs", {})
    validated = {}

    for param_name, expected_type in inputs_spec.items():
        if param_name not in provided:
            raise ValueError(
                f"Missing required input '{param_name}' "
                f"of type {expected_type.__name__}"
            )

        value = provided[param_name]
        if not isinstance(value, expected_type):
            raise TypeError(
                f"Input '{param_name}' expected {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )
        validated[param_name] = value

    return validated
```

## 後方互換性

### 旧スタイルのサポート（非推奨）
```python
# 従来のContext受け取りスタイル（非推奨警告を出力）
@node
def legacy_node(ctx: Context) -> None:
    import warnings
    warnings.warn(
        "Context-based nodes are deprecated. Use typed inputs/outputs.",
        DeprecationWarning,
    )
    ctx["legacy_node"] = {"data": "..."}
```

### 検出と警告
```python
def decorator(fn: Callable) -> Callable:
    # 旧スタイルの検出
    sig = inspect.signature(fn)
    params = list(sig.parameters.values())

    if len(params) == 1 and params[0].annotation == Context:
        import warnings
        warnings.warn(
            f"Node '{fn.__name__}' uses deprecated Context-based style. "
            "Consider migrating to typed inputs/outputs.",
            DeprecationWarning,
            stacklevel=2,
        )
        # 旧スタイルとして処理
        return _legacy_node_decorator(fn)

    # 新スタイルとして処理
    return _typed_node_decorator(fn, inputs, output)
```

## nodeのメタデータ

| 属性 | 型 | 説明 |
|------|-----|------|
| `_node_name` | `str` | ノード名（関数名） |
| `_node_inputs` | `dict[str, Type[Contract]]` | 入力依存の宣言 |
| `_node_output` | `Type[Contract] \| None` | 出力型の宣言 |
| `_original_func` | `Callable` | 元の関数 |

## テスト要件
- 入力なしnodeのデコレート
- 単一入力nodeのデコレート
- 複数入力nodeのデコレート
- 出力型の検証
- 入力型の検証
- 旧スタイルnodeの検出と警告
- メタデータの付与

## 関連ファイル
- 修正: `railway/core/decorators.py`
- 修正: `tests/unit/core/test_decorators.py`

## 優先度
最高
