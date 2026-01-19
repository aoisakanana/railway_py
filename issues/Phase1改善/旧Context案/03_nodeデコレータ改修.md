# Issue #03: nodeデコレータ改修

## 概要
nodeデコレータを改修し、コンテキスト変数を受け取る形に変更する。

## 依存関係
- Issue #01: コンテキスト変数基本設計（先行）
- Issue #02: Contextクラス実装（先行）

## 現在の実装
```python
@node
def fetch_data(user_id: int) -> dict:
    return {"user": get_user(user_id)}

# 使用
result = fetch_data(1)
```

## 新しい実装
```python
@node
def fetch_data(ctx: Context) -> None:
    user_id = ctx.get_param("user_id")
    user = get_user(user_id)
    ctx["fetch_data"] = {"user": user}

# 使用
ctx = Context(entry_point="my_entry")
ctx.register_node("fetch_data")
ctx.set_param("user_id", 1)
fetch_data(ctx)
```

## 改修内容

### nodeデコレータの変更
```python
from typing import Callable
from railway.core.context import Context

def node(func: Callable[[Context], None]) -> Callable[[Context], None]:
    """
    Node decorator for context-based execution.

    The decorated function:
    1. Receives a Context object as its only argument
    2. Reads parameters via ctx.get_param()
    3. Reads other node results via ctx[node_name]
    4. Writes its result to ctx[node_name]

    Example:
        @node
        def fetch_data(ctx: Context) -> None:
            user_id = ctx.get_param("user_id")
            ctx["fetch_data"] = {"user": get_user(user_id)}
    """
    import functools
    from loguru import logger

    node_name = func.__name__

    @functools.wraps(func)
    def wrapper(ctx: Context) -> None:
        logger.info(f"[{node_name}] Starting...")
        try:
            func(ctx)
            logger.info(f"[{node_name}] Completed")
        except Exception as e:
            logger.error(f"[{node_name}] Failed: {e}")
            raise

    wrapper._node_name = node_name
    wrapper._original_func = func
    return wrapper
```

### 設計決定: 明示的な結果書き込み

**採用**: nodeは明示的に`ctx[node_name] = {...}`で結果を書き込む

**理由**:
- 明示的で分かりやすい
- 何を書き込むか制御可能
- 戻り値がNoneなので副作用が明確

**不採用案**: 戻り値を自動的にctx[node_name]に設定
- 暗黙的で分かりにくい
- 戻り値とctxへの書き込みが混在すると混乱する

## nodeの責務

1. **入力**: コンテキストから必要なパラメータ・他node結果を取得
2. **処理**: ビジネスロジックを実行
3. **出力**: 結果をコンテキストの自身のキーに書き込み

```python
@node
def process_data(ctx: Context) -> None:
    # 1. 入力
    user = ctx["fetch_data"]["user"]
    options = ctx.get_param("options", {})

    # 2. 処理
    result = transform(user, options)

    # 3. 出力
    ctx["process_data"] = {"result": result}
```

## nodeの使用パターン

### パターン1: pipeline経由（推奨）
```python
# pipelineがnodeを自動登録するため、register_node不要
ctx = Context(entry_point="my_entry")
ctx.set_param("user_id", 1)
pipeline(ctx, fetch_data, process_data)
```

### パターン2: 直接呼び出し
```python
# 直接呼び出す場合は、事前にregister_nodeが必要
ctx = Context(entry_point="my_entry")
ctx.register_node("fetch_data")  # 必須
ctx.set_param("user_id", 1)
fetch_data(ctx)
```

**注意**: `ctx[node_name] = value`は未登録nodeに対してKeyErrorを発生させる。pipeline経由なら自動登録されるため問題ない。

## 後方互換性

**方針**: 破壊的変更とする（v1.0.0で旧形式を廃止）

**移行ガイド**:
```python
# 旧形式（廃止）
@node
def fetch_data(user_id: int) -> dict:
    return {"user": get_user(user_id)}

# 新形式
@node
def fetch_data(ctx: Context) -> None:
    user_id = ctx.get_param("user_id")
    ctx["fetch_data"] = {"user": get_user(user_id)}
```

**移行支援**:
- マイグレーションガイドをドキュメントに追加
- 旧形式を検出した場合、実行時に警告を出す（v0.x系のみ）

## テスト要件
- 新形式のnodeデコレータ動作
- コンテキストへの読み書き
- エラーハンドリング
- ロギング
- `_node_name`属性の付与

## 関連ファイル
- 修正: `railway/core/decorators.py`
- 修正: `tests/unit/core/test_decorators.py`

## 優先度
最高
