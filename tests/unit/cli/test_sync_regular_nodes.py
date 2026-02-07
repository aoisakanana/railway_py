"""sync transition の通常ノードスケルトン生成テスト（副作用あり）。

BUG-001: `railway sync transition` で通常ノードのスケルトンが生成されない問題の修正。
"""
import pytest
from pathlib import Path


class TestSyncRegularNodes:
    """通常ノード同期のテスト（副作用を含む）。"""

    def test_generates_skeleton_for_missing_node(self, tmp_path: Path) -> None:
        """未実装の通常ノードにスケルトンを生成する。"""
        from railway.core.dag.types import TransitionGraph, NodeDefinition
        from railway.cli.sync import sync_regular_nodes

        graph = TransitionGraph(
            version="1.0",
            entrypoint="myflow",
            description="Test",
            nodes=(
                NodeDefinition(
                    name="process",
                    module="nodes.myflow.process",
                    function="process",
                    description="処理ノード",
                    is_exit=False,
                ),
            ),
            exits=(),
            transitions=(),
            start_node="process",
        )

        result = sync_regular_nodes(graph, tmp_path)

        assert len(result.generated) == 1
        assert (tmp_path / "src/nodes/myflow/process.py").exists()

    def test_skips_existing_node(self, tmp_path: Path) -> None:
        """既存のノードファイルはスキップする。"""
        from railway.core.dag.types import TransitionGraph, NodeDefinition
        from railway.cli.sync import sync_regular_nodes

        # 既存ファイルを作成
        file_path = tmp_path / "src/nodes/myflow/process.py"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("# custom implementation")

        graph = TransitionGraph(
            version="1.0",
            entrypoint="myflow",
            description="Test",
            nodes=(
                NodeDefinition(
                    name="process",
                    module="nodes.myflow.process",
                    function="process",
                    description="処理ノード",
                    is_exit=False,
                ),
            ),
            exits=(),
            transitions=(),
            start_node="process",
        )

        result = sync_regular_nodes(graph, tmp_path)

        assert len(result.generated) == 0
        assert len(result.skipped) == 1
        assert file_path.read_text() == "# custom implementation"

    def test_creates_init_files(self, tmp_path: Path) -> None:
        """__init__.py を各階層に生成する。"""
        from railway.core.dag.types import TransitionGraph, NodeDefinition
        from railway.cli.sync import sync_regular_nodes

        graph = TransitionGraph(
            version="1.0",
            entrypoint="myflow",
            description="Test",
            nodes=(
                NodeDefinition(
                    name="process",
                    module="nodes.myflow.process",
                    function="process",
                    description="処理ノード",
                    is_exit=False,
                ),
            ),
            exits=(),
            transitions=(),
            start_node="process",
        )

        sync_regular_nodes(graph, tmp_path)

        assert (tmp_path / "src/nodes/__init__.py").exists()
        assert (tmp_path / "src/nodes/myflow/__init__.py").exists()

    def test_skips_exit_nodes(self, tmp_path: Path) -> None:
        """終端ノードは処理しない（sync_exit_nodes の責務）。"""
        from railway.core.dag.types import TransitionGraph, NodeDefinition
        from railway.cli.sync import sync_regular_nodes

        graph = TransitionGraph(
            version="1.0",
            entrypoint="myflow",
            description="Test",
            nodes=(
                NodeDefinition(
                    name="exit.success.done",
                    module="nodes.exit.success.done",
                    function="done",
                    description="正常終了",
                    is_exit=True,
                ),
            ),
            exits=(),
            transitions=(),
            start_node="start",
        )

        result = sync_regular_nodes(graph, tmp_path)

        assert len(result.generated) == 0
        assert len(result.skipped) == 0

    def test_generates_multiple_nodes(self, tmp_path: Path) -> None:
        """複数の通常ノードを生成できる。"""
        from railway.core.dag.types import TransitionGraph, NodeDefinition
        from railway.cli.sync import sync_regular_nodes

        graph = TransitionGraph(
            version="1.0",
            entrypoint="myflow",
            description="Test",
            nodes=(
                NodeDefinition(
                    name="start",
                    module="nodes.myflow.start",
                    function="start",
                    description="開始ノード",
                    is_exit=False,
                ),
                NodeDefinition(
                    name="process",
                    module="nodes.myflow.process",
                    function="process",
                    description="処理ノード",
                    is_exit=False,
                ),
                NodeDefinition(
                    name="finalize",
                    module="nodes.myflow.finalize",
                    function="finalize",
                    description="最終ノード",
                    is_exit=False,
                ),
            ),
            exits=(),
            transitions=(),
            start_node="start",
        )

        result = sync_regular_nodes(graph, tmp_path)

        assert len(result.generated) == 3
        assert (tmp_path / "src/nodes/myflow/start.py").exists()
        assert (tmp_path / "src/nodes/myflow/process.py").exists()
        assert (tmp_path / "src/nodes/myflow/finalize.py").exists()

    def test_generated_code_is_valid_python(self, tmp_path: Path) -> None:
        """生成されたコードは有効な Python である。"""
        from railway.core.dag.types import TransitionGraph, NodeDefinition
        from railway.cli.sync import sync_regular_nodes

        graph = TransitionGraph(
            version="1.0",
            entrypoint="myflow",
            description="Test",
            nodes=(
                NodeDefinition(
                    name="process",
                    module="nodes.myflow.process",
                    function="process",
                    description="処理ノード",
                    is_exit=False,
                ),
            ),
            exits=(),
            transitions=(),
            start_node="process",
        )

        sync_regular_nodes(graph, tmp_path)

        file_path = tmp_path / "src/nodes/myflow/process.py"
        content = file_path.read_text()

        # 構文エラーがなければ compile が成功
        compile(content, str(file_path), "exec")

        # 必要な要素が含まれている
        assert "@node" in content
        assert "def process" in content
        assert "Outcome.success" in content
        assert "ctx: ProcessContext | None = None" in content
