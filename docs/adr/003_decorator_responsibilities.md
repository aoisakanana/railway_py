# ADR-003: デコレータの責務定義

## ステータス
承認済み (2025-01-26)

## コンテキスト

DAGワークフロー追加に伴い、`@entry_point` と `@node` デコレータの
責務を明確化する必要がある。

## 決定

### @entry_point の責務

| 責務 | 説明 |
|------|------|
| 初期化 | 設定読み込み、ロギング設定 |
| 実行モデル呼び出し | `typed_pipeline()` または `dag_runner()` |
| 結果ハンドリング | 終了コード、エラーレポート |
| コールバック設定 | on_step, 監査ログ設定 |

```python
from railway import entry_point
from railway.core.dag import dag_runner, StepRecorder, AuditLogger

@entry_point
def main():
    # 初期化: entry_point デコレータが設定を読み込む

    # コールバック設定
    recorder = StepRecorder()
    audit = AuditLogger(workflow_id="incident-123")

    # 実行モデル呼び出し
    result = dag_runner(
        start=fetch_alert,
        transitions=TRANSITIONS,
        on_step=recorder,  # コールバック
    )

    # 結果ハンドリング
    if result.is_success:
        return result.context
    else:
        raise SystemExit(1)
```

### @node の責務（DAGモデル）

| 責務 | 説明 |
|------|------|
| 入力処理 | Contract を受け取る |
| ビジネスロジック | 純粋関数として実行 |
| 出力返却 | `tuple[Contract, Outcome]` |
| 遷移非関知 | 次のノードを知らない |

```python
from railway import node, Contract
from railway.core.dag import Outcome

class AlertContext(Contract):
    incident_id: str
    hostname: str | None = None

@node
def fetch_hostname(ctx: AlertContext) -> tuple[AlertContext, Outcome]:
    """
    責務:
    - AlertContext を受け取る（入力処理）
    - ホスト名を取得する（ビジネスロジック）
    - 新しい AlertContext と Outcome を返す（出力返却）

    NOT 責務:
    - 次にどのノードを呼ぶかを決める（ランナーの責務）
    """
    hostname = lookup_hostname(ctx.incident_id)
    if hostname:
        return ctx.model_copy(update={"hostname": hostname}), Outcome.success("found")
    return ctx, Outcome.failure("not_found")
```

### @node の責務（pipelineモデル）

| 責務 | 説明 |
|------|------|
| 入力処理 | Contract を受け取る |
| 変換ロジック | 純粋関数として実行 |
| 出力返却 | `Contract` |

```python
from railway import node, Contract

class UserData(Contract):
    users: list[dict]

class ReportResult(Contract):
    content: str

@node(output=ReportResult)
def generate_report(data: UserData) -> ReportResult:
    """
    責務:
    - UserData を受け取る（入力処理）
    - レポートを生成する（変換ロジック）
    - ReportResult を返す（出力返却）
    """
    content = "\n".join(u["name"] for u in data.users)
    return ReportResult(content=content)
```

### NOT 責務（共通）

以下は `@node` の責務ではない:

- **次のノードの呼び出し**: ランナー（`typed_pipeline` / `dag_runner`）の責務
- **遷移先の決定**: 遷移テーブル（YAML / dict）の責務
- **グローバル状態の変更**: 純粋関数パラダイム違反
- **ロギング設定**: `@entry_point` の責務

## 結果

- 責務が明確になり、テスト容易性が向上
- 純粋関数パラダイムが維持される
- ノードの再利用性が高まる
- 新規開発者の学習曲線が緩やかに

## 参照

- ADR-001: Output Model Pattern
- ADR-002: 実行モデルの共存
- Issue #15: @node自動マッピング & Outcome
