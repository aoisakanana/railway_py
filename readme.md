# Railway Framework for Python

**シンプルで強力な運用自動化フレームワーク**

Pythonで**型安全**で**エラーに強い**運用自動化ツールを、**5分で**作成開始できます。

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Test Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen.svg)]()
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
- 🔄 **自動リトライ**: 一時的なエラーに自動で対処
- 📊 **構造化ロギング**: loguru による美しいログ出力

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
uv add railway-framework
```

### 2. プロジェクト作成

```bash
railway init my_automation
cd my_automation
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
| `returns` | Railway Oriented Programming | Result型、bind、flow |
| `tenacity` | リトライ処理 | 指数バックオフ、カスタマイズ可能 |
| `pydantic` | データバリデーション | 型安全な設定管理 |
| `pydantic-settings` | 設定管理 | 環境変数 + YAML |
| `typer` | CLIインターフェース | 自動的な引数パース |
| `loguru` | 構造化ロギング | シンプルで強力 |
| `PyYAML` | YAML設定読み込み | |

### 開発ツール
| ライブラリ | 用途 |
|-----------|------|
| `uv` | 高速パッケージ管理 |
| `ruff` | リント・フォーマット |
| `mypy` | 型チェック |
| `pytest` | テスト実行 |
| `pytest-cov` | カバレッジ測定 |

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
A: はい。既存関数に `@node` デコレータを付けるだけで使えます。段階的に移行できます。

**Q: 非同期処理に対応していますか？**
A: Phase 1では `@node` デコレータで `async def` を検出しますが、`pipeline()` は同期ノードのみサポートします。非同期パイプラインはPhase 2で提供予定です。

**Q: エラーログはどこに出力されますか？**
A: `config/{env}.yaml` の logging セクションで設定できます。デフォルトは `logs/` ディレクトリです。

**Q: 本番環境での推奨設定は？**
A: `RAILWAY_ENV=production` を設定し、`config/production.yaml` で以下を調整:
- ログレベル: INFO 以上
- リトライ回数: 適切に設定
- タイムアウト: 環境に応じて調整
- ファイルログ: rotation と retention を設定

**Q: グラフ機能はありますか？**
A: Phase 1 ではシンプルな `pipeline()` のみです。グラフベースの依存関係管理は Phase 2 で提供予定です。

**Q: テストカバレッジの目標は？**
A: 80%以上を推奨しています。`pytest --cov=src` でカバレッジを確認できます。

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

### Phase 1b 🔨 進行中
- 🔜 リトライ機能の拡張
- 🔜 エラー表示の改善（ヒント表示）
- 🔜 `railway run` コマンド
- 🔜 チュートリアル自動生成
- 🔜 テストテンプレート改善

### Phase 2 📋 計画中
- 🔜 `pipeline_async()` - 非同期パイプライン
- 🔜 graph.yaml によるグラフベース実行
- 🔜 WebUI でのグラフ可視化
- 🔜 詳細なメトリクス収集
- 🔜 インタラクティブデバッガ

### Phase 3 🔮 将来
- 🔜 分散実行サポート (Celery/Dask)
- 🔜 クラウドサービス統合 (AWS/GCP/Azure)
- 🔜 スケジューラー統合

---

## 実装状況

| 項目 | テスト数 | カバレッジ |
|------|---------|-----------|
| コア機能 | 79 | 91% |
| CLIコマンド | 36 | 92% |
| **合計** | **115** | **91%** |

---

**さあ、Railway Framework で運用自動化を始めましょう！**

```bash
railway init my_first_automation
cd my_first_automation
railway new entry hello --example
uv run python -m src.hello
```
