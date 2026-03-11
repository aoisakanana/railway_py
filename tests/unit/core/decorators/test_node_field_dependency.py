"""Node デコレータのフィールド依存宣言テスト。

@node デコレータから requires/optional/provides パラメータは削除された。
フィールド依存メタデータは _make_node_with_deps ヘルパーで直接設定する。
"""

import pytest

from railway import Contract, node
from railway.core.dag import Outcome
from railway.core.dag.field_dependency import FieldDependency


class WorkflowContext(Contract):
    """テスト用 Contract。"""

    incident_id: str
    severity: str
    hostname: str | None = None
    escalated: bool = False


def _make_node_with_deps(
    func, *, requires=None, optional=None, provides=None, name=None
):
    """Test helper: set field dependency metadata on a function."""
    func._is_railway_node = True
    func._node_name = name or func.__name__
    func._is_board_node = False
    func._is_async = False
    func._node_inputs = {}
    func._node_output = None
    func._requires = frozenset(requires or [])
    func._optional = frozenset(optional or [])
    func._provides = frozenset(provides or [])
    func._field_dependency = FieldDependency(
        requires=func._requires,
        optional=func._optional,
        provides=func._provides,
    )
    return func


class TestNodeFieldDeclaration:
    """フィールド依存宣言のテスト。"""

    def test_declares_requires(self) -> None:
        """requires を宣言できる。"""

        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        _make_node_with_deps(my_node, requires=["incident_id", "severity"])

        assert my_node._requires == frozenset(["incident_id", "severity"])

    def test_declares_optional(self) -> None:
        """optional を宣言できる。"""

        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        _make_node_with_deps(my_node, optional=["hostname"])

        assert my_node._optional == frozenset(["hostname"])

    def test_declares_provides(self) -> None:
        """provides を宣言できる。"""

        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx.model_copy(update={"escalated": True}), Outcome.success("done")

        _make_node_with_deps(my_node, provides=["escalated"])

        assert my_node._provides == frozenset(["escalated"])

    def test_all_declarations_together(self) -> None:
        """requires/optional/provides をすべて宣言できる。"""

        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        _make_node_with_deps(
            my_node,
            requires=["incident_id"],
            optional=["hostname"],
            provides=["escalated"],
        )

        assert my_node._requires == frozenset(["incident_id"])
        assert my_node._optional == frozenset(["hostname"])
        assert my_node._provides == frozenset(["escalated"])

    def test_empty_declarations_default(self) -> None:
        """宣言しない場合は空の frozenset。"""

        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        _make_node_with_deps(my_node)

        assert my_node._requires == frozenset()
        assert my_node._optional == frozenset()
        assert my_node._provides == frozenset()


class TestNodeFieldDependencyObject:
    """FieldDependency オブジェクトの取得テスト。"""

    def test_get_field_dependency(self) -> None:
        """FieldDependency オブジェクトを取得できる。"""

        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        _make_node_with_deps(my_node, requires=["a"], optional=["b"], provides=["c"])

        dep = my_node._field_dependency
        assert isinstance(dep, FieldDependency)
        assert dep.requires == frozenset(["a"])
        assert dep.optional == frozenset(["b"])
        assert dep.provides == frozenset(["c"])

    def test_field_dependency_with_empty_declarations(self) -> None:
        """宣言なしの場合も FieldDependency を取得できる。"""

        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        _make_node_with_deps(my_node)

        dep = my_node._field_dependency
        assert isinstance(dep, FieldDependency)
        assert dep.requires == frozenset()
        assert dep.optional == frozenset()
        assert dep.provides == frozenset()


class TestNodeWithExistingFeatures:
    """既存機能との組み合わせテスト。"""

    def test_with_name_parameter(self) -> None:
        """name パラメータと組み合わせられる。"""

        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        _make_node_with_deps(
            my_node, name="custom_name", requires=["a"], provides=["b"]
        )

        assert my_node._node_name == "custom_name"
        assert my_node._requires == frozenset(["a"])

    def test_with_helper_metadata(self) -> None:
        """ヘルパーでメタデータを設定できる。"""

        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        _make_node_with_deps(my_node, requires=["a"])

        assert my_node._requires == frozenset(["a"])

    def test_node_still_callable(self) -> None:
        """フィールド依存宣言後もノードが正常に呼び出せる。"""

        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        _make_node_with_deps(my_node, requires=["incident_id"], provides=["processed"])

        ctx = WorkflowContext(incident_id="INC-001", severity="high")
        result_ctx, outcome = my_node(ctx)

        assert outcome.outcome_type == "success"
        assert outcome.detail == "done"


class TestAsyncNodeFieldDeclaration:
    """非同期ノードのフィールド依存宣言テスト。"""

    def test_async_node_declares_dependencies(self) -> None:
        """非同期ノードでも依存を宣言できる。"""

        async def my_async_node(
            ctx: WorkflowContext,
        ) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        _make_node_with_deps(
            my_async_node, requires=["incident_id"], provides=["result"]
        )

        assert my_async_node._requires == frozenset(["incident_id"])
        assert my_async_node._provides == frozenset(["result"])

    def test_async_node_field_dependency(self) -> None:
        """非同期ノードでも FieldDependency を取得できる。"""

        async def my_async_node(
            ctx: WorkflowContext,
        ) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        _make_node_with_deps(
            my_async_node, requires=["a"], optional=["b"], provides=["c"]
        )

        dep = my_async_node._field_dependency
        assert isinstance(dep, FieldDependency)
        assert dep.requires == frozenset(["a"])
