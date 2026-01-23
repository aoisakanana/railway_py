"""Tests for @node decorator type preservation.

This module tests that the @node decorator correctly preserves
function signatures for type checkers like mypy.
"""

import pytest

from railway import node, Contract


class UserContract(Contract):
    """Test contract for type checking."""
    name: str


class TestNodeTypePreservation:
    """@node デコレータの型保持テスト"""

    def test_preserves_return_type(self) -> None:
        """@node デコレータが戻り値型を保持する"""

        @node
        def fetch_users() -> list[str]:
            return ["Alice", "Bob"]

        result: list[str] = fetch_users()
        assert result == ["Alice", "Bob"]

    def test_preserves_argument_types(self) -> None:
        """@node デコレータが引数型を保持する"""

        @node
        def greet(name: str, count: int) -> str:
            return f"Hello, {name}!" * count

        result: str = greet("World", 2)
        assert result == "Hello, World!Hello, World!"

    def test_with_retry_parameter(self) -> None:
        """retry パラメータ指定時も型を保持する"""

        @node(retry=False)
        def fetch_data() -> dict[str, int]:
            return {"count": 42}

        result: dict[str, int] = fetch_data()
        assert result == {"count": 42}

    def test_with_output_parameter(self) -> None:
        """output パラメータ指定時も型を保持する"""

        @node(output=UserContract)
        def create_user(name: str) -> UserContract:
            return UserContract(name=name)

        result: UserContract = create_user("Alice")
        assert result.name == "Alice"

    def test_with_empty_parentheses(self) -> None:
        """空の括弧付きでも型を保持する"""

        @node()
        def simple_func() -> int:
            return 42

        result: int = simple_func()
        assert result == 42

    def test_multiple_optional_parameters(self) -> None:
        """複数のオプションパラメータ指定時も型を保持する"""

        @node(log_input=True, log_output=True)
        def verbose_func(x: int) -> str:
            return str(x)

        result: str = verbose_func(123)
        assert result == "123"

    def test_with_name_parameter(self) -> None:
        """name パラメータ指定時も型を保持する"""

        @node(name="custom_name")
        def original_name() -> bool:
            return True

        result: bool = original_name()
        assert result is True
