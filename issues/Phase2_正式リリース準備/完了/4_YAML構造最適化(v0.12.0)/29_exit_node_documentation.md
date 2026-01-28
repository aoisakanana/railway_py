# Issue #29: 終端ノードドキュメント追加

**Phase:** 2
**優先度:** 中
**依存関係:** Issue #30（E2E 統合テスト完了後）
**見積もり:** 0.25日

---

## 概要

終端ノード（`nodes.exit` 配下）機能のドキュメントを追加する。
コールバックの概念を知らない運用者でも、終了処理を記述できることを伝える。

---

## ドキュメント更新箇所

### 1. readme.md - 「終端ノード」セクション追加

「アーキテクチャ」セクションの「Exit（終了コード）」の後に追加。

```markdown
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

**実装例:**

```python
# src/nodes/exit/success/done.py
from railway import Contract, node

class FinalSummary(Contract):
    status: str
    processed_count: int

@node
def done(ctx: WorkflowContext) -> FinalSummary:
    """終端ノードは Context のみを返す（Outcome 不要）。"""
    send_slack_notification(f"処理完了: {ctx.count}件")
    return FinalSummary(
        status="completed",
        processed_count=ctx.count,
    )
```

**特徴:**

| 項目 | 説明 |
|------|------|
| 一貫性 | 通常のノードと同じ書き方 |
| テスト可能性 | 純粋関数としてテスト可能 |
| 表現力 | 詳細な終了状態を表現（done, skipped, timeout など） |
| 自動解決 | module/function は省略可能 |
```

---

### 2. TUTORIAL.md - 終端ノード体験ステップ追加

```markdown
## Step 7: 終端ノード - 終了時の処理

### 7.1 終端ノードを定義

`transition_graphs/greeting.yml` を編集:

```yaml
nodes:
  greet:
    description: "挨拶する"

  exit:
    success:
      done:
        description: "正常終了"
    failure:
      error:
        description: "異常終了"

transitions:
  greet:
    success::done: exit.success.done
    failure::error: exit.failure.error
```

### 7.2 終端ノードを実装

`src/nodes/exit/success/done.py` を作成:

```python
from railway import node

@node
def done(ctx):
    """終端ノードは Context のみを返す。"""
    print(f"[完了] ワークフロー正常終了: {ctx}")
    return {"status": "completed", "original": ctx}
```

### 7.3 コード生成と実行

```bash
railway sync transition --entry greeting
railway run greeting
```

### 7.4 終了時の処理を確認

終端ノードの関数が実行され、Slack 通知などの処理を挿入できます。
```

---

### 3. docs/transition_graph_reference.md - nodes.exit セクション詳細

```markdown
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

`module` と `function` は省略可能です。YAML パスから自動解決されます。

| YAML パス | module | function |
|----------|--------|----------|
| `nodes.exit.success.done` | `nodes.exit.success.done` | `done` |
| `nodes.exit.failure.ssh.handshake` | `nodes.exit.failure.ssh.handshake` | `handshake` |

### 終了コード

| パス | 終了コード |
|------|-----------|
| `exit.success.*` | 0 |
| `exit.failure.*` | 1 |
| `exit.warning.*` | 1（デフォルト） |
| カスタム | `exit_code` で指定 |

```yaml
nodes:
  exit:
    warning:
      low_disk:
        description: "ディスク容量警告"
        exit_code: 2
```

### 終端ノードの返り値

終端ノードは `Context` のみを返します（`Outcome` は不要）:

```python
@node
def done(ctx: WorkflowContext) -> FinalSummary:
    return FinalSummary(status="completed")
```

遷移先がないため、`Outcome` を返す必要がありません。

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
```

---

## 実装手順

### Step 1: readme.md 更新

終端ノードセクションを追加。

### Step 2: TUTORIAL.md 更新

Step 7 として終端ノード体験ステップを追加。

### Step 3: docs/transition_graph_reference.md 更新

nodes.exit セクションの詳細を追加。

---

## 完了条件

- [ ] readme.md に「終端ノード」セクション追加
- [ ] TUTORIAL.md に終端ノード体験ステップ追加
- [ ] docs/transition_graph_reference.md 更新
- [ ] 新 YAML 構造（nodes.exit 配下）の説明
- [ ] module/function 自動解決の説明
- [ ] 終了コード自動判定の説明
- [ ] 終端ノードの返り値（Context のみ）の説明

---

## 関連 Issue

- Issue #30: E2E 統合テスト（前提）
- ADR-004: Exit ノードの設計と例外処理
