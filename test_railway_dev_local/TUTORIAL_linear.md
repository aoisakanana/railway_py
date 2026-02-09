# test_railway_dev_local チュートリアル - 線形パイプライン

このチュートリアルでは、`typed_pipeline` を使用した線形パイプラインの開発を学びます。

条件分岐が必要な場合は [TUTORIAL.md](TUTORIAL.md) の dag_runner を使用してください。

## 線形パイプラインとは

処理が必ず順番に実行されるパイプラインです：

```
A → B → C → D
```

条件分岐はありません。ETL、データ変換に適しています。

## 所要時間

約10分

## 前提条件

- Python 3.10以上
- uv インストール済み
- VSCode推奨（IDE補完を体験するため）

---

## Step 1: プロジェクト初期化（1分）

```bash
railway init my_pipeline
cd my_pipeline
uv sync
```

---

## Step 2: エントリーポイント作成（1分）

```bash
railway new entry my_pipeline --mode linear
```

以下のファイルが生成されます：

- `src/my_pipeline.py` - エントリーポイント（typed_pipeline 使用）
- `src/nodes/my_pipeline/step1.py` - ステップ1
- `src/nodes/my_pipeline/step2.py` - ステップ2

---

## Step 3: 生成されるコード

### エントリーポイント

`src/my_pipeline.py`:

```python
from railway import entry_point, typed_pipeline
from nodes.my_pipeline.step1 import step1
from nodes.my_pipeline.step2 import step2


@entry_point
def main():
    """パイプラインを実行"""
    result = typed_pipeline(
        step1,
        step2,
    )
    print(f"完了: {result}")
    return result
```

### ノード

`src/nodes/my_pipeline/step1.py`:

```python
from railway import Contract, node


class Step1Output(Contract):
    """ステップ1の出力"""
    data: str


@node(output=Step1Output)
def step1() -> Step1Output:
    """ステップ1の処理"""
    return Step1Output(data="processed")
```

---

## Step 4: 実行（1分）

```bash
railway run my_pipeline
```

---

## Step 5: Contract - データの「契約」を定義（3分）

### 5.1 Contractを作成

```bash
railway new contract UsersFetchResult
```

### 5.2 ファイルを編集

`src/contracts/users_fetch_result.py`:

```python
from railway import Contract


class User(Contract):
    id: int
    name: str


class UsersFetchResult(Contract):
    users: list[User]
    total: int
```

---

## Step 6: typed_pipeline - 依存関係の自動解決（3分）

### 6.1 複数のノードを組み合わせ

```python
from railway import entry_point, typed_pipeline

from nodes.fetch_users import fetch_users
from nodes.generate_report import generate_report


@entry_point
def main():
    result = typed_pipeline(
        fetch_users,      # UsersFetchResult を出力
        generate_report,  # UsersFetchResult を入力 → ReportResult を出力
    )

    print(result.content)  # IDE補完が効く！
    return result
```

### 6.2 依存関係の自動解決

```
fetch_users ──────────────> generate_report
  output: UsersFetchResult    input: UsersFetchResult
                              output: ReportResult
```

フレームワークが**型を見て自動的に依存関係を解決**します。

---

## typed_pipeline の特徴

- **Contract 自動解決**: 次のノードに必要な Contract を自動で渡す
- **シンプル**: 状態管理不要
- **線形処理専用**: 条件分岐不可
- **IDE補完**: Contract の型情報でIDE補完が効く

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

```
# typed_pipeline: 線形フロー
A → B → C → D

# dag_runner: 条件分岐フロー
    ┌→ B → D
A → │
    └→ C → E
```

---

## 次のステップ

- [TUTORIAL.md](TUTORIAL.md) - DAGワークフローチュートリアル
- [docs/adr/002_execution_models.md](docs/adr/002_execution_models.md) - 実行モデルの詳細
