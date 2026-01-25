# Issue #14: TUTORIAL.md 更新

**Phase:** 2d
**優先度:** 中
**依存関係:** #10, #12
**見積もり:** 1日

---

## 概要

プロジェクト生成時の TUTORIAL.md にDAGワークフローのチュートリアルを追加する。
ハンズオン形式で、ユーザーがDAGワークフローを体験できるようにする。

---

## 追加セクション

### DAGワークフロー入門

```markdown
## 5. DAGワークフロー入門

このセクションでは、条件分岐を含むワークフローの作成方法を学びます。

### 5.1 DAGワークフローとは

DAG（Directed Acyclic Graph：有向非巡回グラフ）ワークフローは、
条件に応じて異なる処理パスを実行できるワークフローです。

```
[開始] → [チェック] →┬→ [パスA] → [終了]
                     └→ [パスB] → [終了]
```

Railway Frameworkでは、このようなワークフローを**YAMLで宣言的に定義**できます。

### 5.2 遷移グラフの作成

`transition_graphs/greeting_20250125120000.yml` を作成：

```yaml
version: "1.0"
entrypoint: greeting
description: "挨拶ワークフロー"

nodes:
  check_time:
    module: nodes.check_time
    function: check_time
    description: "時間帯を判定"
  greet_morning:
    module: nodes.greet
    function: greet_morning
    description: "朝の挨拶"
  greet_afternoon:
    module: nodes.greet
    function: greet_afternoon
    description: "午後の挨拶"
  greet_evening:
    module: nodes.greet
    function: greet_evening
    description: "夜の挨拶"

exits:
  success:
    code: 0
    description: "正常終了"

start: check_time

transitions:
  check_time:
    success::morning: greet_morning
    success::afternoon: greet_afternoon
    success::evening: greet_evening
  greet_morning:
    success::done: exit::success
  greet_afternoon:
    success::done: exit::success
  greet_evening:
    success::done: exit::success
```

### 5.3 コード生成

```bash
railway sync transition --entry greeting
```

`_railway/generated/greeting_transitions.py` が生成されます。

### 5.4 ノードの実装

`src/nodes/check_time.py`:

```python
from railway import node
from datetime import datetime
from _railway.generated.greeting_transitions import GreetingState

@node
def check_time() -> tuple[dict, GreetingState]:
    """時間帯を判定して状態を返す"""
    hour = datetime.now().hour

    if 5 <= hour < 12:
        return {"period": "morning"}, GreetingState.CHECK_TIME_SUCCESS_MORNING
    elif 12 <= hour < 18:
        return {"period": "afternoon"}, GreetingState.CHECK_TIME_SUCCESS_AFTERNOON
    else:
        return {"period": "evening"}, GreetingState.CHECK_TIME_SUCCESS_EVENING
```

`src/nodes/greet.py`:

```python
from railway import node
from _railway.generated.greeting_transitions import GreetingState

@node
def greet_morning(ctx: dict) -> tuple[dict, GreetingState]:
    """朝の挨拶"""
    print("おはようございます！")
    return ctx, GreetingState.GREET_MORNING_SUCCESS_DONE

@node
def greet_afternoon(ctx: dict) -> tuple[dict, GreetingState]:
    """午後の挨拶"""
    print("こんにちは！")
    return ctx, GreetingState.GREET_AFTERNOON_SUCCESS_DONE

@node
def greet_evening(ctx: dict) -> tuple[dict, GreetingState]:
    """夜の挨拶"""
    print("こんばんは！")
    return ctx, GreetingState.GREET_EVENING_SUCCESS_DONE
```

### 5.5 エントリーポイント

`src/greeting.py`:

```python
from railway import entry_point
from railway.core.dag.runner import dag_runner
from _railway.generated.greeting_transitions import (
    TRANSITION_TABLE,
    GRAPH_METADATA,
)
from nodes.check_time import check_time

@entry_point
def main():
    """時間帯に応じた挨拶を出力"""
    result = dag_runner(
        start=check_time,
        transitions=TRANSITION_TABLE,
        max_iterations=GRAPH_METADATA["max_iterations"],
    )

    if result.is_success:
        print(f"ワークフロー完了: {result.iterations} ステップ")
    else:
        print(f"エラー: {result.exit_code}")

    return result
```

### 5.6 実行

```bash
railway run greeting
```

時間帯に応じた挨拶が表示されます：

```
[check_time] 開始...
[check_time] ✓ 完了
[greet_morning] 開始...
おはようございます！
[greet_morning] ✓ 完了
ワークフロー完了: 2 ステップ
```

### 5.7 ポイント

1. **ノードは状態を返すだけ** - 遷移先はYAMLで定義
2. **状態は具体的に** - `success::morning` のように詳細を含める
3. **YAMLを変更したら再sync** - `railway sync transition --entry greeting`

### 5.8 チャレンジ

1. 時間帯ごとに異なるメッセージを追加してみましょう
2. 失敗パス（`failure::*`）を追加してエラーハンドリングを実装
3. 週末と平日で挨拶を変える分岐を追加
```

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/docs/test_tutorial_dag.py
"""Tests for DAG tutorial content."""
import pytest


class TestTutorialDAGContent:
    """Test TUTORIAL template contains DAG section."""

    @pytest.fixture
    def tutorial_template(self):
        """Read TUTORIAL.md template."""
        from pathlib import Path
        template_path = (
            Path(__file__).parent.parent.parent.parent /
            "railway" / "templates" / "project" / "TUTORIAL.md"
        )
        return template_path.read_text()

    def test_tutorial_has_dag_section(self, tutorial_template):
        """TUTORIAL should have DAG workflow section."""
        assert "DAG" in tutorial_template

    def test_tutorial_has_transition_yaml(self, tutorial_template):
        """TUTORIAL should show transition YAML example."""
        assert "transition" in tutorial_template.lower()
        assert "version:" in tutorial_template

    def test_tutorial_has_sync_command(self, tutorial_template):
        """TUTORIAL should show sync command."""
        assert "railway sync" in tutorial_template

    def test_tutorial_has_node_example(self, tutorial_template):
        """TUTORIAL should show node returning state."""
        assert "GreetingState" in tutorial_template or "State" in tutorial_template

    def test_tutorial_has_dag_runner(self, tutorial_template):
        """TUTORIAL should show dag_runner usage."""
        assert "dag_runner" in tutorial_template

    def test_tutorial_is_hands_on(self, tutorial_template):
        """TUTORIAL should be hands-on with steps."""
        assert "5.1" in tutorial_template or "Step" in tutorial_template
```

```bash
pytest tests/unit/docs/test_tutorial_dag.py -v
# Expected: FAILED
```

### Step 2: Green（TUTORIAL.md テンプレートを更新）

`railway/templates/project/TUTORIAL.md` に上記のセクションを追加。

```bash
pytest tests/unit/docs/test_tutorial_dag.py -v
# Expected: PASSED
```

---

## 完了条件

- [ ] DAGワークフローの概念説明
- [ ] YAMLの作成手順
- [ ] `railway sync transition` の使い方
- [ ] ノード実装のサンプル（状態を返す）
- [ ] エントリーポイントの `dag_runner` 使用例
- [ ] 実行結果の表示例
- [ ] ポイント・チャレンジ課題
- [ ] テストが通過

---

## 完了後

Phase 2 の全Issueが完了したら：

1. 事例１ワークフローを新APIで再実装して動作確認
2. v0.10.2 リリースノート作成
3. リリース
