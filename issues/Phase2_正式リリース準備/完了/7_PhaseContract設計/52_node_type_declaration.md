# Issue #52: Node 依存宣言拡張

## 概要

`@node` デコレータを拡張し、`requires`/`optional`/`provides` を宣言できるようにする。

## 設計

### 新しい API

```python
@node(
    requires=["incident_id"],           # 必須フィールド
    optional=["hostname"],              # オプションフィールド
    provides=["escalated", "notified"], # 追加するフィールド
)
def escalate(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
    if ctx.hostname:  # オプションなので存在チェック
        notify_with_host(ctx.hostname)
    return ctx.model_copy(update={"escalated": True, "notified": True}), Outcome.success("done")
```

### NodeDefinition の拡張

```python
@dataclass(frozen=True)
class NodeDefinition:
    name: str
    module: str
    function: str
    description: str
    is_exit: bool = False
    requires: frozenset[str] = frozenset()   # 追加
    optional: frozenset[str] = frozenset()   # 追加
    provides: frozenset[str] = frozenset()   # 追加
```

## タスク

### 1. Red Phase: 失敗するテストを作成

`tests/unit/core/decorators/test_node_field_dependency.py`:

```python
"""Node デコレータのフィールド依存宣言テスト。"""

import pytest
from railway import Contract, node
from railway.core.dag import Outcome


class WorkflowContext(Contract):
    incident_id: str
    severity: str
    hostname: str | None = None
    escalated: bool = False


class TestNodeFieldDeclaration:
    """フィールド依存宣言のテスト。"""

    def test_declares_requires(self) -> None:
        """requires を宣言できる。"""
        @node(requires=["incident_id", "severity"])
        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        assert my_node._requires == frozenset(["incident_id", "severity"])

    def test_declares_optional(self) -> None:
        """optional を宣言できる。"""
        @node(optional=["hostname"])
        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        assert my_node._optional == frozenset(["hostname"])

    def test_declares_provides(self) -> None:
        """provides を宣言できる。"""
        @node(provides=["escalated"])
        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx.model_copy(update={"escalated": True}), Outcome.success("done")

        assert my_node._provides == frozenset(["escalated"])

    def test_all_declarations_together(self) -> None:
        """requires/optional/provides をすべて宣言できる。"""
        @node(
            requires=["incident_id"],
            optional=["hostname"],
            provides=["escalated", "notified"],
        )
        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        assert my_node._requires == frozenset(["incident_id"])
        assert my_node._optional == frozenset(["hostname"])
        assert my_node._provides == frozenset(["escalated", "notified"])

    def test_empty_declarations_default(self) -> None:
        """宣言しない場合は空の frozenset。"""
        @node
        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        assert my_node._requires == frozenset()
        assert my_node._optional == frozenset()
        assert my_node._provides == frozenset()


class TestNodeFieldDependencyObject:
    """FieldDependency オブジェクトの取得テスト。"""

    def test_get_field_dependency(self) -> None:
        """FieldDependency オブジェクトを取得できる。"""
        from railway.core.dag.field_dependency import FieldDependency

        @node(requires=["a"], optional=["b"], provides=["c"])
        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        dep = my_node._field_dependency
        assert isinstance(dep, FieldDependency)
        assert dep.requires == frozenset(["a"])
        assert dep.optional == frozenset(["b"])
        assert dep.provides == frozenset(["c"])


class TestNodeWithExistingFeatures:
    """既存機能との組み合わせテスト。"""

    def test_with_name_parameter(self) -> None:
        """name パラメータと組み合わせられる。"""
        @node(name="custom_name", requires=["a"], provides=["b"])
        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        assert my_node._node_name == "custom_name"
        assert my_node._requires == frozenset(["a"])

    def test_with_retries_parameter(self) -> None:
        """retries パラメータと組み合わせられる。"""
        @node(requires=["a"], retries=3, retry_on=(ValueError,))
        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        assert my_node._requires == frozenset(["a"])
        assert my_node._retries == 3
```

### 2. Green Phase: デコレータ拡張

`railway/core/decorators.py` を更新:

```python
from railway.core.dag.field_dependency import FieldDependency


def node(
    func: Callable[P, T] | None = None,
    *,
    name: str | None = None,
    output: type | None = None,
    requires: Sequence[str] | None = None,    # 追加
    optional: Sequence[str] | None = None,    # 追加
    provides: Sequence[str] | None = None,    # 追加
    retries: int = 0,
    retry_on: tuple[type[Exception], ...] = (),
) -> Callable[P, T] | Callable[[Callable[P, T]], Callable[P, T]]:
    """ノード関数デコレータ。

    Args:
        func: デコレート対象の関数
        name: ノード名（省略時は関数名）
        output: 出力 Contract 型
        requires: 必須フィールド（このノードが必要とするフィールド）
        optional: オプションフィールド（あれば使用するフィールド）
        provides: 提供フィールド（このノードが追加するフィールド）
        retries: リトライ回数
        retry_on: リトライ対象の例外タプル
    """
    def decorator(fn: Callable[P, T]) -> Callable[P, T]:
        # 既存のメタデータ設定
        fn._node_name = name or fn.__name__
        fn._output_type = output
        fn._retries = retries
        fn._retry_on = retry_on

        # フィールド依存関係を設定
        fn._requires = frozenset(requires or [])
        fn._optional = frozenset(optional or [])
        fn._provides = frozenset(provides or [])

        # FieldDependency オブジェクトを作成
        fn._field_dependency = FieldDependency(
            requires=fn._requires,
            optional=fn._optional,
            provides=fn._provides,
        )

        return fn

    if func is not None:
        return decorator(func)
    return decorator
```

### 3. Refactor Phase

- 型ヒントの追加
- ドキュメンテーション改善
- 終端ノードの特別処理（provides なし）

## 完了条件

- [ ] `@node` デコレータが `requires`/`optional`/`provides` をサポート
- [ ] `_requires`, `_optional`, `_provides` 属性が設定される
- [ ] `_field_dependency` 属性で FieldDependency を取得できる
- [ ] 既存のパラメータ（name, retries 等）と組み合わせて使える
- [ ] すべてのテストが通過

## 依存関係

- Issue #51 (FieldDependency 型システム) が完了していること

## 関連ファイル

- `railway/core/decorators.py` (更新)
- `tests/unit/core/decorators/test_node_field_dependency.py` (新規)
