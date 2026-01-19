# Issue #02: Contractベースクラス実装

## 概要
型契約（Contract）の基盤となるベースクラスとレジストリを実装する。

## 依存関係
- Issue #01: Output Model基本設計（先行）

## 実装要件

### 1. Contractベースクラス

```python
# railway/core/contract.py
from pydantic import BaseModel, ConfigDict

class Contract(BaseModel):
    """
    Base class for all data contracts.

    All contracts should inherit from this class.
    Provides Pydantic validation and serialization.

    Example:
        class UsersFetchResult(Contract):
            users: list[User]
            total: int
    """
    # Pydantic v2 スタイル
    model_config = ConfigDict(
        extra="forbid",   # 追加フィールドを禁止（typoを防ぐ）
        frozen=True,      # 不変オブジェクトとして扱う
    )
```

### 2. 初期パラメータ用Contract

```python
# railway/core/contract.py
class Params(Contract):
    """
    Base class for entry point parameters.

    Example:
        class ReportParams(Params):
            user_id: int
            include_details: bool = False
    """
    pass
```

### 3. Contractレジストリ

```python
# railway/core/registry.py
from typing import Type
from railway.core.contract import Contract

class ContractRegistry:
    """Registry for contract types."""

    def __init__(self):
        self._contracts: dict[str, Type[Contract]] = {}

    def register(self, contract_cls: Type[Contract]) -> Type[Contract]:
        """Register a contract class."""
        name = contract_cls.__name__
        if name in self._contracts:
            raise ValueError(f"Contract '{name}' already registered")
        self._contracts[name] = contract_cls
        return contract_cls

    def get(self, name: str) -> Type[Contract]:
        """Get a contract class by name."""
        if name not in self._contracts:
            raise KeyError(f"Contract '{name}' not found")
        return self._contracts[name]

    def list_all(self) -> list[str]:
        """List all registered contract names."""
        return list(self._contracts.keys())


# グローバルレジストリ
_contract_registry = ContractRegistry()

def register_contract(cls: Type[Contract]) -> Type[Contract]:
    """Decorator to register a contract class."""
    return _contract_registry.register(cls)

def get_contract(name: str) -> Type[Contract]:
    """Get a contract class by name."""
    return _contract_registry.get(name)
```

### 4. 自動登録機構

```python
# railway/core/contract.py
from pydantic import BaseModel, ConfigDict
from railway.core.registry import _contract_registry

def _register_on_init_subclass(cls):
    """サブクラス定義時に自動登録"""
    if cls.__name__ not in ("Contract", "Params"):
        _contract_registry.register(cls)

class Contract(BaseModel):
    """
    Base class with auto-registration.

    継承時に自動的にレジストリに登録される。
    """
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        _register_on_init_subclass(cls)
```

**注意**: Pydantic v2では`__init_subclass__`を使用することで、メタクラスの競合を回避しています。

### 5. Contractの検証ユーティリティ

```python
# railway/core/contract.py
from typing import Any, Type, TypeVar

T = TypeVar("T", bound=Contract)

def validate_contract(data: Any, contract_type: Type[T]) -> T:
    """
    Validate data against a contract type.

    Args:
        data: Data to validate (dict or Contract instance)
        contract_type: Expected contract type

    Returns:
        Validated contract instance

    Raises:
        ValidationError: If validation fails
    """
    if isinstance(data, contract_type):
        return data
    if isinstance(data, dict):
        return contract_type(**data)
    raise TypeError(
        f"Expected {contract_type.__name__} or dict, got {type(data).__name__}"
    )
```

## 使用例

### Contract定義
```python
# src/contracts/user_contracts.py
from railway import Contract
from datetime import datetime

class User(Contract):
    """ユーザーエンティティ"""
    id: int
    name: str
    email: str

class UsersFetchResult(Contract):
    """fetch_usersノードの出力契約"""
    users: list[User]
    total: int
    fetched_at: datetime
```

### Params定義
```python
# src/contracts/params.py
from railway import Params

class ReportParams(Params):
    """レポート生成パラメータ"""
    user_id: int
    include_details: bool = False
    format: str = "json"
```

### Contractの使用
```python
from contracts.user_contracts import UsersFetchResult, User
from datetime import datetime

# 作成
result = UsersFetchResult(
    users=[User(id=1, name="Alice", email="alice@example.com")],
    total=1,
    fetched_at=datetime.now(),
)

# アクセス（IDE補完が効く）
print(result.users[0].name)  # "Alice"
print(result.total)          # 1

# 不正なフィールドはエラー
result = UsersFetchResult(
    users=[...],
    total=1,
    invalid_field="error",  # ValidationError!
)
```

## エラーハンドリング

| 操作 | エラー条件 | 例外 |
|------|-----------|------|
| Contract作成 | 型不一致 | `pydantic.ValidationError` |
| Contract作成 | 必須フィールド欠落 | `pydantic.ValidationError` |
| Contract作成 | 不明なフィールド | `pydantic.ValidationError` |
| `get_contract()` | 未登録の名前 | `KeyError` |
| `register_contract()` | 重複登録 | `ValueError` |

## テスト要件
- Contractの作成と検証
- Paramsの作成と検証
- バリデーションエラーのケース
- レジストリへの登録・取得
- 自動登録機構
- `validate_contract()`ユーティリティ

## 関連ファイル
- 新規: `railway/core/contract.py`
- 修正: `railway/core/registry.py`
- 新規: `tests/unit/core/test_contract.py`

## 優先度
最高
