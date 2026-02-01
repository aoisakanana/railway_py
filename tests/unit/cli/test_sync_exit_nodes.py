"""Issue #44 & #62: 終端ノード同期のテスト（副作用を含む）。

TDD Red Phase: 失敗するテストを先に作成。

Issue #62 追加分:
- _sync_entry() から sync_exit_nodes() が呼ばれることをテスト（バグ修正）
"""
import pytest
from pathlib import Path

from railway.core.dag.types import TransitionGraph, NodeDefinition, ExitDefinition


class TestSyncResult:
    """SyncResult のテスト（イミュータブルデータ）。"""

    def test_creates_with_generated_and_skipped(self) -> None:
        """generated と skipped を持つ結果を作成できる。"""
        from railway.cli.sync import SyncResult

        result = SyncResult(
            generated=(Path("/tmp/a.py"),),
            skipped=(Path("/tmp/b.py"),),
        )

        assert len(result.generated) == 1
        assert len(result.skipped) == 1

    def test_is_frozen(self) -> None:
        """SyncResult は不変。"""
        from railway.cli.sync import SyncResult

        result = SyncResult(
            generated=(),
            skipped=(),
        )

        with pytest.raises((TypeError, AttributeError)):
            result.generated = ()  # type: ignore


class TestSyncExitNodes:
    """終端ノード同期のテスト（副作用を含む）。"""

    @pytest.fixture
    def exit_node(self) -> NodeDefinition:
        return NodeDefinition(
            name="exit.success.done",
            module="nodes.exit.success.done",
            function="done",
            description="正常終了",
            is_exit=True,
        )

    @pytest.fixture
    def regular_node(self) -> NodeDefinition:
        return NodeDefinition(
            name="start",
            module="nodes.start",
            function="start",
            description="開始ノード",
            is_exit=False,
        )

    @pytest.fixture
    def graph_with_exit(
        self, exit_node: NodeDefinition, regular_node: NodeDefinition
    ) -> TransitionGraph:
        return TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test workflow",
            nodes=(regular_node, exit_node),
            exits=(),
            transitions=(),
            start_node="start",
        )

    def test_generates_skeleton_for_missing_exit_node(
        self,
        tmp_path: Path,
        graph_with_exit: TransitionGraph,
    ) -> None:
        """未実装の終端ノードにスケルトンを生成する。"""
        from railway.cli.sync import sync_exit_nodes, SyncResult

        result = sync_exit_nodes(graph_with_exit, tmp_path)

        assert isinstance(result, SyncResult)
        assert len(result.generated) == 1
        assert (tmp_path / "src/nodes/exit/success/done.py").exists()

    def test_skips_existing_exit_node(
        self,
        tmp_path: Path,
        graph_with_exit: TransitionGraph,
    ) -> None:
        """既存の終端ノードファイルはスキップする。"""
        from railway.cli.sync import sync_exit_nodes

        # 既存ファイルを作成
        file_path = tmp_path / "src/nodes/exit/success/done.py"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("# existing code")

        result = sync_exit_nodes(graph_with_exit, tmp_path)

        assert len(result.skipped) == 1
        assert len(result.generated) == 0
        # 既存コードが上書きされていない
        assert file_path.read_text() == "# existing code"

    def test_creates_init_files(
        self,
        tmp_path: Path,
        graph_with_exit: TransitionGraph,
    ) -> None:
        """__init__.py を各階層に生成する。"""
        from railway.cli.sync import sync_exit_nodes

        sync_exit_nodes(graph_with_exit, tmp_path)

        assert (tmp_path / "src/nodes/__init__.py").exists()
        assert (tmp_path / "src/nodes/exit/__init__.py").exists()
        assert (tmp_path / "src/nodes/exit/success/__init__.py").exists()

    def test_returns_immutable_result(
        self,
        tmp_path: Path,
        graph_with_exit: TransitionGraph,
    ) -> None:
        """戻り値は不変（frozen dataclass）。"""
        from railway.cli.sync import sync_exit_nodes

        result = sync_exit_nodes(graph_with_exit, tmp_path)

        with pytest.raises((TypeError, AttributeError)):
            result.generated = ()  # type: ignore

    def test_skips_regular_nodes(
        self,
        tmp_path: Path,
    ) -> None:
        """通常ノードは処理しない。"""
        from railway.cli.sync import sync_exit_nodes

        regular_node = NodeDefinition(
            name="process",
            module="nodes.process",
            function="process",
            description="処理ノード",
            is_exit=False,
        )

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=(regular_node,),
            exits=(),
            transitions=(),
            start_node="process",
        )

        result = sync_exit_nodes(graph, tmp_path)

        assert len(result.generated) == 0
        assert len(result.skipped) == 0

    def test_generates_multiple_exit_nodes(
        self,
        tmp_path: Path,
    ) -> None:
        """複数の終端ノードを一括生成。"""
        from railway.cli.sync import sync_exit_nodes

        exit_done = NodeDefinition(
            name="exit.success.done",
            module="nodes.exit.success.done",
            function="done",
            description="正常終了",
            is_exit=True,
        )
        exit_timeout = NodeDefinition(
            name="exit.failure.timeout",
            module="nodes.exit.failure.timeout",
            function="timeout",
            description="タイムアウト",
            is_exit=True,
        )

        graph = TransitionGraph(
            version="1.0",
            entrypoint="test",
            description="Test",
            nodes=(exit_done, exit_timeout),
            exits=(),
            transitions=(),
            start_node="start",
        )

        result = sync_exit_nodes(graph, tmp_path)

        assert len(result.generated) == 2
        assert (tmp_path / "src/nodes/exit/success/done.py").exists()
        assert (tmp_path / "src/nodes/exit/failure/timeout.py").exists()

    def test_generated_file_contains_valid_code(
        self,
        tmp_path: Path,
        graph_with_exit: TransitionGraph,
    ) -> None:
        """生成されたファイルは有効な Python コード。"""
        from railway.cli.sync import sync_exit_nodes

        sync_exit_nodes(graph_with_exit, tmp_path)

        file_path = tmp_path / "src/nodes/exit/success/done.py"
        content = file_path.read_text()

        # 構文エラーがなければ compile が成功
        compile(content, str(file_path), "exec")

        # 必要な要素が含まれている
        assert "class SuccessDoneResult(ExitContract):" in content
        assert '@node(name="exit.success.done")' in content


# =============================================================================
# Issue #62: _sync_entry() から sync_exit_nodes() が呼ばれるテスト（バグ修正）
# =============================================================================


class TestSyncEntryCallsSyncExitNodes:
    """_sync_entry() から sync_exit_nodes() が呼ばれることのテスト。

    バグ修正: sync_exit_nodes() は存在するが _sync_entry() で呼ばれていなかった。
    """

    def test_sync_entry_generates_exit_nodes(self, tmp_path: Path) -> None:
        """_sync_entry() 実行時に終端ノードが生成される。"""
        from railway.cli.sync import _sync_entry

        # YAML を作成
        graphs_dir = tmp_path / "transition_graphs"
        graphs_dir.mkdir()
        yaml_content = '''version: "1.0"
entrypoint: test
description: "テストワークフロー"

nodes:
  start:
    module: nodes.test.start
    function: start
    description: "開始ノード"
  exit:
    success:
      done:
        description: "正常終了"
    failure:
      timeout:
        description: "タイムアウト"

start: start

transitions:
  start:
    success::done: exit.success.done
    failure::timeout: exit.failure.timeout
'''
        (graphs_dir / "test_20260201000000.yml").write_text(yaml_content)

        # sync 実行
        output_dir = tmp_path / "_railway" / "generated"
        output_dir.mkdir(parents=True)
        (tmp_path / "src").mkdir()

        _sync_entry(
            entry_name="test",
            graphs_dir=graphs_dir,
            output_dir=output_dir,
            dry_run=False,
            validate_only=False,
            # デフォルトで上書き
        )

        # 終端ノードが生成されている
        assert (tmp_path / "src/nodes/exit/success/done.py").exists()
        assert (tmp_path / "src/nodes/exit/failure/timeout.py").exists()

    def test_sync_entry_skips_existing_exit_nodes(self, tmp_path: Path) -> None:
        """既存の終端ノードは上書きされない。"""
        from railway.cli.sync import _sync_entry

        graphs_dir = tmp_path / "transition_graphs"
        graphs_dir.mkdir()
        yaml_content = '''version: "1.0"
entrypoint: test
description: "テストワークフロー"

nodes:
  start:
    module: nodes.test.start
    function: start
    description: "開始ノード"
  exit:
    success:
      done:
        description: "正常終了"

start: start

transitions:
  start:
    success::done: exit.success.done
'''
        (graphs_dir / "test_20260201000000.yml").write_text(yaml_content)

        # 既存ファイルを作成
        exit_path = tmp_path / "src/nodes/exit/success/done.py"
        exit_path.parent.mkdir(parents=True)
        exit_path.write_text("# custom implementation")

        output_dir = tmp_path / "_railway" / "generated"
        output_dir.mkdir(parents=True)

        _sync_entry(
            entry_name="test",
            graphs_dir=graphs_dir,
            output_dir=output_dir,
            dry_run=False,
            validate_only=False,
            # デフォルトで上書き
        )

        # 上書きされていない
        assert exit_path.read_text() == "# custom implementation"

    def test_sync_entry_dry_run_skips_exit_nodes(self, tmp_path: Path) -> None:
        """dry-run 時は終端ノードを生成しない。"""
        from railway.cli.sync import _sync_entry

        graphs_dir = tmp_path / "transition_graphs"
        graphs_dir.mkdir()
        yaml_content = '''version: "1.0"
entrypoint: test
description: "テストワークフロー"

nodes:
  start:
    module: nodes.test.start
    function: start
    description: "開始ノード"
  exit:
    success:
      done:
        description: "正常終了"

start: start

transitions:
  start:
    success::done: exit.success.done
'''
        (graphs_dir / "test_20260201000000.yml").write_text(yaml_content)

        output_dir = tmp_path / "_railway" / "generated"
        output_dir.mkdir(parents=True)
        (tmp_path / "src").mkdir()

        _sync_entry(
            entry_name="test",
            graphs_dir=graphs_dir,
            output_dir=output_dir,
            dry_run=True,
            validate_only=False,
            # デフォルトで上書き
        )

        # dry-run なので生成されない
        assert not (tmp_path / "src/nodes/exit/success/done.py").exists()

    def test_sync_entry_validate_only_skips_exit_nodes(self, tmp_path: Path) -> None:
        """validate-only 時は終端ノードを生成しない。"""
        from railway.cli.sync import _sync_entry

        graphs_dir = tmp_path / "transition_graphs"
        graphs_dir.mkdir()
        yaml_content = '''version: "1.0"
entrypoint: test
description: "テストワークフロー"

nodes:
  start:
    module: nodes.test.start
    function: start
    description: "開始ノード"
  exit:
    success:
      done:
        description: "正常終了"

start: start

transitions:
  start:
    success::done: exit.success.done
'''
        (graphs_dir / "test_20260201000000.yml").write_text(yaml_content)

        output_dir = tmp_path / "_railway" / "generated"
        output_dir.mkdir(parents=True)
        (tmp_path / "src").mkdir()

        _sync_entry(
            entry_name="test",
            graphs_dir=graphs_dir,
            output_dir=output_dir,
            dry_run=False,
            validate_only=True,
            # デフォルトで上書き
        )

        # validate-only なので生成されない
        assert not (tmp_path / "src/nodes/exit/success/done.py").exists()
