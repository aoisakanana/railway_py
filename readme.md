# Railway Framework for Python

**型安全なパイプラインで、運用自動化をシンプルに。**

```python
# IDE補完が効く型安全なパイプライン
from railway import Contract, node, typed_pipeline

class UsersFetchResult(Contract):
    users: list[dict]
    total: int

class ReportResult(Contract):
    content: str

@node(output=UsersFetchResult)
def fetch_users() -> UsersFetchResult:
    return UsersFetchResult(users=[{"id": 1, "name": "Alice"}], total=1)

@node(inputs={"data": UsersFetchResult}, output=ReportResult)
def generate_report(data: UsersFetchResult) -> ReportResult:
    return ReportResult(content=f"{data.total} users found")
    #                            ^^^^
    #                            Ctrl+Space でフィールド補完！

result = typed_pipeline(fetch_users, generate_report)
print(result.content)  # IDE補完が効く！
```

**特徴:**
- IDE補完で開発効率アップ
- 型チェックでバグを早期発見
- テストはモック不要、引数を渡すだけ

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Test Coverage](https://img.shields.io/badge/coverage-90%25+-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-305%20passing-success.svg)]()

---

## Why Railway?

### 従来のパイプラインの問題

```python
# ❌ 従来: 何が渡されるか分からない
def process(data):
    users = data["users"]  # KeyError? typo? IDE補完なし
    return {"processed": users[0]["name"]}  # ネストが深い...

result = pipeline(fetch, process, save)
# result["???"] 何が入ってる？
```

### Railway の解決策

```python
# ✅ Railway: 型契約で明確に
@node(inputs={"data": FetchResult}, output=ProcessResult)
def process(data: FetchResult) -> ProcessResult:
    users = data.users  # IDE補完 ✓ 型チェック ✓
    return ProcessResult(name=users[0].name)
    #                         ^^^^
    #                         Ctrl+Space で候補表示

result = typed_pipeline(fetch, process, save)
print(result.saved_count)  # 補完が効く！
```

| 観点 | 従来 | Railway |
|------|------|---------|
| データ構造 | `dict["key"]["nested"]` | `model.field` |
| IDE補完 | ❌ | ✅ |
| 型チェック | ❌ | ✅ (mypy対応) |
| テスト | モック必須 | 引数渡しのみ |
| リファクタ | grep検索 | IDE一括変更 (F2) |

---

## Quick Start (5分)

### 1. インストール

```bash
# uvをインストール（未インストールの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# railway コマンドをインストール
uv tool install railway-framework
```

### 2. プロジェクト作成

```bash
railway init my_automation
cd my_automation
uv sync
cp .env.example .env
```

### 3. 型契約（Contract）を定義

```bash
railway new contract UsersFetchResult
```

```python
# src/contracts/users_fetch_result.py
from railway import Contract

class User(Contract):
    id: int
    name: str

class UsersFetchResult(Contract):
    users: list[User]
    total: int
```

### 4. 型付きノードを作成

```bash
railway new node fetch_users --output UsersFetchResult
```

```python
# src/nodes/fetch_users.py
from railway import node
from contracts.users_fetch_result import UsersFetchResult, User

@node(output=UsersFetchResult)
def fetch_users() -> UsersFetchResult:
    # APIからユーザー取得
    return UsersFetchResult(
        users=[User(id=1, name="Alice")],
        total=1,
    )
```

### 5. テストを書く（TDD）

```python
# tests/nodes/test_fetch_users.py
from nodes.fetch_users import fetch_users
from contracts.users_fetch_result import UsersFetchResult

def test_fetch_users():
    result = fetch_users()  # モック不要！

    assert isinstance(result, UsersFetchResult)
    assert result.total == len(result.users)
```

### 6. 実行

```bash
uv run railway run main
```

**🎉 完成！ 型安全な自動化ツールができました。**

---

## アーキテクチャ

### Contract（型契約）

ノード間で交換されるデータの「契約」を定義します。

```python
from railway import Contract

class OrderResult(Contract):
    """注文処理の結果"""
    order_id: int
    status: str
    total: float
```

**Contractの特徴:**
- **Pydantic BaseModel** がベース（自動バリデーション）
- **イミュータブル** で安全（frozen=True）
- **IDE補完** が効く

### Node（処理単位）

```python
@node(
    inputs={"order": OrderResult},  # 必要な入力を宣言
    output=ShippingResult,          # 出力の型を宣言
)
def create_shipping(order: OrderResult) -> ShippingResult:
    # 純粋関数として実装
    return ShippingResult(
        order_id=order.order_id,
        tracking_number=generate_tracking(),
    )
```

### Pipeline（実行）

```python
from railway import typed_pipeline

result = typed_pipeline(
    create_order,      # OrderResult を出力
    process_payment,   # PaymentResult を出力
    create_shipping,   # OrderResult を入力、ShippingResult を出力
)
# result は ShippingResult 型
```

**依存関係はフレームワークが自動解決:**
```
create_order ─────────────────┐
  output: OrderResult              │
                                   ├──> create_shipping
process_payment ──────────────┘       output: ShippingResult
  output: PaymentResult
```

---

## CLI Commands

### プロジェクト管理
```bash
railway init <name>              # プロジェクト作成
railway new entry <name>         # エントリポイント作成
railway docs                     # ドキュメント表示
```

### Contract（型契約）
```bash
railway new contract <Name>          # Contract作成
railway new contract <Name> --entity # エンティティContract（id付き）
railway new contract <Name> --params # パラメータ用Contract
railway list contracts               # Contract一覧
```

### Node（処理単位）
```bash
railway new node <name>                      # 基本node作成
railway new node <name> --output ResultType  # 出力型指定
railway new node <name> --input data:InputType --output ResultType
railway show node <name>                     # 依存関係表示
```

### 実行
```bash
railway run <entry>              # 実行
railway list                     # エントリポイント/ノード一覧
```

---

## 特徴

- ✨ **5分で開始**: `railway init` でプロジェクト作成、すぐに実装開始
- 🛤️ **型安全パイプライン**: Contract による型契約でIDE補完が効く
- 🔒 **型チェック**: mypyによる静的型チェック + ランタイム検証
- 🐍 **Pythonらしいエラーハンドリング**: 例外機構を活かした3層設計
- ⚡ **非同期対応**: async/await 完全サポート
- 🎯 **シンプルなAPI**: デコレータベースで直感的
- 📝 **自動生成**: テンプレートから即座にコード生成
- 🧪 **テスト容易**: モック不要、引数を渡すだけ
- ⚙️ **環境別設定**: development/production を簡単に切り替え
- 🔄 **自動リトライ**: 一時的なエラーに自動で対処
- 📊 **構造化ロギング**: loguru による美しいログ出力

---

## コア概念

### 1. ノード (@node)

**ノード = 再利用可能な処理単位**

```python
from railway import node
from loguru import logger

@node(retry=True)  # リトライ有効化
def fetch_data(url: str) -> dict:
    """データ取得ノード"""
    logger.info(f"Fetching from {url}")
    response = requests.get(url)
    return response.json()
```

**型付きノード（推奨）:**
```python
@node(output=UsersFetchResult)
def fetch_users() -> UsersFetchResult:
    return UsersFetchResult(users=[...], total=10)

@node(inputs={"users": UsersFetchResult}, output=ReportResult)
def generate_report(users: UsersFetchResult) -> ReportResult:
    return ReportResult(content=f"{users.total} users")
```

### 2. エントリーポイント (@entry_point)

**エントリーポイント = 実行の起点**

```python
from railway import entry_point, typed_pipeline

@entry_point
def main(date: str = None, dry_run: bool = False):
    """日次レポート生成"""
    result = typed_pipeline(
        fetch_data,
        process_data,
        generate_report,
    )
    return result
```

### 3. パイプライン

**レガシーパイプライン（dict渡し）:**
```python
result = pipeline(
    step1(),
    step2,
    step3,
)
```

**型付きパイプライン（推奨）:**
```python
result = typed_pipeline(
    fetch_users,      # UsersFetchResult を出力
    process_users,    # UsersFetchResult を入力
    generate_report,  # ReportResult を出力
)
# result は ReportResult 型
```

**inputs 自動推論:**

Contract 型の引数は自動的に依存関係として解決されます。
明示的な `inputs=` 指定は不要です。

```python
# 型ヒントから自動的に inputs が推論される
@node(output=ReportResult)
def generate_report(users: UsersFetchResult) -> ReportResult:
    # UsersFetchResult は自動的に前のステップから解決
    return ReportResult(content=f"{users.total} users")
```

### pipeline vs typed_pipeline

| 特徴 | `typed_pipeline` | `pipeline` |
|------|------------------|------------|
| 最初の引数 | 関数（@node） | 評価済みの値 |
| 型安全性 | Contract ベース | 限定的 |
| IDE補完 | フル対応 | 限定的 |
| 依存解決 | 自動 | なし |
| エラーハンドリング | `on_error`, `on_step` | 例外伝播のみ |
| 推奨用途 | **通常の開発** | 動的構成、既存値から開始 |

**typed_pipeline（推奨）:**
```python
result = typed_pipeline(fetch, process, save)  # 関数を渡す
```

**pipeline（レガシー）:**
```python
result = pipeline(initial_value, step1, step2)  # 最初に値を渡す
```

---

## エラーハンドリング

Railway Framework は **Python標準の例外機構を最大限活用** します。
新しい概念を導入せず、Pythonエンジニアが慣れ親しんだパターンで運用できます。

### 設計思想: 3層のエラーハンドリング

```
┌─────────────────────────────────────────────────────────────┐
│ レベル1: Node内部                                            │
│   シンプル: 必要な箇所でtry/exceptを書く                      │
│   リトライ: retry_on で一時的エラーを自動リトライ             │
├─────────────────────────────────────────────────────────────┤
│ レベル2: Pipeline（デフォルト）                              │
│   何もしない: 例外はそのまま伝播                              │
│   スタックトレース保持、デバッグ容易                          │
├─────────────────────────────────────────────────────────────┤
│ レベル3: Pipeline（必要な時だけ）                            │
│   on_error: 例外をマッチしてフォールバック/ログ/再送出        │
└─────────────────────────────────────────────────────────────┘
```

### なぜこの設計か？

| 設計判断 | 理由 |
|----------|------|
| Result型を採用しない | Pythonエコシステム（requests等）は例外ベース。ラップは冗長。 |
| デフォルトは例外伝播 | スタックトレースが保持され、デバッグしやすい。 |
| on_errorは任意 | 高度な制御が必要な時だけ使う。シンプルなケースを複雑にしない。 |

### 使用例

#### シンプルなケース（レベル2で十分）

```python
# 例外はそのまま伝播。これで十分なケースが多い。
result = typed_pipeline(fetch_users, process, save)
```

#### Node内で処理（レベル1）

```python
@node
def fetch_users():
    try:
        return api.get_users()
    except NotFoundError:
        return []  # このNodeで完結
```

#### 一時的エラーのリトライ（レベル1）

```python
@node(retries=3, retry_on=(ConnectionError, TimeoutError))
def fetch_data():
    return requests.get(API_URL).json()
```

#### Pipeline単位の高度な制御（レベル3）

```python
def handle_error(error: Exception, step_name: str) -> Any:
    match error:
        case ConnectionError():
            return load_from_cache()  # フォールバック
        case _:
            raise  # 再送出

result = typed_pipeline(fetch, process, save, on_error=handle_error)
```

---

## デバッグと監査

### on_step コールバック

パイプラインの各ステップ完了後にコールバックを受け取れます。
デバッグ、監査ログ、メトリクス収集に便利です。

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

**on_error と併用可能:**

```python
result = typed_pipeline(
    fetch, process, save,
    on_step=capture_step,    # 各ステップをログ
    on_error=handle_error    # エラー時のフォールバック
)
```

---

## 設定管理

### 統合設定ファイル: config/development.yaml

```yaml
# アプリケーション設定
app:
  name: my_automation

# API設定
api:
  base_url: "https://api.example.com"
  timeout: 30

# ログ設定
logging:
  level: DEBUG
  handlers:
    - type: console
      level: DEBUG
    - type: file
      path: logs/app.log

# リトライ設定
retry:
  default:
    max_attempts: 3
    min_wait: 2
    max_wait: 10
```

### コードから設定にアクセス

```python
from src.settings import settings

url = settings.api.base_url
retry_config = settings.get_retry_settings("fetch_data")
```

---

## テストの書き方

**型付きノードはテストが簡単:**

```python
# tests/nodes/test_process_users.py
from contracts.users import UsersFetchResult, User
from contracts.report import ReportResult
from nodes.process_users import process_users

def test_process_users():
    # Arrange - 引数を渡すだけ（モック不要）
    users = UsersFetchResult(
        users=[User(id=1, name="Alice")],
        total=1,
    )

    # Act
    result = process_users(users)

    # Assert
    assert isinstance(result, ReportResult)
    assert "Alice" in result.content
```

```bash
# テスト実行
pytest -v
pytest --cov=src --cov-report=html
```

---

## 実例: 日次レポート生成

### ステップ1: Contractを定義

```bash
railway new contract SalesData
railway new contract ReportResult
```

### ステップ2: ノードを作成

```bash
railway new node fetch_sales --output SalesData
railway new node generate_report --input data:SalesData --output ReportResult
```

### ステップ3: エントリーポイント

```python
# src/daily_report.py
from railway import entry_point, typed_pipeline
from nodes.fetch_sales import fetch_sales
from nodes.generate_report import generate_report

@entry_point
def main(date: str = None):
    result = typed_pipeline(
        fetch_sales,
        generate_report,
    )
    print(result.content)
    return result
```

### ステップ4: 実行

```bash
uv run railway run daily_report
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

## 採用技術スタック

| ライブラリ | 用途 |
|-----------|------|
| `pydantic` | Contract（データバリデーション） |
| `tenacity` | リトライ処理 |
| `typer` | CLIインターフェース |
| `loguru` | 構造化ロギング |

---

## ロードマップ

### Phase 1 ✅ 完了
- ✅ `@node`, `@entry_point` デコレータ
- ✅ `pipeline()`, `async_pipeline()` 関数
- ✅ 設定管理、ロギング、リトライ
- ✅ CLIツール (`init`, `new`, `list`, `run`)

### Phase 1.5 ✅ 完了（Output Model Pattern）
- ✅ `Contract` ベースクラス
- ✅ `Params` パラメータクラス
- ✅ `typed_pipeline()`, `typed_async_pipeline()`
- ✅ `DependencyResolver` 自動依存解決
- ✅ CLI拡張 (`new contract`, `list contracts`, `show node`)

### Phase 1.6 ✅ 完了（3層エラーハンドリング）
- ✅ `on_error` コールバック（パイプラインレベルのエラー制御）
- ✅ `on_step` コールバック（中間結果へのアクセス）
- ✅ `RetryPolicy` / `retries` / `retry_on`（柔軟なリトライ設定）
- ✅ inputs 自動推論（型ヒントからの依存関係解決）
- ✅ ログメッセージ日本語統一

### Phase 2 📋 計画中
- 🔜 並列パイプライン実行
- 🔜 グラフベースワークフロー
- 🔜 WebUI
- 🔜 メトリクス収集

---

## ライセンス

MIT License

---

**Railway Framework で型安全な運用自動化を始めましょう！**

```bash
railway init my_automation
cd my_automation
railway new contract UserResult
railway new node fetch_users --output UserResult
uv run railway run main
```
