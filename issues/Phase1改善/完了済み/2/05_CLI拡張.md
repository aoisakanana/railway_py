# Issue #05: CLI拡張

## 概要
Output Modelパターンに対応したCLIコマンドを追加する。

## 依存関係
- Issue #01: Output Model基本設計（先行）
- Issue #02: Contractベースクラス実装（先行）
- Issue #03: nodeデコレータ拡張（先行）
- Issue #04: 依存解決とパイプライン改修（先行）

## 新規コマンド

### 1. Contract生成

```bash
# 基本的なContract生成
railway new contract UsersFetchResult

# エンティティContract生成
railway new contract User --entity

# ParamsContract生成
railway new contract ReportParams --params
```

#### 生成されるファイル

**基本Contract** (`railway new contract UsersFetchResult`)
```python
# src/contracts/users_fetch_result.py
from railway import Contract
from datetime import datetime

class UsersFetchResult(Contract):
    """
    Output contract for a node.

    TODO: Define the fields for this contract.
    """
    # Example fields (modify as needed):
    # items: list[dict]
    # total: int
    # fetched_at: datetime
    pass
```

**エンティティContract** (`railway new contract User --entity`)
```python
# src/contracts/user.py
from railway import Contract

class User(Contract):
    """
    Entity contract representing a user.

    TODO: Define the fields for this entity.
    """
    id: int
    # name: str
    # email: str
```

**ParamsContract** (`railway new contract ReportParams --params`)
```python
# src/contracts/report_params.py
from railway import Params

class ReportParams(Params):
    """
    Parameters for an entry point.

    TODO: Define the parameters.
    """
    # user_id: int
    # include_details: bool = False
```

### 2. 型付きNode生成

```bash
# 出力型のみ指定
railway new node fetch_users --output UsersFetchResult

# 入力と出力を指定
railway new node process_users \
    --input users:UsersFetchResult \
    --output UsersProcessResult

# 複数入力
railway new node generate_report \
    --input users:UsersFetchResult \
    --input orders:OrdersFetchResult \
    --output ReportResult

# パラメータ入力
railway new node fetch_by_id \
    --input params:FetchParams \
    --output UsersFetchResult
```

#### 生成されるファイル

**出力型のみ** (`railway new node fetch_users --output UsersFetchResult`)
```python
# src/nodes/fetch_users.py
from railway import node
from contracts.users_fetch_result import UsersFetchResult

@node(output=UsersFetchResult)
def fetch_users() -> UsersFetchResult:
    """
    TODO: Implement this node.

    Returns:
        UsersFetchResult: The result of this node.
    """
    # TODO: Implement the logic
    return UsersFetchResult(
        # Fill in the required fields
    )
```

**入力と出力** (`railway new node process_users --input users:UsersFetchResult --output UsersProcessResult`)
```python
# src/nodes/process_users.py
from railway import node
from contracts.users_fetch_result import UsersFetchResult
from contracts.users_process_result import UsersProcessResult

@node(
    inputs={"users": UsersFetchResult},
    output=UsersProcessResult,
)
def process_users(users: UsersFetchResult) -> UsersProcessResult:
    """
    Process users data.

    Args:
        users: Input from a node that outputs UsersFetchResult.

    Returns:
        UsersProcessResult: The processed result.
    """
    # TODO: Implement the logic
    return UsersProcessResult(
        # Fill in the required fields
    )
```

#### 生成されるテスト

```python
# tests/nodes/test_fetch_users.py
import pytest
from contracts.users_fetch_result import UsersFetchResult
from nodes.fetch_users import fetch_users

class TestFetchUsers:
    def test_fetch_users_returns_correct_type(self):
        """Node returns the expected output type."""
        result = fetch_users()
        assert isinstance(result, UsersFetchResult)

    def test_fetch_users_basic(self):
        """Basic functionality test."""
        pytest.skip("TODO: Implement this test")
```

```python
# tests/nodes/test_process_users.py
import pytest
from contracts.users_fetch_result import UsersFetchResult
from contracts.users_process_result import UsersProcessResult
from nodes.process_users import process_users

class TestProcessUsers:
    def test_process_users_returns_correct_type(self):
        """Node returns the expected output type."""
        # Arrange
        users = UsersFetchResult(
            # TODO: Fill in test data
        )

        # Act
        result = process_users(users)

        # Assert
        assert isinstance(result, UsersProcessResult)

    def test_process_users_basic(self):
        """Basic functionality test."""
        pytest.skip("TODO: Implement this test")
```

### 3. Contract一覧表示

```bash
# 登録されているContract一覧
railway list contracts

# 出力例:
# Contracts:
#   UsersFetchResult    src/contracts/users_fetch_result.py
#   UsersProcessResult  src/contracts/users_process_result.py
#   User                src/contracts/user.py
#
# Params:
#   ReportParams        src/contracts/report_params.py
```

### 4. Node依存関係表示

```bash
# nodeの依存関係を表示
railway show node generate_report

# 出力例:
# Node: generate_report
#
# Inputs:
#   users: UsersFetchResult
#   orders: OrdersFetchResult
#
# Output:
#   ReportResult
#
# Dependencies:
#   └── generate_report (ReportResult)
#       ├── fetch_users (UsersFetchResult)
#       └── fetch_orders (OrdersFetchResult)
```

### 5. パイプライン依存グラフ表示

```bash
# パイプラインの依存グラフを表示
railway show pipeline fetch_users fetch_orders generate_report

# 出力例:
# Pipeline Dependency Graph:
#
# fetch_users ─────────────┐
#   output: UsersFetchResult    │
#                               ├──> generate_report
# fetch_orders ────────────┘       output: ReportResult
#   output: OrdersFetchResult
```

## 既存コマンドの更新

### `railway new entry`

```bash
# デフォルト（最小限）
railway new entry my_entry

# 例示付き（Output Model形式）
railway new entry my_entry --example
```

**生成されるエントリポイント（--example）**
```python
# src/my_entry.py
from railway import pipeline
from contracts.my_entry_params import MyEntryParams
from nodes.fetch_data import fetch_data
from nodes.process_data import process_data

def main():
    """Entry point for my_entry."""
    result = pipeline(
        fetch_data,
        process_data,
        params=MyEntryParams(
            # Configure parameters here
        ),
    )
    print(f"Result: {result}")
    return result

if __name__ == "__main__":
    main()
```

### `railway new node`

```bash
# デフォルト（最小限、旧形式警告なし）
railway new node my_node

# 例示付き（Output Model形式）
railway new node my_node --example

# 型指定（推奨）
railway new node my_node --output MyResult
```

**デフォルト生成（最小限）**
```python
# src/nodes/my_node.py
from railway import node

@node
def my_node():
    """TODO: Implement this node."""
    pass
```

**--example 生成**
```python
# src/nodes/my_node.py
from railway import node
from railway.core.contract import Contract

class MyNodeResult(Contract):
    """Output contract for my_node."""
    message: str

@node(output=MyNodeResult)
def my_node() -> MyNodeResult:
    """
    Example node implementation.

    Returns:
        MyNodeResult: The result of this node.
    """
    return MyNodeResult(message="Hello from my_node!")
```

## 実装タスク

1. [ ] `railway new contract`コマンドの実装
2. [ ] `railway new node --input/--output`オプションの実装
3. [ ] `railway list contracts`コマンドの実装
4. [ ] `railway show node`コマンドの実装
5. [ ] `railway show pipeline`コマンドの実装
6. [ ] `railway new entry --example`の更新
7. [ ] テンプレートファイルの作成

## テスト要件
- Contract生成（基本、エンティティ、Params）
- 型付きNode生成（出力のみ、入力あり、複数入力）
- テストファイルの生成
- Contract一覧表示
- Node依存関係表示
- パイプライン依存グラフ表示

## 関連ファイル
- 修正: `railway/cli/commands.py`
- 新規: `railway/cli/templates/contract.py.template`
- 新規: `railway/cli/templates/typed_node.py.template`
- 修正: `tests/unit/cli/test_commands.py`

## 優先度
最高
