# Railway Framework for Python

**型安全なワークフローで、運用自動化をシンプルに。**

条件分岐を含む複雑なワークフローをYAMLで宣言的に定義できます。

```python
# DAGワークフロー: 条件分岐対応
from railway import Contract, node, entry_point
from railway.core.dag import dag_runner, Exit, Outcome

class AlertContext(Contract):
    severity: str
    handled: bool = False

@node
def check_severity(ctx: AlertContext) -> tuple[AlertContext, Outcome]:
    if ctx.severity == "critical":
        return ctx, Outcome.success("critical")
    return ctx, Outcome.success("normal")

@node
def escalate(ctx: AlertContext) -> tuple[AlertContext, Outcome]:
    return ctx.model_copy(update={"handled": True}), Outcome.success("done")

@node
def log_only(ctx: AlertContext) -> tuple[AlertContext, Outcome]:
    return ctx.model_copy(update={"handled": True}), Outcome.success("done")

TRANSITIONS = {
    "check_severity::success::critical": escalate,
    "check_severity::success::normal": log_only,
    "escalate::success::done": Exit.GREEN,
    "log_only::success::done": Exit.GREEN,
}

@entry_point
def main():
    result = dag_runner(
        start=lambda: (AlertContext(severity="critical"), Outcome.success("start")),
        transitions=TRANSITIONS,
    )
    return result.context
```

**特徴:**
- DAGワークフロー: 条件分岐を含むワークフローをYAMLで定義
- 型安全: Contract + Outcome による静的型チェック
- 純粋関数: ノードは副作用のない純粋関数
- コード生成: YAMLから遷移コードを自動生成
- バージョン管理: プロジェクトバージョン追跡、自動マイグレーション

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Test Coverage](https://img.shields.io/badge/coverage-90%25+-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-305%20passing-success.svg)]()

---

## クイックスタート

### 1. インストール

```bash
# uvをインストール（未インストールの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# railway コマンドをインストール
uv tool install railway-framework
```

### 2. プロジェクト作成

```bash
railway init my_workflow
cd my_workflow
uv sync
```

### 3. エントリーポイント作成

```bash
railway new entry my_workflow
```

これにより以下が生成されます：
- `src/my_workflow.py` - エントリーポイント（dag_runner使用）
- `src/nodes/my_workflow/start.py` - 開始ノード
- `transition_graphs/my_workflow_*.yml` - 遷移グラフ

### 4. 遷移グラフを編集

`transition_graphs/my_workflow_*.yml`:

```yaml
version: "1.0"
entrypoint: my_workflow

nodes:
  start:
    module: nodes.my_workflow.start
    function: start
    description: "開始ノード"
  process:
    module: nodes.my_workflow.process
    function: process
    description: "処理ノード"

exits:
  success:
    code: 0
  error:
    code: 1

start: start

transitions:
  start:
    success::done: process
    failure::error: exit::error
  process:
    success::complete: exit::success
    failure::error: exit::error
```

### 5. コード生成

```bash
railway sync transition --entry my_workflow
```

### 6. 実行

```bash
railway run my_workflow
```

---

## ノードの実装

ノードは `Contract` と `Outcome` を返す純粋関数です：

```python
from railway import Contract, node
from railway.core.dag import Outcome


class MyContext(Contract):
    value: str


@node
def process(ctx: MyContext) -> tuple[MyContext, Outcome]:
    if ctx.value:
        return ctx, Outcome.success("done")
    else:
        return ctx, Outcome.failure("empty")
```

**Outcomeの種類:**

| メソッド | 用途 | 例 |
|----------|------|-----|
| `Outcome.success(detail)` | 正常完了 | `Outcome.success("done")` |
| `Outcome.failure(detail)` | エラー | `Outcome.failure("not_found")` |

**遷移キーの形式:**
```
node_name::status::detail
```

例: `check_severity::success::critical` → `escalate` ノードへ遷移

---

## ノードの作成

`railway new node` コマンドは、**型安全なノードをすぐに開発開始できる状態で生成**します。

**なぜこのコマンドを使うのか？**

| 手動作成 | `railway new node` |
|----------|-------------------|
| ノード、Contract、テストを個別に作成 | **3ファイル同時生成** |
| import文を自分で書く | **正しいimport済み** |
| テスト構造を考える | **TDDテンプレート付き** |
| Outcomeの使い方を調べる | **動作するサンプル付き** |

```bash
# dag 形式（デフォルト）: 条件分岐ワークフロー向け
railway new node check_status
# → src/nodes/check_status.py        ← ノード本体（動作するサンプル付き）
# → src/contracts/check_status_context.py  ← Contract（型安全）
# → tests/nodes/test_check_status.py       ← TDDテンプレート

# linear 形式: 線形パイプライン向け
railway new node transform --mode linear
# → Input/Output の2つのContractが生成される
```

**dag 形式（デフォルト）** - 条件分岐が可能:

```python
from railway import node
from railway.core.dag.outcome import Outcome

from contracts.check_status_context import CheckStatusContext


@node
def check_status(ctx: CheckStatusContext) -> tuple[CheckStatusContext, Outcome]:
    """ステータスをチェックする。"""
    if ctx.is_valid:
        return ctx, Outcome.success("valid")   # → valid 遷移
    return ctx, Outcome.failure("invalid")     # → invalid 遷移
```

**linear 形式** - シンプルなデータ変換向け:

```python
from typing import Optional

from railway import node

from contracts.transform_input import TransformInput
from contracts.transform_output import TransformOutput


@node
def transform(input_data: Optional[TransformInput] = None) -> TransformOutput:
    """データを変換する。"""
    return TransformOutput(result="transformed")
```

### どちらを使う？

| 用途 | 形式 | 理由 |
|------|------|------|
| 運用自動化、条件分岐あり | **dag（デフォルト）** | Outcomeで遷移を制御 |
| ETL、データ変換 | linear | シンプルな入出力 |
| 迷ったら | **dag** | より汎用的 |

### 使い分けガイド

| 場面 | 推奨方法 |
|------|----------|
| 既存ワークフローにノード追加 | `railway new node` |
| 単体の処理を作成 | `railway new node` |
| 新規ワークフロー作成 | `railway new entry`（ノードも同時生成） |

---

## 実行モデル

Railway Framework は2つの実行モデルを提供します：

| モデル | 用途 | コマンド |
|--------|------|----------|
| **dag_runner** | 条件分岐ワークフロー（推奨） | `railway new entry <name>` |
| typed_pipeline | 線形パイプライン | `railway new entry <name> --mode linear` |

### どちらを使うべきか？

**dag_runner を使う:**
- 条件分岐がある（if-else, switch）
- エラーパスが複数ある
- 運用自動化、複雑なワークフロー

**typed_pipeline を使う:**
- 処理が必ず順番に実行される（A→B→C→D）
- 条件分岐がない
- ETL、データ変換パイプライン

### dag_runner（推奨）

条件分岐がある複雑なワークフローに適しています：

```python
from railway.core.dag import dag_runner, Exit, Outcome

TRANSITIONS = {
    "check::success::critical": escalate,
    "check::success::normal": log_only,
    "escalate::success::done": Exit.GREEN,
    "log_only::success::done": Exit.GREEN,
}

result = dag_runner(
    start=check_severity,
    transitions=TRANSITIONS,
)

if result.is_success:
    print("Workflow completed successfully")
```

**dag_runner の特徴:**
- 条件分岐: Outcome に応じて遷移先を決定
- YAML定義: 遷移グラフをYAMLで宣言的に定義
- コード生成: `railway sync transition` で遷移コードを自動生成
- ステップコールバック: `on_step` で各ステップを監視

### typed_pipeline（線形パイプライン）

条件分岐がない線形処理に適しています：

```python
from railway import typed_pipeline

result = typed_pipeline(
    fetch_data,       # 1. データ取得
    transform_data,   # 2. 変換
    save_result,      # 3. 保存
)
```

線形パイプラインの詳細は [readme_linear.md](readme_linear.md) を参照してください。

詳細な設計判断は [ADR-002: 実行モデルの共存](docs/adr/002_execution_models.md) を参照。

---

## CLI Commands

### プロジェクト管理
```bash
railway init <name>              # プロジェクト作成
railway new entry <name>         # エントリポイント作成（dag_runnerモード）
railway new entry <name> --mode linear  # 線形パイプラインモード
railway docs                     # ドキュメント表示
```

### 遷移グラフ管理
```bash
railway sync transition --entry <name>  # 遷移コード生成
railway sync transition --all          # 全遷移コード生成
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

### バージョン管理
```bash
railway update                   # プロジェクトを最新バージョンに更新
railway update --dry-run         # 変更をプレビュー（実行しない）
railway update --init            # バージョン情報のないプロジェクトを初期化
railway backup list              # バックアップ一覧
railway backup restore           # バックアップから復元
railway backup clean --keep 3    # 古いバックアップを削除
```

---

## 特徴

- ✨ **5分で開始**: `railway init` でプロジェクト作成、すぐに実装開始
- 🛤️ **DAGワークフロー**: 条件分岐を含むワークフローをYAMLで宣言的に定義
- 🔒 **型安全**: Contract + Outcome による静的型チェック
- 🎯 **純粋関数**: ノードは副作用のない純粋関数
- ⚡ **コード生成**: YAMLから遷移コードを自動生成
- 🔄 **2つの実行モデル**: dag_runner（条件分岐）と typed_pipeline（線形）
- 🧪 **テスト容易**: モック不要、引数を渡すだけ
- ⚙️ **環境別設定**: development/production を簡単に切り替え
- 📊 **構造化ロギング**: loguru による美しいログ出力
- 🆙 **バージョン管理**: プロジェクトバージョン追跡、自動マイグレーション

---

## アーキテクチャ

### Contract（型契約）

ノード間で交換されるデータの「契約」を定義します。

```python
from railway import Contract

class AlertContext(Contract):
    """アラート処理のコンテキスト"""
    incident_id: str
    severity: str
    hostname: str | None = None
```

**Contractの特徴:**
- **Pydantic BaseModel** がベース（自動バリデーション）
- **イミュータブル** で安全（frozen=True）
- **IDE補完** が効く

### Node（処理単位）

DAGワークフローのノードは `tuple[Contract, Outcome]` を返します：

```python
@node
def check_host(ctx: AlertContext) -> tuple[AlertContext, Outcome]:
    """ホスト情報を取得するノード"""
    hostname = lookup_hostname(ctx.incident_id)
    if hostname:
        new_ctx = ctx.model_copy(update={"hostname": hostname})
        return new_ctx, Outcome.success("found")
    return ctx, Outcome.failure("not_found")
```

### Exit（終了コード）

ワークフローの終了状態を表します：

```python
from railway.core.dag import Exit

TRANSITIONS = {
    "final_step::success::done": Exit.GREEN,    # 正常終了
    "final_step::failure::error": Exit.RED,     # エラー終了
    "warning_step::success::warn": Exit.YELLOW, # 警告終了
}
```

| Exit | 意味 | exit_code |
|------|------|-----------|
| `Exit.GREEN` | 正常終了 | `exit::green::done` |
| `Exit.YELLOW` | 警告終了 | `exit::yellow::warning` |
| `Exit.RED` | エラー終了 | `exit::red::error` |

---

## デバッグと監査

### on_step コールバック

各ステップ完了後にコールバックを受け取れます：

```python
from railway.core.dag import dag_runner, StepRecorder

recorder = StepRecorder()

result = dag_runner(
    start=check_severity,
    transitions=TRANSITIONS,
    on_step=recorder,
)

# 実行履歴を確認
for step in recorder.get_history():
    print(f"[{step.node_name}] -> {step.state}")
```

### AuditLogger

監査ログを出力：

```python
from railway.core.dag import AuditLogger

audit = AuditLogger(workflow_id="incident-123")

result = dag_runner(
    start=check_severity,
    transitions=TRANSITIONS,
    on_step=audit,
)
```

---

## バージョン管理

Railway Framework はプロジェクトのバージョン情報を追跡し、安全なアップグレードを支援します。

### なぜバージョン管理が必要か？

| 問題 | 影響 | Railway の解決策 |
|------|------|------------------|
| バージョン不明 | チームで不整合発生 | `.railway/project.yaml` で明示 |
| テンプレート変更 | `railway new` で不整合 | 互換性チェック + 警告 |
| 手動マイグレーション | 面倒、ミスしやすい | `railway update` で自動化 |

### プロジェクトメタデータ

`railway init` 実行時に自動生成:

```yaml
# .railway/project.yaml
railway:
  version: "0.10.0"              # 生成時のrailway-frameworkバージョン
  created_at: "2026-01-23T10:30:00+09:00"
  updated_at: "2026-01-23T10:30:00+09:00"

project:
  name: "my_automation"

compatibility:
  min_version: "0.10.0"          # 必要な最小バージョン
```

**設計判断:**

| 判断 | 理由 |
|------|------|
| YAML形式 | 人間が読みやすく、手動編集も可能 |
| `.railway/` ディレクトリ | フレームワーク関連ファイルを集約 |
| Git管理対象 | チーム全員でバージョン情報を共有 |

### バージョン互換性ルール

| 条件 | 動作 |
|------|------|
| 同一バージョン | そのまま実行 |
| マイナー差異 | 警告 + 確認 |
| メジャー差異 | エラー + 拒否 |
| バージョン不明 | 警告 + 確認 |

---

## テストの書き方

**DAGノードはテストが簡単:**

```python
from contracts.alert import AlertContext
from nodes.check_severity import check_severity
from railway.core.dag import Outcome

def test_check_severity_critical():
    # Arrange
    ctx = AlertContext(incident_id="INC-001", severity="critical")

    # Act
    result_ctx, outcome = check_severity(ctx)

    # Assert
    assert outcome == Outcome.success("critical")
    assert result_ctx.severity == "critical"
```

```bash
# テスト実行
pytest -v
pytest --cov=src --cov-report=html
```

---

## 実例: アラート処理ワークフロー

### ステップ1: Contractを定義

```python
# src/contracts/alert.py
from railway import Contract

class AlertContext(Contract):
    incident_id: str
    severity: str
    escalated: bool = False
```

### ステップ2: ノードを作成

```python
# src/nodes/alert/check_severity.py
from railway import node
from railway.core.dag import Outcome
from contracts.alert import AlertContext

@node
def check_severity(ctx: AlertContext) -> tuple[AlertContext, Outcome]:
    if ctx.severity == "critical":
        return ctx, Outcome.success("critical")
    return ctx, Outcome.success("normal")
```

### ステップ3: 遷移グラフを定義

```yaml
# transition_graphs/alert_workflow.yml
version: "1.0"
entrypoint: alert_workflow

nodes:
  check_severity:
    module: nodes.alert.check_severity
    function: check_severity
  escalate:
    module: nodes.alert.escalate
    function: escalate
  log_only:
    module: nodes.alert.log_only
    function: log_only

start: check_severity

transitions:
  check_severity:
    success::critical: escalate
    success::normal: log_only
  escalate:
    success::done: exit::success
  log_only:
    success::done: exit::success
```

### ステップ4: コード生成と実行

```bash
railway sync transition --entry alert_workflow
railway run alert_workflow
```

---

## ドキュメント

- [TUTORIAL.md](TUTORIAL.md) - ハンズオンチュートリアル
- [readme_linear.md](readme_linear.md) - 線形パイプライン詳細
- [docs/adr/](docs/adr/) - 設計決定記録

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

### Phase 2 ✅ 完了（バージョン管理 & DAGワークフロー）
- ✅ プロジェクトバージョン記録（`.railway/project.yaml`）
- ✅ バージョン互換性チェック（`railway new` 実行時）
- ✅ `railway update` コマンド（プロジェクトマイグレーション）
- ✅ `railway backup` コマンド（バックアップ・ロールバック）
- ✅ DAGワークフロー（`dag_runner`、条件分岐対応）
- ✅ Outcomeクラス & 遷移グラフ
- ✅ `railway sync transition` コマンド

### Phase 3 📋 計画中
- 🔜 並列パイプライン実行
- 🔜 WebUI
- 🔜 メトリクス収集

---

## ライセンス

MIT License

---

**Railway Framework で型安全な運用自動化を始めましょう！**

```bash
railway init my_workflow
cd my_workflow
railway new entry my_workflow
railway sync transition --entry my_workflow
railway run my_workflow
```
