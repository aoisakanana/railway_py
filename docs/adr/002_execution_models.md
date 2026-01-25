# ADR-002: 実行モデルの共存（typed_pipeline と dag_runner）

## ステータス
承認済み (2025-01-26)

## コンテキスト

Railway Framework v0.11.0で条件分岐対応のDAGワークフローを追加する。
既存の `typed_pipeline` API との関係を明確にする必要がある。

## 決定

`typed_pipeline` と `dag_runner` を**相互排他的な実行モデル**として共存させる。
1つのエントリーポイントではどちらか一方のみを使用する。

### 2つの実行モデル

| モデル | 用途 | 遷移制御 | 分岐 | Contract解決 |
|--------|------|----------|------|--------------|
| `typed_pipeline` | 線形パイプライン | 順番に実行 | 不可 | 自動 |
| `dag_runner` | 条件分岐ワークフロー | 状態ベース | 可能 | ノードが返す |

### 使い分けガイドライン

**typed_pipeline を使う:**
- 処理が必ず順番に実行される（A→B→C→D）
- 条件分岐がない
- Contract の自動解決を活用したい
- ETL、データ変換パイプライン

**dag_runner を使う:**
- 条件分岐がある（if-else, switch）
- エラーパスが複数ある
- ワークフローをYAMLで可視化したい
- 運用自動化、複雑なワークフロー

### コード例

#### typed_pipeline（線形パイプライン）

```python
from railway import entry_point, typed_pipeline, Contract

class UserData(Contract):
    users: list[dict]

class ReportResult(Contract):
    content: str

@node(output=UserData)
def fetch_users() -> UserData:
    return UserData(users=[...])

@node(output=ReportResult)
def generate_report(data: UserData) -> ReportResult:
    return ReportResult(content="...")

@entry_point
def main():
    # 順番に実行: fetch_users → generate_report
    result = typed_pipeline(fetch_users, generate_report)
    return result
```

#### dag_runner（条件分岐ワークフロー）

```python
from railway import entry_point, Contract
from railway.core.dag import dag_runner, Exit, Outcome

class AlertContext(Contract):
    incident_id: str
    severity: str

def check_severity(ctx: AlertContext) -> tuple[AlertContext, Outcome]:
    if ctx.severity == "critical":
        return ctx, Outcome.success("critical")
    return ctx, Outcome.success("normal")

def escalate(ctx: AlertContext) -> tuple[AlertContext, Outcome]:
    # 緊急対応
    return ctx, Outcome.success("done")

def log_only(ctx: AlertContext) -> tuple[AlertContext, Outcome]:
    # ログ記録のみ
    return ctx, Outcome.success("done")

transitions = {
    "check_severity::success::critical": escalate,
    "check_severity::success::normal": log_only,
    "escalate::success::done": Exit.GREEN,
    "log_only::success::done": Exit.GREEN,
}

@entry_point
def main(incident_id: str):
    ctx = AlertContext(incident_id=incident_id, severity="critical")
    result = dag_runner(
        start=lambda: (ctx, Outcome.success("start")),
        transitions=transitions,
    )
    return result
```

## 結果

- 既存の `typed_pipeline` ユーザーに影響なし（後方互換性維持）
- 新規ユーザーは用途に応じて選択可能
- ドキュメントで使い分けを明確に説明
- 将来的な統合の可能性を残す

## 参照

- Issue #10: DAGランナー実装
- Issue #15: @node自動マッピング & Outcome
- ADR-001: Output Model Pattern
