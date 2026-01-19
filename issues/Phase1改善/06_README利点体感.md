# Issue #06: README.md - Output Model アーキテクチャの利点体感

## 概要
README.mdを更新し、Output Modelパターンの利点をユーザーが直感的に体感できるようにする。

## 依存関係
- Issue #01-05: Output Modelコアアーキテクチャ（先行）

## 目的
READMEを読んだユーザーが「これは便利そうだ」と感じ、すぐに試したくなる構成にする。

---

## 利点の体感ポイント

### 1. 型安全性とIDE補完

**Before（従来）**:
```python
@node
def process_data(ctx):
    user = ctx["fetch_users"]["users"][0]  # 何が入ってる？
    #      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    #      IDE補完なし、typoに気づかない
```

**After（Output Model）**:
```python
@node(inputs={"data": UsersFetchResult}, output=ProcessResult)
def process_data(data: UsersFetchResult) -> ProcessResult:
    user = data.users[0]  # IDE補完が効く！
    #      ^^^^
    #      Ctrl+Space で候補が出る
    return ProcessResult(processed=user.name)
```

### 2. テストの簡潔さ

**Before（従来）**:
```python
def test_process_data():
    # Contextのモックが必要
    ctx = MagicMock()
    ctx.__getitem__.return_value = {"users": [...]}
    process_data(ctx)
    # 何がセットされたか確認が面倒
```

**After（Output Model）**:
```python
def test_process_data():
    # 引数を渡すだけ
    data = UsersFetchResult(users=[User(id=1, name="Alice")], total=1)
    result = process_data(data)
    assert result.processed == "Alice"  # 明確！
```

### 3. リファクタリングの安全性

**Before（従来）**:
```python
# "users" を "members" に変更したい...
ctx["fetch_users"]["users"]  # どこで使われてる？ 全部探す？
```

**After（Output Model）**:
```python
# フィールド名を変更 → IDEが全参照箇所をハイライト
class UsersFetchResult(Contract):
    members: list[User]  # users → members に変更
#   ^^^^^^^
#   F2キーで一括リネーム可能
```

---

## README.md 更新内容

### 1. ヒーローセクション（冒頭）

```markdown
# Railway Framework

**運用自動化を型安全に。**

```python
# 型で守られたパイプライン
@node(output=UsersFetchResult)
def fetch_users() -> UsersFetchResult:
    return UsersFetchResult(users=api.get_users())

@node(inputs={"users": UsersFetchResult}, output=ReportResult)
def generate_report(users: UsersFetchResult) -> ReportResult:
    return ReportResult(content=f"{len(users.users)} users found")

# 実行
result = pipeline(fetch_users, generate_report)
print(result.content)  # IDE補完が効く！
```

✅ IDE補完が効く
✅ 型チェックでバグを早期発見
✅ テストはモック不要
```

### 2. Why Railway? セクション

```markdown
## Why Railway?

### 従来のパイプラインの問題

```python
# ❌ 従来: 何が渡されるか分からない
def process(data):
    users = data["users"]  # KeyError? typo?
    return {"processed": users}

result = pipeline(fetch, process, save)
# result["???"] 何が入ってる？
```

### Railway の解決策

```python
# ✅ Railway: 型契約で明確に
@node(inputs={"data": FetchResult}, output=ProcessResult)
def process(data: FetchResult) -> ProcessResult:
    users = data.users  # IDE補完 ✓ 型チェック ✓
    return ProcessResult(processed=users)

result = pipeline(fetch, process, save)
print(result.saved_count)  # 補完が効く！
```

| 観点 | 従来 | Railway |
|------|------|---------|
| データ構造 | `dict["key"]["nested"]` | `model.field` |
| IDE補完 | ❌ | ✅ |
| 型チェック | ❌ | ✅ (mypy対応) |
| テスト | モック必須 | 引数渡しのみ |
| リファクタ | grep検索 | IDE一括変更 |
```

### 3. Quick Start セクション

```markdown
## Quick Start

### 1. インストール
```bash
pip install railway-framework
```

### 2. プロジェクト作成
```bash
railway init myproject
cd myproject
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
    result = fetch_users()

    assert isinstance(result, UsersFetchResult)
    assert result.total == len(result.users)
```

### 6. 実行
```bash
railway run main
```
```

### 4. アーキテクチャセクション

```markdown
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

Contractは：
- **Pydantic BaseModel** がベース
- **自動バリデーション** で不正なデータを弾く
- **イミュータブル** で安全

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
from railway import pipeline

result = pipeline(
    create_order,      # OrderResult を出力
    process_payment,   # PaymentResult を出力
    create_shipping,   # OrderResult を入力、ShippingResult を出力
)
# result は ShippingResult 型
```

依存関係はフレームワークが自動解決：
```
create_order ─────────────────┐
  output: OrderResult              │
                                   ├──> create_shipping
process_payment ──────────────┘       output: ShippingResult
  output: PaymentResult
```
```

### 5. CLIコマンド一覧

```markdown
## CLI Commands

### プロジェクト管理
```bash
railway init <name>              # プロジェクト作成
railway new entry <name>         # エントリポイント作成
```

### Contract（型契約）
```bash
railway new contract <Name>          # Contract作成
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

### 実行・テスト
```bash
railway run <entry>              # 実行
railway run <entry> --param k=v  # パラメータ付き実行
railway test                     # テスト実行
```
```

---

## 実装タスク

1. [ ] ヒーローセクションの作成（コード例で利点を即座に示す）
2. [ ] Why Railway? セクションの作成（Before/After比較）
3. [ ] Quick Startの更新（Contract → Node → Test → Run の流れ）
4. [ ] アーキテクチャセクションの図解
5. [ ] CLIコマンド一覧の更新
6. [ ] 既存コンテンツとの整合性確認

## 優先度
高（#01-05完了後、最初に実施）

## 関連ファイル
- `README.md`

## 成功基準
- READMEを5分読んだユーザーが「試してみたい」と思える
- IDE補完の利点が視覚的に伝わる
- 従来手法との違いが明確
