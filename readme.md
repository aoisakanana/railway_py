# Railway Framework for Python

**シンプルで強力な運用自動化フレームワーク**

Pythonで**型安全**で**エラーに強い**運用自動化ツールを、**5分で**作成開始できます。

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 特徴

- ✨ **5分で開始**: `railway init` でプロジェクト作成、すぐに実装開始
- 🛤️ **Railway Oriented Programming**: エラーハンドリングが自動的に処理される
- 🔒 **型安全**: mypyによる完全な型チェック
- 🎯 **シンプルなAPI**: デコレータベースで直感的
- 📝 **自動生成**: テンプレートから即座にコード生成
- 🧪 **テスト容易**: テストコードも自動生成
- ⚙️ **環境別設定**: development/production を簡単に切り替え

---

## これは何？

Railway Oriented Programming（ROP）パラダイムで、運用自動化スクリプトを構築するフレームワークです。
「成功パス」と「エラーパス」を明確に分離し、エラーハンドリングを簡潔かつ安全に記述できます。

### 従来 vs Railway

**❌ 従来のアプローチ: 複雑で漏れやすいエラーハンドリング**
```python
def process():
    try:
        data = fetch_data()
        if data is None:
            log_error("fetch failed")
            return None

        result = transform(data)
        if result is None:
            log_error("transform failed")
            return None

        save(result)
    except Exception as e:
        log_error(f"Error: {e}")
        return None
```

**✅ Railway Framework: シンプルで安全**
```python
from railway import entry_point, node, pipeline

@node
def fetch_data() -> dict:
    # エラーは自動的にキャッチされる
    return api.get("/data")

@node
def transform(data: dict) -> dict:
    return {"processed": data}

@node
def save(data: dict) -> str:
    db.save(data)
    return "Saved!"

@entry_point
def process():
    # エラーは自動的に伝播、後続処理はスキップされる
    return pipeline(
        fetch_data(),
        transform,
        save
    )
```

---

## クイックスタート（5分）

### 1. インストール

```bash
# uvをインストール（未インストールの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# Railwayフレームワークをインストール
pip install railway-framework
```

### 2. プロジェクト作成

```bash
railway init my_automation
cd my_automation
```

これで以下が自動生成されます:
```
my_automation/
├── src/              # コード
├── tests/            # テスト
├── config/           # 設定ファイル
├── .env.example      # 環境変数テンプレート
└── TUTORIAL.md       # ステップバイステップガイド
```

### 3. 最初のエントリーポイント作成

```bash
railway new entry hello --example
```

これで `src/hello.py` が生成されます:

```python
from railway import entry_point, node

@node
def greet(name: str) -> str:
    return f"Hello, {name}!"

@entry_point
def main(name: str = "World"):
    message = greet(name)
    print(message)
    return message
```

### 4. 実行！

```bash
uv run python -m src.hello
# Output: Hello, World!

uv run python -m src.hello --name Alice
# Output: Hello, Alice!
```

**🎉 完成！ たった4ステップで動作する自動化ツールができました。**

---

## もっと詳しく: 段階的チュートリアル

プロジェクトには `TUTORIAL.md` が含まれており、以下を段階的に学べます:

1. **Hello World** (5分) - 基本的なノードとエントリーポイント
2. **エラーハンドリング** (10分) - 自動的なエラー処理
3. **パイプライン** (10分) - 複数ノードの連携
4. **設定管理** (15分) - 環境別設定
5. **テスト** (20分) - テストの書き方

---

## コア概念

### 1. ノード (@node)

**ノード = 再利用可能な処理単位**

```python
from railway import node

@node
def fetch_data(url: str) -> dict:
    """データ取得ノード"""
    response = requests.get(url)  # エラーは自動的にキャッチされる
    return response.json()

@node(retry=True)  # リトライ有効化
def send_email(data: dict) -> str:
    """メール送信ノード（リトライあり）"""
    mailer.send(data)
    return "Email sent"
```

**ノードの特徴:**
- 例外は自動的にキャッチされ、Failure として伝播
- `retry=True` でリトライ機能を有効化
- 設定ファイルでリトライポリシーを制御可能

### 2. エントリーポイント (@entry_point)

**エントリーポイント = 実行の起点**

```python
from railway import entry_point, pipeline

@entry_point
def main(date: str = None, dry_run: bool = False):
    """日次レポート生成"""
    result = pipeline(
        fetch_data(date),
        process_data,
        generate_report,
        send_report if not dry_run else skip
    )
    return result
```

**エントリーポイントの特徴:**
- コマンドライン引数を自動的にパース
- エラーハンドリングとログ出力が自動化
- 成功時は exit code 0、失敗時は 1

### 3. パイプライン (pipeline)

**パイプライン = ノードの連鎖**

```python
result = pipeline(
    step1(),      # 最初のノード
    step2,        # step1の出力がstep2の入力になる
    step3,        # step2の出力がstep3の入力になる
)
```

**パイプラインの動作:**
```
Success Track:  ════════════════════════════
step1 ──> step2 ──> step3 ──> Complete!
  ✓         ✓         ✓

Failure Track:  ════════════════════════════
step1 ──> step2 ──> step3
  ✓         ✗
            └──> Skip ──> Failure(error)
```

---

## プロジェクト構造

```
my_automation/
├── src/
│   ├── settings.py          # 設定読み込み
│   ├── daily_report.py      # エントリーポイント
│   ├── nodes/               # 処理ノード
│   │   ├── fetch_data.py
│   │   └── process_data.py
│   └── common/              # 共通ユーティリティ
│       └── api_client.py
├── tests/
│   └── nodes/
│       └── test_fetch_data.py
├── config/
│   ├── development.yaml     # 開発環境設定
│   └── production.yaml      # 本番環境設定
├── logs/                    # ログ出力先
├── .env                     # 環境変数（gitignore対象）
├── .env.example             # 環境変数テンプレート
└── TUTORIAL.md              # チュートリアル
```

---

## CLIコマンド

### プロジェクト管理

```bash
# 新規プロジェクト作成
railway init my_project

# サンプルコード付きで作成
railway init my_project --with-examples
```

### コード生成

```bash
# エントリーポイント作成
railway new entry daily_report

# サンプルコード付きでノード作成
railway new node fetch_data --example

# 既存ファイルを上書き
railway new node fetch_data --force
```

### 情報表示

```bash
# エントリーポイントとノードの一覧
railway list

# エントリーポイントのみ
railway list entries

# ノードのみ
railway list nodes
```

---

## 設定管理

### 統合設定ファイル: config/development.yaml

すべての設定が1つのファイルに統合されています:

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
    - type: file
      path: logs/app.log
      level: INFO
    - type: console
      level: DEBUG

# リトライ設定
retry:
  default:
    max_attempts: 3
    min_wait: 2
    max_wait: 10
  nodes:
    fetch_data:      # ノード別設定
      max_attempts: 5
```

### 環境別設定の切り替え

```bash
# .env ファイルで環境を指定
RAILWAY_ENV=development   # config/development.yaml を使用
RAILWAY_ENV=production    # config/production.yaml を使用
```

### コードから設定にアクセス

```python
from src.settings import settings

# API設定
url = settings.api.base_url
timeout = settings.api.timeout

# リトライ設定
retry_config = settings.get_retry_settings("fetch_data")
max_attempts = retry_config.max_attempts
```

---

## 実例: 日次レポート生成

### ステップ1: ノードを作成

```bash
railway new node fetch_sales_data --example
railway new node calculate_metrics --example
railway new node generate_report --example
```

### ステップ2: エントリーポイントを作成

```python
# src/daily_sales_report.py
from railway import entry_point, pipeline
from datetime import datetime
from src.nodes.fetch_sales_data import fetch_sales_data
from src.nodes.calculate_metrics import calculate_metrics
from src.nodes.generate_report import generate_report

@entry_point
def main(date: str = None, dry_run: bool = False):
    """
    日次売上レポートを生成して送信する。

    Args:
        date: レポート日付 (YYYY-MM-DD)、デフォルトは今日
        dry_run: Trueの場合、レポート送信をスキップ
    """
    date = date or datetime.now().strftime("%Y-%m-%d")

    result = pipeline(
        fetch_sales_data(date),
        calculate_metrics,
        generate_report,
        send_report if not dry_run else lambda x: x
    )

    return result
```

### ステップ3: 実行

```bash
# 開発環境でdry-run
uv run python -m src.daily_sales_report --dry-run

# 本番環境で実行（.env で RAILWAY_ENV=production に設定）
uv run python -m src.daily_sales_report
```

---

## テストの書き方

ノード作成時にテストテンプレートも自動生成されます:

```python
# tests/nodes/test_fetch_sales_data.py
import pytest
from unittest.mock import patch
from src.nodes.fetch_sales_data import fetch_sales_data

def test_fetch_sales_data_success():
    """正常系: データ取得成功"""
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = {"sales": [100, 200]}

        result = fetch_sales_data("2024-01-01")

        assert result == {"sales": [100, 200]}

def test_fetch_sales_data_api_error():
    """異常系: API エラー"""
    with patch('requests.get') as mock_get:
        mock_get.side_effect = Exception("API Error")

        with pytest.raises(Exception):
            fetch_sales_data("2024-01-01")
```

### テスト実行

```bash
# すべてのテスト実行
pytest

# カバレッジ付き
pytest --cov=src --cov-report=html

# 特定のテストのみ
pytest tests/nodes/test_fetch_sales_data.py -v
```

---

## 開発ワークフロー

```bash
# 1. ノード作成
railway new node my_feature --example

# 2. ノードを実装
# src/nodes/my_feature.py を編集

# 3. テスト作成
# tests/nodes/test_my_feature.py を編集

# 4. テスト実行
pytest tests/nodes/test_my_feature.py -v

# 5. 型チェック
mypy src/nodes/my_feature.py

# 6. リント
ruff check src/nodes/my_feature.py

# 7. エントリーポイントに組み込み
# src/my_entry.py で使用

# 8. 動作確認
uv run python -m src.my_entry --dry-run

# 9. 本番実行
uv run python -m src.my_entry
```

---

## 採用技術スタック

### コア機能
| ライブラリ | 用途 | 備考 |
|-----------|------|------|
| `returns` | Railway Oriented Programming | Result型、bind、flow |
| `tenacity` | リトライ処理 | 指数バックオフ、カスタマイズ可能 |
| `pydantic` | データバリデーション | 型安全な設定管理 |
| `typer` | CLIインターフェース | 自動的な引数パース |
| `loguru` | 構造化ロギング | シンプルで強力 |

### 開発ツール
| ライブラリ | 用途 |
|-----------|------|
| `ruff` | リント・フォーマット |
| `mypy` | 型チェック |
| `pytest` | テスト実行 |
| `uv` | 高速パッケージ管理 |

---

## ユースケース

### 1. API統合の自動化
```python
@entry_point
def sync_users():
    """外部APIからユーザーを同期"""
    return pipeline(
        fetch_from_api_a(),
        transform_to_internal_format,
        validate_data,
        save_to_database,
        send_notification
    )
```

### 2. データバッチ処理
```python
@entry_point
def daily_etl(date: str):
    """日次ETL処理"""
    return pipeline(
        extract_from_database(date),
        transform_data,
        load_to_warehouse,
        update_metrics
    )
```

### 3. レポート生成
```python
@entry_point
def weekly_report():
    """週次レポート生成"""
    return pipeline(
        fetch_weekly_data(),
        calculate_kpis,
        generate_charts,
        create_pdf_report,
        send_via_email
    )
```

---

## Advanced: 明示的なResult型の使用

初心者はデコレータに任せればOKですが、上級者は明示的にResult型を扱えます:

```python
from railway import entry_point, node
from returns.result import Result, Success, Failure
from returns.pipeline import flow

@node
def risky_operation() -> Result[dict, Exception]:
    """明示的なResult型"""
    try:
        data = {"value": 100}
        return Success(data)
    except Exception as e:
        return Failure(e)

@entry_point(handle_result=False)  # 自動ハンドリングを無効化
def advanced_main() -> Result[str, Exception]:
    """明示的なResult型を返すエントリーポイント"""
    return flow(
        risky_operation(),
        lambda x: Success(f"Result: {x['value']}")
    )
```

---

## FAQ

**Q: 既存のスクリプトを移行できますか？**
A: はい。既存関数に `@node` デコレータを付けるだけで使えます。

**Q: 非同期処理に対応していますか？**
A: はい。ノードを `async def` で定義するだけで使えます。

**Q: エラーログはどこに出力されますか？**
A: `config/{env}.yaml` の logging セクションで設定できます。デフォルトは `logs/` ディレクトリです。

**Q: 本番環境での推奨設定は？**
A: `RAILWAY_ENV=production` を設定し、`config/production.yaml` で以下を調整:
- ログレベル: INFO 以上
- リトライ回数: 適切に設定
- タイムアウト: 環境に応じて調整

**Q: グラフ機能はありますか？**
A: Phase 1 ではシンプルな `pipeline()` のみです。グラフベースの依存関係管理は Phase 2 で提供予定です。

---

## コントリビューション

Issue・PRを歓迎します！

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. Pull Request を作成

---

## ライセンス

MIT License

---

## ロードマップ

### Phase 1 (Current)
- ✅ シンプルなノードベースのパイプライン
- ✅ デコレータベースのAPI
- ✅ 環境別設定管理
- ✅ 自動的なエラーハンドリング
- ✅ リトライ機能

### Phase 2 (Next 3 months)
- 🔜 graph.yaml によるグラフベース実行
- 🔜 WebUI でのグラフ可視化
- 🔜 詳細なメトリクス収集
- 🔜 インタラクティブデバッガ

### Phase 3 (Next 6 months)
- 🔜 分散実行サポート (Celery/Dask)
- 🔜 クラウドサービス統合 (AWS/GCP/Azure)
- 🔜 スケジューラー統合

---

**さあ、Railway Framework で運用自動化を始めましょう！**

```bash
railway init my_first_automation
```
