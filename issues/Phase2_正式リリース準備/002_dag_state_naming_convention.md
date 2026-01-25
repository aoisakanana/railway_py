# DAGノード状態の命名規則標準化

## ステータス

- **優先度**: High (★★★★☆)
- **対象バージョン**: v0.10.2
- **種別**: 設計決定 / 機能追加
- **関連Issue**: 001_dag_pipeline_native_support.md

## 背景

### 事例での現状実装

事例１では、ノード状態を以下のように定義している：

```python
class NodeState(str, Enum):
    # 成功状態
    SUCCESS_GET_ALERT = "success::get_alert"
    SUCCESS_SESSION_EXIST = "success::session::exist"
    SUCCESS_CTIME_LESSTHAN = "success::ctime::lessthan"

    # 失敗状態
    FAILURE_HTTP = "failure::http"
    FAILURE_SSH = "failure::ssh"
    FAILURE_DATA_FORMAT = "failure::data::format"

class ExitCode(str, Enum):
    GREEN_1 = "exit::green::1"  # ACTIVEタイムアウト
    GREEN_2 = "exit::green::2"  # CTIME <= 5400
    RED_1 = "exit::red::1"      # 異常終了
```

### 現状の問題点

1. **命名規則の不一致**
   - 階層の深さがバラバラ（`success::get_alert` vs `success::session::exist`）
   - セパレータの使い方が曖昧

2. **ノードとの関連が暗黙的**
   - `FAILURE_HTTP` がどのノードで発生するか不明
   - 同じ失敗原因が複数ノードで発生する場合に区別できない

3. **状態の網羅性チェックが困難**
   - あるノードが返しうる状態の一覧が分散している
   - 遷移マップの完全性を検証しづらい

4. **終了コードの意味が不透明**
   - `GREEN_1`, `GREEN_2` の違いがコメントに依存
   - 番号の意味が自明でない

## 提案: 命名規則の標準化案

### 案1: 階層型命名規則（推奨）

```
{node_name}::{outcome}::{detail}
```

| 要素 | 説明 | 例 |
|------|------|-----|
| `node_name` | ノード関数名（スネークケース） | `fetch_alert`, `check_session` |
| `outcome` | 結果種別 | `success`, `failure` |
| `detail` | 詳細状態 | `found`, `not_found`, `timeout`, `http_error` |

**例**:
```python
class NodeState(str, Enum):
    # fetch_alert ノード
    FETCH_ALERT_SUCCESS = "fetch_alert::success::done"
    FETCH_ALERT_FAILURE_HTTP = "fetch_alert::failure::http_error"
    FETCH_ALERT_FAILURE_API = "fetch_alert::failure::api_error"

    # check_session ノード
    CHECK_SESSION_SUCCESS_EXIST = "check_session::success::exist"
    CHECK_SESSION_SUCCESS_NOT_EXIST = "check_session::success::not_exist"
    CHECK_SESSION_FAILURE_SSH = "check_session::failure::ssh_error"
    CHECK_SESSION_FAILURE_SQL = "check_session::failure::sql_error"
```

**メリット**:
- ノードとの対応が明確
- grep/検索しやすい
- 状態の網羅性をノード単位でチェック可能

**デメリット**:
- 名前が長くなる
- 同じ失敗原因でも各ノードで別定義が必要

---

### 案2: ノードスコープ型（Enum per Node）

各ノードごとに専用のEnumを定義：

```python
from railway import NodeOutcome

class FetchAlertOutcome(NodeOutcome):
    SUCCESS = "success"
    FAILURE_HTTP = "failure::http"
    FAILURE_API = "failure::api"

class CheckSessionOutcome(NodeOutcome):
    SUCCESS_EXIST = "success::exist"
    SUCCESS_NOT_EXIST = "success::not_exist"
    FAILURE_SSH = "failure::ssh"
    FAILURE_SQL = "failure::sql"

@dag_node(outcome=FetchAlertOutcome)
def fetch_alert(ctx: WorkflowContext) -> tuple[WorkflowContext, FetchAlertOutcome]:
    ...
    return ctx, FetchAlertOutcome.SUCCESS
```

**メリット**:
- 型安全性が高い（ノードごとに返せる状態が制限される）
- IDEの補完が効く
- 状態の網羅性をmypyでチェック可能

**デメリット**:
- クラス数が増える
- 遷移マップの定義が複雑になる可能性

---

### 案3: ビルダー/ファクトリーパターン

フレームワークが状態生成ヘルパーを提供：

```python
from railway import StateBuilder

# ワークフロー全体の状態を一括定義
states = StateBuilder("session_workflow")

# ノードごとに状態を登録
states.node("fetch_alert").success("done").failure("http", "api", "timeout")
states.node("check_session").success("exist", "not_exist").failure("ssh", "sql")
states.node("kill_session").success("killed").failure("permission", "not_found")

# 終了コードも同様に定義
states.exit("normal_complete", color="green", description="正常終了")
states.exit("timeout_exit", color="green", description="タイムアウトによる正常終了")
states.exit("error", color="red", description="異常終了")

# Enumを自動生成
NodeState = states.build_state_enum()
ExitCode = states.build_exit_enum()
```

**生成される値**:
```python
NodeState.FETCH_ALERT_SUCCESS_DONE       # "fetch_alert::success::done"
NodeState.FETCH_ALERT_FAILURE_HTTP       # "fetch_alert::failure::http"
NodeState.CHECK_SESSION_SUCCESS_EXIST    # "check_session::success::exist"
ExitCode.NORMAL_COMPLETE                 # "exit::green::normal_complete"
```

**メリット**:
- DRY（重複が少ない）
- 一箇所で全状態を俯瞰できる
- 検証機能を組み込みやすい

**デメリット**:
- 動的生成のため、IDEの静的解析が効きにくい
- デバッグが難しい可能性

---

### 案4: デコレータによる自動抽出

ノード関数の戻り値型から状態を自動抽出：

```python
from railway import dag_node, Success, Failure

@dag_node
def fetch_alert(ctx: WorkflowContext) -> WorkflowContext:
    try:
        alert = api.get_alert(ctx.incident_id)
        return ctx.with_state(Success.DONE)
    except HTTPError:
        return ctx.with_state(Failure.HTTP)
    except APIError:
        return ctx.with_state(Failure.API)

@dag_node
def check_session(ctx: WorkflowContext) -> WorkflowContext:
    session = db.query_session(ctx.session_id)
    if session:
        return ctx.with_state(Success.EXIST)
    else:
        return ctx.with_state(Success.NOT_EXIST)
```

フレームワークがAST解析またはランタイム検査で状態を収集し、遷移マップの検証に使用。

**メリット**:
- ボイラープレートが最小
- コードが自然に読める

**デメリット**:
- 実装が複雑
- 静的解析の限界（動的に状態を決定する場合など）

---

### 案5: 終了コードの意味的命名

終了コードについては、番号ではなく意味的な名前を推奨：

```python
class ExitCode(str, Enum):
    # Before (現状)
    GREEN_1 = "exit::green::1"
    GREEN_2 = "exit::green::2"

    # After (推奨)
    SUCCESS_RESOLVED = "exit::success::resolved"
    SUCCESS_TIMEOUT_NORMAL = "exit::success::timeout_normal"
    SUCCESS_CTIME_WITHIN_LIMIT = "exit::success::ctime_within_limit"
    FAILURE_UNHANDLED = "exit::failure::unhandled"
    FAILURE_MAX_RETRIES = "exit::failure::max_retries"
```

## 推奨案

**フェーズ1（v0.10.2）**: 案1（階層型命名規則）+ 案5（終了コードの意味的命名）

- 最も保守的で導入しやすい
- ドキュメントとベストプラクティスとして提供
- 強制ではなくガイダンスとして

**フェーズ2（将来）**: 案2（NodeOutcome基底クラス）の提供

- 型安全性を向上させたいユーザー向けのオプション
- 案1との互換性を維持

## Railway Frameworkが提供すべきもの

### 1. 基底クラス/型

```python
# railway/core/dag.py

from enum import Enum
from typing import Protocol

class NodeOutcome(str, Enum):
    """ノード状態の基底クラス（オプション）"""
    pass

class ExitOutcome(str, Enum):
    """終了コードの基底クラス（オプション）"""
    pass
```

### 2. 命名規則バリデータ

```python
# railway/core/dag.py

def validate_state_naming(state: str) -> bool:
    """
    推奨命名規則に従っているかチェック

    推奨形式: {node_name}::{outcome}::{detail}
    """
    parts = state.split("::")
    if len(parts) < 2:
        return False
    outcome = parts[-2] if len(parts) >= 2 else parts[0]
    return outcome in ("success", "failure", "exit")

def validate_transition_map(
    transitions: dict,
    nodes: list[Callable],
    states: type[Enum],
) -> list[str]:
    """
    遷移マップの整合性をチェック

    Returns:
        警告メッセージのリスト
    """
    warnings = []
    # 未定義の状態への遷移がないかチェック
    # 到達不能なノードがないかチェック
    # すべての状態に遷移先が定義されているかチェック
    return warnings
```

### 3. ドキュメント/テンプレート

```python
# railway new で生成されるテンプレートに含める

"""
# 状態命名規則ガイド

## 推奨形式
{node_name}::{outcome}::{detail}

## 例
- fetch_data::success::done
- fetch_data::failure::http_error
- validate_input::success::valid
- validate_input::failure::invalid_format

## 終了コード
- exit::success::{reason}
- exit::failure::{reason}
"""
```

## 次のアクション

1. [ ] 案1〜5の比較表作成
2. [ ] 事例１を案1で書き直した場合のサンプル作成
3. [ ] `NodeOutcome` 基底クラスの設計
4. [ ] バリデータの実装
5. [ ] ドキュメント/ガイドライン作成
