# Issue #27: codegen の終端ノード対応

**Phase:** 2
**優先度:** 高
**依存関係:** Issue #24, #25（NodeDefinition, パーサー）
**見積もり:** 0.5日

---

## 概要

コード生成（codegen）を更新し、終端ノードの import 文と `EXIT_CODES` マッピングを生成する。

---

## 生成されるコード

### Before（現状）

```python
# transition_table.py
from nodes.start import start
from nodes.process import process

TRANSITION_TABLE: dict[str, Callable] = {
    "start::success::done": process,
}
```

### After（新形式）

```python
# transition_table.py
"""Auto-generated transition table."""

from typing import Callable

from nodes.start import start
from nodes.process import process
from nodes.exit.success.done import done as _exit_success_done
from nodes.exit.failure.timeout import timeout as _exit_failure_timeout

# ノード名属性の設定（dag_runner がノード名を取得するために必要）
start._node_name = "start"
process._node_name = "process"
_exit_success_done._node_name = "exit.success.done"
_exit_failure_timeout._node_name = "exit.failure.timeout"

TRANSITION_TABLE: dict[str, Callable] = {
    "start::success::done": process,
    "process::success::done": _exit_success_done,
    "process::failure::timeout": _exit_failure_timeout,
}

EXIT_CODES: dict[str, int] = {
    "exit.success.done": 0,
    "exit.failure.timeout": 1,
}


def get_exit_code(node_name: str) -> int | None:
    """終端ノードの終了コードを取得する。

    Args:
        node_name: ノード名

    Returns:
        終了コード（終端ノードでない場合は None）
    """
    return EXIT_CODES.get(node_name)
```

**重要:** `_node_name` 属性は `dag_runner` がノード名を取得するために必要です。
Issue #28 のテストでは手動設定していますが、生成コードでは自動設定されます。

---

## 設計上の注意点

### 遷移先の判定

**重要:** 新形式では遷移先が `exit.success.done` のようなノード名になります。
`StateTransition.is_exit` プロパティは旧形式 `exit::` をチェックするため、使用しません。

代わりに、遷移先ノードを `graph.nodes` から検索し、`is_exit` プロパティをチェックします。

```python
# 正しいアプローチ
target_node = _find_node_by_name(graph.nodes, transition.to_target)
if target_node and target_node.is_exit:
    # 終端ノードへの遷移
    ...
```

---

## 実装（純粋関数）

### 1. ヘルパー関数

```python
def _find_node_by_name(
    nodes: tuple[NodeDefinition, ...],
    name: str,
) -> NodeDefinition | None:
    """ノード名からノードを検索（純粋関数）。"""
    return next((n for n in nodes if n.name == name), None)


def _node_to_alias(node: NodeDefinition) -> str:
    """ノード名からエイリアスを生成（純粋関数）。

    終端ノードは関数名が衝突する可能性があるため、
    ノード名をエイリアスとして使用する。

    例: "exit.success.done" → "_exit_success_done"

    Note:
        アンダースコアプレフィックスで通常ノードとの衝突を回避。
        通常ノード名に "_exit_" プレフィックスは使用しない規約。
    """
    return "_" + node.name.replace(".", "_")
```

### 2. import 文生成

```python
def generate_imports(graph: TransitionGraph) -> str:
    """すべてのノード（終端含む）のimport文を生成（純粋関数）。

    終端ノードは関数名が衝突する可能性があるため、
    エイリアスを付ける（例: done as exit_success_done）。
    """
    import_lines: list[str] = []

    for node in graph.nodes:
        if not node.has_handler:
            continue

        if node.is_exit:
            # 終端ノードはエイリアス付き
            alias = _node_to_alias(node)
            import_lines.append(
                f"from {node.module} import {node.function} as {alias}"
            )
        else:
            import_lines.append(
                f"from {node.module} import {node.function}"
            )

    return "\n".join(import_lines)


def generate_node_name_assignments(graph: TransitionGraph) -> str:
    """全ノードの _node_name 属性設定コードを生成（純粋関数）。

    dag_runner がノード名を取得するために必要。
    """
    lines: list[str] = ["# ノード名属性の設定（dag_runner がノード名を取得するために必要）"]

    for node in graph.nodes:
        if not node.has_handler:
            continue

        if node.is_exit:
            alias = _node_to_alias(node)
            lines.append(f'{alias}._node_name = "{node.name}"')
        else:
            lines.append(f'{node.function}._node_name = "{node.name}"')

    return "\n".join(lines)
```

### 3. EXIT_CODES 生成

```python
def generate_exit_codes(graph: TransitionGraph) -> str:
    """終端ノードの終了コードマッピングを生成（純粋関数）。"""
    exit_nodes = tuple(
        n for n in graph.nodes
        if n.is_exit and n.exit_code is not None
    )

    if not exit_nodes:
        return "EXIT_CODES: dict[str, int] = {}"

    entries = (
        f'    "{node.name}": {node.exit_code},'
        for node in exit_nodes
    )
    return "\n".join((
        "EXIT_CODES: dict[str, int] = {",
        *entries,
        "}",
    ))
```

### 4. TRANSITION_TABLE 生成（修正版）

```python
def generate_transition_table(graph: TransitionGraph) -> str:
    """遷移テーブルを生成（純粋関数）。

    終端ノードへの遷移も含める。
    終端ノードの関数名はエイリアスを使用。

    Note:
        StateTransition.is_exit は旧形式 (exit::) をチェックするため使用しない。
        代わりに遷移先ノードを検索して is_exit を確認する。
    """
    entries: list[str] = []

    for transition in graph.transitions:
        state_string = f"{transition.from_node}::{transition.from_state}"

        # 遷移先ノードを検索
        target_node = _find_node_by_name(graph.nodes, transition.to_target)

        if target_node is None:
            # バリデーションで検出されるべきエラー
            continue

        if target_node.is_exit:
            # 終端ノードへの遷移（エイリアスを使用）
            if target_node.has_handler:
                alias = _node_to_alias(target_node)
                entries.append(f'    "{state_string}": {alias},')
            # ハンドラがない終端ノードは TRANSITION_TABLE に含めない
            # （dag_runner が EXIT_CODES で終端を判定する）
        else:
            # 通常ノードへの遷移
            entries.append(
                f'    "{state_string}": {target_node.function},'
            )

    return "\n".join((
        "TRANSITION_TABLE: dict[str, Callable] = {",
        *entries,
        "}",
    ))
```

### 5. ヘルパー関数生成

```python
def generate_exit_code_helper() -> str:
    """終了コード取得ヘルパーを生成。"""
    return '''
def get_exit_code(node_name: str) -> int | None:
    """終端ノードの終了コードを取得する。

    Args:
        node_name: ノード名

    Returns:
        終了コード（終端ノードでない場合は None）
    """
    return EXIT_CODES.get(node_name)
'''
```

---

## TDD 実装手順

### Step 1: codegen テスト（Red）

```python
# tests/unit/dag/test_codegen_exit.py
"""Tests for codegen exit node support."""

import pytest
from railway.core.dag.codegen import (
    generate_imports,
    generate_exit_codes,
    generate_transition_table,
    generate_transition_code,
    _find_node_by_name,
    _node_to_alias,
)
from railway.core.dag.types import (
    NodeDefinition,
    StateTransition,
    TransitionGraph,
)


class TestHelperFunctions:
    """ヘルパー関数テスト。"""

    def test_find_node_by_name_found(self) -> None:
        """ノードが見つかる。"""
        nodes = (
            NodeDefinition(
                name="start",
                module="nodes.start",
                function="start",
                description="開始",
            ),
        )
        result = _find_node_by_name(nodes, "start")
        assert result is not None
        assert result.name == "start"

    def test_find_node_by_name_not_found(self) -> None:
        """ノードが見つからない。"""
        nodes = (
            NodeDefinition(
                name="start",
                module="nodes.start",
                function="start",
                description="開始",
            ),
        )
        result = _find_node_by_name(nodes, "nonexistent")
        assert result is None

    def test_node_to_alias(self) -> None:
        """ノード名からエイリアスを生成。"""
        node = NodeDefinition(
            name="exit.success.done",
            module="nodes.exit.success.done",
            function="done",
            description="正常終了",
            is_exit=True,
            exit_code=0,
        )
        assert _node_to_alias(node) == "_exit_success_done"


class TestGenerateImports:
    """import 文生成テスト。"""

    def test_generates_normal_node_import(self) -> None:
        """通常ノードの import 文。"""
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

        result = generate_imports(graph)

        assert "from nodes.start import start" in result

    def test_generates_exit_node_import_with_alias(self) -> None:
        """終端ノードはエイリアス付きでインポート。"""
        nodes = (
            NodeDefinition(
                name="exit.success.done",
                module="nodes.exit.success.done",
                function="done",
                description="正常終了",
                is_exit=True,
                exit_code=0,
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

        result = generate_imports(graph)

        assert "from nodes.exit.success.done import done as _exit_success_done" in result

    def test_skips_node_without_handler(self) -> None:
        """ハンドラのないノードは import しない。"""
        nodes = (
            NodeDefinition(
                name="exit.success.done",
                module="",
                function="",
                description="正常終了（ハンドラなし）",
                is_exit=True,
                exit_code=0,
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

        result = generate_imports(graph)

        assert result == ""


class TestGenerateExitCodes:
    """EXIT_CODES 生成テスト。"""

    def test_generates_exit_codes_mapping(self) -> None:
        """EXIT_CODES マッピングが生成される。"""
        nodes = (
            NodeDefinition(
                name="exit.success.done",
                module="nodes.exit.success.done",
                function="done",
                description="正常終了",
                is_exit=True,
                exit_code=0,
            ),
            NodeDefinition(
                name="exit.failure.timeout",
                module="nodes.exit.failure.timeout",
                function="timeout",
                description="タイムアウト",
                is_exit=True,
                exit_code=1,
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

        result = generate_exit_codes(graph)

        assert "EXIT_CODES: dict[str, int] = {" in result
        assert '"exit.success.done": 0' in result
        assert '"exit.failure.timeout": 1' in result

    def test_empty_when_no_exit_nodes(self) -> None:
        """終端ノードがない場合は空の dict。"""
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

        result = generate_exit_codes(graph)

        assert result == "EXIT_CODES: dict[str, int] = {}"


class TestGenerateTransitionTable:
    """TRANSITION_TABLE 生成テスト。"""

    def test_transition_to_exit_node_uses_alias(self) -> None:
        """終端ノードへの遷移はエイリアスを使用。"""
        nodes = (
            NodeDefinition(
                name="process",
                module="nodes.process",
                function="process",
                description="処理",
            ),
            NodeDefinition(
                name="exit.success.done",
                module="nodes.exit.success.done",
                function="done",
                description="正常終了",
                is_exit=True,
                exit_code=0,
            ),
        )
        transitions = (
            StateTransition(
                from_node="process",
                from_state="success::done",
                to_target="exit.success.done",  # 新形式
            ),
        )
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=nodes,
            exits=(),
            transitions=transitions,
            start_node="process",
            options=None,
        )

        result = generate_transition_table(graph)

        # エイリアスを使用（アンダースコアプレフィックス）
        assert '"process::success::done": _exit_success_done' in result

    def test_transition_to_normal_node(self) -> None:
        """通常ノードへの遷移は関数名を使用。"""
        nodes = (
            NodeDefinition(
                name="start",
                module="nodes.start",
                function="start",
                description="開始",
            ),
            NodeDefinition(
                name="process",
                module="nodes.process",
                function="process",
                description="処理",
            ),
        )
        transitions = (
            StateTransition(
                from_node="start",
                from_state="success::done",
                to_target="process",
            ),
        )
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=nodes,
            exits=(),
            transitions=transitions,
            start_node="start",
            options=None,
        )

        result = generate_transition_table(graph)

        assert '"start::success::done": process' in result

    def test_skips_exit_node_without_handler(self) -> None:
        """ハンドラのない終端ノードは TRANSITION_TABLE に含めない。"""
        nodes = (
            NodeDefinition(
                name="start",
                module="nodes.start",
                function="start",
                description="開始",
            ),
            NodeDefinition(
                name="exit.success.done",
                module="",  # ハンドラなし
                function="",
                description="正常終了",
                is_exit=True,
                exit_code=0,
            ),
        )
        transitions = (
            StateTransition(
                from_node="start",
                from_state="success::done",
                to_target="exit.success.done",
            ),
        )
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=nodes,
            exits=(),
            transitions=transitions,
            start_node="start",
            options=None,
        )

        result = generate_transition_table(graph)

        # ハンドラがない終端ノードへの遷移は含まれない
        assert "_exit_success_done" not in result


class TestGenerateTransitionCodeIntegration:
    """統合テスト。"""

    def test_generated_code_is_valid_python(self) -> None:
        """生成されたコードが有効な Python。"""
        nodes = (
            NodeDefinition(
                name="start",
                module="nodes.start",
                function="start",
                description="開始",
            ),
            NodeDefinition(
                name="exit.success.done",
                module="nodes.exit.success.done",
                function="done",
                description="正常終了",
                is_exit=True,
                exit_code=0,
            ),
        )
        transitions = (
            StateTransition(
                from_node="start",
                from_state="success::done",
                to_target="exit.success.done",
            ),
        )
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=nodes,
            exits=(),
            transitions=transitions,
            start_node="start",
            options=None,
        )

        code = generate_transition_code(graph, "test.yml")

        # Python として構文解析可能
        compile(code, "<string>", "exec")

    def test_includes_exit_codes_and_helper(self) -> None:
        """EXIT_CODES とヘルパー関数が含まれる。"""
        nodes = (
            NodeDefinition(
                name="exit.success.done",
                module="nodes.exit.success.done",
                function="done",
                description="正常終了",
                is_exit=True,
                exit_code=0,
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

        assert "EXIT_CODES" in code
        assert "def get_exit_code" in code
```

---

## 完了条件

- [ ] `_find_node_by_name` ヘルパー関数
- [ ] `_node_to_alias` ヘルパー関数
- [ ] 終端ノードの import 文生成（エイリアス付き）
- [ ] `generate_node_name_assignments` 関数（`_node_name` 属性設定コード生成）
- [ ] `EXIT_CODES` マッピング生成
- [ ] `get_exit_code` ヘルパー関数生成
- [ ] ハンドラのない終端ノードは import しない
- [ ] 新形式の遷移先（`exit.success.done`）を正しく処理
- [ ] 生成コードが有効な Python
- [ ] 既存テスト通過
- [ ] 新規テスト通過

---

## 関連 Issue

- Issue #24: NodeDefinition の終端ノード対応（前提）
- Issue #25: パーサーのネスト構造対応（前提）
- Issue #28: dag_runner の終端ノード実行
