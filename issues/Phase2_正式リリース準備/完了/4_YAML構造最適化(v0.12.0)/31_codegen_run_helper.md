# Issue #31: codegen に run() ヘルパー関数を追加

**Phase:** 2
**優先度:** 中
**依存関係:** Issue #27（codegen の終端ノード対応）, Issue #28（dag_runner の終端ノード実行）
**見積もり:** 0.25日

---

## 背景

### 現状の問題

YAML で `start` ノードを定義しているにもかかわらず、`dag_runner` 呼び出し時に再度 `start` を渡す必要がある。

```yaml
# transition_graphs/my_workflow.yml
start: fetch_alert  # ← ここで定義

transitions:
  fetch_alert:
    success::done: process
```

```python
# エントリーポイント
from src.transitions.my_workflow import TRANSITION_TABLE, EXIT_CODES
from nodes.fetch_alert import fetch_alert

result = dag_runner(
    start=fetch_alert,  # ← YAML と重複（不整合リスク）
    transitions=TRANSITION_TABLE,
    exit_codes=EXIT_CODES,
)
```

**問題点:**
1. **冗長:** 同じ情報を2箇所で管理
2. **不整合リスク:** YAML を変更してもコードを更新し忘れる
3. **使いにくい:** 毎回 import と設定が必要

---

## 解決策

`railway sync` で生成するコードに以下を追加:

1. **`START_NODE` 定数:** 開始ノード関数への参照
2. **`run()` ヘルパー関数:** ワークフロー実行を簡略化

---

## 生成されるコード

### Before（現状）

```python
# src/transitions/my_workflow.py
from typing import Callable
from nodes.fetch_alert import fetch_alert
from nodes.process import process

TRANSITION_TABLE: dict[str, Callable] = {
    "fetch_alert::success::done": process,
}

EXIT_CODES: dict[str, int] = {
    "exit.success.done": 0,
}
```

### After（改善後）

```python
# src/transitions/my_workflow.py
"""Auto-generated transition module for my_workflow."""

from typing import Any, Callable

from railway.core.dag import dag_runner, DagRunnerResult

from nodes.fetch_alert import fetch_alert
from nodes.process import process
from nodes.exit.success.done import done as _exit_success_done

# Start node (from YAML: start: fetch_alert)
START_NODE = fetch_alert

TRANSITION_TABLE: dict[str, Callable] = {
    "fetch_alert::success::done": process,
    "process::success::done": _exit_success_done,
}

EXIT_CODES: dict[str, int] = {
    "exit.success.done": 0,
}


def run(
    initial_context: Any,
    *,
    on_step: Callable[[str, str, Any], None] | None = None,
    strict: bool = True,
    max_iterations: int = 100,
) -> DagRunnerResult:
    """このワークフローを実行する。

    YAML の start ノードから自動的に開始し、
    TRANSITION_TABLE と EXIT_CODES を使用する。

    Args:
        initial_context: 開始ノードに渡す初期コンテキスト
        on_step: ステップごとに呼ばれるコールバック
        strict: 未定義の状態でエラーにするか（デフォルト: True）
        max_iterations: 最大反復回数（デフォルト: 100）

    Returns:
        DagRunnerResult: 実行結果

    Example:
        >>> from src.transitions.my_workflow import run
        >>> result = run({"user_id": 123})
        >>> print(result.context)
    """
    return dag_runner(
        start=lambda: START_NODE(initial_context),
        transitions=TRANSITION_TABLE,
        exit_codes=EXIT_CODES,
        on_step=on_step,
        strict=strict,
        max_iterations=max_iterations,
    )
```

---

## 使用例

### シンプルケース（推奨）

```python
from src.transitions.my_workflow import run

# 1行でワークフロー実行
result = run({"user_id": 123})

if result.is_success:
    print(f"完了: {result.context}")
else:
    print(f"失敗: {result.exit_code}")
```

### コールバック付き

```python
from src.transitions.my_workflow import run

def on_step(node_name: str, state: str, ctx: Any) -> None:
    print(f"[{node_name}] {state}")

result = run(
    {"user_id": 123},
    on_step=on_step,
)
```

### 上級者向け（カスタマイズ）

```python
from src.transitions.my_workflow import (
    START_NODE,
    TRANSITION_TABLE,
    EXIT_CODES,
)
from railway.core.dag import dag_runner

# 開始ノードをカスタマイズ
def custom_start():
    # 特殊な初期化処理
    ctx = prepare_context()
    return START_NODE(ctx)

result = dag_runner(
    start=custom_start,
    transitions=TRANSITION_TABLE,
    exit_codes=EXIT_CODES,
)
```

---

## 実装（純粋関数）

### codegen.py への追加

```python
def generate_start_node_constant(graph: TransitionGraph) -> str:
    """START_NODE 定数を生成（純粋関数）。"""
    start_node = _find_node_by_name(graph.nodes, graph.start_node)
    if start_node is None:
        return "# START_NODE: not found"

    return f"# Start node (from YAML: start: {graph.start_node})\nSTART_NODE = {start_node.function}"


def generate_run_helper() -> str:
    """run() と run_async() ヘルパー関数を生成（純粋関数）。"""
    return '''
def run(
    initial_context: Any,
    *,
    on_step: Callable[[str, str, Any], None] | None = None,
    strict: bool = True,
    max_iterations: int = 100,
) -> DagRunnerResult:
    """このワークフローを実行する（同期版）。

    YAML の start ノードから自動的に開始し、
    TRANSITION_TABLE と EXIT_CODES を使用する。

    Args:
        initial_context: 開始ノードに渡す初期コンテキスト
        on_step: ステップごとに呼ばれるコールバック
        strict: 未定義の状態でエラーにするか（デフォルト: True）
        max_iterations: 最大反復回数（デフォルト: 100）

    Returns:
        DagRunnerResult: 実行結果
    """
    return dag_runner(
        start=lambda: START_NODE(initial_context),
        transitions=TRANSITION_TABLE,
        exit_codes=EXIT_CODES,
        on_step=on_step,
        strict=strict,
        max_iterations=max_iterations,
    )


async def run_async(
    initial_context: Any,
    *,
    on_step: Callable[[str, str, Any], None] | None = None,
    strict: bool = True,
    max_iterations: int = 100,
) -> DagRunnerResult:
    """このワークフローを実行する（非同期版）。

    非同期ノードを使用するワークフロー向け。

    Args:
        initial_context: 開始ノードに渡す初期コンテキスト
        on_step: ステップごとに呼ばれるコールバック
        strict: 未定義の状態でエラーにするか（デフォルト: True）
        max_iterations: 最大反復回数（デフォルト: 100）

    Returns:
        DagRunnerResult: 実行結果
    """
    return await async_dag_runner(
        start=lambda: START_NODE(initial_context),
        transitions=TRANSITION_TABLE,
        exit_codes=EXIT_CODES,
        on_step=on_step,
        strict=strict,
        max_iterations=max_iterations,
    )
'''
```

### テンプレート更新

```python
TRANSITION_MODULE_TEMPLATE = '''
"""Auto-generated transition module for {entrypoint}."""

from typing import Any, Callable

from railway.core.dag import dag_runner, async_dag_runner, DagRunnerResult

{imports}

{start_node_constant}

{transition_table}

{exit_codes}

{run_helper}
'''
```

---

## TDD 実装手順

### Step 1: テスト（Red）

```python
# tests/unit/dag/test_codegen_run_helper.py
"""Tests for codegen run helper generation."""

import pytest
from railway.core.dag.codegen import (
    generate_start_node_constant,
    generate_run_helper,
    generate_transition_code,
)
from railway.core.dag.types import (
    NodeDefinition,
    TransitionGraph,
)


class TestGenerateStartNodeConstant:
    """START_NODE 定数生成テスト。"""

    def test_generates_start_node_constant(self) -> None:
        """START_NODE 定数が生成される。"""
        nodes = (
            NodeDefinition(
                name="fetch_alert",
                module="nodes.fetch_alert",
                function="fetch_alert",
                description="アラート取得",
            ),
        )
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=nodes,
            exits=(),
            transitions=(),
            start_node="fetch_alert",
            options=None,
        )

        result = generate_start_node_constant(graph)

        assert "START_NODE = fetch_alert" in result


class TestGenerateRunHelper:
    """run() ヘルパー関数生成テスト。"""

    def test_generates_run_function(self) -> None:
        """run() 関数が生成される。"""
        result = generate_run_helper()

        assert "def run(" in result
        assert "initial_context: Any" in result
        assert "on_step:" in result
        assert "dag_runner(" in result
        assert "START_NODE" in result


class TestGenerateTransitionCodeWithRunHelper:
    """run() ヘルパー込みの統合テスト。"""

    def test_generated_code_includes_run_helper(self) -> None:
        """生成コードに run() が含まれる。"""
        nodes = (
            NodeDefinition(
                name="start",
                module="nodes.start",
                function="start",
                description="開始",
            ),
        )
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=nodes,
            exits=(),
            transitions=(),
            start_node="start",
            options=None,
        )

        code = generate_transition_code(graph, "test.yml")

        assert "START_NODE = start" in code
        assert "def run(" in code
        assert "from railway.core.dag import dag_runner" in code

    def test_generated_code_is_valid_python(self) -> None:
        """生成コードが有効な Python。"""
        nodes = (
            NodeDefinition(
                name="start",
                module="nodes.start",
                function="start",
                description="開始",
            ),
        )
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=nodes,
            exits=(),
            transitions=(),
            start_node="start",
            options=None,
        )

        code = generate_transition_code(graph, "test.yml")

        # Python として構文解析可能
        compile(code, "<string>", "exec")
```

---

## 完了条件

- [ ] `generate_start_node_constant` 関数追加
- [ ] `generate_run_helper` 関数追加（run, run_async 両方生成）
- [ ] テンプレートに START_NODE, run(), run_async() を追加
- [ ] `from railway.core.dag import dag_runner, async_dag_runner, DagRunnerResult` を import に追加
- [ ] 生成コードが有効な Python
- [ ] 既存テスト通過
- [ ] 新規テスト通過

---

## 関連 Issue

- Issue #27: codegen の終端ノード対応（前提）
- Issue #28: dag_runner の終端ノード実行
- Issue #30: E2E 統合テスト（テストケース追加）
