# Railway Framework - 線形パイプライン

このドキュメントは `typed_pipeline` を使用した線形パイプラインの詳細ガイドです。

条件分岐が必要な場合は [README.md](readme.md) の dag_runner を使用してください。

---

## 線形パイプラインとは

処理が必ず順番に実行されるパイプラインです：

```
A → B → C → D
```

条件分岐はありません。ETL、データ変換に適しています。

---

## クイックスタート

### 1. エントリーポイント作成

```bash
railway new entry my_pipeline --mode linear
```

### 2. 生成されるファイル

```
src/
├── my_pipeline.py           # typed_pipeline 使用
└── nodes/
    └── my_pipeline/
        ├── __init__.py
        ├── step1.py         # Contract 返却
        └── step2.py
```

### 3. エントリーポイント

```python
from railway import entry_point, typed_pipeline
from nodes.my_pipeline.step1 import step1
from nodes.my_pipeline.step2 import step2


@entry_point
def main():
    result = typed_pipeline(
        step1,
        step2,
    )
    return result
```

### 4. ノード実装

```python
from railway import Contract, node


class Step1Output(Contract):
    data: str


@node(output=Step1Output)
def step1() -> Step1Output:
    return Step1Output(data="processed")
```

---

## typed_pipeline の特徴

- **Contract 自動解決**: 次のノードに必要な Contract を自動で渡す
- **シンプル**: 状態管理不要
- **線形処理専用**: 条件分岐不可
- **IDE補完**: Contract の型情報でIDE補完が効く

---

## ノードの書き方

### 基本形

```python
from railway import Contract, node


class UsersFetchResult(Contract):
    users: list[dict]
    total: int


@node(output=UsersFetchResult)
def fetch_users() -> UsersFetchResult:
    """ユーザー取得ノード"""
    return UsersFetchResult(
        users=[{"id": 1, "name": "Alice"}],
        total=1,
    )
```

### 入力依存

型ヒントから自動的に依存関係が解決されます：

```python
from railway import Contract, node


class ReportResult(Contract):
    content: str


@node(output=ReportResult)
def generate_report(users: UsersFetchResult) -> ReportResult:
    """レポート生成ノード

    UsersFetchResult は前のステップから自動解決される
    """
    return ReportResult(content=f"{users.total} users found")
```

### 複数入力

```python
@node(output=SummaryResult)
def create_summary(
    users: UsersFetchResult,
    orders: OrdersFetchResult
) -> SummaryResult:
    """複数の入力を受け取るノード"""
    return SummaryResult(
        user_count=users.total,
        order_count=orders.total,
    )
```

---

## パイプラインの構成

### 基本形

```python
from railway import typed_pipeline

result = typed_pipeline(
    fetch_users,      # UsersFetchResult を出力
    process_users,    # UsersFetchResult を入力、ProcessedResult を出力
    generate_report,  # ProcessedResult を入力、ReportResult を出力
)
# result は ReportResult 型
```

### 依存関係の自動解決

```
fetch_users ─────────────────┐
  output: UsersFetchResult        │
                                  ├──> generate_report
process_payment ──────────────┘       output: ReportResult
  output: PaymentResult
```

### on_step コールバック

各ステップ完了後にコールバックを受け取れます：

```python
steps = []

def capture_step(step_name: str, output: Any) -> None:
    steps.append({"step": step_name, "output": output})

result = typed_pipeline(
    fetch_users, process_users, generate_report,
    on_step=capture_step
)

# 各ステップの結果を確認
for step in steps:
    print(f"[{step['step']}] -> {step['output']}")
```

### on_error コールバック

エラー発生時のハンドリング：

```python
def handle_error(error: Exception, step_name: str) -> Any:
    match error:
        case ConnectionError():
            return load_from_cache()  # フォールバック
        case _:
            raise  # 再送出

result = typed_pipeline(
    fetch, process, save,
    on_error=handle_error
)
```

---

## 非同期サポート

```python
from railway import node
from railway.core.resolver import typed_async_pipeline

@node(output=UsersFetchResult)
async def fetch_users_async() -> UsersFetchResult:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            return UsersFetchResult(users=data["users"], total=len(data["users"]))

@entry_point
async def main():
    result = await typed_async_pipeline(
        fetch_users_async,
        process_users,
    )
    return result
```

---

## dag_runner との比較

| 項目 | typed_pipeline | dag_runner |
|------|----------------|------------|
| 分岐 | 不可 | 可能 |
| 遷移定義 | コード内（順番で定義） | YAML |
| 戻り値 | Contract | tuple[Contract, Outcome] |
| 用途 | ETL、データ変換 | 運用自動化 |
| 複雑度 | シンプル | やや複雑 |
| 柔軟性 | 低い | 高い |

---

## いつ dag_runner に移行すべきか

以下の場合は dag_runner への移行を検討してください：

- **条件分岐が必要**: 処理結果に応じて次のステップが変わる
- **エラーパスが複数**: エラー種別に応じて異なる対応が必要
- **複雑なワークフロー**: 複数の終了パスがある

```python
# typed_pipeline: 線形フロー
A → B → C → D

# dag_runner: 条件分岐フロー
    ┌→ B → D
A → │
    └→ C → E
```

---

## 実例: ETLパイプライン

### ステップ1: Contractを定義

```python
# src/contracts/sales.py
from railway import Contract

class SalesData(Contract):
    records: list[dict]
    date: str

class TransformedData(Contract):
    total: float
    count: int
    date: str

class SaveResult(Contract):
    success: bool
    file_path: str
```

### ステップ2: ノードを作成

```python
# src/nodes/extract.py
@node(output=SalesData)
def extract() -> SalesData:
    # CSVからデータ抽出
    return SalesData(records=[...], date="2026-01-26")

# src/nodes/transform.py
@node(output=TransformedData)
def transform(data: SalesData) -> TransformedData:
    total = sum(r["amount"] for r in data.records)
    return TransformedData(total=total, count=len(data.records), date=data.date)

# src/nodes/load.py
@node(output=SaveResult)
def load(data: TransformedData) -> SaveResult:
    # データベースに保存
    return SaveResult(success=True, file_path=f"/data/{data.date}.json")
```

### ステップ3: エントリーポイント

```python
# src/daily_etl.py
from railway import entry_point, typed_pipeline
from nodes.extract import extract
from nodes.transform import transform
from nodes.load import load

@entry_point
def main():
    result = typed_pipeline(
        extract,
        transform,
        load,
    )
    print(f"Saved to: {result.file_path}")
    return result
```

### ステップ4: 実行

```bash
railway run daily_etl
```

---

## テストの書き方

```python
from contracts.sales import SalesData, TransformedData
from nodes.transform import transform

def test_transform():
    # Arrange
    data = SalesData(
        records=[
            {"amount": 100},
            {"amount": 200},
        ],
        date="2026-01-26"
    )

    # Act
    result = transform(data)

    # Assert
    assert isinstance(result, TransformedData)
    assert result.total == 300
    assert result.count == 2
```

---

## 参照

- [README.md](readme.md) - メインドキュメント（dag_runner）
- [ADR-002: 実行モデルの共存](docs/adr/002_execution_models.md) - 設計決定
- [TUTORIAL.md](TUTORIAL.md) - ハンズオンチュートリアル
