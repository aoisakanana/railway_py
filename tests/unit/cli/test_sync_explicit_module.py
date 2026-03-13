"""sync transition が YAML の module 指定を尊重するテスト。

Issue 39-01: module を明示指定しても、デフォルト位置にスタブが生成される問題の修正。
"""
from pathlib import Path

from railway.core.dag.types import NodeDefinition


class TestHasExplicitModule:
    """_has_explicit_module 純粋関数のテスト。"""

    def test_custom_module_detected(self) -> None:
        """カスタム module 指定は明示的として検出される。"""
        from railway.cli.sync import _has_explicit_module

        node = NodeDefinition(
            name="check",
            module="nodes.custom.check",
            function="check",
            description="",
        )
        assert _has_explicit_module(node, "my_workflow") is True

    def test_default_module_not_explicit(self) -> None:
        """デフォルトの module パスは明示的ではない。"""
        from railway.cli.sync import _has_explicit_module

        node = NodeDefinition(
            name="check",
            module="nodes.my_workflow.check",
            function="check",
            description="",
        )
        assert _has_explicit_module(node, "my_workflow") is False

    def test_dotted_name_default_module(self) -> None:
        """ドット付きノード名のデフォルト module パスは明示的ではない。"""
        from railway.cli.sync import _has_explicit_module

        node = NodeDefinition(
            name="process.check.db",
            module="nodes.my_wf.process.check.db",
            function="db",
            description="",
        )
        assert _has_explicit_module(node, "my_wf") is False


class TestSyncRegularNodesExplicitModule:
    """明示 module ノードの sync_regular_nodes テスト（副作用あり）。"""

    def test_explicit_module_generates_at_custom_path(self, tmp_path: Path) -> None:
        """明示 module ノードはカスタムパスにスケルトンを生成する。"""
        from railway.cli.sync import sync_regular_nodes
        from railway.core.dag.types import TransitionGraph

        graph = TransitionGraph(
            version="1.0",
            entrypoint="my_workflow",
            description="Test",
            nodes=(
                NodeDefinition(
                    name="check",
                    module="nodes.custom.check",
                    function="check",
                    description="カスタムモジュール",
                    is_exit=False,
                ),
            ),
            exits=(),
            transitions=(),
            start_node="check",
        )

        result = sync_regular_nodes(graph, tmp_path)

        assert len(result.generated) == 1
        # カスタムパスに生成されること
        expected = tmp_path / "src/nodes/custom/check.py"
        assert expected.exists()
        # デフォルトパスには生成されないこと
        default = tmp_path / "src/nodes/my_workflow/check.py"
        assert not default.exists()

    def test_explicit_module_skips_existing(self, tmp_path: Path) -> None:
        """明示 module ノードで既存ファイルがある場合はスキップする。"""
        from railway.cli.sync import sync_regular_nodes
        from railway.core.dag.types import TransitionGraph

        # 既存ファイルを作成
        file_path = tmp_path / "src/nodes/custom/check.py"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("# existing")

        graph = TransitionGraph(
            version="1.0",
            entrypoint="my_workflow",
            description="Test",
            nodes=(
                NodeDefinition(
                    name="check",
                    module="nodes.custom.check",
                    function="check",
                    description="カスタムモジュール",
                    is_exit=False,
                ),
            ),
            exits=(),
            transitions=(),
            start_node="check",
        )

        result = sync_regular_nodes(graph, tmp_path)

        assert len(result.generated) == 0
        assert len(result.skipped) == 1
        assert file_path.read_text() == "# existing"

    def test_mixed_explicit_and_default_nodes(self, tmp_path: Path) -> None:
        """明示 module とデフォルト module が混在するケース。"""
        from railway.cli.sync import sync_regular_nodes
        from railway.core.dag.types import TransitionGraph

        graph = TransitionGraph(
            version="1.0",
            entrypoint="my_workflow",
            description="Test",
            nodes=(
                NodeDefinition(
                    name="check",
                    module="nodes.custom.check",
                    function="check",
                    description="明示モジュール",
                    is_exit=False,
                ),
                NodeDefinition(
                    name="process",
                    module="nodes.my_workflow.process",
                    function="process",
                    description="デフォルトモジュール",
                    is_exit=False,
                ),
                NodeDefinition(
                    name="exit.success.done",
                    module="nodes.exit.success.done",
                    function="done",
                    description="終端ノード",
                    is_exit=True,
                ),
            ),
            exits=(),
            transitions=(),
            start_node="check",
        )

        result = sync_regular_nodes(graph, tmp_path)

        assert len(result.generated) == 2
        # 明示 module はカスタムパスに
        assert (tmp_path / "src/nodes/custom/check.py").exists()
        # デフォルト module はデフォルトパスに
        assert (tmp_path / "src/nodes/my_workflow/process.py").exists()
        # 終端ノードは生成されない
        assert not (tmp_path / "src/nodes/exit/success/done.py").exists()

    def test_explicit_module_generated_code_is_valid(self, tmp_path: Path) -> None:
        """明示 module ノードで生成されたコードは有効な Python である。"""
        from railway.cli.sync import sync_regular_nodes
        from railway.core.dag.types import TransitionGraph

        graph = TransitionGraph(
            version="1.0",
            entrypoint="my_workflow",
            description="Test",
            nodes=(
                NodeDefinition(
                    name="check",
                    module="nodes.custom.check",
                    function="check",
                    description="カスタムモジュール",
                    is_exit=False,
                ),
            ),
            exits=(),
            transitions=(),
            start_node="check",
        )

        sync_regular_nodes(graph, tmp_path)

        file_path = tmp_path / "src/nodes/custom/check.py"
        content = file_path.read_text()
        compile(content, str(file_path), "exec")
        assert "def check(board)" in content
        assert "Outcome.success" in content
