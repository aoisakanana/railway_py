"""Tests for @node decorator typed extension (inputs/output parameters)."""

from unittest.mock import patch

import pytest


class TestNodeOutputParameter:
    """Test @node decorator with output parameter."""

    def test_node_with_output_stores_metadata(self):
        """Should store output type in metadata."""
        from railway.core.decorators import node
        from railway.core.contract import Contract

        class ResultContract(Contract):
            value: int

        @node(output=ResultContract)
        def my_node() -> ResultContract:
            return ResultContract(value=42)

        assert my_node._node_output == ResultContract

    def test_node_with_output_returns_correct_type(self):
        """Should return contract instance when output is specified."""
        from railway.core.decorators import node
        from railway.core.contract import Contract

        class ResultContract(Contract):
            value: int

        @node(output=ResultContract)
        def my_node() -> ResultContract:
            return ResultContract(value=42)

        with patch("railway.core.decorators.logger"):
            result = my_node()

        assert isinstance(result, ResultContract)
        assert result.value == 42

    def test_node_with_output_validates_return_type(self):
        """Should raise TypeError if return type doesn't match output."""
        from railway.core.decorators import node
        from railway.core.contract import Contract

        class ExpectedContract(Contract):
            value: int

        class WrongContract(Contract):
            other: str

        @node(output=ExpectedContract)
        def my_node() -> ExpectedContract:
            return WrongContract(other="wrong")  # type: ignore

        with patch("railway.core.decorators.logger"):
            with pytest.raises(TypeError, match="expected to return ExpectedContract"):
                my_node()

    def test_node_without_output_has_none_metadata(self):
        """Should have None for _node_output when not specified."""
        from railway.core.decorators import node

        @node
        def my_node() -> int:
            return 42

        assert my_node._node_output is None


class TestNodeInputsParameter:
    """Test @node decorator with inputs parameter."""

    def test_node_with_inputs_stores_metadata(self):
        """Should store inputs dict in metadata."""
        from railway.core.decorators import node
        from railway.core.contract import Contract

        class InputContract(Contract):
            data: str

        class OutputContract(Contract):
            result: str

        @node(inputs={"data": InputContract}, output=OutputContract)
        def my_node(data: InputContract) -> OutputContract:
            return OutputContract(result=data.data.upper())

        assert my_node._node_inputs == {"data": InputContract}

    def test_node_with_inputs_accepts_contract_argument(self):
        """Should accept contract instance as argument."""
        from railway.core.decorators import node
        from railway.core.contract import Contract

        class InputContract(Contract):
            value: int

        class OutputContract(Contract):
            doubled: int

        @node(inputs={"data": InputContract}, output=OutputContract)
        def double_node(data: InputContract) -> OutputContract:
            return OutputContract(doubled=data.value * 2)

        with patch("railway.core.decorators.logger"):
            input_data = InputContract(value=21)
            result = double_node(data=input_data)

        assert result.doubled == 42

    def test_node_with_multiple_inputs(self):
        """Should support multiple input contracts."""
        from railway.core.decorators import node
        from railway.core.contract import Contract

        class UsersContract(Contract):
            count: int

        class OrdersContract(Contract):
            count: int

        class ReportContract(Contract):
            total: int

        @node(
            inputs={
                "users": UsersContract,
                "orders": OrdersContract,
            },
            output=ReportContract,
        )
        def generate_report(
            users: UsersContract,
            orders: OrdersContract,
        ) -> ReportContract:
            return ReportContract(total=users.count + orders.count)

        assert generate_report._node_inputs == {
            "users": UsersContract,
            "orders": OrdersContract,
        }

        with patch("railway.core.decorators.logger"):
            result = generate_report(
                users=UsersContract(count=10),
                orders=OrdersContract(count=5),
            )

        assert result.total == 15

    def test_node_without_inputs_has_empty_dict_metadata(self):
        """Should have empty dict for _node_inputs when not specified."""
        from railway.core.decorators import node

        @node
        def my_node() -> int:
            return 42

        assert my_node._node_inputs == {}


class TestNodeInputsWithTagged:
    """Test @node decorator with Tagged inputs."""

    def test_node_with_tagged_input_stores_metadata(self):
        """Should store Tagged in inputs metadata."""
        from railway.core.decorators import node
        from railway.core.contract import Contract, Tagged

        class UserContract(Contract):
            name: str

        class OutputContract(Contract):
            result: str

        @node(
            inputs={
                "active": Tagged(UserContract, source="fetch_active"),
                "inactive": Tagged(UserContract, source="fetch_inactive"),
            },
            output=OutputContract,
        )
        def merge_users(
            active: UserContract,
            inactive: UserContract,
        ) -> OutputContract:
            return OutputContract(result=f"{active.name},{inactive.name}")

        inputs = merge_users._node_inputs
        assert isinstance(inputs["active"], Tagged)
        assert inputs["active"].contract_type == UserContract
        assert inputs["active"].source == "fetch_active"
        assert isinstance(inputs["inactive"], Tagged)
        assert inputs["inactive"].source == "fetch_inactive"


class TestNodeTypedAsync:
    """Test @node decorator typed extension with async functions."""

    @pytest.mark.asyncio
    async def test_async_node_with_output(self):
        """Async node should support output parameter."""
        from railway.core.decorators import node
        from railway.core.contract import Contract

        class ResultContract(Contract):
            value: int

        @node(output=ResultContract)
        async def async_node() -> ResultContract:
            return ResultContract(value=42)

        assert async_node._node_output == ResultContract

        with patch("railway.core.decorators.logger"):
            result = await async_node()

        assert isinstance(result, ResultContract)
        assert result.value == 42

    @pytest.mark.asyncio
    async def test_async_node_with_inputs_and_output(self):
        """Async node should support both inputs and output."""
        from railway.core.decorators import node
        from railway.core.contract import Contract

        class InputContract(Contract):
            data: str

        class OutputContract(Contract):
            result: str

        @node(inputs={"data": InputContract}, output=OutputContract)
        async def async_process(data: InputContract) -> OutputContract:
            return OutputContract(result=data.data.upper())

        assert async_process._node_inputs == {"data": InputContract}
        assert async_process._node_output == OutputContract

        with patch("railway.core.decorators.logger"):
            result = await async_process(data=InputContract(data="hello"))

        assert result.result == "HELLO"

    @pytest.mark.asyncio
    async def test_async_node_validates_output_type(self):
        """Async node should validate output type."""
        from railway.core.decorators import node
        from railway.core.contract import Contract

        class ExpectedContract(Contract):
            value: int

        class WrongContract(Contract):
            other: str

        @node(output=ExpectedContract)
        async def async_node() -> ExpectedContract:
            return WrongContract(other="wrong")  # type: ignore

        with patch("railway.core.decorators.logger"):
            with pytest.raises(TypeError, match="expected to return ExpectedContract"):
                await async_node()


class TestNodeTypedWithExistingFeatures:
    """Test that typed extension works with existing node features."""

    def test_node_with_output_and_retry(self):
        """Should support output with retry."""
        from railway.core.decorators import node, Retry
        from railway.core.contract import Contract

        class ResultContract(Contract):
            value: int

        @node(output=ResultContract, retry=Retry(max_attempts=2))
        def retryable_node() -> ResultContract:
            return ResultContract(value=1)

        assert retryable_node._node_output == ResultContract

    def test_node_with_output_and_logging(self):
        """Should support output with log_input/log_output."""
        from railway.core.decorators import node
        from railway.core.contract import Contract

        class InputContract(Contract):
            data: str

        class OutputContract(Contract):
            result: str

        @node(
            inputs={"data": InputContract},
            output=OutputContract,
            log_input=True,
            log_output=True,
        )
        def logged_node(data: InputContract) -> OutputContract:
            return OutputContract(result=data.data)

        assert logged_node._node_inputs == {"data": InputContract}
        assert logged_node._node_output == OutputContract

    def test_node_with_output_and_custom_name(self):
        """Should support output with custom name."""
        from railway.core.decorators import node
        from railway.core.contract import Contract

        class ResultContract(Contract):
            value: int

        @node(output=ResultContract, name="custom_name")
        def original_name() -> ResultContract:
            return ResultContract(value=1)

        assert original_name._node_name == "custom_name"
        assert original_name._node_output == ResultContract


class TestNodeTypedMetadataComplete:
    """Test that all metadata is properly set for typed nodes."""

    def test_all_metadata_present(self):
        """Should have all expected metadata attributes."""
        from railway.core.decorators import node
        from railway.core.contract import Contract

        class InputContract(Contract):
            value: int

        class OutputContract(Contract):
            result: int

        @node(inputs={"data": InputContract}, output=OutputContract)
        def full_node(data: InputContract) -> OutputContract:
            """A fully typed node."""
            return OutputContract(result=data.value)

        # Existing metadata
        assert full_node._is_railway_node is True
        assert full_node._node_name == "full_node"
        assert full_node._is_async is False
        assert hasattr(full_node, "_original_func")

        # New metadata
        assert full_node._node_inputs == {"data": InputContract}
        assert full_node._node_output == OutputContract
