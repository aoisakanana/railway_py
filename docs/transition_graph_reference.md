# Transition Graph リファレンス

Railway Framework の遷移グラフ YAML の詳細仕様。

---

## 基本構造

```yaml
version: "1.0"
entrypoint: my_workflow
description: "ワークフローの説明"

nodes:
  # 通常のノード
  start:
    module: nodes.start
    function: start
    description: "開始ノード"

  # 終端ノード
  exit:
    success:
      done:
        description: "正常終了"

# 開始ノード
start: start

# 遷移定義
transitions:
  start:
    success::done: exit.success.done
```

---

## nodes セクション

**重要:** 依存情報（requires/optional/provides）は YAML に記述しません。
ノードの Python コードで `@node` デコレータに宣言します。

```yaml
# ✅ 正しい: 遷移のみ
nodes:
  check_host:
    description: "ホスト情報を取得"

# ❌ 不要: 依存情報は書かない
nodes:
  check_host:
    requires: [incident_id]  # ← これは書かない！
    provides: [hostname]      # ← これも書かない！
```

依存情報はノードコードに記述:

```python
# nodes/check_host.py
@node(requires=["incident_id"], provides=["hostname"])
def check_host(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
    ...
```

詳細は [ARCHITECTURE.md](ARCHITECTURE.md#フィールドベース依存関係) を参照。

### 通常のノード

```yaml
nodes:
  process:
    module: nodes.process       # Python モジュール
    function: process           # 関数名
    description: "処理ノード"   # 説明
```

### 自動解決（v0.13.4+）

`module` と `function` は省略可能。`entrypoint` とノード名から自動解決されます。

```yaml
entrypoint: alert_workflow

nodes:
  fetch_alert:
    description: "アラート取得"
    # module: nodes.alert_workflow.fetch_alert (自動)
    # function: fetch_alert (自動)

  # 深いネストも対応
  process:
    check:
      db:
        description: "DB確認"
        # module: nodes.alert_workflow.process.check.db (自動)
        # function: db (自動)
```

| entrypoint | ノードパス | module | function |
|------------|-----------|--------|----------|
| `my_wf` | `start` | `nodes.my_wf.start` | `start` |
| `my_wf` | `process.check.db` | `nodes.my_wf.process.check.db` | `db` |

**Note:** 終端ノード（`exit.*`）は `entrypoint` を含みません。

---

## nodes.exit セクション（終端ノード）

終端ノードは `nodes.exit` 配下に定義します。

### 基本形式

```yaml
nodes:
  exit:
    success:
      done:
        description: "正常終了"
    failure:
      timeout:
        description: "タイムアウト"
```

### 自動解決

`module` と `function` は省略可能。YAML パスから自動解決されます。

**Note:** 終端ノードは `entrypoint` を含みません（通常ノードとは異なる）。

| YAML パス | module | function |
|----------|--------|----------|
| `nodes.exit.success.done` | `nodes.exit.success.done` | `done` |
| `nodes.exit.failure.ssh.handshake` | `nodes.exit.failure.ssh.handshake` | `handshake` |

### 終了コード

| パス | 終了コード | 結果 |
|------|-----------|------|
| `exit.success.*` | 0 | 成功 |
| `exit.failure.*` | 1 | 失敗 |
| `exit.warning.*` | 1（デフォルト） | 失敗扱い |
| カスタム | `exit_code` で指定 | 指定値 |

**カスタム終了コードの例:**

```yaml
nodes:
  exit:
    warning:
      low_disk:
        description: "ディスク容量警告"
        exit_code: 2
      high_memory:
        description: "メモリ使用量警告"
        exit_code: 3
```

### 終端ノードの返り値

終端ノードは `ExitContract` サブクラスを返します（`Outcome` は不要）:

```python
from railway import ExitContract, node

class FinalSummary(ExitContract):
    """終了時のサマリー。"""
    status: str
    exit_state: str = "success.done"

@node(name="exit.success.done")
def done(ctx: WorkflowContext) -> FinalSummary:
    """終端ノードは ExitContract を返す。"""
    return FinalSummary(status="completed")
```

遷移先がないため、`Outcome` を返す必要がありません。
v0.12.3 以降、`ExitContract` サブクラス以外を返すと `ExitNodeTypeError` が発生します。

### 深いネスト

エラーの詳細分類に便利:

```yaml
nodes:
  exit:
    failure:
      ssh:
        handshake:
          description: "SSHハンドシェイク失敗"
        authentication:
          description: "SSH認証失敗"
      api:
        request:
          timeout:
            description: "リクエストタイムアウト"
```

遷移先指定: `exit.failure.ssh.handshake`

---

## transitions セクション

遷移ルールを定義します。

### 基本形式

```yaml
transitions:
  from_node:
    状態キー: 遷移先
```

### 状態キーの形式

```
outcome_type::detail
```

| outcome_type | 用途 |
|--------------|------|
| `success` | 正常処理完了 |
| `failure` | エラー発生 |

例:
- `success::done` - 正常完了
- `success::skipped` - スキップして成功
- `failure::timeout` - タイムアウトエラー
- `failure::not_found` - リソース未検出

### 遷移先の形式

| 形式 | 説明 | 例 |
|------|------|-----|
| ノード名 | 次のノードへ | `process` |
| `exit.category.detail` | 終端ノードへ（v0.12.0+） | `exit.success.done` |
| `exit::name`（レガシー） | 旧形式の終了 | `exit::success` |

**v0.12.0+ 形式（推奨）:**

```yaml
transitions:
  process:
    success::done: exit.success.done
    failure::error: exit.failure.error
```

**レガシー形式（v0.11.x）:**

```yaml
exits:
  success:
    code: 0
  error:
    code: 1

transitions:
  process:
    success::done: exit::success
    failure::error: exit::error
```

---

## start セクション

ワークフローの開始ノードを指定します。

```yaml
start: check_severity
```

---

## options セクション（オプション）

実行時オプションを指定できます。

```yaml
options:
  max_iterations: 100  # 最大イテレーション数
```

---

## 完全な例

```yaml
version: "1.0"
entrypoint: alert_workflow
description: "アラート処理ワークフロー"

nodes:
  check_severity:
    description: "重要度をチェック"

  escalate:
    description: "エスカレーション"

  log_only:
    description: "ログ出力のみ"

  exit:
    success:
      escalated:
        description: "エスカレーション完了"
      logged:
        description: "ログ記録完了"
    failure:
      api_error:
        description: "API エラー"
      timeout:
        description: "タイムアウト"

start: check_severity

transitions:
  check_severity:
    success::critical: escalate
    success::normal: log_only
    failure::error: exit.failure.api_error

  escalate:
    success::done: exit.success.escalated
    failure::timeout: exit.failure.timeout

  log_only:
    success::done: exit.success.logged
    failure::error: exit.failure.api_error

options:
  max_iterations: 50
```

---

## 関連ドキュメント

- [readme.md](../readme.md) - 概要
- [docs/adr/004_exit_node_design.md](adr/004_exit_node_design.md) - 終端ノードの設計
