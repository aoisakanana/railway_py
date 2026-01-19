"""Tests for Contract base class and related utilities."""

import pytest
from pydantic import ValidationError


class TestContractBasic:
    """Test Contract base class functionality."""

    def test_contract_creation(self):
        """Should create contract instance with valid data."""
        from railway.core.contract import Contract

        class UserContract(Contract):
            name: str
            age: int

        user = UserContract(name="Alice", age=30)
        assert user.name == "Alice"
        assert user.age == 30

    def test_contract_validation_type_error(self):
        """Should raise ValidationError on type mismatch."""
        from railway.core.contract import Contract

        class UserContract(Contract):
            name: str
            age: int

        with pytest.raises(ValidationError):
            UserContract(name="Alice", age="not_an_int")

    def test_contract_validation_missing_field(self):
        """Should raise ValidationError on missing required field."""
        from railway.core.contract import Contract

        class UserContract(Contract):
            name: str
            age: int

        with pytest.raises(ValidationError):
            UserContract(name="Alice")

    def test_contract_forbids_extra_fields(self):
        """Should raise ValidationError on extra fields."""
        from railway.core.contract import Contract

        class UserContract(Contract):
            name: str

        with pytest.raises(ValidationError):
            UserContract(name="Alice", unknown_field="value")

    def test_contract_is_immutable(self):
        """Should be frozen (immutable)."""
        from railway.core.contract import Contract

        class UserContract(Contract):
            name: str

        user = UserContract(name="Alice")
        with pytest.raises(ValidationError):
            user.name = "Bob"

    def test_contract_with_default_values(self):
        """Should support default values."""
        from railway.core.contract import Contract

        class ConfigContract(Contract):
            host: str = "localhost"
            port: int = 8080

        config = ConfigContract()
        assert config.host == "localhost"
        assert config.port == 8080

    def test_contract_with_nested_contract(self):
        """Should support nested contracts."""
        from railway.core.contract import Contract

        class AddressContract(Contract):
            city: str
            country: str

        class PersonContract(Contract):
            name: str
            address: AddressContract

        person = PersonContract(
            name="Alice",
            address=AddressContract(city="Tokyo", country="Japan"),
        )
        assert person.address.city == "Tokyo"

    def test_contract_with_list_of_contracts(self):
        """Should support list of contracts."""
        from railway.core.contract import Contract

        class ItemContract(Contract):
            id: int
            name: str

        class OrderContract(Contract):
            items: list[ItemContract]
            total: int

        order = OrderContract(
            items=[
                ItemContract(id=1, name="Item1"),
                ItemContract(id=2, name="Item2"),
            ],
            total=2,
        )
        assert len(order.items) == 2
        assert order.items[0].name == "Item1"


class TestParamsContract:
    """Test Params base class functionality."""

    def test_params_creation(self):
        """Should create params instance."""
        from railway.core.contract import Params

        class ReportParams(Params):
            user_id: int
            include_details: bool = False

        params = ReportParams(user_id=1)
        assert params.user_id == 1
        assert params.include_details is False

    def test_params_inherits_from_contract(self):
        """Params should inherit from Contract."""
        from railway.core.contract import Contract, Params

        assert issubclass(Params, Contract)

    def test_params_is_immutable(self):
        """Params should be frozen."""
        from railway.core.contract import Params

        class MyParams(Params):
            value: int

        params = MyParams(value=10)
        with pytest.raises(ValidationError):
            params.value = 20


class TestTagged:
    """Test Tagged type for same-type disambiguation."""

    def test_tagged_creation(self):
        """Should create Tagged instance."""
        from railway.core.contract import Contract, Tagged

        class UserContract(Contract):
            name: str

        tagged = Tagged(UserContract, source="fetch_users")
        assert tagged.contract_type == UserContract
        assert tagged.source == "fetch_users"

    def test_tagged_is_immutable(self):
        """Tagged should be immutable (frozen dataclass)."""
        from railway.core.contract import Contract, Tagged

        class UserContract(Contract):
            name: str

        tagged = Tagged(UserContract, source="fetch_users")
        with pytest.raises(AttributeError):
            tagged.source = "other_source"

    def test_tagged_equality(self):
        """Tagged instances with same values should be equal."""
        from railway.core.contract import Contract, Tagged

        class UserContract(Contract):
            name: str

        tagged1 = Tagged(UserContract, source="fetch_users")
        tagged2 = Tagged(UserContract, source="fetch_users")
        assert tagged1 == tagged2

    def test_tagged_inequality(self):
        """Tagged instances with different values should not be equal."""
        from railway.core.contract import Contract, Tagged

        class UserContract(Contract):
            name: str

        tagged1 = Tagged(UserContract, source="fetch_users")
        tagged2 = Tagged(UserContract, source="other_source")
        assert tagged1 != tagged2


class TestValidateContract:
    """Test validate_contract utility function."""

    def test_validate_contract_with_instance(self):
        """Should return instance as-is if already correct type."""
        from railway.core.contract import Contract, validate_contract

        class UserContract(Contract):
            name: str

        user = UserContract(name="Alice")
        result = validate_contract(user, UserContract)
        assert result is user

    def test_validate_contract_with_dict(self):
        """Should convert dict to contract instance."""
        from railway.core.contract import Contract, validate_contract

        class UserContract(Contract):
            name: str
            age: int

        result = validate_contract({"name": "Alice", "age": 30}, UserContract)
        assert isinstance(result, UserContract)
        assert result.name == "Alice"
        assert result.age == 30

    def test_validate_contract_with_invalid_type(self):
        """Should raise TypeError on invalid input type."""
        from railway.core.contract import Contract, validate_contract

        class UserContract(Contract):
            name: str

        with pytest.raises(TypeError, match="Expected UserContract or dict"):
            validate_contract("invalid", UserContract)

    def test_validate_contract_with_invalid_dict(self):
        """Should raise ValidationError on invalid dict data."""
        from railway.core.contract import Contract, validate_contract

        class UserContract(Contract):
            name: str
            age: int

        with pytest.raises(ValidationError):
            validate_contract({"name": "Alice"}, UserContract)


class TestContractRegistry:
    """Test ContractRegistry functionality."""

    def test_registry_register_and_get(self):
        """Should register and retrieve contract by name."""
        from railway.core.registry import ContractRegistry

        registry = ContractRegistry()

        from railway.core.contract import Contract

        class TestContract(Contract):
            value: int

        registry.register(TestContract)
        retrieved = registry.get("TestContract")
        assert retrieved is TestContract

    def test_registry_duplicate_registration(self):
        """Should raise ValueError on duplicate registration."""
        from railway.core.registry import ContractRegistry

        registry = ContractRegistry()

        from railway.core.contract import Contract

        class DuplicateContract(Contract):
            value: int

        registry.register(DuplicateContract)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(DuplicateContract)

    def test_registry_get_not_found(self):
        """Should raise KeyError for unregistered contract."""
        from railway.core.registry import ContractRegistry

        registry = ContractRegistry()
        with pytest.raises(KeyError, match="not found"):
            registry.get("NonExistentContract")

    def test_registry_list_all(self):
        """Should list all registered contract names."""
        from railway.core.registry import ContractRegistry

        registry = ContractRegistry()

        from railway.core.contract import Contract

        class Contract1(Contract):
            a: int

        class Contract2(Contract):
            b: str

        registry.register(Contract1)
        registry.register(Contract2)
        names = registry.list_all()
        assert "Contract1" in names
        assert "Contract2" in names


class TestGlobalRegistryFunctions:
    """Test global registry helper functions."""

    def test_register_contract_decorator_on_non_contract(self):
        """Should register non-Contract class using decorator."""
        from railway.core.registry import (
            _contract_registry,
            register_contract,
        )
        from pydantic import BaseModel

        # Clear registry state for test isolation
        original_contracts = _contract_registry._contracts.copy()
        _contract_registry._contracts.clear()

        try:
            # Use a class that doesn't auto-register (doesn't inherit Contract)
            @register_contract
            class ManuallyRegistered(BaseModel):
                value: int

            assert "ManuallyRegistered" in _contract_registry.list_all()
        finally:
            _contract_registry._contracts = original_contracts

    def test_get_contract_function(self):
        """Should get contract using global function."""
        from railway.core.registry import (
            _contract_registry,
            get_contract,
        )

        # Clear registry state for test isolation
        original_contracts = _contract_registry._contracts.copy()
        _contract_registry._contracts.clear()

        try:
            from railway.core.contract import Contract

            # Contract subclasses auto-register via __init_subclass__
            class AutoGetTestContract(Contract):
                value: int

            retrieved = get_contract("AutoGetTestContract")
            assert retrieved.__name__ == "AutoGetTestContract"
        finally:
            _contract_registry._contracts = original_contracts


class TestContractAutoRegistration:
    """Test automatic contract registration via __init_subclass__."""

    def test_auto_registration_on_subclass(self):
        """Contract subclasses should auto-register."""
        from railway.core.registry import _contract_registry

        # Clear registry state for test isolation
        original_contracts = _contract_registry._contracts.copy()
        _contract_registry._contracts.clear()

        try:
            from railway.core.contract import Contract

            class AutoRegisteredContract(Contract):
                value: int

            assert "AutoRegisteredContract" in _contract_registry.list_all()
        finally:
            _contract_registry._contracts = original_contracts

    def test_params_auto_registration(self):
        """Params subclasses should auto-register."""
        from railway.core.registry import _contract_registry

        # Clear registry state for test isolation
        original_contracts = _contract_registry._contracts.copy()
        _contract_registry._contracts.clear()

        try:
            from railway.core.contract import Params

            class AutoRegisteredParams(Params):
                param: str

            assert "AutoRegisteredParams" in _contract_registry.list_all()
        finally:
            _contract_registry._contracts = original_contracts

    def test_base_classes_not_registered(self):
        """Contract and Params base classes should not be registered."""
        from railway.core.registry import _contract_registry

        names = _contract_registry.list_all()
        assert "Contract" not in names
        assert "Params" not in names
