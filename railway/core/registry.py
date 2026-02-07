"""Contract registry for type-based dependency resolution."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from railway.core.contract import Contract


class ContractRegistry:
    """Registry for contract types.

    Provides registration and lookup of Contract classes by name.
    Used by the dependency resolution system to find contracts.
    """

    def __init__(self) -> None:
        self._contracts: dict[str, type[Contract]] = {}

    def register(self, contract_cls: type[Contract]) -> type[Contract]:
        """Register a contract class.

        Args:
            contract_cls: The Contract subclass to register.

        Returns:
            The registered contract class (for use as decorator).

        Raises:
            ValueError: If a contract with the same name is already registered.
        """
        name = contract_cls.__name__
        if name in self._contracts:
            raise ValueError(f"Contract '{name}' already registered")
        self._contracts[name] = contract_cls
        return contract_cls

    def get(self, name: str) -> type[Contract]:
        """Get a contract class by name.

        Args:
            name: The name of the contract class.

        Returns:
            The registered Contract class.

        Raises:
            KeyError: If no contract with the given name is registered.
        """
        if name not in self._contracts:
            raise KeyError(f"Contract '{name}' not found")
        return self._contracts[name]

    def list_all(self) -> list[str]:
        """List all registered contract names.

        Returns:
            List of registered contract class names.
        """
        return list(self._contracts.keys())

    def clear(self) -> None:
        """Clear all registered contracts.

        Primarily for testing purposes.
        """
        self._contracts.clear()


# Global registry instance
_contract_registry = ContractRegistry()


def register_contract(cls: type[Contract]) -> type[Contract]:
    """Decorator to register a contract class in the global registry.

    Example:
        @register_contract
        class MyContract(Contract):
            value: int
    """
    return _contract_registry.register(cls)


def get_contract(name: str) -> type[Contract]:
    """Get a contract class by name from the global registry.

    Args:
        name: The name of the contract class.

    Returns:
        The registered Contract class.

    Raises:
        KeyError: If no contract with the given name is registered.
    """
    return _contract_registry.get(name)
