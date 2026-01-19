# Issue #01: Output Model 基本設計

## 概要
型契約（Contract）ベースのノード間データ交換アーキテクチャの基本設計を策定する。

## 背景・問題点

### 現行設計の問題（線形パイプライン）
```python
pipeline(value, node_a, node_b, node_c)
#              ↓      ↓      ↓
#           output → input → output
#
# node_cはnode_aの結果に直接アクセスできない
# 各nodeは前段nodeの出力形式に暗黙的に依存
```

### Context変数案の残存問題
```python
@node
def fetch_users(ctx):
    ctx["fetch_users"] = {"items": [...], "total": 100}

@node
def generate_report(ctx):
    users = ctx["fetch_users"]["items"]  # 内部構造への依存
    #                  ^^^^^^^
    # fetch_usersが構造を変更すると、ここも壊れる
```

**問題**: 「遷移依存」は解消されるが、「構造依存」が残る

### 目指す設計: Output Model パターン
```python
from railway import Contract, node

class User(Contract):
    id: int
    name: str

class UsersFetchResult(Contract):
    users: list[User]
    total: int

@node(output=UsersFetchResult)
def fetch_users() -> UsersFetchResult:
    return UsersFetchResult(users=[...], total=100)

@node(inputs={"users": UsersFetchResult}, output=ReportResult)
def generate_report(users: UsersFetchResult) -> ReportResult:
    # users.users でアクセス（IDE補完が効く）
    return ReportResult(content=f"{users.total} users")
```

**解決**: nodeは「型契約」のみに依存。内部構造への依存なし。

## 設計原則

### 1. 型契約による依存
- ノード間のデータ交換は**型定義（Contract）**を通じて行う
- nodeは他nodeの実装詳細を知らず、契約のみに依存する
- フレームワークが依存解決と型検証を担当

### 2. 純粋関数としてのnode
```python
# 旧: 副作用あり（ctxへの書き込み）
@node
def fetch_data(ctx: Context) -> None:
    ctx["fetch_data"] = {...}

# 新: 純粋関数（引数を受け取り、値を返す）
@node(output=FetchResult)
def fetch_data() -> FetchResult:
    return FetchResult(...)
```

### 3. 依存関係の明示的宣言
```python
@node(
    inputs={               # 必要な入力を型で宣言
        "users": UsersFetchResult,
        "orders": OrdersFetchResult,
    },
    output=ReportResult,   # 出力の型を宣言
)
def generate_report(
    users: UsersFetchResult,
    orders: OrdersFetchResult,
) -> ReportResult:
    ...
```

## ディレクトリ構造

```
project/
├── src/
│   ├── contracts/           # 【新規】型契約の定義
│   │   ├── __init__.py
│   │   ├── user_contracts.py
│   │   └── order_contracts.py
│   ├── nodes/
│   │   ├── fetch_users.py
│   │   └── generate_report.py
│   └── main.py
└── tests/
    ├── contracts/           # 契約のテスト（オプション）
    └── nodes/
```

## Contractの定義規則

### 基本形式
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

### 命名規則
| 種類 | 命名パターン | 例 |
|------|-------------|-----|
| エンティティ | 単数名詞 | `User`, `Order` |
| ノード出力 | `{NodeName}Result` | `UsersFetchResult` |
| パラメータ | `{UseCase}Params` | `ReportGenerationParams` |

### Contractの責務
1. **データ構造の定義**: フィールドと型
2. **バリデーション**: Pydanticによる自動検証
3. **ドキュメント**: docstringによる説明

## 依存解決の仕組み

### フレームワーク内部の動作
```python
def pipeline(*nodes):
    results = {}  # {型: インスタンス} のマッピング

    for node in nodes:
        # 1. inputsから必要な型を特定し、resultsから取得
        kwargs = {}
        for param_name, required_type in node.inputs.items():
            for stored_value in results.values():
                if isinstance(stored_value, required_type):
                    kwargs[param_name] = stored_value
                    break

        # 2. nodeを実行
        result = node.func(**kwargs)

        # 3. 結果を型でインデックスして保存
        results[type(result)] = result

    return result
```

### 同一型の複数出力への対応
```python
from railway import node, Tagged

# 同じ型を出力するnodeが複数ある場合
@node(output=UsersFetchResult)
def fetch_active_users() -> UsersFetchResult: ...

@node(output=UsersFetchResult)
def fetch_inactive_users() -> UsersFetchResult: ...

# Tagged を使って明示的に解決
@node(
    inputs={
        "active": Tagged(UsersFetchResult, source="fetch_active_users"),
        "inactive": Tagged(UsersFetchResult, source="fetch_inactive_users"),
    },
    output=MergedResult,
)
def merge_users(active: UsersFetchResult, inactive: UsersFetchResult) -> MergedResult:
    ...
```

**注意**: 同一型の出力が1つだけの場合は、型のみで自動解決されます。

## 後方互換性

### 旧スタイルのサポート（非推奨）
```python
# 従来のContext直接操作（引き続き動作、非推奨警告）
@node
def legacy_node(ctx: Context) -> None:
    ctx["legacy_node"] = {"data": "..."}

# 新スタイル（推奨）
@node(output=ResultModel)
def new_node() -> ResultModel:
    return ResultModel(data="...")
```

### 移行パス
1. 新規nodeは新スタイルで作成
2. 既存nodeは段階的に移行
3. v1.0.0でContext直接操作を非推奨化
4. v2.0.0でContext直接操作を廃止

## 関連Issue
- Issue #02: Contractベースクラス実装
- Issue #03: nodeデコレータ拡張
- Issue #04: 依存解決・パイプライン改修
- Issue #05: CLI拡張

## 優先度
最高（他のすべてのissueに影響）
