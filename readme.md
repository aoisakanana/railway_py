# Railway Framework for Python

**シンプルで強力な運用自動化フレームワーク**

Pythonで**型安全**で**エラーに強い**運用自動化ツールを、**5分で**作成開始できます。

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Test Coverage](https://img.shields.io/badge/coverage-90%25+-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-222%20passing-success.svg)]()

---

## 特徴

- ✨ **5分で開始**: `railway init` でプロジェクト作成、すぐに実装開始
- 🛤️ **Railway Oriented Programming**: エラーハンドリングが自動的に処理される
- 🔒 **型安全**: mypyによる完全な型チェック + ランタイム型検証（strict mode）
- ⚡ **非同期対応**: async/await 完全サポート、同期・非同期の混在可能
- 🎯 **シンプルなAPI**: デコレータベースで直感的
- 📝 **自動生成**: テンプレートから即座にコード生成
- 🧪 **テスト容易**: テストコードも自動生成
- ⚙️ **環境別設定**: development/production を簡単に切り替え
- 🔄 **自動リトライ**: 一時的なエラーに自動で対処
- 📊 **構造化ロギング**: loguru による美しいログ出力
- 🎨 **カスタムエラー型**: 日本語ヒント付きエラーで即座に原因把握

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
from railway.core.errors import NetworkError

@node(retry=True)  # 自動リトライ
def fetch_data() -> dict:
    # エラーは自動的にキャッチされ、詳細にログ出力
    try:
        return api.get("/data")
    except ConnectionError as e:
        # 日本語ヒント付きエラー
        raise NetworkError(
            "API connection failed",
            hint="ネットワーク接続を確認してください"
        ) from e

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
    # strict=True で型チェックも可能
    return pipeline(
        fetch_data(),
        transform,
        save,
        strict=True  # 開発時に型の不一致を検出
    )
```

**結果:**
- ✅ 10行以上のエラーハンドリングコードが不要
- ✅ 自動リトライで一時的なエラーに対応
- ✅ 日本語ヒントで即座に原因把握
- ✅ 型チェックで事前にバグ防止
- ✅ 美しいログ出力で問題追跡が容易

---

## クイックスタート（5分）

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

これで以下が自動生成されます:
```
my_automation/
├── src/                  # コード
│   ├── __init__.py
│   ├── settings.py       # 設定読み込み
│   ├── nodes/            # 処理ノード
│   │   └── __init__.py
│   └── common/           # 共通ユーティリティ
│       └── __init__.py
├── tests/                # テスト
│   ├── conftest.py
│   └── nodes/
├── config/               # 設定ファイル
│   └── development.yaml
├── logs/                 # ログ出力先
├── .env.example          # 環境変数テンプレート
├── .gitignore
├── pyproject.toml
└── TUTORIAL.md           # ステップバイステップガイド
```

### 3. 最初のエントリーポイント作成

```bash
railway new entry hello --example
```

これで `src/hello.py` が生成されます:

```python
from railway import entry_point, node
from loguru import logger

@node
def greet(name: str) -> str:
    logger.info(f"Greeting {name}")
    return f"Hello, {name}!"

@entry_point
def main(name: str = "World"):
    message = greet(name)
    print(message)
    return message
```

### 4. 実行！

```bash
# 方法1: railway run コマンド（推奨）
uv run railway run hello
# Output: Hello, World!

uv run railway run hello -- --name Alice
# Output: Hello, Alice!

# 方法2: Python モジュールとして直接実行
uv run python -m src.hello
# Output: Hello, World!

uv run python -m src.hello --name Alice
# Output: Hello, Alice!
```

**🎉 完成！ たった4ステップで動作する自動化ツールができました。**

---

## もっと詳しく: 段階的チュートリアル

プロジェクトには `TUTORIAL.md` が含まれており、以下を段階的に学べます:

| ステップ | 内容 | 所要時間 |
|---------|------|---------|
| 1. Hello World | 基本的なノードとエントリーポイント | 5分 |
| 2. エラーハンドリング | 自動的なエラー処理 | 10分 |
| 3. パイプライン | 複数ノードの連携 | 10分 |
| 4. 設定管理 | 環境別設定 | 15分 |
| 5. テスト | テストの書き方 | 20分 |
| 6. トラブルシューティング | デバッグ方法 | 10分 |

---

## コア概念

### 1. ノード (@node)

**ノード = 再利用可能な処理単位**

```python
from railway import node
from loguru import logger

@node
def fetch_data(url: str) -> dict:
    """データ取得ノード"""
    logger.info(f"Fetching from {url}")
    response = requests.get(url)  # エラーは自動的にキャッチされる
    return response.json()

@node(retry=True)  # リトライ有効化
def send_email(data: dict) -> str:
    """メール送信ノード（リトライあり）"""
    mailer.send(data)
    return "Email sent"
```

**ノードの特徴:**
- ✅ 例外は自動的にキャッチされ、ログ出力される
- ✅ `retry=True` でリトライ機能を有効化
- ✅ 設定ファイルでリトライポリシーを制御可能
- ✅ 実行開始・完了・エラーが自動的にログ出力される

**ログ出力例:**
```
12:34:56 | INFO | [fetch_data] Starting...
12:34:57 | INFO | [fetch_data] ✓ Completed
```

### 2. エントリーポイント (@entry_point)

**エントリーポイント = 実行の起点**

```python
from railway import entry_point, pipeline

@entry_point
def main(date: str = None, dry_run: bool = False):
    """日次レポート生成

    Args:
        date: 対象日（YYYY-MM-DD形式）
        dry_run: テスト実行モード
    """
    result = pipeline(
        fetch_data(date),
        process_data,
        generate_report,
        send_report if not dry_run else lambda x: x
    )
    return result
```

**エントリーポイントの特徴:**
- ✅ コマンドライン引数を自動的にパース（typer使用）
- ✅ `--help` で自動的にヘルプ表示
- ✅ エラーハンドリングとログ出力が自動化
- ✅ 成功時は exit code 0、失敗時は 1

**実行例:**
```bash
# ヘルプ表示
uv run python -m src.daily_report --help

# オプション付き実行
uv run python -m src.daily_report --date 2024-01-15 --dry-run
```

### 3. パイプライン (pipeline)

**パイプライン = ノードの連鎖**

```python
result = pipeline(
    step1(),      # 最初のノード（初期値）
    step2,        # step1の出力がstep2の入力になる
    step3,        # step2の出力がstep3の入力になる
)
```

**パイプラインの動作:**
```
成功パス:  ════════════════════════════════════
  step1 ──────> step2 ──────> step3 ──────> Complete!
    ✓             ✓             ✓

失敗パス:  ════════════════════════════════════
  step1 ──────> step2 ──────> step3
    ✓             ✗
                  └──> 後続をスキップ ──> Failure(error)
```

**ログ出力例:**
```
12:34:56 | DEBUG | Pipeline starting with 3 steps
12:34:56 | INFO  | [fetch_data] Starting...
12:34:57 | INFO  | [fetch_data] ✓ Completed
12:34:57 | INFO  | [process_data] Starting...
12:34:57 | ERROR | [process_data] ✗ Failed: ValueError: Invalid data
12:34:57 | INFO  | Pipeline: Skipping remaining 1 steps
```

---

## CLIコマンド

### railway init - プロジェクト作成

```bash
railway init my_project [OPTIONS]

Options:
  --python-version TEXT  Python バージョン (default: 3.10)
  --with-examples        サンプルコード付きで作成
```

**出力例:**
```
Created project: my_project

Project structure:
  my_project/
  ├── src/
  ├── tests/
  ├── config/
  ├── .env.example
  └── TUTORIAL.md

Next steps:
  1. cd my_project
  2. cp .env.example .env
  3. Open TUTORIAL.md and follow the guide
  4. railway new entry hello --example
```

### railway new - コード生成

```bash
# エントリーポイント作成
railway new entry daily_report

# ノード作成（テストファイルも自動生成）
railway new node fetch_data

# サンプルコード付きで作成
railway new entry my_entry --example
railway new node my_node --example

# 既存ファイルを上書き
railway new node existing_node --force
```

**ノード作成時の出力例:**
```
Created node: src/nodes/fetch_data.py
Created test: tests/nodes/test_fetch_data.py

To use in an entry point:
  from src.nodes.fetch_data import fetch_data
```

### railway list - 一覧表示

```bash
# すべて表示
railway list

# エントリーポイントのみ
railway list entries

# ノードのみ
railway list nodes
```

**出力例:**
```
Entry Points:
  * daily_report         Generate daily report
  * weekly_batch         Weekly batch processing

Nodes:
  * fetch_data           Fetch data from external API
  * process_data         Process and transform data
  * send_report          Send report via email/Slack

Statistics:
  2 entry points, 3 nodes, 5 tests
```

### railway run - エントリーポイント実行

```bash
# エントリーポイントを実行（プロジェクト内で実行）
uv run railway run daily_report

# 引数を渡す（-- 以降がエントリーポイントに渡される）
uv run railway run daily_report -- --date 2024-01-15 --dry-run

# プロジェクトディレクトリを指定
uv run railway run --project /path/to/project daily_report
```

**特徴:**
- プロジェクト構造を自動検出
- エラー時に利用可能なエントリーポイント一覧を表示
- `--` 以降の引数をそのままエントリーポイントに渡す

---

## 設定管理

### 統合設定ファイル: config/development.yaml

すべての設定が1つのファイルに統合されています:

```yaml
# アプリケーション設定
app:
  name: my_automation
  version: "0.1.0"

# API設定
api:
  base_url: "https://api.example.com"
  timeout: 30
  max_retries: 3

# ログ設定
logging:
  level: DEBUG
  format: "{time:HH:mm:ss} | {level} | {message}"
  handlers:
    - type: console
      level: DEBUG
    - type: file
      path: logs/app.log
      level: INFO
      rotation: "1 day"
      retention: "7 days"

# リトライ設定
retry:
  default:
    max_attempts: 3
    min_wait: 2
    max_wait: 10
    multiplier: 1
  nodes:
    fetch_data:      # ノード別設定
      max_attempts: 5
      min_wait: 1
```

### 環境変数 (.env)

```env
# 環境（development/staging/production）
RAILWAY_ENV=development

# アプリケーション
APP_NAME=my_automation

# ログレベル上書き（オプション）
LOG_LEVEL=DEBUG

# API認証情報（例）
API_KEY=your_api_key_here
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

# リトライ設定（ノード別）
retry_config = settings.get_retry_settings("fetch_data")
max_attempts = retry_config.max_attempts  # 5

# ログ設定
log_level = settings.logging.level  # "DEBUG"
```

---

## 実例: 日次レポート生成

### ステップ1: ノードを作成

```bash
railway new node fetch_sales_data --example
railway new node calculate_metrics --example
railway new node generate_report --example
```

### ステップ2: ノードを実装

```python
# src/nodes/fetch_sales_data.py
from railway import node
from loguru import logger
from src.settings import settings

@node(retry=True)
def fetch_sales_data(date: str) -> dict:
    """売上データを取得する"""
    logger.info(f"Fetching sales data for {date}")

    url = f"{settings.api.base_url}/sales?date={date}"
    response = requests.get(url, timeout=settings.api.timeout)
    response.raise_for_status()

    return response.json()
```

```python
# src/nodes/calculate_metrics.py
from railway import node
from loguru import logger

@node
def calculate_metrics(data: dict) -> dict:
    """メトリクスを計算する"""
    records = data.get("records", [])

    return {
        "total_sales": sum(r["amount"] for r in records),
        "count": len(records),
        "average": sum(r["amount"] for r in records) / len(records) if records else 0
    }
```

### ステップ3: エントリーポイントを作成

```python
# src/daily_sales_report.py
from railway import entry_point, pipeline
from datetime import datetime
from loguru import logger

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

    if dry_run:
        logger.warning("DRY RUN mode - no actual sending")

    result = pipeline(
        fetch_sales_data(date),
        calculate_metrics,
        generate_report,
        send_report if not dry_run else lambda x: x
    )

    return result


if __name__ == "__main__":
    main()
```

### ステップ4: 実行

```bash
# 開発環境でdry-run
uv run python -m src.daily_sales_report --dry-run

# 特定日のレポート
uv run python -m src.daily_sales_report --date 2024-01-15

# 本番環境で実行
RAILWAY_ENV=production uv run python -m src.daily_sales_report
```

---

## テストの書き方

ノード作成時にテストテンプレートも自動生成されます:

```python
# tests/nodes/test_fetch_sales_data.py
import pytest
from unittest.mock import patch, MagicMock
from src.nodes.fetch_sales_data import fetch_sales_data


class TestFetchSalesData:
    """fetch_sales_data ノードのテスト"""

    def test_success(self):
        """正常系: データ取得成功"""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"records": [{"amount": 100}]}
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            result = fetch_sales_data("2024-01-01")

            assert result == {"records": [{"amount": 100}]}
            mock_get.assert_called_once()

    def test_api_error(self):
        """異常系: API エラー"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("API Error")

            with pytest.raises(Exception) as exc_info:
                fetch_sales_data("2024-01-01")

            assert "API Error" in str(exc_info.value)

    def test_empty_response(self):
        """境界値: 空のレスポンス"""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"records": []}
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            result = fetch_sales_data("2024-01-01")

            assert result == {"records": []}
```

### テスト実行

```bash
# すべてのテスト実行
pytest

# 詳細出力
pytest -v

# カバレッジ付き
pytest --cov=src --cov-report=html

# 特定のテストのみ
pytest tests/nodes/test_fetch_sales_data.py -v

# print文を表示
pytest -v -s
```

---

## トラブルシューティング

### よくあるエラーと解決方法

#### 1. ModuleNotFoundError

```
ModuleNotFoundError: No module named 'src.nodes.fetch_data'
```

**解決策:**
- プロジェクトルートから実行しているか確認
- ファイルが正しいパスに存在するか確認
- `__init__.py` が各ディレクトリに存在するか確認

```bash
# 正しい実行方法
cd my_project
uv run python -m src.my_entry
```

#### 2. 設定ファイルエラー

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for APISettings
base_url
  Field required
```

**解決策:**
- `config/development.yaml` に必要なフィールドが存在するか確認
- YAMLのインデントが正しいか確認
- `.env` に `RAILWAY_ENV=development` が設定されているか確認

#### 3. 接続エラー

```
ConnectionError: Unable to connect to API
```

**解決策:**
- ネットワーク接続を確認
- `config/development.yaml` の `api.base_url` が正しいか確認
- `--dry-run` オプションでテスト実行

#### 4. リトライ後も失敗

```
[fetch_data] ✗ Failed after 3 attempts: TimeoutError
```

**解決策:**
- `config/development.yaml` でリトライ設定を調整:
  ```yaml
  retry:
    nodes:
      fetch_data:
        max_attempts: 5
        max_wait: 30
  ```
- APIのタイムアウト値を増やす
- APIサーバーの状態を確認

### ログの確認方法

```bash
# リアルタイムでログを監視
tail -f logs/app.log

# エラーログのみ表示
grep ERROR logs/app.log

# 最新50行を表示
tail -50 logs/app.log
```

### デバッグモード

```bash
# 環境変数でDEBUGレベルに設定
LOG_LEVEL=DEBUG uv run python -m src.my_entry

# または .env で設定
LOG_LEVEL=DEBUG
```

---

## 開発ワークフロー

```bash
# 1. ノード作成
railway new node my_feature --example

# 2. ノードを実装
# src/nodes/my_feature.py を編集

# 3. テスト作成・実行
pytest tests/nodes/test_my_feature.py -v

# 4. 型チェック
mypy src/nodes/my_feature.py

# 5. リント
ruff check src/nodes/my_feature.py
ruff format src/nodes/my_feature.py

# 6. エントリーポイントに組み込み
railway new entry my_entry

# 7. 動作確認（dry-run）
uv run python -m src.my_entry --dry-run

# 8. 本番実行
uv run python -m src.my_entry
```

### コードレビュー前チェック

```bash
# すべてのチェックを実行
ruff check .         # リント
ruff format .        # フォーマット
mypy src/            # 型チェック
pytest               # テスト実行
```

---

## 採用技術スタック

### コア機能
| ライブラリ | 用途 | 備考 |
|-----------|------|------|
| `tenacity` | リトライ処理 | 同期・非同期対応、指数バックオフ |
| `pydantic` | データバリデーション | 型安全な設定管理 |
| `pydantic-settings` | 設定管理 | 環境変数 + YAML |
| `typer` | CLIインターフェース | 自動的な引数パース |
| `loguru` | 構造化ロギング | シンプルで強力 |
| `PyYAML` | YAML設定読み込み | |
| `Jinja2` | テンプレートエンジン | コード生成 |
| `asyncio` (標準ライブラリ) | 非同期処理 | async/await サポート |

### 開発ツール
| ライブラリ | 用途 |
|-----------|------|
| `uv` | 高速パッケージ管理 |
| `ruff` | リント・フォーマット |
| `mypy` | 型チェック |
| `pytest` | テスト実行 |
| `pytest-cov` | カバレッジ測定 |
| `pytest-asyncio` | 非同期テストサポート |

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

### 4. 監視・アラート
```python
@entry_point
def health_check():
    """システムヘルスチェック"""
    return pipeline(
        check_api_endpoints(),
        check_database_connections,
        check_disk_space,
        aggregate_results,
        send_alert_if_unhealthy
    )
```

### 5. 非同期API統合（複数APIの並行呼び出し）
```python
from railway.core.pipeline import async_pipeline
import asyncio

@node
async def fetch_weather_async(city: str) -> dict:
    """天気APIから非同期取得"""
    async with aiohttp.ClientSession() as session:
        url = f"https://api.weather.com/v1/{city}"
        async with session.get(url) as response:
            return await response.json()

@node
async def fetch_news_async(city: str) -> dict:
    """ニュースAPIから非同期取得"""
    async with aiohttp.ClientSession() as session:
        url = f"https://api.news.com/v1/{city}"
        async with session.get(url) as response:
            return await response.json()

@node
async def merge_data(weather: dict, news: dict) -> dict:
    """データを結合"""
    return {"weather": weather, "news": news}

@entry_point
async def city_info_report(city: str):
    """都市情報レポート（非同期）"""
    # 並行実行で高速化
    weather, news = await asyncio.gather(
        fetch_weather_async(city),
        fetch_news_async(city)
    )
    return await merge_data(weather, news)
```

---

## Advanced機能

### 1. 非同期ノードとパイプライン

async/await を使った非同期処理を完全サポート:

```python
from railway import node, entry_point
from railway.core.pipeline import async_pipeline
import asyncio
import aiohttp

@node
async def fetch_data_async(url: str) -> dict:
    """非同期でデータ取得"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

@node
async def process_async(data: dict) -> dict:
    """非同期で処理"""
    await asyncio.sleep(0.1)  # 重い処理の例
    return {"processed": data}

@node
def save_sync(data: dict) -> str:
    """同期処理（混在可能）"""
    # データベースに保存
    return "Saved!"

@entry_point
async def async_workflow():
    """非同期ワークフロー"""
    # 同期と非同期のノードを混在できる
    result = await async_pipeline(
        "https://api.example.com/data",
        fetch_data_async,
        process_async,
        save_sync  # 同期ノードも使える
    )
    return result
```

**特徴:**
- ✅ `async def` の関数を `@node` でラップ可能
- ✅ `async_pipeline()` で非同期パイプライン実行
- ✅ 同期・非同期ノードの混在が可能
- ✅ リトライ機能も非同期対応済み

**注意:**
- 同期 `pipeline()` に非同期ノードを渡すとエラー
- 非同期エントリーポイントは `async def` で定義

### 2. Strict モード: ランタイム型チェック

開発時に型の不一致を早期発見:

```python
from railway import node
from railway.core.pipeline import pipeline

@node
def get_number(x: str) -> int:
    return int(x)

@node
def double(x: int) -> int:
    return x * 2

@node
def format_result(x: str) -> str:  # 型が合わない！
    return f"Result: {x}"

# strict=True でランタイム型チェック
result = pipeline(
    "42",
    get_number,  # str -> int
    double,      # int -> int
    format_result,  # int を期待するが str を要求
    strict=True
)
# TypeError: Pipeline type mismatch at step 3 (format_result):
# expected str, got int (value: 84)
```

**Strict モードの特徴:**
- ✅ 各ステップ間の型互換性をランタイムで検証
- ✅ Optional/Union 型にも対応
- ✅ 詳細なエラーメッセージ（ステップ番号、期待型、実際の型）
- ✅ デフォルトは `strict=False`（本番環境向け）

**使い分け:**
- 開発・テスト: `strict=True` で型チェック
- 本番環境: `strict=False` でパフォーマンス優先

### 3. カスタムエラー型

Railway Frameworkの独自エラー型で原因を即座に把握:

```python
from railway.core.errors import (
    RailwayError,
    ConfigurationError,
    NodeError,
    NetworkError,
    ValidationError,
)

@node
def validate_config(config: dict) -> dict:
    """設定を検証"""
    if "api_key" not in config:
        raise ConfigurationError(
            "API key is missing",
            config_key="api.key",
            hint="config/development.yaml に api.key を追加してください"
        )
    return config

@node
def fetch_from_api(url: str) -> dict:
    """APIからデータ取得"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError as e:
        raise NetworkError(
            "Failed to connect to API",
            url=url,
            hint="ネットワーク接続を確認してください"
        ) from e
```

**エラー出力例:**
```
[E001] [fetch_from_api] Failed to connect to API
URL: https://api.example.com/data
ヒント: ネットワーク接続を確認してください。APIエンドポイントが正しいか確認してください。
```

**利用可能なエラー型:**
| エラー型 | 用途 | リトライ可否 |
|---------|------|------------|
| `RailwayError` | ベースクラス | 設定可能 |
| `ConfigurationError` | 設定エラー | ❌ |
| `NodeError` | ノード実行エラー | ✅ |
| `PipelineError` | パイプラインエラー | ❌ |
| `NetworkError` | ネットワークエラー | ✅ |
| `ValidationError` | バリデーションエラー | ❌ |
| `TimeoutError` | タイムアウト | ✅ |

**特徴:**
- ✅ `retryable` 属性でリトライ可否を自動判定
- ✅ 日本語ヒントメッセージ
- ✅ `full_message()` で詳細メッセージ取得
- ✅ `to_dict()` でJSON化可能

---

## FAQ

**Q: 既存のスクリプトを移行できますか？**
A: はい。既存関数に `@node` デコレータを付けるだけで使えます。段階的に移行できます。

**Q: 非同期処理に対応していますか？**
A: はい、完全対応しています！`async def` で定義した関数を `@node` でラップし、`async_pipeline()` で実行できます。同期・非同期ノードの混在も可能です。

**Q: strict モードは常に有効にすべきですか？**
A: 開発・テスト時は `strict=True` を推奨しますが、本番環境ではパフォーマンスのため `strict=False`（デフォルト）を推奨します。mypy で静的型チェックを併用すると効果的です。

**Q: エラーログはどこに出力されますか？**
A: `config/{env}.yaml` の logging セクションで設定できます。デフォルトは `logs/` ディレクトリです。

**Q: カスタムエラー型を使うべきですか？**
A: はい！特にチーム開発では、日本語ヒント付きエラーによって問題解決が大幅に早くなります。標準の `Exception` の代わりに `NetworkError`, `ConfigurationError` などを使用することを推奨します。

**Q: 本番環境での推奨設定は？**
A: `RAILWAY_ENV=production` を設定し、`config/production.yaml` で以下を調整:
- ログレベル: INFO 以上
- リトライ回数: 適切に設定
- タイムアウト: 環境に応じて調整
- ファイルログ: rotation と retention を設定
- strict モード: 無効（パフォーマンス優先）

**Q: グラフ機能はありますか？**
A: Phase 1 ではシンプルな `pipeline()` / `async_pipeline()` のみです。グラフベースの依存関係管理は Phase 2 で提供予定です。

**Q: テストカバレッジの目標は？**
A: 80%以上を推奨しています。`pytest --cov=src` でカバレッジを確認できます。コアモジュールは90%以上を維持しています。

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

### Phase 1a ✅ 完了
- ✅ プロジェクト構造とCI/CD
- ✅ `@node` デコレータ（基本版）
- ✅ `@entry_point` デコレータ
- ✅ `pipeline()` 関数
- ✅ 設定管理（Settings）
- ✅ ロギング初期化
- ✅ `railway init` コマンド
- ✅ `railway new` コマンド
- ✅ `railway list` コマンド
- ✅ テスト自動生成

### Phase 1b ✅ 完了
- ✅ リトライ機能の拡張（tenacity統合）
- ✅ エラー表示の改善（日本語ヒント表示）
- ✅ `railway run` コマンド
- ✅ チュートリアル自動生成
- ✅ テストテンプレート改善

### Phase 1c ✅ 完了
- ✅ `pipeline()` strict モード（ランタイム型チェック）
- ✅ 非同期ノード基本サポート（`async_pipeline()`）
- ✅ カスタムエラー型階層
- ✅ 遅延初期化（`_SettingsProxy`）
- ✅ 統合テストとドキュメント

### Phase 2 📋 計画中
- 🔜 並列パイプライン実行
- 🔜 graph.yaml によるグラフベース実行
- 🔜 WebUI でのグラフ可視化
- 🔜 詳細なメトリクス収集
- 🔜 ストリーミング処理
- 🔜 プラグインシステム

### Phase 3 🔮 将来
- 🔜 分散実行サポート (Celery/Dask)
- 🔜 クラウドサービス統合 (AWS/GCP/Azure)
- 🔜 スケジューラー統合

---

## 実装状況

| 項目 | テスト数 | カバレッジ |
|------|---------|-----------|
| コア機能 | 140+ | 90%+ |
| CLI/統合 | 82 | 74% |
| **合計** | **222** | **90%+** (コア) |

**Phase 1 完了！** 全20 Issueの実装が完了し、プロダクション使用可能な状態です。

---

**さあ、Railway Framework で運用自動化を始めましょう！**

```bash
railway init my_first_automation
cd my_first_automation
railway new entry hello --example
railway run hello
```

---

## 🎉 Phase 1 完了記念

**Railway Framework Phase 1 (全20 Issue) が完了しました！**

以下の機能が全て実装され、プロダクション使用可能です：

### ✨ 実装済み機能
- ✅ Railway Oriented Programming パターン
- ✅ デコレータベースAPI (`@node`, `@entry_point`)
- ✅ 同期・非同期パイプライン (`pipeline`, `async_pipeline`)
- ✅ ランタイム型チェック (strict mode)
- ✅ 自動リトライ機能 (tenacity)
- ✅ カスタムエラー型（日本語ヒント付き）
- ✅ 設定管理（YAML + 環境変数）
- ✅ 構造化ロギング (loguru)
- ✅ CLIツール (`init`, `new`, `list`, `run`)
- ✅ テスト自動生成
- ✅ チュートリアル自動生成

### 📊 品質指標
- **総テスト数:** 222 (全て成功)
- **カバレッジ:** コアモジュール 90%+
- **型安全性:** mypy完全対応

### 🚀 次のステップ
Phase 2では以下を実装予定：
- 並列パイプライン実行
- グラフベースワークフロー
- メトリクス収集
- ストリーミング処理

**ご意見・ご要望は[Issue](https://github.com/your-org/railway-py/issues)でお待ちしています！**
