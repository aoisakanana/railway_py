# Issue #07: TUTORIAL.md - Output Model 体験の再設計

## 概要
`railway init`で自動生成されるTUTORIAL.mdを再設計し、Output Modelパターンの利点を段階的に体験できるようにする。

## 依存関係
- Issue #01-05: Output Modelコアアーキテクチャ（先行）
- Issue #06: README利点体感（参考）

## 目的
チュートリアルを完了したユーザーが：
1. **型安全性の価値**を実感している
2. **Contract → Node → Pipeline**の流れを理解している
3. **TDDワークフロー**を体験している
4. **「モックなしでテストできる」**喜びを感じている

---

## 体験設計の原則

### 1. 段階的な「アハ体験」

| Step | 体験 | アハ体験 |
|------|------|---------|
| 1 | Hello World | 「2分で動いた！」 |
| 2 | Contract定義 | 「型を定義するのか」 |
| 3 | TDD Red Phase | 「テストが先なんだ」 |
| 4 | Node実装 | 「引数で受け取って返すだけ！」 |
| 5 | IDE補完体験 | 「補完が効く！便利！」 |
| 6 | Pipeline | 「依存関係が自動解決される！」 |
| 7 | リファクタ | 「フィールド名変更が安全！」 |

### 2. 従来手法との対比

各Stepで「従来ならこう書く → Railwayならこう書く」を示し、利点を実感させる。

### 3. 実践的なシナリオ

「ユーザー一覧を取得してレポートを生成する」という現実的なシナリオで一貫して進める。

---

## TUTORIAL.md 構成

### Step 0: はじめに（1分）

```markdown
# Railway チュートリアル

このチュートリアルでは、Railwayの**型安全なパイプライン**を体験します。

## 学べること
- ✅ Contract（型契約）によるデータ定義
- ✅ Node（処理単位）の実装
- ✅ TDDワークフロー
- ✅ IDE補完の活用
- ✅ Pipeline（実行）の組み立て

## 所要時間
約15分

## 前提条件
- Python 3.10+
- お好みのIDE（VSCode推奨）
```

### Step 1: Hello World（2分）

```markdown
## Step 1: Hello World

### 1.1 エントリポイントの作成

```bash
railway new entry hello
```

### 1.2 実行

```bash
railway run hello
```

出力：
```
Hello, Railway!
```

🎉 **2分でHello World完了！**

次のStepでは、型安全なパイプラインの核心である「Contract」を学びます。
```

### Step 2: Contract（型契約）の定義（3分）

```markdown
## Step 2: Contract - データの「契約」を定義する

Railwayでは、ノード間で交換するデータの構造を**Contract**として定義します。

### 2.1 なぜContractが必要？

従来のパイプライン：
```python
# ❌ 何が入っているか分からない
def process(data):
    users = data["users"]  # KeyError? typo?
    return {"result": users}
```

Railway：
```python
# ✅ 型で明確に定義
class UsersFetchResult(Contract):
    users: list[User]
    total: int

def process(data: UsersFetchResult) -> ProcessResult:
    users = data.users  # IDE補完が効く！
```

### 2.2 Contractを作成

```bash
railway new contract UsersFetchResult
```

生成されたファイルを編集：

```python
# src/contracts/users_fetch_result.py
from railway import Contract

class User(Contract):
    """ユーザーエンティティ"""
    id: int
    name: str
    email: str

class UsersFetchResult(Contract):
    """fetch_usersノードの出力契約"""
    users: list[User]
    total: int
```

### 2.3 ポイント

- Contractは **Pydantic BaseModel** がベース
- フィールドに型を指定すると **自動バリデーション**
- IDE補完・型チェックが有効に
```

### Step 3: TDD - テストを先に書く（3分）

```markdown
## Step 3: TDD - テストを先に書く

Railwayでは **テストファースト** を推奨します。まず失敗するテストを書きましょう。

### 3.1 テストファイルを確認

`railway new node`でNodeと一緒にテストファイルが生成されます：

```bash
railway new node fetch_users --output UsersFetchResult
```

### 3.2 テストを書く（Red Phase）

```python
# tests/nodes/test_fetch_users.py
from contracts.users_fetch_result import UsersFetchResult, User
from nodes.fetch_users import fetch_users

class TestFetchUsers:
    def test_returns_users_fetch_result(self):
        """正しい型を返すこと"""
        result = fetch_users()
        assert isinstance(result, UsersFetchResult)

    def test_returns_at_least_one_user(self):
        """少なくとも1人のユーザーを返すこと"""
        result = fetch_users()
        assert result.total >= 1
        assert len(result.users) == result.total
```

### 3.3 テストを実行（失敗を確認）

```bash
uv run pytest tests/nodes/test_fetch_users.py -v
```

```
FAILED test_returns_users_fetch_result - NotImplementedError
FAILED test_returns_at_least_one_user - NotImplementedError
```

🔴 **これがRed Phase！** テストが失敗することを確認しました。

### 3.4 ポイント：モックが不要！

```python
# ❌ 従来: Contextのモックが必要
def test_fetch_users():
    ctx = MagicMock()
    fetch_users(ctx)
    ctx.__setitem__.assert_called_with("fetch_users", ...)

# ✅ Railway: 引数を渡して戻り値を確認するだけ
def test_fetch_users():
    result = fetch_users()
    assert result.total >= 1
```

**純粋関数なのでテストが簡単！**
```

### Step 4: Node実装（3分）

```markdown
## Step 4: Node - 処理を実装する

テストを通すための実装を書きます。

### 4.1 Nodeを実装（Green Phase）

```python
# src/nodes/fetch_users.py
from railway import node
from contracts.users_fetch_result import UsersFetchResult, User

@node(output=UsersFetchResult)
def fetch_users() -> UsersFetchResult:
    """ユーザー一覧を取得する"""
    # 実際のAPIコール（ここではダミーデータ）
    users = [
        User(id=1, name="Alice", email="alice@example.com"),
        User(id=2, name="Bob", email="bob@example.com"),
    ]
    return UsersFetchResult(
        users=users,
        total=len(users),
    )
```

### 4.2 テストを実行（成功を確認）

```bash
uv run pytest tests/nodes/test_fetch_users.py -v
```

```
PASSED test_returns_users_fetch_result
PASSED test_returns_at_least_one_user
```

🟢 **これがGreen Phase！** テストが通りました。

### 4.3 ポイント

```python
@node(output=UsersFetchResult)  # 出力型を宣言
def fetch_users() -> UsersFetchResult:  # 型ヒントで明確
    return UsersFetchResult(...)  # Contractインスタンスを返す
```

- **純粋関数**: 引数を受け取り、値を返すだけ
- **副作用なし**: ctx への書き込みは不要
- **型安全**: 戻り値の型が保証される
```

### Step 5: IDE補完を体験（2分）

```markdown
## Step 5: IDE補完を体験する

Output Modelパターンの最大の利点を体験しましょう。

### 5.1 別のNodeを作成

```bash
railway new node generate_report \
    --input users:UsersFetchResult \
    --output ReportResult
```

### 5.2 IDEで補完を試す

VSCodeで `src/nodes/generate_report.py` を開き：

```python
@node(
    inputs={"users": UsersFetchResult},
    output=ReportResult,
)
def generate_report(users: UsersFetchResult) -> ReportResult:
    # ここで users. と入力してみてください
    users.  # ← Ctrl+Space
```

補完候補：
```
users.users  → list[User]
users.total  → int
```

さらに：
```python
    user = users.users[0]
    user.  # ← Ctrl+Space
```

補完候補：
```
user.id     → int
user.name   → str
user.email  → str
```

🎉 **IDE補完が効く！** typoも型エラーも即座に発見できます。

### 5.3 従来との比較

```python
# ❌ 従来: 補完が効かない
users = ctx["fetch_users"]["users"][0]
users["name"]  # typo しても気づかない

# ✅ Railway: 補完が効く
user = users.users[0]
user.name  # typo するとIDEが警告
```
```

### Step 6: Pipeline（3分）

```markdown
## Step 6: Pipeline - ノードを組み合わせる

複数のNodeを組み合わせてパイプラインを構築します。

### 6.1 ReportResult Contractを作成

```bash
railway new contract ReportResult
```

```python
# src/contracts/report_result.py
from railway import Contract
from datetime import datetime

class ReportResult(Contract):
    """レポート生成結果"""
    content: str
    user_count: int
    generated_at: datetime
```

### 6.2 generate_reportを実装

```python
# src/nodes/generate_report.py
from datetime import datetime
from railway import node
from contracts.users_fetch_result import UsersFetchResult
from contracts.report_result import ReportResult

@node(
    inputs={"users": UsersFetchResult},
    output=ReportResult,
)
def generate_report(users: UsersFetchResult) -> ReportResult:
    """ユーザー一覧からレポートを生成"""
    names = ", ".join(u.name for u in users.users)
    return ReportResult(
        content=f"Users: {names}",
        user_count=users.total,
        generated_at=datetime.now(),
    )
```

### 6.3 Pipelineで実行

```python
# src/main.py
from railway import pipeline
from nodes.fetch_users import fetch_users
from nodes.generate_report import generate_report

def main():
    result = pipeline(
        fetch_users,      # UsersFetchResult を出力
        generate_report,  # UsersFetchResult を入力 → ReportResult を出力
    )

    print(result.content)      # IDE補完が効く！
    print(result.user_count)   # 型も明確！

if __name__ == "__main__":
    main()
```

### 6.4 実行

```bash
railway run main
```

```
Users: Alice, Bob
2
```

### 6.5 依存関係の自動解決

```
fetch_users ──────────────> generate_report
  output: UsersFetchResult    input: UsersFetchResult
                              output: ReportResult
```

フレームワークが型を見て自動的に依存関係を解決します。
```

### Step 7: リファクタリングの安全性（2分）

```markdown
## Step 7: 安全なリファクタリング

Output Modelパターンのもう一つの大きな利点を体験します。

### 7.1 フィールド名を変更したい

`UsersFetchResult.total` を `count` に変更したいとします。

### 7.2 従来の問題

```python
# ❌ 従来: 文字列なので grep で探すしかない
ctx["fetch_users"]["total"]  # どこで使われてる？
```

変更漏れがあっても、実行時まで気づかない...

### 7.3 Railwayでの安全な変更

1. **Contract を変更**:
```python
class UsersFetchResult(Contract):
    users: list[User]
    count: int  # total → count に変更
```

2. **IDEが全参照箇所をハイライト**:
   - `fetch_users.py` の `total=len(users)`
   - `generate_report.py` の `users.total`
   - テストファイル内の参照

3. **一括リネーム** (F2キー):
   - 全ファイルを自動で更新

4. **型チェックで確認**:
```bash
mypy src/
```

🎉 **変更漏れゼロ！** IDEと型チェッカーが守ってくれます。
```

### Step 8: 次のステップ

```markdown
## 次のステップ

おめでとうございます！🎉 Railwayの基本を習得しました。

### 学んだこと
- ✅ Contract で型契約を定義
- ✅ Node で純粋関数として処理を実装
- ✅ TDD でテストファーストに開発
- ✅ IDE補完の活用
- ✅ Pipeline で依存関係を自動解決
- ✅ 安全なリファクタリング

### さらに学ぶ
- [非同期Node](./docs/async.md)
- [リトライ機能](./docs/retry.md)
- [設定管理](./docs/config.md)
- [本番運用のベストプラクティス](./docs/production.md)

### コミュニティ
- [GitHub Issues](https://github.com/...)
- [Discussions](https://github.com/.../discussions)
```

---

## 実装タスク

1. [ ] Step 0-1: Hello World（既存の流用可）
2. [ ] Step 2: Contract体験（なぜ必要かを先に説明）
3. [ ] Step 3: TDD Red Phase（失敗を体験させる）
4. [ ] Step 4: Node実装（純粋関数の利点を強調）
5. [ ] Step 5: IDE補完体験（スクリーンショット検討）
6. [ ] Step 6: Pipeline（依存自動解決を図解）
7. [ ] Step 7: リファクタ体験（安全性を実感）
8. [ ] Step 8: 次のステップへの誘導

## 優先度
高（#01-05, #06完了後）

## 関連ファイル
- TUTORIAL.mdテンプレート生成処理
- `railway init`コマンド

## 成功基準
- チュートリアル完了後、ユーザーが「型安全って便利」と感じる
- 「モックなしでテストできる」ことに感動する
- 「IDE補完が効く」ことを実際に体験している
