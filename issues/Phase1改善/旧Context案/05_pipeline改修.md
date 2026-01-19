# Issue #05: pipeline改修

## 概要
pipelineをコンテキスト変数ベースの実行に改修する。

## 依存関係
- Issue #01: コンテキスト変数基本設計（先行）
- Issue #02: Contextクラス実装（先行）
- Issue #03: nodeデコレータ改修（先行）
- Issue #04: CLIコマンド拡張（先行）

## 現在の実装
```python
result = pipeline(
    initial_value,
    step1,
    step2,
    step3,
)
```

## 新しい実装

### パターン1: 明示的なnode指定（推奨）
```python
ctx = Context(entry_point="my_entry")
ctx.set_param("user_id", 1)

# pipelineがnodeを自動登録するため、register_node()は不要
pipeline(ctx, fetch_data, process_data)
```

### パターン2: context.yamlからの自動実行
```python
ctx = Context.from_entry("my_entry")
ctx.set_param("user_id", 1)

pipeline(ctx)  # ctx.meta.nodesの順序で実行
```

**推奨**: パターン1（明示的）を基本とし、パターン2は簡易実行用

## 改修内容

### pipeline関数のシグネチャ
```python
def pipeline(
    ctx: Context,
    *nodes: Callable[[Context], None],
) -> Context:
    """
    Execute a pipeline of nodes with shared context.

    Args:
        ctx: Context object containing params and node results
        *nodes: Node functions to execute. If not provided,
                executes nodes registered in ctx.meta.nodes

    Returns:
        The context object with all node results

    Example:
        # Explicit nodes
        pipeline(ctx, fetch_data, process_data, save_data)

        # Auto-execute from context.yaml
        pipeline(ctx)
    """
```

### 実行ロジック
```python
from railway.core.context import Context
from railway.core.registry import get_node_by_name  # nodeレジストリから取得

def pipeline(ctx: Context, *nodes) -> Context:
    # nodesが指定されていなければ、コンテキストの登録順を使用
    if not nodes:
        node_names = ctx.meta.nodes
        nodes = tuple(get_node_by_name(name) for name in node_names)

    if not nodes:
        logger.warning("No nodes to execute")
        return ctx

    logger.debug(f"Pipeline starting with {len(nodes)} nodes")

    for node_func in nodes:
        node_name = getattr(node_func, "_node_name", node_func.__name__)

        # nodeがコンテキストに登録されていなければ自動登録
        if node_name not in ctx.meta.nodes:
            ctx.register_node(node_name)

        try:
            node_func(ctx)
        except Exception as e:
            logger.error(f"Pipeline failed at node '{node_name}': {e}")
            raise

    logger.debug("Pipeline completed successfully")
    return ctx
```

### nodeレジストリ

`pipeline(ctx)`でnode名からnode関数を解決するためのレジストリ:

```python
# railway/core/registry.py
from typing import Callable
from importlib import import_module

_node_registry: dict[str, Callable] = {}

def register_node_func(node_func: Callable) -> None:
    """nodeをレジストリに登録"""
    name = getattr(node_func, "_node_name", node_func.__name__)
    _node_registry[name] = node_func

def get_node_by_name(name: str) -> Callable:
    """名前からnode関数を取得"""
    if name in _node_registry:
        return _node_registry[name]

    # レジストリにない場合、動的インポートを試みる
    try:
        module = import_module(f"nodes.{name}")
        return getattr(module, name)
    except (ImportError, AttributeError) as e:
        raise ValueError(f"Node '{name}' not found") from e
```

### async_pipeline
```python
async def async_pipeline(
    ctx: Context,
    *nodes: Callable[[Context], None] | Callable[[Context], Coroutine],
) -> Context:
    """Async version of pipeline."""
    if not nodes:
        node_names = ctx.meta.nodes
        nodes = tuple(get_node_by_name(name) for name in node_names)

    for node_func in nodes:
        node_name = getattr(node_func, "_node_name", node_func.__name__)

        if node_name not in ctx.meta.nodes:
            ctx.register_node(node_name)

        is_async = inspect.iscoroutinefunction(
            getattr(node_func, "_original_func", node_func)
        )

        try:
            if is_async:
                await node_func(ctx)
            else:
                node_func(ctx)
        except Exception as e:
            logger.error(f"Async pipeline failed at node '{node_name}': {e}")
            raise

    return ctx
```

## 使用例

### 基本的な使用（推奨）
```python
from railway import Context, pipeline, node

@node
def fetch_data(ctx: Context) -> None:
    user_id = ctx.get_param("user_id")
    ctx["fetch_data"] = {"user": get_user(user_id)}

@node
def process_data(ctx: Context) -> None:
    user = ctx["fetch_data"]["user"]
    ctx["process_data"] = {"processed": transform(user)}

# 実行
ctx = Context(entry_point="my_entry")
ctx.set_param("user_id", 1)

result_ctx = pipeline(ctx, fetch_data, process_data)
print(result_ctx["process_data"]["processed"])
```

### context.yamlからの自動実行
```python
# context.yamlに登録済みのnodeを順に実行
ctx = Context.from_entry("my_entry")
ctx.set_param("user_id", 1)
pipeline(ctx)
```

## 後方互換性

**方針**: v1.0.0で旧形式を廃止

**移行ガイド**:
```python
# 旧形式（廃止）
result = pipeline(fetch_data(user_id), process_data, save_data)

# 新形式
ctx = Context(entry_point="my_entry")
ctx.set_param("user_id", user_id)
pipeline(ctx, fetch_data, process_data, save_data)
result = ctx["save_data"]
```

## テスト要件
- 明示的node指定でのpipeline実行
- ctx.meta.nodesからの自動実行
- nodeレジストリからの解決
- エラーハンドリング
- async_pipeline
- node自動登録

## 関連ファイル
- 修正: `railway/core/pipeline.py`
- 新規: `railway/core/registry.py`
- 修正: `tests/unit/core/test_pipeline.py`
- 修正: `tests/integration/test_full_workflow.py`

## 優先度
最高
