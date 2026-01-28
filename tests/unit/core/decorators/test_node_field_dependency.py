"""Node デコレータのフィールド依存宣言テスト。

TDD Red Phase: このテストは最初は失敗する（パラメータが存在しない）
"""

import pytest

from railway import Contract, node
from railway.core.dag import Outcome


class WorkflowContext(Contract):
    """テスト用 Contract。"""

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
            provides=["escalated"],
        )
        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        assert my_node._requires == frozenset(["incident_id"])
        assert my_node._optional == frozenset(["hostname"])
        assert my_node._provides == frozenset(["escalated"])

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

    def test_field_dependency_with_empty_declarations(self) -> None:
        """宣言なしの場合も FieldDependency を取得できる。"""
        from railway.core.dag.field_dependency import FieldDependency

        @node
        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        dep = my_node._field_dependency
        assert isinstance(dep, FieldDependency)
        assert dep.requires == frozenset()
        assert dep.optional == frozenset()
        assert dep.provides == frozenset()


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
        # retries は retry_policy に変換される場合があるので、動作することを確認

    def test_node_still_callable(self) -> None:
        """フィールド依存宣言後もノードが正常に呼び出せる。"""

        @node(requires=["incident_id"], provides=["processed"])
        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        ctx = WorkflowContext(incident_id="INC-001", severity="high")
        result_ctx, outcome = my_node(ctx)

        assert outcome.outcome_type == "success"
        assert outcome.detail == "done"


class TestAsyncNodeFieldDeclaration:
    """非同期ノードのフィールド依存宣言テスト。"""

    def test_async_node_declares_dependencies(self) -> None:
        """非同期ノードでも依存を宣言できる。"""

        @node(requires=["incident_id"], provides=["result"])
        async def my_async_node(
            ctx: WorkflowContext,
        ) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        assert my_async_node._requires == frozenset(["incident_id"])
        assert my_async_node._provides == frozenset(["result"])

    def test_async_node_field_dependency(self) -> None:
        """非同期ノードでも FieldDependency を取得できる。"""
        from railway.core.dag.field_dependency import FieldDependency

        @node(requires=["a"], optional=["b"], provides=["c"])
        async def my_async_node(
            ctx: WorkflowContext,
        ) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        dep = my_async_node._field_dependency
        assert isinstance(dep, FieldDependency)
        assert dep.requires == frozenset(["a"])
