"""Tests for DependencyResolver and typed pipeline."""

from unittest.mock import patch

import pytest


class TestDependencyResolver:
    """Test DependencyResolver functionality."""

    def test_register_and_get_result_by_type(self):
        """Should register and retrieve result by type."""
        from railway.core.contract import Contract
        from railway.core.resolver import DependencyResolver

        class MyContract(Contract):
            value: int

        resolver = DependencyResolver()
        instance = MyContract(value=42)
        resolver.register_result(instance, source_name="my_node")

        result = resolver.get_result(MyContract)
        assert result is instance

    def test_register_result_with_source_name(self):
        """Should store result with source node name."""
        from railway.core.contract import Contract
        from railway.core.resolver import DependencyResolver

        class MyContract(Contract):
            value: int

        resolver = DependencyResolver()
        instance = MyContract(value=42)
        resolver.register_result(instance, source_name="fetch_node")

        # Should be able to retrieve by source name
        assert resolver.get_named_result("fetch_node") is instance

    def test_get_result_not_found(self):
        """Should raise DependencyError when type not found."""
        from railway.core.contract import Contract
        from railway.core.resolver import DependencyError, DependencyResolver

        class MissingContract(Contract):
            value: int

        resolver = DependencyResolver()

        with pytest.raises(DependencyError, match="No result of type"):
            resolver.get_result(MissingContract)

    def test_resolve_inputs_by_type(self):
        """Should resolve inputs by Contract type."""
        from railway.core.contract import Contract
        from railway.core.decorators import node
        from railway.core.resolver import DependencyResolver

        class InputContract(Contract):
            data: str

        class OutputContract(Contract):
            result: str

        @node(inputs={"data": InputContract}, output=OutputContract)
        def my_node(data: InputContract) -> OutputContract:
            return OutputContract(result=data.data)

        resolver = DependencyResolver()
        input_instance = InputContract(data="test")
        resolver.register_result(input_instance, source_name="input_node")

        resolved = resolver.resolve_inputs(my_node)
        assert resolved == {"data": input_instance}

    def test_resolve_inputs_multiple(self):
        """Should resolve multiple inputs."""
        from railway.core.contract import Contract
        from railway.core.decorators import node
        from railway.core.resolver import DependencyResolver

        class UsersContract(Contract):
            count: int

        class OrdersContract(Contract):
            count: int

        class ReportContract(Contract):
            total: int

        @node(
            inputs={"users": UsersContract, "orders": OrdersContract},
            output=ReportContract,
        )
        def generate_report(
            users: UsersContract, orders: OrdersContract
        ) -> ReportContract:
            return ReportContract(total=users.count + orders.count)

        resolver = DependencyResolver()
        resolver.register_result(UsersContract(count=10), source_name="fetch_users")
        resolver.register_result(OrdersContract(count=5), source_name="fetch_orders")

        resolved = resolver.resolve_inputs(generate_report)
        assert resolved["users"].count == 10
        assert resolved["orders"].count == 5

    def test_resolve_inputs_with_tagged(self):
        """Should resolve inputs using Tagged for same-type disambiguation."""
        from railway.core.contract import Contract, Tagged
        from railway.core.decorators import node
        from railway.core.resolver import DependencyResolver

        class UserContract(Contract):
            name: str

        class MergedContract(Contract):
            combined: str

        @node(
            inputs={
                "active": Tagged(UserContract, source="fetch_active"),
                "inactive": Tagged(UserContract, source="fetch_inactive"),
            },
            output=MergedContract,
        )
        def merge_users(
            active: UserContract, inactive: UserContract
        ) -> MergedContract:
            return MergedContract(combined=f"{active.name},{inactive.name}")

        resolver = DependencyResolver()
        resolver.register_result(UserContract(name="Alice"), source_name="fetch_active")
        resolver.register_result(UserContract(name="Bob"), source_name="fetch_inactive")

        resolved = resolver.resolve_inputs(merge_users)
        assert resolved["active"].name == "Alice"
        assert resolved["inactive"].name == "Bob"

    def test_resolve_inputs_tagged_source_not_found(self):
        """Should raise DependencyError when Tagged source not found."""
        from railway.core.contract import Contract, Tagged
        from railway.core.decorators import node
        from railway.core.resolver import DependencyError, DependencyResolver

        class UserContract(Contract):
            name: str

        class OutputContract(Contract):
            result: str

        @node(
            inputs={"user": Tagged(UserContract, source="nonexistent_node")},
            output=OutputContract,
        )
        def my_node(user: UserContract) -> OutputContract:
            return OutputContract(result=user.name)

        resolver = DependencyResolver()

        with pytest.raises(DependencyError, match="No result from node"):
            resolver.resolve_inputs(my_node)

    def test_resolve_inputs_type_not_found(self):
        """Should raise DependencyError when required type not found."""
        from railway.core.contract import Contract
        from railway.core.decorators import node
        from railway.core.resolver import DependencyError, DependencyResolver

        class MissingContract(Contract):
            value: int

        class OutputContract(Contract):
            result: int

        @node(inputs={"data": MissingContract}, output=OutputContract)
        def my_node(data: MissingContract) -> OutputContract:
            return OutputContract(result=data.value)

        resolver = DependencyResolver()

        with pytest.raises(DependencyError, match="Cannot resolve input"):
            resolver.resolve_inputs(my_node)


class TestTypedPipeline:
    """Test typed_pipeline function."""

    def test_basic_pipeline(self):
        """Should execute basic typed pipeline."""
        from railway.core.contract import Contract
        from railway.core.decorators import node
        from railway.core.resolver import typed_pipeline

        class ResultA(Contract):
            value: int

        class ResultB(Contract):
            doubled: int

        @node(output=ResultA)
        def step_a() -> ResultA:
            return ResultA(value=21)

        @node(inputs={"data": ResultA}, output=ResultB)
        def step_b(data: ResultA) -> ResultB:
            return ResultB(doubled=data.value * 2)

        with patch("railway.core.decorators.logger"):
            result = typed_pipeline(step_a, step_b)

        assert isinstance(result, ResultB)
        assert result.doubled == 42

    def test_pipeline_with_params(self):
        """Should accept initial params."""
        from railway.core.contract import Contract, Params
        from railway.core.decorators import node
        from railway.core.resolver import typed_pipeline

        class FetchParams(Params):
            user_id: int

        class UserResult(Contract):
            name: str

        @node(inputs={"params": FetchParams}, output=UserResult)
        def fetch_user(params: FetchParams) -> UserResult:
            return UserResult(name=f"User{params.user_id}")

        with patch("railway.core.decorators.logger"):
            result = typed_pipeline(fetch_user, params=FetchParams(user_id=123))

        assert result.name == "User123"

    def test_pipeline_with_dict_params(self):
        """Should accept dict as params (converted to dynamic Contract)."""
        from railway.core.contract import Contract
        from railway.core.decorators import node
        from railway.core.resolver import typed_pipeline

        class ResultContract(Contract):
            message: str

        @node(output=ResultContract)
        def create_message() -> ResultContract:
            return ResultContract(message="Hello")

        with patch("railway.core.decorators.logger"):
            result = typed_pipeline(create_message, params={"debug": True})

        assert result.message == "Hello"

    def test_pipeline_requires_at_least_one_node(self):
        """Should raise ValueError when no nodes provided."""
        from railway.core.resolver import typed_pipeline

        with pytest.raises(ValueError, match="at least one node"):
            typed_pipeline()

    def test_pipeline_dependency_error_propagates(self):
        """Should propagate DependencyError when resolution fails."""
        from railway.core.contract import Contract
        from railway.core.decorators import node
        from railway.core.resolver import DependencyError, typed_pipeline

        class MissingContract(Contract):
            value: int

        class OutputContract(Contract):
            result: int

        @node(inputs={"data": MissingContract}, output=OutputContract)
        def my_node(data: MissingContract) -> OutputContract:
            return OutputContract(result=data.value)

        with patch("railway.core.decorators.logger"):
            with pytest.raises(DependencyError):
                typed_pipeline(my_node)

    def test_pipeline_multiple_nodes(self):
        """Should handle multiple nodes in sequence."""
        from railway.core.contract import Contract
        from railway.core.decorators import node
        from railway.core.resolver import typed_pipeline

        class Step1Result(Contract):
            a: int

        class Step2Result(Contract):
            b: int

        class Step3Result(Contract):
            c: int

        @node(output=Step1Result)
        def step1() -> Step1Result:
            return Step1Result(a=1)

        @node(inputs={"s1": Step1Result}, output=Step2Result)
        def step2(s1: Step1Result) -> Step2Result:
            return Step2Result(b=s1.a + 1)

        @node(inputs={"s1": Step1Result, "s2": Step2Result}, output=Step3Result)
        def step3(s1: Step1Result, s2: Step2Result) -> Step3Result:
            return Step3Result(c=s1.a + s2.b)

        with patch("railway.core.decorators.logger"):
            result = typed_pipeline(step1, step2, step3)

        assert result.c == 3  # 1 + 2

    def test_pipeline_node_execution_error(self):
        """Should propagate node execution errors."""
        from railway.core.contract import Contract
        from railway.core.decorators import node
        from railway.core.resolver import typed_pipeline

        class ResultContract(Contract):
            value: int

        @node(output=ResultContract)
        def failing_node() -> ResultContract:
            raise RuntimeError("Node execution failed")

        with patch("railway.core.decorators.logger"):
            with pytest.raises(RuntimeError, match="Node execution failed"):
                typed_pipeline(failing_node)


class TestTypedAsyncPipeline:
    """Test typed_async_pipeline function."""

    @pytest.mark.asyncio
    async def test_basic_async_pipeline(self):
        """Should execute basic async typed pipeline."""
        from railway.core.contract import Contract
        from railway.core.decorators import node
        from railway.core.resolver import typed_async_pipeline

        class ResultA(Contract):
            value: int

        class ResultB(Contract):
            doubled: int

        @node(output=ResultA)
        async def async_step_a() -> ResultA:
            return ResultA(value=21)

        @node(inputs={"data": ResultA}, output=ResultB)
        async def async_step_b(data: ResultA) -> ResultB:
            return ResultB(doubled=data.value * 2)

        with patch("railway.core.decorators.logger"):
            result = await typed_async_pipeline(async_step_a, async_step_b)

        assert isinstance(result, ResultB)
        assert result.doubled == 42

    @pytest.mark.asyncio
    async def test_async_pipeline_with_sync_nodes(self):
        """Should handle mix of sync and async nodes."""
        from railway.core.contract import Contract
        from railway.core.decorators import node
        from railway.core.resolver import typed_async_pipeline

        class ResultA(Contract):
            value: int

        class ResultB(Contract):
            doubled: int

        @node(output=ResultA)
        def sync_step() -> ResultA:
            return ResultA(value=10)

        @node(inputs={"data": ResultA}, output=ResultB)
        async def async_step(data: ResultA) -> ResultB:
            return ResultB(doubled=data.value * 2)

        with patch("railway.core.decorators.logger"):
            result = await typed_async_pipeline(sync_step, async_step)

        assert result.doubled == 20

    @pytest.mark.asyncio
    async def test_async_pipeline_with_params(self):
        """Should accept params in async pipeline."""
        from railway.core.contract import Contract, Params
        from railway.core.decorators import node
        from railway.core.resolver import typed_async_pipeline

        class FetchParams(Params):
            count: int

        class ResultContract(Contract):
            total: int

        @node(inputs={"params": FetchParams}, output=ResultContract)
        async def async_fetch(params: FetchParams) -> ResultContract:
            return ResultContract(total=params.count * 10)

        with patch("railway.core.decorators.logger"):
            result = await typed_async_pipeline(
                async_fetch, params=FetchParams(count=5)
            )

        assert result.total == 50


class TestDependencyError:
    """Test DependencyError exception."""

    def test_dependency_error_message(self):
        """Should have descriptive error message."""
        from railway.core.resolver import DependencyError

        error = DependencyError("Test error message")
        assert str(error) == "Test error message"

    def test_dependency_error_inheritance(self):
        """Should inherit from Exception."""
        from railway.core.resolver import DependencyError

        assert issubclass(DependencyError, Exception)
