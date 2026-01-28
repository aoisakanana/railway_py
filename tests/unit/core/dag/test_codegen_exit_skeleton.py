"""Issue #44: 終端ノードスケルトン生成のテスト。

TDD Red Phase: 失敗するテストを先に作成。
"""
import pytest

from railway.core.dag.types import NodeDefinition


class TestExitPathToContractName:
    """Contract 名生成のテスト（純粋関数）。"""

    @pytest.mark.parametrize(
        "exit_path,expected",
        [
            ("exit.success.done", "SuccessDoneResult"),
            ("exit.failure.timeout", "FailureTimeoutResult"),
            ("exit.failure.ssh.handshake", "FailureSshHandshakeResult"),
            ("exit.done", "DoneResult"),
            ("exit.success.api.created", "SuccessApiCreatedResult"),
        ],
    )
    def test_converts_exit_path_to_pascal_case_result(
        self, exit_path: str, expected: str
    ) -> None:
        from railway.core.dag.codegen import _exit_path_to_contract_name

        assert _exit_path_to_contract_name(exit_path) == expected


class TestExitPathToExitState:
    """exit_state 生成のテスト（純粋関数）。"""

    @pytest.mark.parametrize(
        "exit_path,expected",
        [
            ("exit.success.done", "success.done"),
            ("exit.failure.ssh.handshake", "failure.ssh.handshake"),
            ("exit.warning.disk_full", "warning.disk_full"),
        ],
    )
    def test_removes_exit_prefix(self, exit_path: str, expected: str) -> None:
        from railway.core.dag.codegen import _exit_path_to_exit_state

        assert _exit_path_to_exit_state(exit_path) == expected


class TestGenerateExitNodeSkeleton:
    """終端ノードスケルトン生成のテスト。"""

    @pytest.fixture
    def success_done_node(self) -> NodeDefinition:
        """正常終了ノードのフィクスチャ。"""
        return NodeDefinition(
            name="exit.success.done",
            module="nodes.exit.success.done",
            function="done",
            description="正常終了",
            is_exit=True,
        )

    @pytest.fixture
    def deep_nested_node(self) -> NodeDefinition:
        """深いネストの終端ノードフィクスチャ。"""
        return NodeDefinition(
            name="exit.failure.ssh.handshake",
            module="nodes.exit.failure.ssh.handshake",
            function="handshake",
            description="SSHハンドシェイク失敗",
            is_exit=True,
        )

    def test_generates_exit_contract_subclass(
        self, success_done_node: NodeDefinition
    ) -> None:
        """ExitContract サブクラスを生成する。"""
        from railway.core.dag.codegen import generate_exit_node_skeleton

        code = generate_exit_node_skeleton(success_done_node)

        assert "class SuccessDoneResult(ExitContract):" in code
        assert 'exit_state: str = "success.done"' in code

    def test_generates_node_decorator_with_name(
        self, success_done_node: NodeDefinition
    ) -> None:
        """@node デコレータに name を付与する。"""
        from railway.core.dag.codegen import generate_exit_node_skeleton

        code = generate_exit_node_skeleton(success_done_node)

        assert '@node(name="exit.success.done")' in code

    def test_function_has_exit_contract_type_hint(
        self, success_done_node: NodeDefinition
    ) -> None:
        """関数の ctx パラメータに ExitContract 型ヒントがある。

        Note:
            Any ではなく ExitContract を使用することで型安全性を確保。
            開発者は必要に応じてより具体的な型に変更できる。
        """
        from railway.core.dag.codegen import generate_exit_node_skeleton

        code = generate_exit_node_skeleton(success_done_node)

        assert "def done(ctx: ExitContract) -> SuccessDoneResult:" in code

    def test_imports_exit_contract_and_node(
        self, success_done_node: NodeDefinition
    ) -> None:
        """ExitContract と node をインポートする。"""
        from railway.core.dag.codegen import generate_exit_node_skeleton

        code = generate_exit_node_skeleton(success_done_node)

        assert "from railway import ExitContract, node" in code

    def test_includes_todo_comments(
        self, success_done_node: NodeDefinition
    ) -> None:
        """TODO コメントが含まれる。"""
        from railway.core.dag.codegen import generate_exit_node_skeleton

        code = generate_exit_node_skeleton(success_done_node)

        assert "TODO:" in code

    def test_deep_nested_exit_node(
        self, deep_nested_node: NodeDefinition
    ) -> None:
        """深いネストの終端ノードにも対応。"""
        from railway.core.dag.codegen import generate_exit_node_skeleton

        code = generate_exit_node_skeleton(deep_nested_node)

        assert "class FailureSshHandshakeResult(ExitContract):" in code
        assert 'exit_state: str = "failure.ssh.handshake"' in code
        assert "def handshake(ctx: ExitContract) -> FailureSshHandshakeResult:" in code

    def test_generated_code_is_valid_python(
        self, success_done_node: NodeDefinition
    ) -> None:
        """生成されたコードは構文的に正しい。"""
        from railway.core.dag.codegen import generate_exit_node_skeleton

        code = generate_exit_node_skeleton(success_done_node)

        # 構文エラーがなければ compile が成功する
        compile(code, "<string>", "exec")

    def test_includes_docstring_with_description(
        self, success_done_node: NodeDefinition
    ) -> None:
        """description が docstring に含まれる。"""
        from railway.core.dag.codegen import generate_exit_node_skeleton

        code = generate_exit_node_skeleton(success_done_node)

        assert '"""正常終了' in code
