# Railway Framework for Python  

railway oliented programming を python で実践するための実装  
運用高度化案件はDAGに落とし込めることが多い。  
さしあたっては運用高度化の現場で使っていくことを考えたい(単にテーマとして都合がいいだけなので、DAGっぽい処理では使えると思います)  

**型安全なワークフローで、運用自動化をシンプルに。**  

条件分岐を含む複雑なワークフローをYAMLで宣言的に定義できます。

### Board モード（v0.14.0+ 推奨 / Riverboard パターン）

```python
# Board モード: ミュータブルな共有状態で直感的に記述
from railway.core.board import BoardBase, WorkflowResult
from railway.core.dag import dag_runner, Outcome
from railway import node

@node
def check_severity(board) -> Outcome:
    if board.severity == "critical":
        board.escalated = True
        return Outcome.success("critical")
    return Outcome.success("normal")

@node
def escalate(board) -> Outcome:
    board.notified = True
    return Outcome.success("done")

# 終端ノード
def exit_done(board) -> None:
    board.completed = True
exit_done._node_name = "exit.success.done"

result = dag_runner(
    start=check_severity,
    transitions={
        "check_severity::success::critical": escalate,
        "check_severity::success::normal": exit_done,
        "escalate::success::done": exit_done,
    },
    board=BoardBase(severity="critical"),
)
# result は WorkflowResult: is_success, exit_code, exit_state, board を持つ
```

<details>
<summary>Contract モード（従来方式 / イミュータブル）</summary>

```python
# Contract モード: イミュータブルな型安全ワークフロー
from railway import Contract, ExitContract, node, entry_point
from railway.core.dag import dag_runner, Outcome

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

# 終端ノード: ExitContract を返す（v0.12.3+）
class AlertResult(ExitContract):
    exit_state: str = "success.done"
    handled: bool

def exit_success_done(ctx: AlertContext) -> AlertResult:
    return AlertResult(handled=ctx.handled)

exit_success_done._node_name = "exit.success.done"

TRANSITIONS = {
    "check_severity::success::critical": escalate,
    "check_severity::success::normal": log_only,
    "escalate::success::done": exit_success_done,
    "log_only::success::done": exit_success_done,
}

@entry_point
def main():
    result = dag_runner(
        start=lambda: (AlertContext(severity="critical"), Outcome.success("start")),
        transitions=TRANSITIONS,
    )
    # result は ExitContract: exit_code, exit_state, is_success 等を持つ
    return result
```

</details>

**特徴:**
- DAGワークフロー: 条件分岐を含むワークフローをYAMLで定義
- Board モード: ミュータブルな共有状態で直感的に記述（v0.14.0+ / Riverboard パターン）
- 型安全: Contract + Outcome による静的型チェック（Contract モード）
- AST依存解析: Board モードではフィールド依存を自動検出
- コード生成: YAMLから遷移コードを自動生成
- バージョン管理: プロジェクトバージョン追跡、自動マイグレーション  

> **設計思想を理解したい方へ**: [アーキテクチャガイド](docs/ARCHITECTURE.md) で 3 つのコンポーネントと 5 つの設計思想を解説しています。  

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)  
[![Test Coverage](https://img.shields.io/badge/coverage-90%25+-brightgreen.svg)]()  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)  
[![Tests](https://img.shields.io/badge/tests-2025%20passing-success.svg)]()  

---  

## クイックスタート  

### 1. インストール  

```bash  
# uvをインストール（未インストールの場合）  
curl -LsSf https://astral.sh/uv/install.sh | sh  

# railway コマンドをインストール  
uv tool install railway-framework  
```  

### 2. プロジェクト作成 → エントリーポイント作成 → 実行  

**v0.13.1+**: 3 コマンドで動作するワークフローが完成します。    
その後はノードに集中できます。    

```bash  
railway init my_workflow && cd my_workflow  
uv sync  
railway new entry my_workflow  # 自動的に sync も実行される  
railway run my_workflow        # すぐに実行可能！  
```  

これにより以下が自動生成されます：  
- `src/my_workflow.py` - エントリーポイント（すぐに実行可能）  
- `src/nodes/my_workflow/start.py` - 開始ノード  
- `src/nodes/exit/success/done.py` - 正常終了ノード  
- `src/nodes/exit/failure/error.py` - エラー終了ノード  
- `transition_graphs/my_workflow_*.yml` - 遷移グラフ  
- `_railway/generated/my_workflow_transitions.py` - 遷移コード  

### 3. 遷移グラフをカスタマイズ（オプション）  

`transition_graphs/my_workflow_*.yml` を編集してワークフローを拡張できます：  

```yaml  
version: "1.0"  
entrypoint: my_workflow  
description: "my_workflow ワークフロー"  

nodes:  
  start:  
    module: nodes.my_workflow.start  
    function: start  
    description: "開始ノード"  

  process:  
    description: "処理ノード"  # → nodes.my_workflow.process に自動解決  

  # 終端ノードは nodes.exit 配下に定義  
  exit:  
    success:  
      done:  
        description: "正常終了"  
    failure:  
      error:  
        description: "エラー終了"  

start: start  

transitions:  
  start:  
    success::done: process  
    failure::error: exit.failure.error  
  process:  
    success::complete: exit.success.done  
    failure::error: exit.failure.error  

options:  
  max_iterations: 100  
```  

編集後は再度同期：  

```bash  
railway sync transition --entry my_workflow  
```  

---  

## ノードの実装

### Board モード（v0.14.0+ 推奨）

ノードは `board` を受け取り、`Outcome` のみを返します。状態は board に直接書き込みます：

```python
from railway import node
from railway.core.dag import Outcome


@node
def process(board) -> Outcome:
    if board.value:
        board.processed = True
        return Outcome.success("done")
    else:
        return Outcome.failure("empty")
```

### Contract モード（従来方式）

ノードは `Contract` と `Outcome` のタプルを返す純粋関数です：

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

| 手動作成 | `railway new node` |
|----------|-------------------|
| ノード、テストを個別に作成 | **2ファイル同時生成** |
| import文を自分で書く | **正しいimport済み** |
| テスト構造を考える | **TDDテンプレート付き** |
| Outcomeの使い方を調べる | **動作するサンプル付き** |  

```bash
# dag 形式（デフォルト / Board モード）: 条件分岐ワークフロー向け
railway new node check_status
# → src/nodes/check_status.py        ← ノード本体（Board モード）
# → tests/nodes/test_check_status.py  ← TDDテンプレート

# 階層ノード（v0.13.18+）: ドット区切りでサブディレクトリに生成
railway new node processing.validate
# → src/nodes/processing/validate.py        ← 関数名: validate
# → tests/nodes/processing/test_validate.py

```

**命名規則（v0.13.18+）:**

| 入力 | 結果 |
|------|------|
| `check_status` | フラットなノード作成 |
| `processing.validate` | `src/nodes/processing/validate.py` に階層作成 |
| `my-node` | エラー（ハイフン不可、`my_node` を提案） |
| `import` | エラー（Python予約語） |
| `greeting/farewell` | エラー（スラッシュ不可、`greeting.farewell` を提案） |  

**dag 形式（デフォルト / Board モード）** - 条件分岐が可能:

```python
from railway import node
from railway.core.dag.outcome import Outcome


@node
def check_status(board) -> Outcome:
    """ステータスをチェックする。"""
    if board.is_valid:
        return Outcome.success("valid")   # → valid 遷移
    return Outcome.failure("invalid")     # → invalid 遷移
```

Board モードでは Contract の定義が不要で、board に直接読み書きするだけです。
依存関係は AST 解析で自動検出されるため、手動宣言も必要ありません。

<details>
<summary>Contract モード（従来方式）</summary>

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

</details>

### 使い分け

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
| typed_pipeline | 線形パイプライン | Python コードから直接使用 |

dag_runner は **Board モード**（v0.14.0+）と **Contract モード** の2つのスタイルをサポートします。

| スタイル | 状態管理 | ノード返り値 | 依存解析 |
|----------|----------|-------------|----------|
| **Board モード**（推奨） | ミュータブル共有状態 | `Outcome` のみ | AST自動検出 |
| Contract モード | イミュータブル | `tuple[Contract, Outcome]` | `@node` デコレータで宣言 |

### どちらを使うべきか？

**dag_runner を使う:**
- 条件分岐がある（if-else, switch）
- エラーパスが複数ある
- 運用自動化、複雑なワークフロー

**typed_pipeline を使う:**
- 処理が必ず順番に実行される（A→B→C→D）
- 条件分岐がない
- ETL、データ変換パイプライン

### dag_runner - Board モード（v0.14.0+ 推奨）

`BoardBase` をミュータブルな共有状態として使用します。ノードは `Outcome` のみを返し、状態は board に直接書き込みます：

```python
from railway.core.board import BoardBase, WorkflowResult
from railway.core.dag import dag_runner, Outcome
from railway import node

@node
def check_severity(board) -> Outcome:
    if board.severity == "critical":
        board.escalated = True
        return Outcome.success("critical")
    return Outcome.success("normal")

# 終端ノード: None を返す（board に書き込むだけ）
def exit_done(board) -> None:
    board.completed = True
exit_done._node_name = "exit.success.done"

result = dag_runner(
    start=check_severity,
    transitions=TRANSITIONS,
    board=BoardBase(severity="critical"),
)

# result は WorkflowResult: is_success, exit_code, exit_state, board を持つ
if result.is_success:
    print(f"完了: board.escalated={result.board.escalated}")
```

**Board モードの特徴:**
- ミュータブル状態: `model_copy()` 不要、board に直接書き込み
- AST依存解析: フィールドの読み書きをASTで自動検出（手動宣言不要）
- トレース: `railway run --trace` でノードごとの変更を可視化
- WorkflowResult: 実行結果 + board への参照を保持

### dag_runner - Contract モード（従来方式）

イミュータブルな Contract で型安全にデータを扱います：

```python
from railway import ExitContract
from railway.core.dag import dag_runner, Outcome

# 終端ノードを定義（v0.12.3+: ExitContract を返す）
class DoneResult(ExitContract):
    exit_state: str = "success.done"

def exit_success_done(ctx) -> DoneResult:
    return DoneResult()

exit_success_done._node_name = "exit.success.done"

TRANSITIONS = {
    "check::success::critical": escalate,
    "check::success::normal": log_only,
    "escalate::success::done": exit_success_done,
    "log_only::success::done": exit_success_done,
}

result = dag_runner(
    start=check_severity,
    transitions=TRANSITIONS,
)

# result は ExitContract: is_success, exit_code, exit_state を持つ
if result.is_success:
    print("Workflow completed successfully")
```

**dag_runner の特徴:**
- 条件分岐: Outcome に応じて遷移先を決定
- YAML定義: 遷移グラフをYAMLで宣言的に定義
- コード生成: `railway sync transition` で遷移コードを自動生成
- ステップコールバック: `on_step` で各ステップを監視

### async_dag_runner（非同期版）

`async_dag_runner` は `dag_runner` の非同期版です。async/await 対応のノードを実行できます：

```python
import asyncio
from railway.core.dag import async_dag_runner, Outcome

@node
async def fetch_data(ctx: MyContext) -> tuple[MyContext, Outcome]:
    result = await external_api.fetch(ctx.resource_id)
    return ctx.model_copy(update={"data": result}), Outcome.success("done")

result = asyncio.run(
    async_dag_runner(
        start=fetch_data_start,
        transitions=TRANSITIONS,
    )
)
```

**API は `dag_runner` と同一です。** async ノードと sync ノードを混在させることもできます。
codegen が生成する `run_async()` ヘルパーは内部で `async_dag_runner` を使用しています。

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
railway docs                     # README をターミナルに表示  
railway docs --browser           # ブラウザでドキュメントを開く  
```  

### 遷移グラフ管理  
```bash  
railway sync transition --entry <name>  # 遷移コード生成（デフォルトで上書き）  
railway sync transition --all           # 全遷移コード生成  
railway sync transition --entry <name> --no-overwrite  # 既存ファイルをスキップ  
railway sync transition --entry <name> --convert       # 旧形式YAMLを新形式に変換
railway sync transition --entry <name> --convert --dry-run  # 変換プレビュー（変換後データで検証）
railway sync transition --entry <name> --dry-run       # プレビューのみ
```

#### 旧形式 YAML の変換

v0.11.x〜v0.13.x の `exits` セクションを使用している YAML を新形式に変換できます:

```bash
# プレビュー（変更なし）
railway sync transition --entry my_workflow --convert --dry-run

# 変換実行
railway sync transition --entry my_workflow --convert
```

**対応する旧形式:**

| 形式 | 例 | 対応 |
|------|-----|------|
| v0.11.x フラット | `exits: { green_success: { code: 0 } }` | v0.13.3+ |
| v0.12.x ネスト | `exits: { success: { done: { ... } } }` | **v0.13.11rc1+** |

変換は安全に行われます:
- 変換前にファイルの内容をバックアップ
- 変換後にスキーマ検証を実施
- 検証失敗時は自動的にロールバック

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
railway new node sub.deep.process            # 階層ノード作成（v0.13.18+）
railway new node <name> --output ResultType  # 出力型指定
railway new node <name> --input data:InputType --output ResultType
railway show node <name>                     # 依存関係表示
```  

### 実行
```bash
railway run <entry>              # 実行
railway run <entry> --trace      # 実行（ノードごとの変更をトレース表示）
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
- 🎛️ **Board モード**: ミュータブル共有状態で直感的に記述（v0.14.0+ / Riverboard パターン）
- 🔒 **型安全**: Contract + Outcome による静的型チェック（Contract モード）
- 🔍 **AST依存解析**: Board モードではフィールド依存をASTで自動検出
- ⚡ **コード生成**: YAMLから遷移コードを自動生成
- 🔄 **2つの実行モデル**: dag_runner（条件分岐）と typed_pipeline（線形）
- 🔗 **フィールドベース依存関係**: ノードコードで依存を宣言、sync時に自動検証
- 🧪 **テスト容易**: モック不要、引数を渡すだけ
- 📊 **実行トレース**: `railway run --trace` でノードごとの変更を可視化
- ⚙️ **環境別設定**: development/production を簡単に切り替え
- 🆙 **バージョン管理**: プロジェクトバージョン追跡、自動マイグレーション  

---  

## アーキテクチャ

### BoardBase（ミュータブル共有状態 / v0.14.0+）

Board モードでは `BoardBase` がワークフロー全体の共有状態を保持します。
Pydantic ベースではなく、ミュータブルなオブジェクトとして設計されています。

```python
from railway.core.board import BoardBase

# 初期状態を設定して board を作成
board = BoardBase(
    severity="critical",
    incident_id="INC-001",
)

# ノードから直接読み書き可能
board.escalated = True
board.hostname = "web-01"
```

**BoardBase の特徴:**

| 項目 | 説明 |
|------|------|
| ミュータブル | `model_copy()` 不要、直接書き込み |
| AST依存解析 | `board.x` の読み書きを自動検出 |
| トレース対応 | `--trace` でノードごとの変更差分を表示 |

### WorkflowResult（Board モード実行結果）

Board モードの `dag_runner()` は `WorkflowResult`（frozen dataclass）を返します：

```python
result = dag_runner(start=..., transitions=..., board=board)

result.is_success      # True if exit_code == 0
result.exit_code       # 0 (success.*) or 1 (failure.*)
result.exit_state      # "success.done", "failure.timeout" など
result.board           # 実行後の BoardBase（全ノードの変更を反映）
result.execution_path  # ("start", "process", "exit.success.done")
result.iterations      # 実行したノード数
```

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

**Board モード（v0.14.0+）:** ノードは `board` を受け取り `Outcome` を返します：

```python
@node
def check_host(board) -> Outcome:
    """ホスト情報を取得するノード"""
    hostname = lookup_hostname(board.incident_id)
    if hostname:
        board.hostname = hostname  # 直接書き込み
        return Outcome.success("found")
    return Outcome.failure("not_found")
```

**Contract モード:** ノードは `tuple[Contract, Outcome]` を返します：

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

**状態の引き継ぎ:**

| モード | 方式 |
|--------|------|
| Board | board に直接書き込み。全ノードが同じ board を共有 |
| Contract | `model_copy()` で新しいコンテキストを生成して引き継ぎ |

詳細は [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) を参照。  

### フィールドベース依存関係

**Board モード（v0.14.0+）:** AST解析でフィールド依存を自動検出します。手動宣言は不要です：

```python
@node
def escalate(board) -> Outcome:
    # AST が board.hostname の読み取りと board.escalated の書き込みを自動検出
    if board.hostname:
        notify_with_host(board.hostname)
    board.escalated = True
    return Outcome.success("done")
```

**Contract モード:** `@node` デコレータで依存を宣言します：

```python
@node(
    requires=["incident_id"],      # 必須: なければ実行エラー
    optional=["hostname"],         # 任意: あれば使用
    provides=["escalated"],        # 提供: このノードが追加
)
def escalate(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
    if ctx.hostname:  # optional なので存在チェック
        notify_with_host(ctx.hostname)
    return ctx.model_copy(update={"escalated": True}), Outcome.success("done")
```

**YAML には依存情報を書かない:**

```yaml
# ノード名と遷移のみ
nodes:
  check_host:
    description: "ホスト情報取得"
  escalate:
    description: "エスカレーション"

transitions:
  check_host:
    success::found: escalate  # フレームワークが依存を自動検証
```

**利点:**
- Board モード: AST が `board.x` の読み書きを自動検出、手動宣言不要
- YAML 記述者はノード実装の詳細を知らなくてよい
- `railway sync transition` で依存エラーを自動検出
- YAML のみでフロー変更、ノードコード変更不要

詳細は [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#フィールドベース依存関係) を参照。  

### ExitContract（Contract モード実行結果）

Contract モードの `dag_runner()` は `ExitContract` を返します。終了状態とメタデータを含みます（Board モードでは `WorkflowResult` を使用）：  

```python  
from railway import ExitContract  

result = dag_runner(start=..., transitions=...)  

# 基本プロパティ  
result.is_success    # True if exit_code == 0  
result.is_failure    # True if exit_code != 0  
result.exit_code     # 0 (success.* ) or 1 (failure.*)  
result.exit_state    # "success.done", "failure.timeout" など  
result.context       # 終端ノードが返したコンテキスト  

# メタデータ  
result.execution_path  # ("start", "process", "exit.success.done")  
result.iterations      # 実行したノード数  
```  

| exit_state パターン | exit_code | is_success |  
|---------------------|-----------|------------|  
| `success.*` | 0 | `True` |  
| `failure.*`, その他 | 1 | `False` |  

### 終端ノード（Exit Node）  

ワークフロー終了時に処理を実行できます。通常のノードと同じ形式で記述できるため、  
コールバックの概念を知らなくても実装できます。  

**YAML定義:**  

```yaml  
nodes:  
  finalize:  
    description: "最終処理"  

  exit:  
    success:  
      done:  
        description: "正常終了（Slack通知）"  
      skipped:  
        description: "スキップして終了"  

    failure:  
      timeout:  
        description: "タイムアウト（PagerDuty通知）"  

transitions:  
  finalize:  
    success::complete: exit.success.done  
    success::skipped: exit.success.skipped  
    failure::timeout: exit.failure.timeout  
```  

**実装例（v0.12.3+）:**  

```python  
# src/nodes/exit/success/done.py - ExitContract サブクラスを返す  
from railway import ExitContract, node  

class DoneResult(ExitContract):  
    """正常終了時の詳細結果。"""  
    status: str  
    processed_count: int  
    exit_state: str = "success.done"  

@node(name="exit.success.done")  
def done(ctx: WorkflowContext) -> DoneResult:  
    """終端ノードは ExitContract を返す（Outcome 不要）。"""  
    send_slack_notification(f"処理完了: {ctx.count}件")  
    return DoneResult(  
        status="completed",  
        processed_count=ctx.count,  
    )  
```  

**特徴:**  

| 項目 | 説明 |  
|------|------|  
| 型安全性 | ExitContract で戻り値の型が保証される |  
| IDE補完 | カスタムフィールドに補完が効く |  
| 一貫性 | 通常のノードと同じ書き方 |  
| テスト可能性 | 純粋関数としてテスト可能 |  
| 表現力 | 詳細な終了状態を表現（done, skipped, timeout など） |  
| 自動解決 | module/function は省略可能 |  

詳細は [docs/transition_graph_reference.md](docs/transition_graph_reference.md) を参照。  

---  

## エラーコード  

Railway Framework は分かりやすいエラーメッセージとヒントを提供します。  

| コード | 説明 | 発生箇所 |  
|--------|------|----------|  
| E001 | 開始ノードの引数エラー | dag_runner |  
| E002 | モジュールが見つかりません | sync transition |  
| E003 | 無効な識別子 | sync transition |  
| E004 | 終端ノードの戻り値エラー | dag_runner |  

**エラーメッセージの例:**  

```  
Error [E001]: 開始ノードの引数エラー  

開始ノード 'start' は引数を受け取る必要があります。  

Hint:  
  def start(ctx: Context | None = None) -> tuple[Context, Outcome]:  

詳細: https://github.com/aoisakanana/railway-framework/docs/errors/E001  
```  

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

### バージョン管理の必要性    

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

## 既存プロジェクトのアップグレード  

v0.10.x 以前のプロジェクトを最新形式にアップグレードできます。  

### アップグレードの必要性  

| 旧形式の問題 | v0.11.3 での解決策 |  
|-------------|-------------------|  
| 条件分岐が書きにくい | **dag_runner** で宣言的に定義 |  
| ノードの戻り値が不明確 | **Outcome** で状態を明示 |  
| 遷移ロジックがコードに埋まる | **YAML** で可視化 |  

### アップグレード手順  

**1. プレビュー**（変更内容を確認）  

```bash  
railway update --dry-run  
```  

出力例:  
```  
マイグレーション: 0.10.0 → 0.12.0  

ファイル追加:  
  - transition_graphs/.gitkeep  
  - _railway/generated/.gitkeep  

コードガイダンス:  
  src/nodes/process.py:5  
    現在: def process(data: dict) -> dict:  
    推奨: def process(ctx: ProcessContext) -> tuple[ProcessContext, Outcome]:  
```  

**2. アップグレード実行**  

```bash  
railway update  
```  

**3. ガイダンスに従ってコードを修正**  

旧形式のノードを新形式に変更します:  

**Before:**  
```python  
@node  
def process(data: dict) -> dict:  
    return data  
```  

**After:**  
```python  
@node  
def process(ctx: ProcessContext) -> tuple[ProcessContext, Outcome]:  
    return ctx, Outcome.success("done")  
```  

### 検出される旧形式パターン  

| パターン | 推奨変更 |  
|----------|----------|  
| `def node(data: dict) -> dict:` | `def node(ctx: Context) -> tuple[Context, Outcome]:` |  
| `from railway import pipeline` | `from railway.core.dag import dag_runner` |  

### アップグレードの恩恵  

- **Outcome** で次の遷移先を制御できる  
- **Contract** で型安全にデータを扱える  
- **YAML** で遷移ロジックを可視化できる  

---  

## テストの書き方

**Board モード（v0.14.0+）:**

```python
from railway.core.board import BoardBase
from railway.core.dag import Outcome
from nodes.check_severity import check_severity

def test_check_severity_critical():
    # Arrange
    board = BoardBase(severity="critical")

    # Act
    outcome = check_severity(board)

    # Assert
    assert outcome == Outcome.success("critical")
    assert board.escalated is True
```

**Contract モード:**

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

### テストの配置

| テストタイプ | 配置先 | 生成コマンド |
|-------------|--------|-------------|
| エントリポイントテスト | `tests/test_{entry}.py` | `railway new entry` |
| ノードテスト | `tests/nodes/test_{node}.py` | `railway new node` |

```
tests/
├── __init__.py
├── test_my_workflow.py       # エントリポイントテスト
└── nodes/
    ├── __init__.py
    └── test_check_status.py  # ノードテスト
```

---

## 実例: アラート処理ワークフロー

### ステップ1: ノードを作成

Board モードでは Contract の定義は不要です。ノードは board に直接読み書きし、`Outcome` のみを返します：

```python
# src/nodes/alert/check_severity.py
from railway import node
from railway.core.dag import Outcome

@node
def check_severity(board) -> Outcome:
    if board.severity == "critical":
        board.escalated = True
        return Outcome.success("critical")
    return Outcome.success("normal")
```

```python
# src/nodes/alert/escalate.py
from railway import node
from railway.core.dag import Outcome

@node
def escalate(board) -> Outcome:
    board.notified = True
    return Outcome.success("done")
```

### ステップ2: 遷移グラフを定義

```yaml
# transition_graphs/alert_workflow.yml
version: "1.0"
entrypoint: alert_workflow

nodes:
  check_severity:
    description: "重要度をチェック"
  escalate:
    description: "エスカレーション"
  log_only:
    description: "ログ出力のみ"

  exit:
    success:
      done:
        description: "正常終了"
    failure:
      error:
        description: "エラー終了"

start: check_severity

transitions:
  check_severity:
    success::critical: escalate
    success::normal: log_only
  escalate:
    success::done: exit.success.done
  log_only:
    success::done: exit.success.done
```

### ステップ3: コード生成と実行

```bash
railway sync transition --entry alert_workflow
railway run alert_workflow
```

<details>
<summary>Contract モード（従来方式）での実装例</summary>

### ステップ1: Contract を定義

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

### ステップ3: 遷移グラフを定義（同上）

### ステップ4: コード生成と実行

```bash
railway sync transition --entry alert_workflow
railway run alert_workflow
```

</details>  

---  

## ドキュメント  

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - **アーキテクチャガイド（全体像）**  
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

### Phase 3 ✅ 完了（Board モード / Riverboard パターン）
- ✅ `BoardBase` ミュータブル共有状態（Pydantic 非依存）
- ✅ `WorkflowResult`（frozen dataclass）による実行結果
- ✅ AST依存解析（`board.x` の読み書きを自動検出）
- ✅ `railway run --trace`（ノードごとの変更トレース）
- ✅ Board モード対応の dag_runner / async_dag_runner
- ✅ Contract モードとの後方互換性維持

### Phase 4 ✅ 完了
- ✅ DAG YAMLのビジュアライザ統合
- ✅ 並列パイプライン実行    

---  

## ライセンス  

MIT License  

---  

**Railway Framework で型安全な運用自動化を始めましょう！**  

```bash  
railway init my_workflow  
cd my_workflow  
railway new entry my_workflow  # sync も自動実行  
railway run my_workflow  
```  
