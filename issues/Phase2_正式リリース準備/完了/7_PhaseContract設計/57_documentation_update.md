# Issue #57: ドキュメント更新

## 概要

フィールドベース依存関係のドキュメントを追加・更新する。

## 対象ドキュメント

1. `docs/ARCHITECTURE.md` - フィールドベース依存関係セクション追加
2. `test_project/TUTORIAL.md` - 依存宣言チュートリアル追加
3. `readme.md` - 概要追加
4. `docs/transition_graph_reference.md` - YAML 形式の説明更新
5. `CLAUDE.md` - 開発ガイドライン更新

## タスク

### 1. ARCHITECTURE.md 更新

`docs/ARCHITECTURE.md` に以下のセクションを追加:

```markdown
## フィールドベース依存関係

### 問題: 暗黙的なデータ依存

従来の設計では、ノード間のデータ依存が暗黙的でした。
遷移グラフ（YAML）を変更すると、データ不整合が発生する可能性がありました。

```python
# 問題: hostname はどのノードが設定する？いつ利用可能？
class AlertContext(Contract):
    incident_id: str
    hostname: str | None = None  # 暗黙的な依存
```

### 解決: ノードコードで依存を宣言

フィールドベース依存関係では、各ノードが必要とするフィールドを
**ノードコードで明示的に宣言**します。YAML 記述者はこれを知る必要がありません。

```python
@node(
    requires=["incident_id"],           # 必須: なければ実行不可
    optional=["hostname"],              # 任意: あれば使用
    provides=["escalated", "notified"], # 提供: このノードが追加するフィールド
)
def escalate(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
    if ctx.hostname:  # optional なので存在チェック
        notify_with_host(ctx.hostname)
    return ctx.model_copy(update={"escalated": True}), Outcome.success("done")
```

### 関心の分離

| 役割 | 責務 | 知る必要があること |
|------|------|------------------|
| **ノード実装者** | `@node` で依存を宣言 | ノードが必要とするフィールド |
| **YAML 記述者** | 遷移を定義 | **ノード名と Outcome のみ** |
| **フレームワーク** | 依存の自動検証 | 両方を読み取って検証 |

### sync 時の自動検証

`railway sync transition` 実行時、フレームワークが:

1. ノードコードから依存情報を抽出
2. 遷移グラフの全経路を解析
3. 各経路で requires が満たされるか検証
4. 不整合があればエラー報告

```
$ railway sync transition --entry alert_workflow

❌ 依存関係エラー: 遷移 'check_severity → escalate' が無効です

  escalate が必要とするフィールド:
    requires: [hostname]     ❌ 利用不可
    optional: []

  この時点で利用可能なフィールド:
    [incident_id, severity]

  提案:
    - check_host を経由する遷移に変更してください
```

### 利点

| 観点 | 効果 |
|------|------|
| **関心の分離** | YAML 記述者はノード実装詳細を知らなくてよい |
| **自動検証** | sync 時に依存エラーを検出 |
| **YAML のみで変更** | 遷移グラフ変更時、ノードコード変更不要 |
| **IDE 補完** | optional フィールドの存在チェックが明確 |
```

### 2. TUTORIAL.md 更新

新しい Step として依存宣言チュートリアルを追加:

```markdown
## Step 12: フィールドベース依存関係（5分）

ワークフローが複雑になると、ノード間のデータ依存を管理する必要があります。
フィールドベース依存関係で、YAML だけでワークフローを変更できるようにしましょう。

### 12.1 問題の理解

遷移グラフを変更すると、必要なデータがないエラーが発生することがあります:

```yaml
# Before: check_host → escalate
# After: (check_host を削除) → escalate
#        ↑ hostname がないためエラー！
```

### 12.2 ノードで依存を宣言

各ノードが必要とするフィールドを宣言します:

```python
# nodes/check_host.py
@node(requires=["incident_id"], provides=["hostname"])
def check_host(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
    hostname = lookup_hostname(ctx.incident_id)
    return ctx.model_copy(update={"hostname": hostname}), Outcome.success("found")


# nodes/escalate.py
@node(requires=["incident_id"], optional=["hostname"], provides=["escalated"])
def escalate(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
    if ctx.hostname:  # optional なので存在チェック
        notify_with_host(ctx.hostname)
    else:
        notify_without_host()
    return ctx.model_copy(update={"escalated": True}), Outcome.success("done")
```

### 12.3 YAML には依存を書かない

YAML には遷移のみを記述します。依存情報は不要:

```yaml
# ノード名と遷移のみ
nodes:
  check_severity:
    description: "重要度チェック"
  check_host:
    description: "ホスト情報取得"
  escalate:
    description: "エスカレーション"

transitions:
  check_severity:
    success::critical: check_host
    success::normal: escalate   # ← フレームワークが自動検証
  check_host:
    success::found: escalate
```

### 12.4 sync で自動検証

```bash
$ railway sync transition --entry alert_workflow

✅ 依存関係検証OK

⚠️ 警告:
  - 経路 'check_severity → escalate' で hostname が利用不可
    （escalate は optional で宣言しているため問題なし）
```

### 12.5 依存エラーの例

```bash
$ railway sync transition --entry alert_workflow

❌ 依存関係エラー: 遷移 'check_severity → escalate' が無効です

  escalate が必要とするフィールド:
    requires: [hostname]  ❌ 利用不可

  提案:
    - check_host を経由する遷移に変更
    - または escalate の requires から hostname を削除
```

🎉 **YAML を変更して sync するだけで、依存エラーを検出できます！**
```

### 3. transition_graph_reference.md 更新

依存情報が YAML にないことを明記:

```markdown
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
```

### 4. readme.md 更新

フィールドベース依存関係の概要を追加。

### 5. CLAUDE.md 更新

開発時のガイドラインを追加:

```markdown
## フィールドベース依存関係

### ノード実装時

```python
# 依存を明示的に宣言
@node(
    requires=["field_a"],      # 必須フィールド
    optional=["field_b"],      # オプションフィールド
    provides=["field_c"],      # 追加するフィールド
)
def my_node(ctx: Context) -> tuple[Context, Outcome]:
    ...
```

### YAML 記述時

- 依存情報は YAML に書かない
- ノード名と遷移のみを記述
- sync 時に依存検証が自動実行される
```

## 完了条件

- [ ] `docs/ARCHITECTURE.md` にフィールドベース依存関係セクションが追加されている
- [ ] `test_project/TUTORIAL.md` に Step 12 が追加されている
- [ ] `docs/transition_graph_reference.md` が更新されている
- [ ] `readme.md` に概要が追加されている
- [ ] `CLAUDE.md` が更新されている
- [ ] すべてのコード例が実際に動作する

## 依存関係

- Issue #50-56 がすべて完了していること

## 関連ファイル

- `docs/ARCHITECTURE.md` (更新)
- `test_project/TUTORIAL.md` (更新)
- `docs/transition_graph_reference.md` (更新)
- `readme.md` (更新)
- `CLAUDE.md` (更新)
