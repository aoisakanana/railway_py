"""依存ベースコード生成テスト。

TDD Red Phase: detect_context_type のテスト
"""

import sys
import pytest

from railway.core.dag.codegen import generate_transition_code
from railway.core.dag.types import (
    TransitionGraph,
    NodeDefinition,
    StateTransition,
)


class TestCodegenWithDependencies:
    """依存宣言があるノードのコード生成テスト。"""

    def test_no_contract_types_generated(self) -> None:
        """CONTRACT_TYPES は生成されない。"""
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test workflow",
            nodes=(
                NodeDefinition(
                    name="start",
                    module="nodes.start",
                    function="start",
                    description="Start node",
                ),
            ),
            exits=(),
            transitions=(),
            start_node="start",
        )

        code = generate_transition_code(graph, "test.yml")

        # CONTRACT_TYPES, NODE_TYPES は生成されない
        assert "CONTRACT_TYPES" not in code
        assert "NODE_TYPES" not in code

    def test_generates_transition_table(self) -> None:
        """TRANSITION_TABLE を生成する。"""
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test workflow",
            nodes=(
                NodeDefinition(
                    name="check_host",
                    module="nodes.check_host",
                    function="check_host",
                    description="Check host",
                ),
                NodeDefinition(
                    name="escalate",
                    module="nodes.escalate",
                    function="escalate",
                    description="Escalate",
                ),
            ),
            exits=(),
            transitions=(
                StateTransition(
                    from_node="check_host",
                    from_state="success::found",
                    to_target="escalate",
                ),
            ),
            start_node="check_host",
        )

        code = generate_transition_code(graph, "test.yml")

        assert "TRANSITION_TABLE" in code
        assert '"check_host::success::found": escalate' in code

    def test_generates_run_function(self) -> None:
        """run() 関数を生成する。"""
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test workflow",
            nodes=(
                NodeDefinition(
                    name="start",
                    module="nodes.start",
                    function="start",
                    description="Start node",
                ),
            ),
            exits=(),
            transitions=(),
            start_node="start",
        )

        code = generate_transition_code(graph, "test.yml")

        assert "def run(" in code
        assert "dag_runner(" in code


class TestCodegenContextTypeDetection:
    """コンテキスト型検出テスト。"""

    def test_detects_context_type_from_start_node(self, tmp_path, monkeypatch) -> None:
        """開始ノードからコンテキスト型を検出する。"""
        from railway.core.dag.codegen import detect_context_type

        # ユニークなパッケージ名でテスト用モジュールを作成（競合回避）
        pkg_name = f"ctx_detect_{id(tmp_path)}"
        pkg_dir = tmp_path / pkg_name
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")
        (pkg_dir / "start.py").write_text(
            '''
from railway import Contract, node
from railway.core.dag import Outcome

class MyContext(Contract):
    value: str

@node
def start(ctx: MyContext) -> tuple[MyContext, Outcome]:
    return ctx, Outcome.success("done")
'''
        )

        monkeypatch.syspath_prepend(str(tmp_path))

        context_type = detect_context_type(f"{pkg_name}.start", "start")
        assert context_type == "MyContext"

        # クリーンアップ
        for mod in list(sys.modules.keys()):
            if mod.startswith(pkg_name):
                del sys.modules[mod]

    def test_returns_none_for_untyped_function(self, tmp_path, monkeypatch) -> None:
        """型ヒントがない関数は None を返す。"""
        from railway.core.dag.codegen import detect_context_type

        # ユニークなパッケージ名でテスト用モジュールを作成
        pkg_name = f"untyped_{id(tmp_path)}"
        pkg_dir = tmp_path / pkg_name
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")
        (pkg_dir / "start.py").write_text(
            '''
from railway import node
from railway.core.dag import Outcome

@node
def start(ctx):  # 型ヒントなし
    return ctx, Outcome.success("done")
'''
        )

        monkeypatch.syspath_prepend(str(tmp_path))

        context_type = detect_context_type(f"{pkg_name}.start", "start")
        assert context_type is None

        # クリーンアップ
        for mod in list(sys.modules.keys()):
            if mod.startswith(pkg_name):
                del sys.modules[mod]

    def test_returns_none_for_nonexistent_module(self) -> None:
        """存在しないモジュールは None を返す。"""
        from railway.core.dag.codegen import detect_context_type

        context_type = detect_context_type("nonexistent.module", "function")
        assert context_type is None


class TestCodegenDocstrings:
    """生成コードの docstring テスト。"""

    def test_includes_auto_generated_note(self) -> None:
        """自動生成であることを示す注記を含む。"""
        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test workflow",
            nodes=(
                NodeDefinition(
                    name="start",
                    module="nodes.start",
                    function="start",
                    description="Start node",
                ),
            ),
            exits=(),
            transitions=(),
            start_node="start",
        )

        code = generate_transition_code(graph, "test.yml")

        # 自動生成であることを示す
        assert "railway sync transition" in code or "auto-generated" in code.lower()
