# Issue #53: 依存情報の自動抽出

## 概要

ノードの Python コードから依存情報（`_field_dependency`）を自動抽出する機能を実装する。
**YAML には依存情報を書かない** - フレームワークがノードコードから読み取る。

## 設計

### 基本方針

```
YAML（遷移のみ）    +    ノードコード（依存宣言）    =    依存検証
       ↓                         ↓                            ↓
  transitions:              @node(requires=...)          sync で自動検証
    A → B                   def node_b(ctx): ...
```

### 依存情報の取得方法

```python
def extract_field_dependency(node_func: Callable) -> FieldDependency | None:
    """ノード関数から FieldDependency を抽出する。

    Args:
        node_func: @node デコレータが適用された関数

    Returns:
        FieldDependency または None（依存宣言がない場合）
    """
    return getattr(node_func, "_field_dependency", None)
```

### ノードのロードと依存抽出

```python
def load_node_dependencies(
    graph: TransitionGraph,
) -> dict[str, FieldDependency]:
    """遷移グラフの全ノードから依存情報を抽出する。

    Args:
        graph: 遷移グラフ

    Returns:
        ノード名 → FieldDependency のマッピング
    """
    dependencies = {}
    for node_name, node_def in graph.nodes.items():
        # ノード関数をインポート
        node_func = import_node_function(node_def.module, node_def.function)
        # 依存情報を抽出
        dep = extract_field_dependency(node_func)
        if dep:
            dependencies[node_name] = dep
    return dependencies
```

### 初期フィールドの自動導出

**YAML には initial_context を書かない。** 開始ノードの Contract 型から自動導出する:

```python
def extract_initial_fields_from_start_node(
    graph: TransitionGraph,
) -> AvailableFields:
    """開始ノードの Contract から初期フィールドを自動導出する。

    YAML には何も書かない。ノードの型ヒントから自動抽出。

    Args:
        graph: 遷移グラフ

    Returns:
        AvailableFields: 開始時に利用可能なフィールド
    """
    start_node_def = graph.nodes[graph.start]
    node_func = import_node_function(start_node_def.module, start_node_def.function)

    hints = get_type_hints(node_func)
    ctx_type = hints.get("ctx")

    if ctx_type and hasattr(ctx_type, "model_fields"):
        # Pydantic BaseModel のフィールドを取得
        # is_required() でデフォルト値のないフィールドを特定
        required_fields = {
            name for name, field in ctx_type.model_fields.items()
            if field.is_required()
        }
        return AvailableFields(frozenset(required_fields))

    return AvailableFields(frozenset())
```

**設計判断:**
- YAML に `initial_context` や `contracts` セクションを追加しない
- 開始ノードの第一引数（ctx）の型ヒントから Contract 型を取得
- `is_required()` で必須フィールド（デフォルト値なし）を初期フィールドとして扱う
- Optional フィールドは初期フィールドに含まれない（ノードが provides する前提）

## タスク

### 1. Red Phase: 失敗するテストを作成

`tests/unit/core/dag/test_dependency_extraction.py`:

```python
"""依存情報の自動抽出テスト。"""

import pytest
from railway import Contract, node
from railway.core.dag import Outcome
from railway.core.dag.field_dependency import FieldDependency
from railway.core.dag.dependency_extraction import (
    extract_field_dependency,
    load_node_dependencies,
)


class WorkflowContext(Contract):
    incident_id: str
    hostname: str | None = None


class TestExtractFieldDependency:
    """単一ノードからの依存抽出テスト。"""

    def test_extracts_from_decorated_node(self) -> None:
        """@node デコレータ付きノードから依存を抽出する。"""
        @node(requires=["incident_id"], optional=["hostname"], provides=["result"])
        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        dep = extract_field_dependency(my_node)

        assert dep is not None
        assert dep.requires == frozenset(["incident_id"])
        assert dep.optional == frozenset(["hostname"])
        assert dep.provides == frozenset(["result"])

    def test_returns_none_for_undecorated_function(self) -> None:
        """デコレータなし関数は None を返す。"""
        def plain_function(ctx):
            return ctx

        dep = extract_field_dependency(plain_function)
        assert dep is None

    def test_returns_empty_dependency_for_node_without_declarations(self) -> None:
        """依存宣言なしの @node は空の FieldDependency を返す。"""
        @node
        def simple_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        dep = extract_field_dependency(simple_node)

        assert dep is not None
        assert dep.requires == frozenset()
        assert dep.optional == frozenset()
        assert dep.provides == frozenset()


class TestLoadNodeDependencies:
    """遷移グラフからの依存ロードテスト。"""

    def test_loads_dependencies_from_graph(self, tmp_path, monkeypatch) -> None:
        """遷移グラフの全ノードから依存を読み込む。"""
        from railway.core.dag.types import TransitionGraph, NodeDefinition

        # テスト用ノードモジュールを作成
        nodes_dir = tmp_path / "nodes"
        nodes_dir.mkdir()
        (nodes_dir / "__init__.py").write_text("")
        (nodes_dir / "check_host.py").write_text('''
from railway import Contract, node
from railway.core.dag import Outcome

class Ctx(Contract):
    incident_id: str

@node(requires=["incident_id"], provides=["hostname"])
def check_host(ctx: Ctx) -> tuple[Ctx, Outcome]:
    return ctx, Outcome.success("done")
''')

        # sys.path に追加
        import sys
        monkeypatch.syspath_prepend(str(tmp_path))

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
            },
            start="check_host",
            transitions={},
        )

        deps = load_node_dependencies(graph)

        assert "check_host" in deps
        assert deps["check_host"].requires == frozenset(["incident_id"])
        assert deps["check_host"].provides == frozenset(["hostname"])


class TestDependencyExtractionEdgeCases:
    """エッジケースのテスト。"""

    def test_handles_exit_node(self) -> None:
        """終端ノードからも依存を抽出できる。"""
        from railway import ExitContract

        class DoneResult(ExitContract):
            exit_state: str = "success.done"

        @node(name="exit.success.done", requires=["processed"])
        def done(ctx) -> DoneResult:
            return DoneResult()

        dep = extract_field_dependency(done)

        assert dep is not None
        assert dep.requires == frozenset(["processed"])

    def test_handles_async_node(self) -> None:
        """非同期ノードからも依存を抽出できる。"""
        @node(requires=["data"], provides=["result"])
        async def async_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        dep = extract_field_dependency(async_node)

        assert dep is not None
        assert dep.requires == frozenset(["data"])


class TestExtractInitialFieldsFromStartNode:
    """開始ノードからの初期フィールド導出テスト。"""

    def test_extracts_required_fields_from_contract(self, tmp_path, monkeypatch) -> None:
        """Contract の必須フィールドを初期フィールドとして抽出する。"""
        from railway.core.dag.types import TransitionGraph, NodeDefinition

        # テスト用ノードモジュールを作成
        nodes_dir = tmp_path / "nodes"
        nodes_dir.mkdir()
        (nodes_dir / "__init__.py").write_text("")
        (nodes_dir / "start.py").write_text('''
from railway import Contract, node
from railway.core.dag import Outcome

class WorkflowContext(Contract):
    incident_id: str          # 必須（初期フィールド）
    severity: str             # 必須（初期フィールド）
    hostname: str | None = None  # Optional（初期フィールドではない）

@node
def start(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
    return ctx, Outcome.success("done")
''')

        import sys
        monkeypatch.syspath_prepend(str(tmp_path))

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

        initial = extract_initial_fields_from_start_node(graph)

        # 必須フィールドのみが初期フィールド
        assert "incident_id" in initial.fields
        assert "severity" in initial.fields
        assert "hostname" not in initial.fields  # Optional は含まれない

    def test_returns_empty_when_no_type_hint(self, tmp_path, monkeypatch) -> None:
        """型ヒントがない場合は空の AvailableFields を返す。"""
        from railway.core.dag.types import TransitionGraph, NodeDefinition

        nodes_dir = tmp_path / "nodes"
        nodes_dir.mkdir()
        (nodes_dir / "__init__.py").write_text("")
        (nodes_dir / "start.py").write_text('''
from railway import node
from railway.core.dag import Outcome

@node
def start(ctx):  # 型ヒントなし
    return ctx, Outcome.success("done")
''')

        import sys
        monkeypatch.syspath_prepend(str(tmp_path))

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

        initial = extract_initial_fields_from_start_node(graph)

        assert initial.fields == frozenset()
```

### 2. Green Phase: 実装

`railway/core/dag/dependency_extraction.py`:

```python
"""依存情報の自動抽出。

ノードの Python コードから FieldDependency を抽出する。
"""

from __future__ import annotations

import importlib
from typing import Any, Callable

from railway.core.dag.field_dependency import FieldDependency
from railway.core.dag.types import TransitionGraph


def extract_field_dependency(node_func: Callable[..., Any]) -> FieldDependency | None:
    """ノード関数から FieldDependency を抽出する。

    Args:
        node_func: @node デコレータが適用された関数

    Returns:
        FieldDependency または None（依存宣言がない場合）
    """
    return getattr(node_func, "_field_dependency", None)


def import_node_function(module_path: str, function_name: str) -> Callable[..., Any]:
    """ノード関数をインポートする。

    Args:
        module_path: モジュールパス（例: "nodes.check_host"）
        function_name: 関数名（例: "check_host"）

    Returns:
        ノード関数

    Raises:
        ImportError: モジュールが見つからない場合
        AttributeError: 関数が見つからない場合
    """
    module = importlib.import_module(module_path)
    return getattr(module, function_name)


def load_node_dependencies(
    graph: TransitionGraph,
) -> dict[str, FieldDependency]:
    """遷移グラフの全ノードから依存情報を抽出する。

    Args:
        graph: 遷移グラフ

    Returns:
        ノード名 → FieldDependency のマッピング
        依存宣言がないノードは含まれない
    """
    dependencies: dict[str, FieldDependency] = {}

    for node_name, node_def in graph.nodes.items():
        try:
            node_func = import_node_function(node_def.module, node_def.function)
            dep = extract_field_dependency(node_func)
            if dep is not None:
                dependencies[node_name] = dep
        except (ImportError, AttributeError) as e:
            # ノードがまだ実装されていない場合はスキップ
            # sync 時に別のエラーとして報告される
            pass

    return dependencies


def extract_initial_fields_from_start_node(
    graph: TransitionGraph,
) -> AvailableFields:
    """開始ノードの Contract から初期フィールドを自動導出する。

    YAML には何も書かない。ノードの型ヒントから自動抽出。

    Args:
        graph: 遷移グラフ

    Returns:
        AvailableFields: 開始時に利用可能なフィールド
    """
    from typing import get_type_hints
    from railway.core.dag.field_dependency import AvailableFields

    start_node_def = graph.nodes[graph.start]

    try:
        node_func = import_node_function(start_node_def.module, start_node_def.function)
        hints = get_type_hints(node_func)
        ctx_type = hints.get("ctx")

        if ctx_type and hasattr(ctx_type, "model_fields"):
            # Pydantic BaseModel のフィールドを取得
            # is_required() でデフォルト値のないフィールドを特定
            required_fields = {
                name for name, field in ctx_type.model_fields.items()
                if field.is_required()
            }
            return AvailableFields(frozenset(required_fields))

    except (ImportError, AttributeError, TypeError):
        # 型情報が取得できない場合は空を返す
        pass

    return AvailableFields(frozenset())
```

### 3. Refactor Phase

- エラーハンドリングの改善
- キャッシュ機能（同じノードを何度もインポートしない）
- ノードが見つからない場合の分かりやすいエラーメッセージ

## 完了条件

- [ ] `extract_field_dependency()` が実装されている
- [ ] `import_node_function()` が実装されている
- [ ] `load_node_dependencies()` が実装されている
- [ ] `extract_initial_fields_from_start_node()` が実装されている
- [ ] 開始ノードの Contract から必須フィールドを初期フィールドとして抽出できる
- [ ] Optional フィールドは初期フィールドに含まれない
- [ ] 終端ノード、非同期ノードからも抽出できる
- [ ] デコレータなし関数は None を返す
- [ ] すべてのテストが通過

## 依存関係

- Issue #51 (FieldDependency 型システム) が完了していること
- Issue #52 (Node 依存宣言拡張) が完了していること

## 関連ファイル

- `railway/core/dag/dependency_extraction.py` (新規)
- `tests/unit/core/dag/test_dependency_extraction.py` (新規)
- `railway/core/dag/__init__.py` (エクスポート追加)
