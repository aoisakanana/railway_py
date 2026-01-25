# test_project チュートリアル

Railway Framework の**型安全なパイプライン**を体験しましょう！

## 学べること

- Contract（型契約）によるデータ定義
- Node（処理単位）の実装
- IDE補完の活用
- TDDワークフロー
- typed_pipeline による依存関係の自動解決
- バージョン管理と安全なアップグレード

## 所要時間

約15分

## 前提条件

- Python 3.10以上
- uv インストール済み（`curl -LsSf https://astral.sh/uv/install.sh | sh`）
- VSCode推奨（IDE補完を体験するため）

## セットアップ

```bash
uv sync --group dev
cp .env.example .env
```

---

## Step 1: Hello World（2分）

まずは動作確認から。

### 1.1 実行

```bash
uv run railway run hello
```

**期待される出力:**
```
Hello, World!
```

🎉 **2分で動きました！** 次のStepでは、型安全の核心「Contract」を学びます。

---

## Step 2: Contract - データの「契約」を定義する（3分）

従来のパイプラインの問題点：

```python
# ❌ 従来: 何が入っているか分からない
def process(data):
    users = data["users"]  # KeyError? typo? IDE補完なし
```

Railwayでは**Contract**でデータ構造を定義します：

```python
# ✅ Railway: 型で明確に定義
class UsersFetchResult(Contract):
    users: list[User]
    total: int
```

### 2.1 Contractを作成

```bash
railway new contract UsersFetchResult
```

### 2.2 ファイルを編集

`src/contracts/users_fetch_result.py` を以下の内容で**上書き**してください:

```python
"""UsersFetchResult contract."""

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

**ポイント:**
- **Pydantic BaseModel** がベース（自動バリデーション）
- フィールドに型を指定 → **IDE補完が効く**

---

## Step 3: TDD - テストを先に書く（3分）

Railwayでは**テストファースト**を推奨。まず失敗するテストを書きます。

### 3.1 型付きノードを生成

```bash
railway new node fetch_users --output UsersFetchResult
```

`--output` オプションで出力型を指定すると、テストファイルも型付きで生成されます。

### 3.2 テストを編集（Red Phase）

`tests/nodes/test_fetch_users.py` を以下の内容で**上書き**してください:

```python
"""Tests for fetch_users node."""

from contracts.users_fetch_result import UsersFetchResult
from nodes.fetch_users import fetch_users


class TestFetchUsers:
    def test_returns_users_fetch_result(self):
        """正しい型を返すこと"""
        result = fetch_users()
        assert isinstance(result, UsersFetchResult)

    def test_returns_at_least_one_user(self):
        """少なくとも1人のユーザーを返すこと"""
        result = fetch_users()
        assert result.total >= 1  # IDE補完が効く！
        assert len(result.users) == result.total
```

**💡 ポイント: モックが不要！**

```python
# ❌ 従来: Contextのモックが必要
def test_fetch_users():
    ctx = MagicMock()
    fetch_users(ctx)
    ctx.__setitem__.assert_called_with(...)

# ✅ Railway: 引数を渡して戻り値を確認するだけ
def test_fetch_users():
    result = fetch_users()
    assert result.total >= 1
```

### 3.3 テスト実行（失敗を確認）

```bash
uv run pytest tests/nodes/test_fetch_users.py -v
```

🔴 **Red Phase!** テストが失敗することを確認しました。

---

## Step 4: Node実装（3分）

テストを通すための実装を書きます。

### 4.1 ノードを実装（Green Phase）

`src/nodes/fetch_users.py` を以下の内容で**上書き**してください:

```python
"""fetch_users node."""

from railway import node
from contracts.users_fetch_result import UsersFetchResult, User


@node(output=UsersFetchResult)
def fetch_users() -> UsersFetchResult:
    """ユーザー一覧を取得する"""
    users = [
        User(id=1, name="Alice", email="alice@example.com"),
        User(id=2, name="Bob", email="bob@example.com"),
    ]
    return UsersFetchResult(
        users=users,
        total=len(users),
    )
```

### 4.2 テスト実行（成功を確認）

```bash
uv run pytest tests/nodes/test_fetch_users.py -v
```

🟢 **Green Phase!** テストが通りました。

**ポイント:**
- `@node(output=UsersFetchResult)` で出力型を宣言
- 純粋関数：引数を受け取り、値を返すだけ
- 型が保証される

---

## Step 5: IDE補完を体験する（2分）

Output Modelパターンの最大の利点を体験しましょう。

### 5.1 別のノードを作成

```bash
railway new contract ReportResult
railway new node generate_report --input users:UsersFetchResult --output ReportResult
```

### 5.2 ContractとNodeを編集

`src/contracts/report_result.py`:

```python
"""ReportResult contract."""

from datetime import datetime
from railway import Contract


class ReportResult(Contract):
    """レポート生成結果"""
    content: str
    user_count: int
    generated_at: datetime
```

### 5.3 VSCodeで補完を試す

`src/nodes/generate_report.py` を開き、以下のように編集してみてください:

```python
"""generate_report node."""

from datetime import datetime
from railway import node
from contracts.users_fetch_result import UsersFetchResult
from contracts.report_result import ReportResult


@node(
    inputs={"users": UsersFetchResult},
    output=ReportResult,
)
def generate_report(users: UsersFetchResult) -> ReportResult:
    # ここで users. と入力して Ctrl+Space を押してください！
    names = ", ".join(u.name for u in users.users)  # IDE補完が効く！
    return ReportResult(
        content=f"Users: {names}",
        user_count=users.total,  # typo するとIDEが警告
        generated_at=datetime.now(),
    )
```

🎉 **IDE補完が効く！** `users.` と入力すると候補が表示されます。

---

## Step 6: typed_pipeline - 依存関係の自動解決（3分）

複数のNodeを組み合わせてパイプラインを構築します。

### 6.1 エントリポイントを作成

```bash
railway new entry user_report
```

`src/user_report.py` を以下の内容で**上書き**してください:

```python
"""user_report entry point."""

from railway import entry_point, typed_pipeline

from nodes.fetch_users import fetch_users
from nodes.generate_report import generate_report


@entry_point
def main():
    """ユーザーレポートを生成する"""
    result = typed_pipeline(
        fetch_users,      # UsersFetchResult を出力
        generate_report,  # UsersFetchResult を入力 → ReportResult を出力
    )

    print(result.content)      # IDE補完が効く！
    print(f"Count: {result.user_count}")
    return result


if __name__ == "__main__":
    main()
```

### 6.2 実行

```bash
uv run railway run user_report
```

**期待される出力:**
```
Users: Alice, Bob
Count: 2
```

**依存関係の自動解決:**

```
fetch_users ──────────────> generate_report
  output: UsersFetchResult    input: UsersFetchResult
                              output: ReportResult
```

フレームワークが**型を見て自動的に依存関係を解決**します。

### 6.3 Nodeはパイプライン構成に依存しない

これがOutput Modelパターンの核心的な利点です:

```python
# 構成1: シンプル
typed_pipeline(fetch_users, generate_report)

# 構成2: 間にフィルター処理を追加
typed_pipeline(fetch_users, filter_active_users, generate_report)

# 構成3: データ加工を追加
typed_pipeline(fetch_users, enrich_users, generate_report)

# ↑ どの構成でも generate_report の実装は同じ！
```

**なぜこれが重要か:**

| 従来 | Railway |
|------|---------|
| パイプライン変更時にNode修正が必要 | Node修正不要 |
| 前後のNode実装を意識 | 入出力Contractだけを意識 |
| 結合テストが必須 | 単体テストで十分 |

`generate_report` は**「UsersFetchResultを受け取りReportResultを返す」**という契約だけを守ればよく、パイプラインの全体構成には一切依存しません。

---

## Step 7: 安全なリファクタリング（2分）

Output Modelパターンのもう一つの利点を体験します。

### 7.1 フィールド名を変更したい

`UsersFetchResult.total` を `count` に変更したいとします。

### 7.2 従来の問題

```python
# ❌ 従来: 文字列なので grep で探すしかない
data["total"]  # どこで使われてる？ 変更漏れがあっても実行時まで気づかない
```

### 7.3 Railwayでの安全な変更

1. **Contract を変更:**
   `src/contracts/users_fetch_result.py` の `total` を `count` に変更

2. **IDEが全参照箇所をハイライト**

3. **一括リネーム (F2キー)**

4. **型チェックで確認:**
   ```bash
   uv run mypy src/
   ```

🎉 **変更漏れゼロ！** IDEと型チェッカーが守ってくれます。

---

## Step 8: エラーハンドリング（実践）（5分）

Railway Framework のエラーハンドリングを実際に体験します。
多くのケースでは「何もしない」で十分ですが、高度な制御が必要な場合の選択肢を学びます。

### 8.1 シナリオ: 不安定な外部APIとの連携

外部APIが不安定で、時々接続エラーが発生する状況を想定します。

まず、不安定なAPIをシミュレートするノードを作成:

```bash
railway new contract ExternalDataResult
railway new node fetch_external_data --output ExternalDataResult
```

`src/contracts/external_data_result.py`:
```python
from railway import Contract

class ExternalDataResult(Contract):
    data: str
    value: int
```

`src/nodes/fetch_external_data.py`:
```python
import random
from railway import node
from contracts.external_data_result import ExternalDataResult

@node(output=ExternalDataResult)
def fetch_external_data() -> ExternalDataResult:
    """不安定な外部APIをシミュレート"""
    if random.random() < 0.5:
        raise ConnectionError("Network timeout")
    return ExternalDataResult(data="success", value=42)
```

### 8.2 レベル1: retry_on で自動リトライ

一時的なエラーには自動リトライが有効です:

```python
@node(
    output=ExternalDataResult,
    retries=3,
    retry_on=(ConnectionError,)
)
def fetch_with_retry() -> ExternalDataResult:
    """ConnectionError は3回までリトライ"""
    if random.random() < 0.5:
        raise ConnectionError("Network timeout")
    return ExternalDataResult(data="success", value=42)
```

**体験**: 何度か実行して、ConnectionErrorが自動リトライされることを確認:
```bash
uv run python -c "from nodes.fetch_external_data import fetch_with_retry; print(fetch_with_retry())"
```

### 8.3 レベル2: デフォルト動作（例外伝播）

何も指定しなければ、例外はそのまま伝播します:

```python
result = typed_pipeline(fetch_external_data, process_data)
# 例外発生時: スタックトレース付きで伝播
```

**これで十分なケースが多いです。** スタックトレースが保持されるため、デバッグが容易です。

### 8.4 レベル3: on_error でPipeline単位の制御

複数のNodeを跨いだ高度な制御が必要な場合:

`src/user_report.py` を編集して試してみましょう:

```python
from railway import entry_point, typed_pipeline

def smart_error_handler(error: Exception, step_name: str):
    """例外タイプに応じて適切に処理"""
    match error:
        case ConnectionError():
            print(f"⚠️ {step_name}: 接続エラー、フォールバック値を使用")
            return ExternalDataResult(data="cached", value=0)
        case _:
            raise  # 他の例外は再送出

@entry_point
def main():
    result = typed_pipeline(
        fetch_external_data,
        on_error=smart_error_handler
    )
    print(f"Result: {result.data}, Value: {result.value}")
```

### 8.5 on_step でデバッグ/監査

各ステップの中間結果を取得できます:

```python
steps = []

def capture_step(step_name: str, output):
    steps.append({"step": step_name, "output": output})
    print(f"[{step_name}] -> {output}")

result = typed_pipeline(
    fetch_users,
    generate_report,
    on_step=capture_step  # 各ステップの結果をキャプチャ
)
```

### 8.6 恩恵のまとめ

| レベル | いつ使う | 恩恵 |
|--------|----------|------|
| retry_on | 一時的エラー | 自動回復、コード簡潔 |
| デフォルト伝播 | **多くのケース** | スタックトレース保持 |
| on_error | 高度な制御 | Pipeline単位の柔軟な対応 |
| on_step | デバッグ/監査 | 中間結果へのアクセス |

**重要**: 多くのケースでは「何もしない」（デフォルト伝播）で十分です。
高度な機能は必要な時だけ使いましょう。

---

## Step 9: バージョン管理 - 安全なアップグレード体験（5分）

Railway Framework は**プロジェクトのバージョンを追跡**し、安全なアップグレードを支援します。

### 9.1 現状を確認

プロジェクトのバージョン情報を確認します:

```bash
cat .railway/project.yaml
```

**出力例:**
```yaml
railway:
  version: "0.10.1"
  created_at: "2026-01-23T10:30:00+09:00"
  updated_at: "2026-01-23T10:30:00+09:00"

project:
  name: "test_project"

compatibility:
  min_version: "0.10.1"
```

**ポイント:**
- `railway init` 時に自動生成される
- チーム全員で同じバージョン情報を共有（Git管理対象）

---

### 9.2 バージョン不一致の警告

フレームワークがアップグレードされた後に `railway new` を実行すると:

```
$ railway new node my_new_node

⚠️  バージョン不一致を検出
    プロジェクト: 0.10.0
    現在:         0.11.0

    [c] 続行 / [u] 'railway update' を実行 / [a] 中止
```

**なぜ重要か:**
- 古いテンプレートと新しいテンプレートの混在を防ぐ
- チーム内の不整合を防止

---

### 9.3 railway update でマイグレーション

プロジェクトを最新バージョンに更新:

```bash
# まず変更内容をプレビュー
railway update --dry-run

# 実際に更新
railway update
```

**ポイント:**
- `--dry-run` で事前確認
- 更新前に自動バックアップ
- ユーザーコード（`src/nodes/*`）は変更されない

---

### 9.4 バックアップから復元

問題が発生した場合は簡単に復元:

```bash
# 一覧表示
railway backup list

# 復元
railway backup restore
```

---

### 9.5 恩恵のまとめ

| 問題 | Railway の解決策 |
|------|------------------|
| バージョン不明 | `.railway/project.yaml` で明示 |
| 手動マイグレーション | `railway update` で自動化 |
| 失敗時のリカバリ | 自動バックアップ + 復元 |
| 変更内容不明 | `--dry-run` で事前確認 |

🎉 **これでバージョンアップも安心！**

---

## よくある質問 (FAQ)

### Q: Result型（Ok/Err）は提供しないの？

Railway Framework は意図的にResult型を採用していません。

**理由:**
- Pythonエコシステム（requests, sqlalchemy等）は例外ベース
- Result型だとすべてをラップする必要があり冗長
- スタックトレースが失われデバッグが困難に

代わりに、Python標準の例外機構 + on_error で十分な制御を提供します。

### Q: on_error と try/except の使い分けは？

| 状況 | 推奨 |
|------|------|
| 1つのNodeで完結 | Node内で try/except |
| 複数Nodeを跨ぐ | on_error |
| リトライで回復可能 | retry_on |
| 特に制御不要 | **何もしない（例外伝播）** |

### Q: inputs の明示的指定は必要？

Contract型の引数は**自動推論**されるため、通常は不要です:

```python
# 自動推論される（推奨）
@node(output=ReportResult)
def generate_report(users: UsersFetchResult) -> ReportResult:
    ...

# 明示的に指定も可能（レガシー互換）
@node(inputs={"users": UsersFetchResult}, output=ReportResult)
def generate_report(users: UsersFetchResult) -> ReportResult:
    ...
```

### Q: 既存プロジェクトにバージョン情報を追加するには？

```bash
railway update --init
```

これにより `.railway/project.yaml` が作成され、バージョン追跡が開始されます。

### Q: バージョン不一致の警告を無視できる？

`--force` オプションで警告をスキップできます:

```bash
railway new node my_node --force
```

ただし、チーム開発では推奨しません。`railway update` で先にプロジェクトを更新してください。

---

## 次のステップ

おめでとうございます！🎉 Railwayの基本と応用を習得しました。

### 学んだこと

- Contract で型契約を定義
- Node で純粋関数として処理を実装
- TDD でテストファーストに開発
- IDE補完の活用
- typed_pipeline で依存関係を自動解決
- 安全なリファクタリング
- **3層エラーハンドリング** (retry_on, デフォルト伝播, on_error)
- **on_step でデバッグ/監査**
- **バージョン管理** (`railway update`, `railway backup`)

### さらに学ぶ

1. **設定管理**: `config/development.yaml` で環境別設定
2. **非同期処理**: `typed_async_pipeline` で非同期対応
3. **ドキュメント**: `railway docs` で詳細を確認

---

## トラブルシューティング

### mypy で型チェックが効かない場合

mypyで「Skipping analyzing "railway"」と表示される場合:

```bash
# 1. パッケージを再インストール
uv sync --reinstall-package railway-framework

# 2. mypy キャッシュをクリア
rm -rf .mypy_cache/

# 3. 確認
uv run mypy src/
```

### テストが失敗する場合

```bash
# pytest キャッシュをクリア
rm -rf .pytest_cache/ __pycache__/

# 依存関係を再同期
uv sync
```
