"""Tests for automatic inputs inference from type hints.

This module tests the ability to automatically infer node inputs
from function parameter type hints, reducing boilerplate.
"""

import pytest

from railway import node, Contract


class UsersFetchResult(Contract):
    """Test contract for type checking."""
    users: list[str]


class ProcessedData(Contract):
    """Test contract for processed data."""
    count: int


class TestInputsAutoInference:
    """inputs 自動推論のテスト"""

    def test_infers_inputs_from_type_hints(self) -> None:
        """inputs は型ヒントから自動推論される"""

        @node(output=ProcessedData)
        def process_users(users: UsersFetchResult) -> ProcessedData:
            return ProcessedData(count=len(users.users))

        assert process_users._node_inputs == {"users": UsersFetchResult}

    def test_explicit_inputs_takes_precedence(self) -> None:
        """明示的な inputs 指定は自動推論より優先される"""

        class AltContract(Contract):
            data: str

        @node(output=ProcessedData, inputs={"data": AltContract})
        def process(data: UsersFetchResult) -> ProcessedData:
            return ProcessedData(count=0)

        assert process._node_inputs == {"data": AltContract}

    def test_non_contract_types_ignored(self) -> None:
        """非 Contract 型は inputs に含まれない"""

        @node(output=ProcessedData)
        def process(name: str, count: int) -> ProcessedData:
            return ProcessedData(count=count)

        # プリミティブ型は含まれない
        assert process._node_inputs == {}

    def test_mixed_contract_and_primitive_types(self) -> None:
        """Contract と プリミティブ型が混在する場合"""

        @node(output=ProcessedData)
        def process(users: UsersFetchResult, limit: int) -> ProcessedData:
            return ProcessedData(count=min(len(users.users), limit))

        # Contract 型のみが inputs に含まれる
        assert process._node_inputs == {"users": UsersFetchResult}

    def test_optional_contract_type(self) -> None:
        """Optional[Contract] も推論される"""

        @node(output=ProcessedData)
        def process(users: UsersFetchResult | None) -> ProcessedData:
            return ProcessedData(count=0 if users is None else len(users.users))

        assert process._node_inputs == {"users": UsersFetchResult}

    def test_multiple_contract_parameters(self) -> None:
        """複数の Contract パラメータがある場合"""

        class Config(Contract):
            settings: dict[str, str]

        @node(output=ProcessedData)
        def process(users: UsersFetchResult, config: Config) -> ProcessedData:
            return ProcessedData(count=len(users.users))

        assert process._node_inputs == {
            "users": UsersFetchResult,
            "config": Config,
        }

    def test_no_type_hints_no_inference(self) -> None:
        """型ヒントがない場合は推論しない"""

        @node(output=ProcessedData)
        def process(data) -> ProcessedData:  # type: ignore[no-untyped-def]
            return ProcessedData(count=0)

        assert process._node_inputs == {}

    def test_decorated_without_parentheses(self) -> None:
        """@node（括弧なし）でも推論される"""

        @node
        def process(users: UsersFetchResult) -> ProcessedData:
            return ProcessedData(count=len(users.users))

        assert process._node_inputs == {"users": UsersFetchResult}

    def test_inference_with_retry_policy(self) -> None:
        """RetryPolicy と組み合わせても推論される"""
        from railway import RetryPolicy

        @node(retry_policy=RetryPolicy(max_retries=3))
        def process(users: UsersFetchResult) -> ProcessedData:
            return ProcessedData(count=len(users.users))

        assert process._node_inputs == {"users": UsersFetchResult}
