# Railway Framework for Python

Pythonで**型安全**で**エラーに強い**運用自動化ツールを、簡単に作成できるフレームワークです。

## 目次

- [これは何？](#これは何)
- [コア概念](#コア概念)
- [クイックスタート](#クイックスタート)
- [主要な特徴](#主要な特徴)
- [ユースケース](#ユースケース)
- [プロジェクト構造](#プロジェクト構造)
- [エントリーポイントの例](#エントリーポイントの例)
- [ノードの例](#ノードの例)
- [設定ファイルと設定管理](#設定ファイルと設定管理)
- [CLIコマンド](#cliコマンド)
- [グラフ定義（オプション）](#グラフ定義オプション機能)
- [採用技術スタック](#採用技術スタック)
- [開発ワークフロー](#開発ワークフロー)
- [テストの書き方](#テストの書き方)
- [Advanced機能](#advanced機能)
- [FAQ](#faq)

## これは何？

Railway Oriented Programming（ROP）パラダイムで、運用自動化スクリプトを構築するためのフレームワークです。
「成功パス」と「エラーパス」を明確に分離し、エラーハンドリングを簡潔かつ安全に記述できます。

### 解決する問題

**従来の運用スクリプトの課題:**
```python
# ❌ 従来のアプローチ: エラーハンドリングが複雑で漏れやすい
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

**Railwayフレームワークのアプローチ:**
```python
# ✅ Railwayフレームワーク: エラーは自動的に伝播、コードは簡潔
@railway_node
def process() -> Result[str, Exception]:
    return (
        fetch_data()
        .bind(transform)
        .bind(save)
    )
```

### Railway Oriented Programmingとは？

関数型プログラミングの概念で、処理を「線路」に例えます:
- **成功パス（Success Track）**: すべてが正常に動作する線路
- **エラーパス（Failure Track）**: エラーが発生した線路

一度エラーパスに入ると、後続の処理はスキップされ、エラーが最終的に返されます。
これにより、if文やtry-exceptのネストが不要になり、コードが読みやすくなります。

## コア概念

### Result型
処理の成功または失敗を表現する型です（`returns`ライブラリ提供）:
```python
from returns.result import Result, Success, Failure

def divide(a: int, b: int) -> Result[float, str]:
    if b == 0:
        return Failure("Division by zero")
    return Success(a / b)

# 使用例
result = divide(10, 2)
result.map(lambda x: print(f"Result: {x}"))      # Result: 5.0
result.alt(lambda e: print(f"Error: {e}"))       # エラー時のみ実行
```

### bind（メソッドチェーン）
Result型の値に対して、次の処理を適用します。エラーの場合は自動的にスキップされます:
```python
def add_one(x: int) -> Result[int, str]:
    return Success(x + 1)

def multiply_two(x: int) -> Result[int, str]:
    return Success(x * 2)

# チェーン処理
result = Success(5).bind(add_one).bind(multiply_two)  # Success(12)
# 5 -> 6 -> 12
```

### flow（パイプライン）
複数の関数を順次実行するパイプラインを構築します:
```python
from returns.pipeline import flow

def fetch() -> Result[dict, Exception]: ...
def validate(data: dict) -> Result[dict, Exception]: ...
def save(data: dict) -> Result[str, Exception]: ...

# flowで処理パイプライン構築
result = flow(
    fetch(),
    validate,
    save,
)
```

**bindとflowの使い分け:**
- **bind**: 既存のResult値にメソッドチェーンで処理を追加
- **flow**: 最初から処理パイプライン全体を定義

### @safeデコレータ
通常の関数を自動的にResult型を返す関数に変換します:
```python
from returns.result import safe

@safe
def risky_operation(x: int) -> int:
    if x < 0:
        raise ValueError("Negative value")
    return x * 2

# 自動的にResult型に変換される
result = risky_operation(5)   # Success(10)
result = risky_operation(-1)  # Failure(ValueError(...))
```

## クイックスタート

```bash
# 1. uvをインストール（未インストールの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. リポジトリをクローン
git clone https://github.com/your-org/railway_py.git
cd railway_py

# 3. プロジェクトを初期化
railway init my_automation
cd my_automation

# 4. エントリーポイントを作成
railway add-entry daily_report

# 5. 生成されたファイルを確認（src/daily_report.py）
# テンプレートには必要なコードがすべて記述済み

# 6. 実行
uv run python -m src.daily_report

# 出力例:
# [INFO] Starting daily_report...
# [INFO] ✓ fetch_data completed
# [INFO] ✓ process_data completed
# [INFO] ✓ send_report completed
# [SUCCESS] Pipeline completed successfully!
```

## 主要な特徴

- **簡潔なエラーハンドリング**: `Result`型で成功/失敗を型安全に表現
- **ワンコマンドでスタート**: テンプレート自動生成で即座に開発開始
- **グラフベースの処理フロー**: ノード間の依存関係を宣言的に定義
- **環境別設定**: development/production等の環境を`.env`で切り替え
- **型安全**: `mypy`による厳格な型チェック
- **リトライ機能**: 設定ファイルでリトライポリシーを管理

## ユースケース

### 1. API統合の自動化
```python
# 外部APIからデータを取得→変換→別APIに送信
def api_integration() -> Result[dict, Exception]:
    return (
        fetch_from_api_a()
        .bind(validate_schema)
        .bind(transform_data)
        .bind(send_to_api_b)
    )
```

### 2. データベースバッチ処理
```python
# DB抽出→集計→レポート生成→通知
def daily_batch() -> Result[str, Exception]:
    return (
        extract_from_db()
        .bind(aggregate_stats)
        .bind(generate_report)
        .bind(send_notification)
    )
```

### 3. ファイル処理パイプライン
```python
# ファイル読込→検証→変換→保存
def file_processing() -> Result[Path, Exception]:
    return (
        read_csv_file()
        .bind(validate_records)
        .bind(transform_format)
        .bind(save_to_storage)
    )
```

## プロジェクト構造

```
my_automation/
├── src/
│   ├── daily_report.py        # エントリーポイント
│   ├── nodes/                 # 処理ノード（再利用可能）
│   │   ├── fetch_data.py
│   │   ├── process_data.py
│   │   └── send_report.py
│   ├── common/                # 共通ユーティリティ
│   │   └── api_client.py
│   └── settings.py            # 設定読み込み
├── config/
│   ├── development/
│   │   ├── app.yaml           # アプリ設定
│   │   ├── logging.yaml       # ログ設定
│   │   └── retry.yaml         # リトライ設定
│   └── production/
│       └── ...
├── tests/                     # テストコード
├── .env                       # 環境変数
└── pyproject.toml
```

## エントリーポイントの例

`railway add-entry daily_report`で生成されるファイル（`src/daily_report.py`）:

```python
"""Daily report generation entry point."""
from returns.result import Result, Success, Failure
from returns.pipeline import flow
from loguru import logger
import typer

from src.nodes.fetch_data import fetch_data
from src.nodes.process_data import process_data
from src.nodes.send_report import send_report
from src.settings import settings

app = typer.Typer()


def run_pipeline() -> Result[str, Exception]:
    """Execute the daily report pipeline."""
    return flow(
        fetch_data(),
        process_data,
        send_report,
    )


@app.command()
def main(
    date: str = typer.Option(None, help="Report date (YYYY-MM-DD)"),
    dry_run: bool = typer.Option(False, help="Dry run mode"),
) -> None:
    """Generate and send daily report."""
    logger.info(f"Starting daily_report (dry_run={dry_run})...")

    result = run_pipeline()

    result.map(lambda x: logger.success(f"✓ Pipeline completed: {x}"))
    result.alt(lambda e: logger.error(f"✗ Pipeline failed: {e}"))


if __name__ == "__main__":
    app()
```

## ノードの例

`railway add-node fetch_data`で生成されるファイル（`src/nodes/fetch_data.py`）:

```python
"""Fetch data from external API."""
from returns.result import Result, Success, Failure, safe
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger

from src.common.api_client import APIClient
from src.settings import settings


@retry(
    stop=stop_after_attempt(settings.retry.max_attempts),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
@safe
def fetch_data() -> dict:
    """
    Fetch data from external API with retry.

    Returns:
        Result[dict, Exception]: Success with data or Failure with error
    """
    logger.info("Fetching data from API...")

    client = APIClient(base_url=settings.api.base_url)
    response = client.get("/data")

    logger.debug(f"Received {len(response)} records")
    return response
```

## 設定ファイルと設定管理

### 設定の仕組み

`src/settings.py`が環境変数（`.env`）とYAML設定ファイルを読み込み、`pydantic`で型安全な設定オブジェクトを生成します:

```python
# src/settings.py（自動生成される）
from pydantic import BaseModel
from pydantic_settings import BaseSettings
import yaml
from pathlib import Path

class APISettings(BaseModel):
    base_url: str
    timeout: int

class RetrySettings(BaseModel):
    max_attempts: int
    multiplier: int
    min_wait: int
    max_wait: int

class Settings(BaseSettings):
    railway_env: str = "development"
    app_name: str
    log_level: str = "INFO"

    # YAMLから読み込まれる設定
    api: APISettings
    retry: RetrySettings

    class Config:
        env_file = ".env"

# グローバル設定オブジェクト
settings = Settings()
```

これにより、コード内で`settings.api.base_url`や`settings.retry.max_attempts`のように型安全にアクセスできます。

### `.env`
```env
# 環境指定（development/staging/production）
RAILWAY_ENV=development

# アプリ設定
APP_NAME=my_automation
LOG_LEVEL=INFO
```

### `config/development/app.yaml`
```yaml
# アプリケーション設定
api:
  base_url: "https://api.example.com"
  timeout: 30

database:
  host: "localhost"
  port: 5432
  name: "dev_db"

notification:
  email_to: "dev@example.com"
  slack_webhook: "https://hooks.slack.com/..."
```

### `config/development/retry.yaml`
```yaml
# リトライポリシー設定
max_attempts: 3
multiplier: 1
min_wait: 2
max_wait: 10

# ノード別の設定
nodes:
  fetch_data:
    max_attempts: 5
    min_wait: 1
  send_notification:
    max_attempts: 2
```

### `config/development/logging.yaml`
```yaml
# ロギング設定
level: "DEBUG"
format: "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}"

handlers:
  - sink: "logs/app.log"
    rotation: "1 day"
    retention: "7 days"
    level: "INFO"

  - sink: "stderr"
    level: "DEBUG"
```

## CLIコマンド

### プロジェクト管理
```bash
railway init <project_name>        # 新規プロジェクト作成
railway info                       # プロジェクト情報表示
```

### エントリーポイント管理
```bash
railway add-entry <name>           # エントリーポイント追加
railway add-entry <name> --async   # 非同期版テンプレート生成
railway list-entries               # エントリーポイント一覧
```

### ノード管理
```bash
railway add-node <name>            # 新規ノード追加
railway list-nodes                 # ノード一覧
```

### グラフ管理
```bash
railway graph validate             # グラフ定義の検証
railway graph visualize            # グラフ構造の可視化（Mermaid形式）
railway graph check-cycles         # 循環依存チェック
```

### 実行・テスト
```bash
uv run python -m src.<entry_name>  # エントリーポイント実行
pytest                             # テスト実行
ruff check .                       # リント
mypy src/                          # 型チェック
```

## グラフ定義（オプション機能）

**基本的な使い方では不要です。** 複雑なパイプラインで依存関係を明示的に管理したい場合に使用します。

ノード間の依存関係を`graph.yaml`で定義すると、実行順序の自動解決と並列実行が可能になります:

```yaml
# graph.yaml
pipeline: daily_report

nodes:
  - name: fetch_data
    type: source              # データ取得ノード
    retry: true

  - name: validate_data
    type: transform           # データ変換ノード
    depends_on: [fetch_data]

  - name: process_data
    type: transform
    depends_on: [validate_data]

  - name: save_to_db
    type: sink               # データ保存ノード
    depends_on: [process_data]
    retry: true

  - name: send_notification
    type: sink
    depends_on: [save_to_db]
    retry: true
    on_failure: log_only     # エラー時もパイプライン続行
```

実行順序は自動的に解決され、並列実行可能なノードは並行処理されます。

## 採用技術スタック

### コア機能
| ライブラリ | 用途 |
|-----------|------|
| `returns` | Railway Oriented Programming |
| `tenacity` | リトライ処理 |
| `pydantic` | 設定バリデーション |
| `typer` | CLIインターフェース |
| `loguru` | 構造化ロギング |

### 開発ツール
| ライブラリ | 用途 |
|-----------|------|
| `ruff` | リント・フォーマット |
| `mypy` | 型チェック |
| `pytest` | テスト実行 |
| `uv` | 高速パッケージ管理 |

## 開発ワークフロー

```bash
# 1. ノード実装
railway add-node my_feature
# → src/nodes/my_feature.py を編集

# 2. テスト作成
# → tests/nodes/test_my_feature.py を編集

# 3. テスト実行
pytest tests/nodes/test_my_feature.py -v

# 4. 型チェック
mypy src/nodes/my_feature.py

# 5. エントリーポイントに組み込み
# → src/my_entry.py の flow に追加

# 6. 動作確認
uv run python -m src.my_entry --dry-run

# 7. 本番実行
uv run python -m src.my_entry
```

## テストの書き方

`railway add-node my_feature`でノードと同時にテストテンプレートも生成されます。

### テストテンプレート例

`tests/nodes/test_fetch_data.py`:
```python
"""Tests for fetch_data node."""
import pytest
from returns.result import Success, Failure
from unittest.mock import Mock, patch

from src.nodes.fetch_data import fetch_data


def test_fetch_data_success():
    """正常系: データ取得に成功"""
    with patch('src.common.api_client.APIClient') as mock_client:
        # モックの設定
        mock_client.return_value.get.return_value = {"records": [1, 2, 3]}

        # 実行
        result = fetch_data()

        # 検証
        assert result.is_success
        data = result.unwrap()
        assert "records" in data
        assert len(data["records"]) == 3


def test_fetch_data_api_error():
    """異常系: API呼び出しエラー"""
    with patch('src.common.api_client.APIClient') as mock_client:
        # API呼び出しが例外を発生
        mock_client.return_value.get.side_effect = ConnectionError("API unavailable")

        # 実行
        result = fetch_data()

        # 検証
        assert result.is_failure
        error = result.failure()
        assert isinstance(error, ConnectionError)


def test_fetch_data_retry():
    """リトライ動作の確認"""
    with patch('src.common.api_client.APIClient') as mock_client:
        # 1回目と2回目は失敗、3回目は成功
        mock_client.return_value.get.side_effect = [
            ConnectionError("Timeout"),
            ConnectionError("Timeout"),
            {"records": [1, 2]},
        ]

        # 実行
        result = fetch_data()

        # 検証
        assert result.is_success
        assert mock_client.return_value.get.call_count == 3
```

### 統合テスト例

`tests/test_daily_report.py`:
```python
"""Integration tests for daily_report pipeline."""
from returns.result import Success
from src.daily_report import run_pipeline


def test_full_pipeline(monkeypatch):
    """パイプライン全体のテスト"""
    # モックデータを設定
    test_data = {"date": "2024-01-01", "records": [1, 2, 3]}

    # 各ノードをモック化
    monkeypatch.setattr(
        'src.nodes.fetch_data.fetch_data',
        lambda: Success(test_data)
    )
    monkeypatch.setattr(
        'src.nodes.process_data.process_data',
        lambda x: Success({"processed": x})
    )
    monkeypatch.setattr(
        'src.nodes.send_report.send_report',
        lambda x: Success("Report sent")
    )

    # パイプライン実行
    result = run_pipeline()

    # 検証
    assert result.is_success
    assert result.unwrap() == "Report sent"
```

## Advanced機能

<details>
<summary>既存スクリプトの移行</summary>

既存の運用スクリプトを段階的にRailwayフレームワークに移行できます。

**移行前の既存スクリプト:**
```python
def daily_batch():
    try:
        # データ取得
        response = requests.get("https://api.example.com/data")
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            return

        data = response.json()

        # データ処理
        processed = []
        for item in data:
            if item['value'] > 0:
                processed.append(item['value'] * 2)

        # 保存
        with open('output.txt', 'w') as f:
            f.write(str(processed))

        print("Success!")
    except Exception as e:
        print(f"Error: {e}")
```

**ステップ1: 既存関数を@safeでラップ**
```python
from returns.result import safe

@safe
def fetch_data():
    response = requests.get("https://api.example.com/data")
    response.raise_for_status()
    return response.json()

@safe
def process_data(data):
    processed = []
    for item in data:
        if item['value'] > 0:
            processed.append(item['value'] * 2)
    return processed

@safe
def save_data(processed):
    with open('output.txt', 'w') as f:
        f.write(str(processed))
    return "Success"
```

**ステップ2: パイプラインで結合**
```python
from returns.pipeline import flow

def daily_batch():
    result = flow(
        fetch_data(),
        process_data,
        save_data,
    )

    result.map(lambda x: logger.success(f"✓ {x}"))
    result.alt(lambda e: logger.error(f"✗ Error: {e}"))
```

**ステップ3: Railwayフレームワークに統合**
```bash
railway add-entry daily_batch
# 生成されたテンプレートにステップ2のコードを移植
```

これで完全にRailwayパラダイムに移行完了です！
</details>

<details>
<summary>非同期処理サポート</summary>

```python
from returns.future import FutureResult
from returns.io import impure_safe

async def async_fetch() -> FutureResult[dict, Exception]:
    """非同期でデータ取得"""
    data = await api_client.async_get("/data")
    return FutureResult.from_value(data)

# 非同期版エントリーポイント
railway add-entry async_pipeline --async
```
</details>

<details>
<summary>依存性注入</summary>

```python
from punq import Container

# DIコンテナ設定
container = Container()
container.register(APIClient, instance=APIClient(settings.api.base_url))
container.register(DatabaseClient)

# ノードでDI使用
@railway_node
def fetch_data(api_client: APIClient = Provide[Container, APIClient]):
    return api_client.get("/data")
```
</details>

<details>
<summary>カスタムエラー型</summary>

```python
from src.common.errors import RailwayError, RetryableError, FatalError

class ValidationError(FatalError):
    """データ検証エラー（リトライ不可）"""
    pass

class APITimeoutError(RetryableError):
    """APIタイムアウト（リトライ可能）"""
    pass
```
</details>

<details>
<summary>メトリクス・監視</summary>

```python
from src.common.observability import measure_time, track_errors

@measure_time
@track_errors
@railway_node
def critical_operation():
    """実行時間とエラー率を自動記録"""
    pass
```
</details>

<details>
<summary>CI/CD統合</summary>

`.github/workflows/ci.yml`が自動生成されます:
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          uv sync
          pytest
          ruff check .
          mypy src/
```
</details>

## FAQ

**Q: 既存のスクリプトを移行できますか？**
A: はい。段階的に移行できます。既存関数を`@safe`デコレータでラップするだけで`Result`型に変換できます。

**Q: エラーログはどこに出力されますか？**
A: `config/{env}/logging.yaml`で設定可能です。デフォルトは`logs/app.log`とstderrです。

**Q: 非同期処理に対応していますか？**
A: はい。`--async`オプションでasync/await対応テンプレートを生成できます。

**Q: テストの書き方は？**
A: `railway add-node`でノードと同時にテストテンプレートも生成されます。

**Q: 本番環境での推奨設定は？**
A: `RAILWAY_ENV=production`を設定し、`config/production/`で以下を調整してください:
- ログレベル: INFO以上
- リトライ回数: 適切に設定
- タイムアウト: 環境に応じて調整

## ライセンス

MIT License

## コントリビューション

Issue・PRを歓迎します！詳細は[CONTRIBUTING.md](CONTRIBUTING.md)を参照してください。
