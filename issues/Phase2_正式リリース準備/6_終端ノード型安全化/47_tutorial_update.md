# Issue #47: TUTORIAL.md 更新

**優先度**: P1
**依存**: #46
**ブロック**: なし
**バージョン**: v0.12.3

---

## 概要

TUTORIAL.md に終端ノードの実装例を追記し、ユーザーが型安全な終端ノードを正しく実装できるようにする。

## 背景

#44-#46 で終端ノードの型安全性を強制したが、ユーザー向けドキュメントが更新されていないと：
- 既存ユーザーが v0.12.3 への移行方法を理解できない
- 新規ユーザーが正しい実装方法を学べない

**ドキュメントの役割**:
```
開発者が TUTORIAL.md を読む
    ↓
終端ノードの正しい実装方法を理解
    ↓
型安全なコードを書ける
```

---

## 追加するコンテンツ

### 1. 終端ノードのセクション

TUTORIAL.md に以下のセクションを追加:

```markdown
## 終端ノード（Exit Node）

ワークフローの終了時に処理を実行し、結果を返す特殊なノードです。

### 基本的な実装

終端ノードは `ExitContract` サブクラスを返します：

```python
# src/nodes/exit/success/done.py
from railway import ExitContract, node


class SuccessDoneResult(ExitContract):
    """正常終了時の結果。"""
    exit_state: str = "success.done"
    processed_count: int
    summary: str


@node(name="exit.success.done")
def done(ctx: WorkflowContext) -> SuccessDoneResult:
    """正常終了処理。

    Args:
        ctx: 直前のノードからのコンテキスト

    Returns:
        SuccessDoneResult: 終了結果
    """
    # 通知処理など
    send_slack_notification(f"処理完了: {ctx.count}件")

    return SuccessDoneResult(
        processed_count=ctx.count,
        summary="All items processed successfully",
    )
```

### YAML での定義

```yaml
nodes:
  # 通常のノード
  process:
    description: "処理ノード"

  # 終端ノード
  exit:
    success:
      done:
        description: "正常終了"
    failure:
      timeout:
        description: "タイムアウト"

transitions:
  process:
    success::complete: exit.success.done
    failure::timeout: exit.failure.timeout
```

### スケルトン自動生成

`railway sync transition` を実行すると、未実装の終端ノードにスケルトンが自動生成されます：

```bash
$ railway sync transition --entry my_workflow

生成: src/nodes/exit/success/done.py
生成: src/nodes/exit/failure/timeout.py
```

生成されたファイルを編集して、TODO コメントを実装してください。

### dag_runner の返り値

`dag_runner()` は終端ノードが返した `ExitContract` を返します：

```python
result = dag_runner(start=start, transitions=TRANSITIONS)

# 基本プロパティ
result.is_success       # True if exit_code == 0
result.exit_code        # 0 (success.*) or 1 (failure.*)
result.exit_state       # "success.done" など

# カスタムフィールド（ExitContract サブクラスの場合）
result.processed_count  # 42
result.summary          # "All items processed"

# メタデータ
result.execution_path   # ("start", "process", "exit.success.done")
result.iterations       # 3
```

### 注意点

| ルール | 説明 |
|--------|------|
| 返り値 | 必ず `ExitContract` サブクラスを返す |
| exit_state | `success.*` で始まると `exit_code=0`、それ以外は `1` |
| Outcome 不要 | 終端ノードは `Outcome` を返さない（遷移先がないため） |

### v0.12.x からの移行

v0.12.x で `dict` や `None` を返していた場合、v0.12.3 で `ExitNodeTypeError` が発生します。

**移行手順**:

1. `railway sync transition` でスケルトン生成
2. 警告に従ってコード修正
3. `ExitContract` サブクラスを返すように変更

**Before (v0.12.x)**:
```python
def done(ctx):
    return {"status": "ok"}  # ← TypeError in v0.12.3
```

**After (v0.12.3)**:
```python
class DoneResult(ExitContract):
    exit_state: str = "success.done"
    status: str

def done(ctx) -> DoneResult:
    return DoneResult(status="ok")
```
```

---

## 修正ファイル

| ファイル | 変更内容 |
|----------|----------|
| `TUTORIAL.md` | 終端ノードセクション追加 |

---

## TDD 実装フロー

### Phase 1: Red

ドキュメントの正確性をテストで担保することは難しいため、代わりに：
- コード例が実際に動作することを確認するテストを作成

```python
# tests/docs/test_tutorial_examples.py

import pytest
from railway import ExitContract, node
from railway.core.dag import dag_runner, Outcome


class TestTutorialExitNodeExamples:
    """TUTORIAL.md の終端ノード例が動作することを確認。"""

    def test_basic_exit_node_example(self) -> None:
        """基本的な終端ノードの例が動作する。"""
        # TUTORIAL.md のコード例を再現
        class SuccessDoneResult(ExitContract):
            exit_state: str = "success.done"
            processed_count: int
            summary: str

        @node(name="exit.success.done")
        def done(ctx: dict) -> SuccessDoneResult:
            return SuccessDoneResult(
                processed_count=42,
                summary="All items processed",
            )

        @node(name="start")
        def start() -> tuple[dict, Outcome]:
            return {"count": 42}, Outcome.success("done")

        result = dag_runner(
            start=start,
            transitions={"start::success::done": done},
        )

        assert result.is_success
        assert result.processed_count == 42
        assert result.summary == "All items processed"
```

### Phase 2: Green

TUTORIAL.md を更新し、テストが通ることを確認。

### Phase 3: Refactor

- 説明文の推敲
- コード例の整理

---

## 受け入れ条件

### コンテンツ
- [ ] 終端ノードの基本的な実装例が記載されている
- [ ] YAML での定義方法が記載されている
- [ ] スケルトン自動生成の説明がある
- [ ] `dag_runner` の返り値の説明がある
- [ ] v0.12.x からの移行方法が記載されている
- [ ] コード例が実際に動作する（テストで確認）

### 品質
- [ ] 既存の TUTORIAL.md のスタイルと一貫している
- [ ] 初心者にも分かりやすい説明になっている
- [ ] 全テスト通過

---

*ユーザー向けドキュメントの更新*
