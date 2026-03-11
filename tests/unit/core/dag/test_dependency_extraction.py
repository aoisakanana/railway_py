"""依存情報の自動抽出テスト。

@node デコレータから requires/optional/provides パラメータは削除された。
フィールド依存メタデータは _make_node_with_deps ヘルパーで直接設定する。
"""

import pytest

from railway import Contract, node
from railway.core.dag import Outcome
from railway.core.dag.field_dependency import FieldDependency


class WorkflowContext(Contract):
    """テスト用 Contract。"""

    incident_id: str
    severity: str
    hostname: str | None = None


def _make_node_with_deps(
    func, *, requires=None, optional=None, provides=None, name=None
):
    """Test helper: set field dependency metadata on a function."""
    func._is_railway_node = True
    func._node_name = name or func.__name__
    func._is_board_node = False
    func._is_async = False
    func._node_inputs = {}
    func._node_output = None
    func._requires = frozenset(requires or [])
    func._optional = frozenset(optional or [])
    func._provides = frozenset(provides or [])
    func._field_dependency = FieldDependency(
        requires=func._requires,
        optional=func._optional,
        provides=func._provides,
    )
    return func


class TestExtractFieldDependency:
    """単一ノードからの依存抽出テスト。"""

    def test_extracts_from_decorated_node(self) -> None:
        """依存メタデータ付きノードから依存を抽出する。"""
        from railway.core.dag.dependency_extraction import extract_field_dependency

        def my_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        _make_node_with_deps(
            my_node, requires=["incident_id"], optional=["hostname"], provides=["result"]
        )

        dep = extract_field_dependency(my_node)

        assert dep is not None
        assert dep.requires == frozenset(["incident_id"])
        assert dep.optional == frozenset(["hostname"])
        assert dep.provides == frozenset(["result"])

    def test_returns_none_for_undecorated_function(self) -> None:
        """デコレータなし関数は None を返す。"""
        from railway.core.dag.dependency_extraction import extract_field_dependency

        def plain_function(ctx):
            return ctx

        dep = extract_field_dependency(plain_function)
        assert dep is None

    def test_returns_empty_dependency_for_node_without_declarations(self) -> None:
        """依存宣言なしの @node は空の FieldDependency を返す。"""
        from railway.core.dag.dependency_extraction import extract_field_dependency

        def simple_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        _make_node_with_deps(simple_node)

        dep = extract_field_dependency(simple_node)

        assert dep is not None
        assert dep.requires == frozenset()
        assert dep.optional == frozenset()
        assert dep.provides == frozenset()


class TestLoadNodeDependencies:
    """遷移グラフからの依存ロードテスト。"""

    def test_loads_dependencies_from_graph(self, tmp_path, monkeypatch) -> None:
        """遷移グラフの全ノードから依存を読み込む。"""
        import sys
        from railway.core.dag.types import TransitionGraph, NodeDefinition
        from railway.core.dag.dependency_extraction import load_node_dependencies

        # ユニークなパッケージ名でテスト用モジュールを作成（競合回避）
        pkg_name = f"load_deps_{id(tmp_path)}"
        pkg_dir = tmp_path / pkg_name
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")
        (pkg_dir / "check_host.py").write_text(
            '''
from railway.core.dag.field_dependency import FieldDependency

def check_host(ctx):
    return ctx, "done"

# Set field dependency metadata directly
check_host._is_railway_node = True
check_host._node_name = "check_host"
check_host._is_board_node = False
check_host._is_async = False
check_host._node_inputs = {}
check_host._node_output = None
check_host._requires = frozenset(["incident_id"])
check_host._optional = frozenset()
check_host._provides = frozenset(["hostname"])
check_host._field_dependency = FieldDependency(
    requires=check_host._requires,
    optional=check_host._optional,
    provides=check_host._provides,
)
'''
        )

        # sys.path に追加
        monkeypatch.syspath_prepend(str(tmp_path))

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(
                NodeDefinition(
                    name="check_host",
                    module=f"{pkg_name}.check_host",
                    function="check_host",
                    description="",
                ),
            ),
            exits=(),
            transitions=(),
            start_node="check_host",
        )

        deps = load_node_dependencies(graph)

        assert "check_host" in deps
        assert deps["check_host"].requires == frozenset(["incident_id"])
        assert deps["check_host"].provides == frozenset(["hostname"])

        # クリーンアップ
        for mod in list(sys.modules.keys()):
            if mod.startswith(pkg_name):
                del sys.modules[mod]

    def test_skips_unimplemented_nodes(self, tmp_path, monkeypatch) -> None:
        """未実装のノードはスキップする。"""
        from railway.core.dag.types import TransitionGraph, NodeDefinition
        from railway.core.dag.dependency_extraction import load_node_dependencies

        # ノードモジュールを作成しない（未実装）
        monkeypatch.syspath_prepend(str(tmp_path))

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(
                NodeDefinition(
                    name="nonexistent",
                    module="nodes.nonexistent",
                    function="nonexistent",
                    description="",
                ),
            ),
            exits=(),
            transitions=(),
            start_node="nonexistent",
        )

        # エラーにならずに空の dict を返す
        deps = load_node_dependencies(graph)
        assert deps == {}


class TestDependencyExtractionEdgeCases:
    """エッジケースのテスト。"""

    def test_handles_exit_node(self) -> None:
        """終端ノードからも依存を抽出できる。"""
        from railway import ExitContract
        from railway.core.dag.dependency_extraction import extract_field_dependency

        class DoneResult(ExitContract):
            exit_state: str = "success.done"

        def done(ctx) -> DoneResult:
            return DoneResult()

        _make_node_with_deps(done, name="exit.success.done", requires=["processed"])

        dep = extract_field_dependency(done)

        assert dep is not None
        assert dep.requires == frozenset(["processed"])

    def test_handles_async_node(self) -> None:
        """非同期ノードからも依存を抽出できる。"""
        from railway.core.dag.dependency_extraction import extract_field_dependency

        async def async_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        _make_node_with_deps(async_node, requires=["data"], provides=["result"])

        dep = extract_field_dependency(async_node)

        assert dep is not None
        assert dep.requires == frozenset(["data"])


class TestImportNodeFunction:
    """ノード関数インポートテスト。"""

    def test_imports_node_function(self, tmp_path, monkeypatch) -> None:
        """ノード関数をインポートできる。"""
        import sys
        from railway.core.dag.dependency_extraction import import_node_function

        # ユニークなパッケージ名でテスト用モジュールを作成（競合回避）
        pkg_name = f"test_pkg_{id(tmp_path)}"
        pkg_dir = tmp_path / pkg_name
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")
        (pkg_dir / "my_node.py").write_text(
            '''
def my_function():
    return "hello"
'''
        )

        monkeypatch.syspath_prepend(str(tmp_path))

        func = import_node_function(f"{pkg_name}.my_node", "my_function")
        assert func() == "hello"

        # クリーンアップ
        if pkg_name in sys.modules:
            del sys.modules[pkg_name]
        if f"{pkg_name}.my_node" in sys.modules:
            del sys.modules[f"{pkg_name}.my_node"]

    def test_raises_import_error_for_missing_module(self) -> None:
        """存在しないモジュールは ImportError。"""
        from railway.core.dag.dependency_extraction import import_node_function

        with pytest.raises(ImportError):
            import_node_function("nonexistent.module", "function")


class TestExtractInitialFieldsFromStartNode:
    """開始ノードからの初期フィールド導出テスト。"""

    def test_extracts_required_fields_from_contract(self, tmp_path, monkeypatch) -> None:
        """Contract の必須フィールドを初期フィールドとして抽出する。"""
        import sys
        from railway.core.dag.types import TransitionGraph, NodeDefinition
        from railway.core.dag.dependency_extraction import (
            extract_initial_fields_from_start_node,
        )

        # ユニークなパッケージ名でテスト用モジュールを作成（競合回避）
        pkg_name = f"extract_test_{id(tmp_path)}"
        pkg_dir = tmp_path / pkg_name
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")
        (pkg_dir / "start.py").write_text(
            '''
from railway import Contract, node
from railway.core.dag import Outcome

class WorkflowContext(Contract):
    incident_id: str          # 必須（初期フィールド）
    severity: str             # 必須（初期フィールド）
    hostname: str | None = None  # Optional（初期フィールドではない）

@node(output=object)
def start(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
    return ctx, Outcome.success("done")
'''
        )

        monkeypatch.syspath_prepend(str(tmp_path))

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(
                NodeDefinition(
                    name="start",
                    module=f"{pkg_name}.start",
                    function="start",
                    description="",
                ),
            ),
            exits=(),
            transitions=(),
            start_node="start",
        )

        initial = extract_initial_fields_from_start_node(graph)

        # 必須フィールドのみが初期フィールド
        assert "incident_id" in initial.fields
        assert "severity" in initial.fields
        assert "hostname" not in initial.fields  # Optional は含まれない

        # クリーンアップ
        for mod in list(sys.modules.keys()):
            if mod.startswith(pkg_name):
                del sys.modules[mod]

    def test_returns_empty_when_no_type_hint(self, tmp_path, monkeypatch) -> None:
        """型ヒントがない場合は空の AvailableFields を返す。"""
        import sys
        from railway.core.dag.types import TransitionGraph, NodeDefinition
        from railway.core.dag.dependency_extraction import (
            extract_initial_fields_from_start_node,
        )

        # ユニークなパッケージ名でテスト用モジュールを作成（競合回避）
        pkg_name = f"nohint_test_{id(tmp_path)}"
        pkg_dir = tmp_path / pkg_name
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")
        (pkg_dir / "start.py").write_text(
            '''
from railway import node
from railway.core.dag import Outcome

@node(output=object)
def start(ctx):  # 型ヒントなし
    return ctx, Outcome.success("done")
'''
        )

        monkeypatch.syspath_prepend(str(tmp_path))

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(
                NodeDefinition(
                    name="start",
                    module=f"{pkg_name}.start",
                    function="start",
                    description="",
                ),
            ),
            exits=(),
            transitions=(),
            start_node="start",
        )

        initial = extract_initial_fields_from_start_node(graph)

        assert initial.fields == frozenset()

        # クリーンアップ
        for mod in list(sys.modules.keys()):
            if mod.startswith(pkg_name):
                del sys.modules[mod]

    def test_returns_empty_when_module_not_found(self, tmp_path, monkeypatch) -> None:
        """モジュールが見つからない場合は空の AvailableFields を返す。"""
        from railway.core.dag.types import TransitionGraph, NodeDefinition
        from railway.core.dag.dependency_extraction import (
            extract_initial_fields_from_start_node,
        )

        monkeypatch.syspath_prepend(str(tmp_path))

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="",
            nodes=(
                NodeDefinition(
                    name="nonexistent",
                    module="nodes.nonexistent",
                    function="nonexistent",
                    description="",
                ),
            ),
            exits=(),
            transitions=(),
            start_node="nonexistent",
        )

        initial = extract_initial_fields_from_start_node(graph)

        assert initial.fields == frozenset()
