"""スケルトン生成のテスト（純粋関数）。

TDD Red Phase: テストを先に作成。

BUG-001: `railway sync transition` で通常ノードのスケルトンが生成されない問題の修正。
"""
import pytest
from pathlib import Path

from railway.core.dag.skeleton import (
    SkeletonSpec,
    generate_skeleton_spec,
    generate_regular_node_content,
    compute_file_path,
    filter_regular_nodes,
    compute_skeleton_specs,
)


class TestGenerateSkeletonSpec:
    """generate_skeleton_spec のテスト"""

    def test_regular_node_spec(self) -> None:
        """通常ノードの仕様生成"""
        spec = generate_skeleton_spec("check_time", "greeting", is_exit_node=False)

        assert spec.node_name == "check_time"
        assert spec.module_path == "nodes.greeting.check_time"
        assert spec.entrypoint == "greeting"
        assert spec.is_exit_node is False

    def test_exit_node_spec(self) -> None:
        """終端ノードの仕様生成"""
        spec = generate_skeleton_spec("exit.success.done", "greeting", is_exit_node=True)

        assert spec.node_name == "exit.success.done"
        assert spec.module_path == "nodes.exit.success.done"
        assert spec.entrypoint == "greeting"
        assert spec.is_exit_node is True

    def test_nested_node_name(self) -> None:
        """ネストしたノード名の仕様生成"""
        spec = generate_skeleton_spec("process.validate", "myflow", is_exit_node=False)

        assert spec.module_path == "nodes.myflow.process.validate"


class TestGenerateRegularNodeContent:
    """generate_regular_node_content のテスト"""

    def test_contains_node_decorator(self) -> None:
        """@node デコレータが含まれる"""
        spec = SkeletonSpec(
            node_name="check_time",
            module_path="nodes.greeting.check_time",
            entrypoint="greeting",
            is_exit_node=False,
        )

        content = generate_regular_node_content(spec)

        assert "@node" in content
        assert "def check_time" in content

    def test_contains_outcome_import(self) -> None:
        """Outcome のインポートが含まれる"""
        spec = SkeletonSpec(
            node_name="process",
            module_path="nodes.myflow.process",
            entrypoint="myflow",
            is_exit_node=False,
        )

        content = generate_regular_node_content(spec)

        assert "from railway.core.dag import Outcome" in content
        assert "Outcome.success" in content

    def test_has_optional_ctx_parameter(self) -> None:
        """Optional な ctx パラメータを持つ"""
        spec = SkeletonSpec(
            node_name="start",
            module_path="nodes.myflow.start",
            entrypoint="myflow",
            is_exit_node=False,
        )

        content = generate_regular_node_content(spec)

        assert "ctx: StartContext | None = None" in content
        assert "if ctx is None:" in content

    def test_generates_context_class(self) -> None:
        """Context クラスが生成される"""
        spec = SkeletonSpec(
            node_name="check_time",
            module_path="nodes.greeting.check_time",
            entrypoint="greeting",
            is_exit_node=False,
        )

        content = generate_regular_node_content(spec)

        assert "class CheckTimeContext(Contract):" in content

    def test_snake_case_to_pascal_case(self) -> None:
        """snake_case が PascalCase に変換される"""
        spec = SkeletonSpec(
            node_name="validate_user_input",
            module_path="nodes.myflow.validate_user_input",
            entrypoint="myflow",
            is_exit_node=False,
        )

        content = generate_regular_node_content(spec)

        assert "class ValidateUserInputContext(Contract):" in content

    def test_is_valid_python(self) -> None:
        """生成されたコードは有効な Python"""
        spec = SkeletonSpec(
            node_name="process",
            module_path="nodes.myflow.process",
            entrypoint="myflow",
            is_exit_node=False,
        )

        content = generate_regular_node_content(spec)

        # 構文エラーがなければ compile が成功
        compile(content, "<test>", "exec")


class TestComputeFilePath:
    """compute_file_path のテスト"""

    def test_regular_node_path(self) -> None:
        """通常ノードのパス計算"""
        spec = SkeletonSpec(
            node_name="check_time",
            module_path="nodes.greeting.check_time",
            entrypoint="greeting",
            is_exit_node=False,
        )

        path = compute_file_path(spec, Path("src"))

        assert path == Path("src/nodes/greeting/check_time.py")

    def test_exit_node_path(self) -> None:
        """終端ノードのパス計算"""
        spec = SkeletonSpec(
            node_name="exit.success.done",
            module_path="nodes.exit.success.done",
            entrypoint="greeting",
            is_exit_node=True,
        )

        path = compute_file_path(spec, Path("src"))

        assert path == Path("src/nodes/exit/success/done.py")

    def test_deep_exit_node_path(self) -> None:
        """深いネストの終端ノードのパス計算"""
        spec = SkeletonSpec(
            node_name="exit.failure.ssh.handshake",
            module_path="nodes.exit.failure.ssh.handshake",
            entrypoint="myflow",
            is_exit_node=True,
        )

        path = compute_file_path(spec, Path("src"))

        assert path == Path("src/nodes/exit/failure/ssh/handshake.py")


class TestFilterRegularNodes:
    """filter_regular_nodes のテスト（純粋関数）"""

    def test_excludes_exit_nodes(self) -> None:
        """終端ノードは除外される"""
        result = filter_regular_nodes(("start", "process", "exit.success.done"))

        assert result == ("start", "process")

    def test_returns_all_when_no_exit_nodes(self) -> None:
        """終端ノードがない場合は全て返す"""
        result = filter_regular_nodes(("start", "process", "validate"))

        assert result == ("start", "process", "validate")

    def test_returns_empty_when_only_exit_nodes(self) -> None:
        """終端ノードのみの場合は空タプル"""
        result = filter_regular_nodes(("exit.success.done", "exit.failure.error"))

        assert result == ()


class TestComputeSkeletonSpecs:
    """compute_skeleton_specs のテスト（純粋関数）"""

    def test_generates_specs_for_all_nodes(self) -> None:
        """全ノードの仕様を生成"""
        specs = compute_skeleton_specs(
            node_names=("start", "process"),
            entrypoint="myflow",
        )

        assert len(specs) == 2
        assert specs[0].node_name == "start"
        assert specs[0].module_path == "nodes.myflow.start"
        assert specs[1].node_name == "process"
        assert specs[1].module_path == "nodes.myflow.process"

    def test_returns_empty_for_empty_input(self) -> None:
        """空入力の場合は空タプル"""
        specs = compute_skeleton_specs(
            node_names=(),
            entrypoint="myflow",
        )

        assert specs == ()
