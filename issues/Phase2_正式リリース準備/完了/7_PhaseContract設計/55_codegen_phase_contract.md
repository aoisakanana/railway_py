# Issue #55: Codegen 依存対応

## 概要

コード生成を更新し、フィールドベース依存関係に対応した遷移コードを生成する。

## 背景

フィールドベース依存関係では、依存情報はノードコードに存在し、YAML には書かない。
そのため、codegen の変更は最小限で済む。

## 設計

### 変更点

| 項目 | 変更内容 |
|------|---------|
| `CONTRACT_TYPES` | **削除**（YAML に contracts がないため） |
| `NODE_TYPES` | **削除**（型情報は YAML にないため） |
| `run()` 関数 | 型パラメータは **任意**（ノードから推論可能） |

### 生成されるコードの例

**Before (Phase Contract 型ベース - 削除):**

```python
# CONTRACT_TYPES, NODE_TYPES は生成しない
```

**After (フィールドベース):**

```python
# 自動生成コード - 編集不要
from nodes.check_host import check_host
from nodes.escalate import escalate
from nodes.exit.success.done import done as exit_success_done

TRANSITIONS = {
    "check_host::success::found": escalate,
    "escalate::success::done": exit_success_done,
}


def run(initial_data: dict) -> ExitContract:
    """ワークフローを実行する。

    Args:
        initial_data: 初期データ（dict）

    Note:
        依存検証は `railway sync transition` で実行済み。
        ノードが宣言した requires/provides に基づいて検証されている。
    """
    return dag_runner(
        start=lambda: (WorkflowContext(**initial_data), Outcome.success("start")),
        transitions=TRANSITIONS,
    )
```

### 初期コンテキストの推論

開始ノードの型ヒントから初期コンテキストの型を推論できる:

```python
# nodes/check_host.py
@node(requires=["incident_id"], provides=["hostname"])
def check_host(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
    ...
```

↓ codegen が解析

```python
# 生成コード
from contracts.workflow import WorkflowContext

def run(initial_data: dict) -> ExitContract:
    # WorkflowContext を自動検出
    return dag_runner(
        start=lambda: (WorkflowContext(**initial_data), Outcome.success("start")),
        ...
    )
```

## タスク

### 1. Red Phase: 失敗するテストを作成

`tests/unit/core/dag/test_codegen_dependency.py`:

```python
"""依存ベースコード生成テスト。"""

import pytest
from railway.core.dag.codegen import generate_transition_code
from railway.core.dag.types import TransitionGraph, NodeDefinition


class TestCodegenWithDependencies:
    """依存宣言があるノードのコード生成テスト。"""

    def test_no_contract_types_generated(self) -> None:
        """CONTRACT_TYPES は生成されない。"""
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            contracts={},  # 空（依存は YAML にない）
            nodes={
                "start": NodeDefinition(
                    name="start",
                    module="nodes.start",
                    function="start",
                    description="",
                ),
            },
            start="start",
            transitions={},
        )

        code = generate_transition_code(graph, "test.yml")

        assert "CONTRACT_TYPES" not in code
        assert "NODE_TYPES" not in code

    def test_generates_transitions_dict(self) -> None:
        """TRANSITIONS dict を生成する。"""
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            contracts={},
            nodes={
                "check_host": NodeDefinition(
                    name="check_host",
                    module="nodes.check_host",
                    function="check_host",
                    description="",
                ),
                "escalate": NodeDefinition(
                    name="escalate",
                    module="nodes.escalate",
                    function="escalate",
                    description="",
                ),
            },
            start="check_host",
            transitions={
                "check_host": {"success::found": "escalate"},
            },
        )

        code = generate_transition_code(graph, "test.yml")

        assert "TRANSITIONS" in code
        assert '"check_host::success::found": escalate' in code

    def test_generates_run_function(self) -> None:
        """run() 関数を生成する。"""
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            contracts={},
            nodes={
                "start": NodeDefinition(
                    name="start",
                    module="nodes.start",
                    function="start",
                    description="",
                ),
            },
            start="start",
            transitions={},
        )

        code = generate_transition_code(graph, "test.yml")

        assert "def run(" in code
        assert "dag_runner(" in code


class TestCodegenContextTypeDetection:
    """コンテキスト型検出テスト。"""

    def test_detects_context_type_from_start_node(self, tmp_path, monkeypatch) -> None:
        """開始ノードからコンテキスト型を検出する。"""
        # テスト用ノードモジュールを作成
        nodes_dir = tmp_path / "nodes"
        nodes_dir.mkdir()
        (nodes_dir / "__init__.py").write_text("")
        (nodes_dir / "start.py").write_text('''
from railway import Contract, node
from railway.core.dag import Outcome

class MyContext(Contract):
    value: str

@node
def start(ctx: MyContext) -> tuple[MyContext, Outcome]:
    return ctx, Outcome.success("done")
''')

        import sys
        monkeypatch.syspath_prepend(str(tmp_path))

        from railway.core.dag.codegen import detect_context_type

        context_type = detect_context_type("nodes.start", "start")
        assert context_type == "MyContext"


class TestCodegenDocstrings:
    """生成コードの docstring テスト。"""

    def test_includes_dependency_validation_note(self) -> None:
        """依存検証に関する注記を含む。"""
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            contracts={},
            nodes={
                "start": NodeDefinition(
                    name="start",
                    module="nodes.start",
                    function="start",
                    description="",
                ),
            },
            start="start",
            transitions={},
        )

        code = generate_transition_code(graph, "test.yml")

        # 依存検証済みであることを示す注記
        assert "railway sync transition" in code or "依存検証" in code
```

### 2. Green Phase: Codegen 更新

`railway/core/dag/codegen.py` を更新:

```python
def detect_context_type(module_path: str, function_name: str) -> str | None:
    """開始ノードからコンテキスト型を検出する。

    Args:
        module_path: モジュールパス
        function_name: 関数名

    Returns:
        コンテキスト型名（検出できない場合は None）
    """
    try:
        import importlib
        import inspect

        module = importlib.import_module(module_path)
        func = getattr(module, function_name)
        hints = inspect.get_type_hints(func)

        # 第一引数の型を取得
        params = list(hints.keys())
        if params and params[0] != "return":
            return hints[params[0]].__name__
    except Exception:
        pass
    return None


def generate_transition_code(graph: TransitionGraph, yaml_path: str) -> str:
    """遷移コードを生成する。

    Note:
        フィールドベース依存関係では、YAML に contracts がないため、
        CONTRACT_TYPES, NODE_TYPES は生成しない。
    """
    lines = [
        '"""遷移定義（自動生成）。',
        "",
        f"Source: {yaml_path}",
        "",
        "Note:",
        "    このファイルは `railway sync transition` で自動生成されます。",
        "    依存検証は sync 時に実行済みです。",
        '"""',
        "",
        "from railway import ExitContract",
        "from railway.core.dag import dag_runner, Outcome",
        "",
    ]

    # ノードの import
    for node_name, node_def in graph.nodes.items():
        if node_def.is_exit:
            # 終端ノードはエイリアス付き
            alias = node_name.replace(".", "_")
            lines.append(
                f"from {node_def.module} import {node_def.function} as {alias}"
            )
        else:
            lines.append(f"from {node_def.module} import {node_def.function}")

    lines.append("")
    lines.append("")

    # TRANSITIONS
    lines.append("TRANSITIONS = {")
    for from_node, transitions in graph.transitions.items():
        for outcome, to_node in transitions.items():
            to_ref = to_node.replace(".", "_") if to_node.startswith("exit.") else to_node
            lines.append(f'    "{from_node}::{outcome}": {to_ref},')
    lines.append("}")
    lines.append("")
    lines.append("")

    # run() 関数
    lines.extend([
        "def run(initial_data: dict) -> ExitContract:",
        '    """ワークフローを実行する。',
        "",
        "    Args:",
        "        initial_data: 初期データ",
        "",
        "    Returns:",
        "        ExitContract: 終了結果",
        "",
        "    Note:",
        "        依存検証は `railway sync transition` で実行済み。",
        '    """',
        "    return dag_runner(",
        f"        start={graph.start},",
        "        transitions=TRANSITIONS,",
        "    )",
    ])

    return "\n".join(lines)
```

### 3. Refactor Phase

- import 文の整理
- 生成コードのフォーマット改善
- テストケース追加

## 完了条件

- [ ] `CONTRACT_TYPES`, `NODE_TYPES` は生成されない
- [ ] `TRANSITIONS` dict が正しく生成される
- [ ] `run()` 関数が生成される
- [ ] コンテキスト型の検出が動作する（オプション）
- [ ] すべてのテストが通過

## 依存関係

- Issue #53 (依存情報の自動抽出) が完了していること

## 関連ファイル

- `railway/core/dag/codegen.py` (更新)
- `tests/unit/core/dag/test_codegen_dependency.py` (新規)
