"""Contract base classes for type-safe node data exchange.

This module provides the foundation for the Output Model pattern,
enabling type-safe data contracts between pipeline nodes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict


def _register_on_init_subclass(cls: type) -> None:
    """Register subclass in the global registry.

    Called automatically when a Contract subclass is defined.
    Skips registration for base classes (Contract, Params).
    """
    # Avoid circular import
    from railway.core.registry import _contract_registry

    if cls.__name__ not in ("Contract", "Params"):
        try:
            _contract_registry.register(cls)
        except ValueError:
            # Already registered (can happen with reload)
            pass


class Contract(BaseModel):
    """Base class for all data contracts.

    All contracts should inherit from this class.
    Provides Pydantic validation and serialization.

    Features:
        - Automatic validation on instantiation
        - Extra fields are forbidden (catches typos)
        - Instances are immutable (frozen)
        - Auto-registration in global registry

    Example:
        class UsersFetchResult(Contract):
            users: list[User]
            total: int
    """

    model_config = ConfigDict(
        extra="forbid",  # Forbid extra fields (catch typos)
        frozen=True,  # Make instances immutable
    )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Register subclass when defined."""
        super().__init_subclass__(**kwargs)
        _register_on_init_subclass(cls)


class Params(Contract):
    """Base class for entry point parameters.

    Use this for pipeline input parameters.
    Inherits all Contract features.

    Example:
        class ReportParams(Params):
            user_id: int
            include_details: bool = False
    """

    pass


@dataclass(frozen=True)
class Tagged:
    """Tagged type specification for disambiguating multiple outputs of same type.

    When multiple nodes output the same Contract type, use Tagged to specify
    which node's output to use.

    Attributes:
        contract_type: The Contract type to match.
        source: The name of the source node.

    Example:
        @node(
            inputs={
                "active": Tagged(UsersFetchResult, source="fetch_active_users"),
                "inactive": Tagged(UsersFetchResult, source="fetch_inactive_users"),
            },
            output=MergedResult,
        )
        def merge_users(active: UsersFetchResult, inactive: UsersFetchResult):
            ...
    """

    contract_type: type[Contract]
    source: str


T = TypeVar("T", bound=Contract)


def validate_contract(data: Any, contract_type: type[T]) -> T:
    """Validate data against a contract type.

    Accepts either:
    - A Contract instance of the expected type (returned as-is)
    - A dict that will be converted to the Contract type

    Args:
        data: Data to validate (dict or Contract instance).
        contract_type: Expected contract type.

    Returns:
        Validated contract instance.

    Raises:
        TypeError: If data is neither a Contract instance nor a dict.
        ValidationError: If validation fails.

    Example:
        result = validate_contract({"name": "Alice"}, UserContract)
    """
    if isinstance(data, contract_type):
        return data
    if isinstance(data, dict):
        return contract_type(**data)
    raise TypeError(
        f"Expected {contract_type.__name__} or dict, got {type(data).__name__}"
    )
