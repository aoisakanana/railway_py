# Issue #13: README.md 更新

**Phase:** 2d
**優先度:** 中
**依存関係:** #10
**見積もり:** 0.5日

---

## 概要

README.md にDAGワークフロー機能のドキュメントを追加する。
新機能の概要、使用方法、ベストプラクティスを記載する。

---

## 追加セクション

### 1. 機能概要への追加

```markdown
## 特徴

- **DAGワークフロー**: 条件分岐を含む複雑なワークフローをYAMLで宣言的に定義
```

### 2. DAGワークフローセクション（新規）

```markdown
## DAGワークフロー

Railway Framework v0.10.2からDAG（有向非巡回グラフ）ワークフローをサポート。
複雑な条件分岐を含むワークフローを、YAMLで宣言的に定義できます。

### 基本的な考え方

1. **遷移はデータ** - ワークフローの遷移ロジックはYAMLで定義
2. **ノードはステートレス** - 各ノードは状態を返すだけ、遷移先を知らない
3. **型安全** - 生成されたEnumで状態を型安全に扱える

### クイックスタート

#### 1. 遷移グラフの定義

`transition_graphs/my_workflow_20250125120000.yml`:

```yaml
version: "1.0"
entrypoint: my_workflow
description: "サンプルワークフロー"

nodes:
  fetch_data:
    module: nodes.fetch
    function: fetch_data
    description: "データ取得"
  process_data:
    module: nodes.process
    function: process_data
    description: "データ処理"

exits:
  success:
    code: 0
    description: "正常終了"
  error:
    code: 1
    description: "異常終了"

start: fetch_data

transitions:
  fetch_data:
    success::done: process_data
    failure::http: exit::error
  process_data:
    success::complete: exit::success
    failure::error: exit::error
```

#### 2. コード生成

```bash
railway sync transition --entry my_workflow
```

これにより `_railway/generated/my_workflow_transitions.py` が生成されます。

#### 3. ノードの実装

```python
# nodes/fetch.py
from railway import node
from _railway.generated.my_workflow_transitions import MyWorkflowState

@node
def fetch_data() -> tuple[dict, MyWorkflowState]:
    try:
        data = api.get("/data")
        return {"data": data}, MyWorkflowState.FETCH_DATA_SUCCESS_DONE
    except HTTPError:
        return {}, MyWorkflowState.FETCH_DATA_FAILURE_HTTP
```

#### 4. エントリーポイント

```python
# my_workflow.py
from railway import entry_point
from railway.core.dag.runner import dag_runner
from _railway.generated.my_workflow_transitions import (
    TRANSITION_TABLE,
    GRAPH_METADATA,
)
from nodes.fetch import fetch_data

@entry_point
def main():
    result = dag_runner(
        start=fetch_data,
        transitions=TRANSITION_TABLE,
        max_iterations=GRAPH_METADATA["max_iterations"],
    )
    return result
```

### 状態の命名規則

状態は `{node_name}::{outcome}::{detail}` 形式で定義します：

```yaml
transitions:
  check_session:
    success::exist: next_node      # セッションが存在
    success::not_exist: other_node # セッションが不在
    failure::ssh: exit::error      # SSH接続エラー
```

### 条件分岐の例

```yaml
transitions:
  check_condition:
    success::type_a: process_a  # 条件Aの場合
    success::type_b: process_b  # 条件Bの場合
    success::type_c: process_c  # 条件Cの場合
    failure::error: exit::error
```

### ベストプラクティス

1. **ノードは小さく保つ** - 1つのノードは1つの責務
2. **状態は具体的に** - `success` より `success::found` が良い
3. **失敗パスを忘れない** - すべてのノードに失敗時の遷移を定義
4. **max_iterations を適切に** - 無限ループ防止のため妥当な値を設定
```

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/docs/test_readme_dag.py
"""Tests for DAG documentation in README."""
import pytest
from pathlib import Path


class TestReadmeDAGContent:
    """Test README contains DAG documentation."""

    @pytest.fixture
    def readme_content(self):
        """Read README.md content."""
        readme_path = Path(__file__).parent.parent.parent.parent / "readme.md"
        return readme_path.read_text()

    def test_readme_mentions_dag_workflow(self, readme_content):
        """README should mention DAG workflow feature."""
        assert "DAG" in readme_content or "dag" in readme_content.lower()

    def test_readme_has_transition_yaml_example(self, readme_content):
        """README should have transition YAML example."""
        assert "transition" in readme_content.lower()
        assert "yaml" in readme_content.lower() or ".yml" in readme_content

    def test_readme_has_sync_command(self, readme_content):
        """README should document sync command."""
        assert "railway sync" in readme_content

    def test_readme_has_dag_runner_example(self, readme_content):
        """README should show dag_runner usage."""
        assert "dag_runner" in readme_content

    def test_readme_explains_state_format(self, readme_content):
        """README should explain state naming convention."""
        assert "success::" in readme_content or "failure::" in readme_content
```

```bash
pytest tests/unit/docs/test_readme_dag.py -v
# Expected: FAILED (content not yet added)
```

### Step 2: Green（README.md を更新）

上記の「追加セクション」の内容を `readme.md` に追記する。

```bash
pytest tests/unit/docs/test_readme_dag.py -v
# Expected: PASSED
```

---

## 完了条件

- [ ] DAGワークフローの概要説明
- [ ] YAMLの書き方とサンプル
- [ ] `railway sync transition` コマンドの説明
- [ ] ノード実装のサンプルコード
- [ ] エントリーポイントのサンプルコード
- [ ] 状態命名規則の説明
- [ ] ベストプラクティス
- [ ] テストが通過

---

## 次のIssue

- #14: TUTORIAL.md 更新
