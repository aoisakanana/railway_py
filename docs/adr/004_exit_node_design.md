# ADR-004: Exit ノードの設計と例外処理

## ステータス
承認済み (2026-01-28)

## コンテキスト

DAGワークフローにおいて、終了時に処理（通知、ログ出力、クリーンアップなど）を実行したいケースがある。
現在の `exits` 定義は `nodes` と異なる構造であり、関数を実行する手段がない。

```yaml
# 現状: exits だけ特殊な構造
nodes:
  finalize:
    module: nodes.finalize
    function: finalize
    description: "終了処理"

exits:
  success:
    code: 0
    description: "正常終了"  # ← module, function がない
```

### 検討事項

1. `exits` を `nodes` と同じ構造に統一すべきか？
2. エントリーポイントは何を返すべきか？
3. exit handler で例外が発生した場合、どう処理すべきか？
4. `exit::success::1` と `exit::success::2` を区別できるか？

## 決定

### 1. exits セクション廃止、nodes.exit 配下に統合

`exits` セクションを廃止し、終端ノードを `nodes.exit` 配下に統合する。
また、`module` と `function` を省略可能にし、YAMLパスから自動解決する。

```yaml
nodes:
  finalize:
    description: "最終処理"
    # 自動解決: module=nodes.finalize, function=finalize

  # nodes.exit 配下 = 終端ノード
  exit:
    success:
      done:
        description: "正常終了（Slack通知）"
        # 自動解決: module=nodes.exit.success.done, function=done
      skipped:
        description: "スキップして終了"

    failure:
      timeout:
        description: "タイムアウト"
      ssh:
        handshake:
          description: "SSHハンドシェイク失敗"
        authentication:
          description: "SSH認証失敗"

transitions:
  finalize:
    success::complete: exit.success.done
    success::skipped: exit.success.skipped
    failure::timeout: exit.failure.timeout
```

**設計原則:**
- `exits` セクションは廃止（後方互換性は不要、旧形式はエラー）
- 終端ノードは `nodes.exit` 配下に集約（散在防止）
- `module`, `function` は省略可能（YAMLパスから自動解決）
- ネストは自由に深くできる（`exit.failure.ssh.handshake`）
- 終了コードは自動判定（`exit.success.*` = 0, `exit.failure.*` = 1）
- 開始ノードは初期コンテキストを引数として受け取る

**理由:**
- 一貫性: `exits` だけが特殊な構造である必要がない
- 表現力: `exit::success::1` と `exit::success::2` を `exit.success.done` と `exit.success.skipped` として区別可能
- 可用性: コールバックの概念を知らない運用者でも終了処理を記述できる
- テスト可能性: 終了処理も純粋関数としてテスト可能
- 冗長性排除: module/function の自動解決により記述量削減

### 2. エントリーポイントの返り値

**終端ノードの返り値（コンテキスト）を返す。**

```python
# src/nodes/exit/success/done.py
from railway import Contract, node


class FinalSummary(Contract):
    """最終サマリー"""
    status: str
    processed_count: int
    elapsed_seconds: float


@node
def done(ctx: WorkflowContext) -> FinalSummary:
    """最終サマリーを計算して返す。

    Note:
        終端ノードは Context のみを返す（Outcome は不要）。
        遷移先がないため、Outcome を返す意味がない。
    """
    return FinalSummary(
        status="completed",
        processed_count=ctx.count,
        elapsed_seconds=calculate_elapsed(ctx.started_at),
    )


# エントリーポイント
@entry_point
def main() -> FinalSummary:
    result = dag_runner(...)
    return result.context  # ← FinalSummary型
```

**理由:**
- 終端ノードが「最終結果を計算する場所」として機能する
- 簡潔性: 終端ノードは `Context` のみを返す（Outcome は遷移先がないため不要）
- 直感的: 「ワークフローの結果 = 最後に実行されたノードの出力」
- 区別: 通常ノード（`tuple[Context, Outcome]`）と終端ノード（`Context`）が明確に区別される

### 3. 例外処理

**終端ノードで発生した例外はそのまま伝播する。特別な処理は行わない。**

```python
# 終端ノードは Context のみを返す
final_context = exit_node(context)
```

**設計思想:**

| 概念 | 説明 | 遷移先 |
|------|------|--------|
| `Outcome.failure` | 想定内のエラー | あり（遷移グラフで定義） |
| Python例外 | 想定外のバグ | なし（プログラムの誤り） |

**理由:**

1. **Railway Oriented Programming との整合性**
   - 処理可能なエラーは `Outcome.failure` で表現し、遷移グラフで適切に処理される
   - 終端ノードに到達した時点で、想定内のエラーはすべて処理済み
   - 例外は「プログラムのバグ」であり、フレームワークが処理すべきではない

2. **一貫性**
   - 通常ノードと同じ動作（例外は伝播）
   - 終端ノードだけ特別扱いする理由がない

3. **終端ノードの役割**
   - 「後処理」であり「本質的な処理」ではない
   - 通知の失敗でワークフロー全体を失敗にすべきではない（多くの場合）
   - 例外が発生する可能性がある処理は try-except で囲むべき

## 影響

### 後方互換性

**後方互換性は提供しない。** 旧形式はエラーとなる。

| ケース | 動作 |
|--------|------|
| 旧形式 `exits` セクション | **パースエラー** |
| 旧形式 `exit::success` 参照 | **パースエラー** |
| 新形式 `nodes.exit` | 正常動作 |
| module/function 明示 | 明示値を使用 |
| module/function 省略 | 自動解決 |

**理由:**
- 設計をシンプルに保つ
- 旧形式と新形式の混在によるバグを防止
- マイグレーションガイドを提供（別途ドキュメント）

### 実装への影響

- `NodeDefinition` に `is_exit`, `exit_code` フィールド追加
- `StateTransition.is_exit` が新形式（`exit.` プレフィックス）をチェック
- YAMLパーサーがネスト構造を再帰的にパース
- module/function の自動解決ロジック追加
- `validator` が新形式の遷移先を検証
- `codegen` が以下を生成:
  - 終端ノードの import 文（エイリアス付き）
  - `_node_name` 属性の自動設定コード
  - `EXIT_CODES` マッピング
  - `run()` / `run_async()` ヘルパー関数
- `dag_runner` が `exit_codes` パラメータを受け取り、終端ノードを実行

### run() ヘルパー

`codegen` が生成する `run()` ヘルパーにより、ワークフロー実行が簡略化される:

```python
# 生成されたモジュール
from src.transitions.my_workflow import run

# 1行でワークフロー実行
result = run({"user_id": 123})

# 非同期版
result = await run_async({"user_id": 123})
```

これにより、YAML の `start` フィールドと Python コードの開始ノード指定の二重管理が不要になる。

## 代替案

### 代替案A: exits セクションに module/function を追加

```yaml
exits:
  success:
    module: nodes.exits.success
    function: exit_success
    description: "正常終了処理"
    code: 0
```

**却下理由:**
- `exit::success::1` と `exit::success::2` を区別できない
- exits セクションが特殊な構造のまま
- 終端ノードが散在する可能性

### 代替案B: on_exit コールバック

```python
result = dag_runner(
    start=...,
    transitions=...,
    on_exit=lambda exit_code, ctx: send_notification(ctx),  # コールバック
)
```

**却下理由:**
- コールバックの概念が必要
- 通常のノードと異なる書き方
- テストしにくい

### 代替案C: 終端ノードの例外を ExitNodeError にラップ

```python
try:
    context, outcome = exit_node(context)
except Exception as e:
    raise ExitNodeError(exit_code, context, e)
```

**却下理由:**
- 複雑になる
- 通常ノードと異なる動作
- 呼び出し元での例外処理が煩雑

### 代替案D: 最後のノード（終端ノード実行前）のコンテキストを返す

**却下理由:**
- 終端ノードで最終サマリーを計算できない
- 「最後に実行されたノードの出力」という直感に反する

## 参考資料

- Issue #23: テスト用 YAML フィクスチャ
- Issue #24: NodeDefinition の終端ノード対応
- Issue #25: パーサーのネスト構造対応（自動解決含む）
- Issue #26: バリデーション更新 - 終端ノード形式対応
- Issue #27: codegen の終端ノード対応
- Issue #28: dag_runner の終端ノード実行
- Issue #29: 終端ノードドキュメント追加
- Issue #30: E2E 統合テスト
- Issue #31: codegen に run() ヘルパー追加
- Issue #32: YAML 構造変換ユーティリティ
- Issue #33: v0.11.3 → v0.12.0 マイグレーション定義
- Railway Oriented Programming: https://fsharpforfunandprofit.com/rop/
