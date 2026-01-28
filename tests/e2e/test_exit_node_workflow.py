"""E2E tests for exit node workflow (v0.12.2 ExitContract 対応).

Tests the complete flow: YAML -> parse -> codegen -> dag_runner -> exit node execution.
"""

import pytest
from pathlib import Path

from railway.core.dag.parser import load_transition_graph
from railway.core.dag.codegen import generate_transition_code
from railway.core.dag.runner import dag_runner, async_dag_runner
from railway.core.dag.outcome import Outcome


class TestExitNodeE2EWorkflow:
    """終端ノード E2E ワークフローテスト。"""

    def test_yaml_to_exit_node_execution(self, exit_node_fixtures: Path) -> None:
        """YAML から終端ノード実行までの全フロー。"""
        # 1. YAML をパース
        yaml_path = exit_node_fixtures / "basic_exit.yml"
        graph = load_transition_graph(yaml_path)

        # 2. 終端ノードが正しくパースされている
        exit_done = next(
            (n for n in graph.nodes if n.name == "exit.success.done"),
            None,
        )
        assert exit_done is not None
        assert exit_done.is_exit is True
        assert exit_done.exit_code == 0

        # 3. コード生成
        code = generate_transition_code(graph, str(yaml_path))
        # Note: v0.12.2 では EXIT_CODES は codegen に含まれる可能性がある
        assert "exit.success.done" in code

        # 4. 生成コードが有効な Python
        compile(code, "<generated>", "exec")

    def test_multiple_exits_workflow(self, exit_node_fixtures: Path) -> None:
        """複数終端ノードを持つワークフロー。"""
        yaml_path = exit_node_fixtures / "multiple_exits.yml"
        graph = load_transition_graph(yaml_path)

        # 複数の終端ノードがパースされている
        exit_nodes = [n for n in graph.nodes if n.is_exit]
        assert len(exit_nodes) >= 4  # success: 3, failure: 4

        # 各終端ノードの終了コードが正しい
        success_exits = [n for n in exit_nodes if "success" in n.name]
        failure_exits = [n for n in exit_nodes if "failure" in n.name]

        for node in success_exits:
            assert node.exit_code == 0

        for node in failure_exits:
            assert node.exit_code == 1

    def test_deep_nested_exit_workflow(self, exit_node_fixtures: Path) -> None:
        """深いネストの終端ノードワークフロー。"""
        yaml_path = exit_node_fixtures / "deep_nested_exit.yml"
        graph = load_transition_graph(yaml_path)

        # 深いネストの終端ノードが正しくパースされている
        ssh_handshake = next(
            (n for n in graph.nodes if n.name == "exit.failure.ssh.handshake"),
            None,
        )
        assert ssh_handshake is not None
        assert ssh_handshake.module == "nodes.exit.failure.ssh.handshake"
        assert ssh_handshake.function == "handshake"

    def test_auto_resolve_workflow(self, exit_node_fixtures: Path) -> None:
        """module/function 自動解決ワークフロー。"""
        yaml_path = exit_node_fixtures / "auto_resolve.yml"
        graph = load_transition_graph(yaml_path)

        # module/function が自動解決されている
        start = next(
            (n for n in graph.nodes if n.name == "start_process"),
            None,
        )
        assert start is not None
        assert start.module == "nodes.start_process"
        assert start.function == "start_process"

    def test_custom_exit_code_workflow(self, exit_node_fixtures: Path) -> None:
        """カスタム終了コードワークフロー。"""
        yaml_path = exit_node_fixtures / "custom_exit_code.yml"
        graph = load_transition_graph(yaml_path)

        # カスタム終了コードが設定されている
        low_disk = next(
            (n for n in graph.nodes if n.name == "exit.warning.low_disk"),
            None,
        )
        assert low_disk is not None
        assert low_disk.exit_code == 2

        high_memory = next(
            (n for n in graph.nodes if n.name == "exit.warning.high_memory"),
            None,
        )
        assert high_memory is not None
        assert high_memory.exit_code == 3


class TestExitNodeE2ERuntime:
    """終端ノード E2E ランタイムテスト（v0.12.2 ExitContract）。"""

    def test_exit_node_execution_with_mock_nodes(self) -> None:
        """モックノードを使った終端ノード実行。

        実際のファイルシステムを使わず、メモリ内でテスト。
        """
        execution_log: list[str] = []

        # モックノード: 開始
        def start():
            execution_log.append("start")
            return {"step": 1}, Outcome.success("done")

        start._node_name = "start"

        # モックノード: 処理
        def process(ctx):
            execution_log.append("process")
            return {"step": 2, "prev": ctx}, Outcome.success("done")

        process._node_name = "process"

        # モックノード: 終端（Context のみを返す）
        def exit_success_done(ctx):
            execution_log.append("exit.success.done")
            return {
                "status": "completed",
                "steps": ctx["step"],
            }

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "start::success::done": process,
            "process::success::done": exit_success_done,
        }

        # 実行
        result = dag_runner(
            start=start,
            transitions=transitions,
        )

        # 検証
        assert execution_log == ["start", "process", "exit.success.done"]
        assert result.context["status"] == "completed"
        assert result.context["steps"] == 2
        assert result.is_success is True
        assert result.exit_state == "success.done"
        assert result.exit_code == 0
        assert result.execution_path == ("start", "process", "exit.success.done")

    def test_failure_exit_node_execution(self) -> None:
        """失敗終端ノードの実行。"""

        def start():
            return {}, Outcome.failure("timeout")

        start._node_name = "start"

        def exit_failure_timeout(ctx):
            return {"error": "Operation timed out"}

        exit_failure_timeout._node_name = "exit.failure.timeout"

        transitions = {
            "start::failure::timeout": exit_failure_timeout,
        }

        result = dag_runner(
            start=start,
            transitions=transitions,
        )

        assert result.is_success is False
        assert result.exit_state == "failure.timeout"
        assert result.exit_code == 1
        assert result.context["error"] == "Operation timed out"

    def test_on_step_callback_with_exit_node(self) -> None:
        """on_step コールバックの E2E テスト。"""
        step_history: list[dict] = []

        def on_step(node_name: str, state: str, ctx) -> None:
            step_history.append({
                "node": node_name,
                "state": state,
                "ctx": ctx,
            })

        def start():
            return {"count": 1}, Outcome.success("done")

        start._node_name = "start"

        def exit_success_done(ctx):
            return {"final": True}

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "start::success::done": exit_success_done,
        }

        dag_runner(
            start=start,
            transitions=transitions,
            on_step=on_step,
        )

        # 2 回呼ばれる（start, exit.success.done）
        assert len(step_history) == 2

        # start ノード
        assert step_history[0]["node"] == "start"
        assert step_history[0]["state"] == "start::success::done"

        # exit ノード
        assert step_history[1]["node"] == "exit.success.done"
        # v0.12.2 では exit:: 形式で状態が返される
        assert "exit" in step_history[1]["state"]


class TestYamlMigrationE2E:
    """YAML マイグレーションの E2E テスト。"""

    def test_v0_11_to_v0_12_migration(self, tmp_path: Path) -> None:
        """v0.11 形式から v0.12 形式への変換。"""
        import yaml
        from railway.migrations.yaml_converter import convert_yaml_structure

        # 旧形式 YAML
        old_yaml = {
            "version": "1.0",
            "entrypoint": "test",
            "nodes": {
                "process": {
                    "module": "nodes.process",
                    "function": "process",
                    "description": "処理",
                },
            },
            "exits": {
                "green_success": {"code": 0, "description": "正常終了"},
                "red_timeout": {"code": 1, "description": "タイムアウト"},
            },
            "start": "process",
            "transitions": {
                "process": {
                    "success::done": "exit::green_success",
                    "failure::timeout": "exit::red_timeout",
                },
            },
        }

        # 変換
        result = convert_yaml_structure(old_yaml)

        # 検証
        assert result.success
        assert "exits" not in result.data
        assert "exit" in result.data["nodes"]
        assert result.data["transitions"]["process"]["success::done"] == "exit.success.done"
        assert result.data["transitions"]["process"]["failure::timeout"] == "exit.failure.timeout"

    def test_migrated_yaml_can_be_parsed(self, tmp_path: Path) -> None:
        """マイグレーション後の YAML がパース可能。"""
        import yaml
        from railway.migrations.yaml_converter import convert_yaml_structure
        from railway.core.dag.parser import load_transition_graph

        # 旧形式 YAML を変換
        old_yaml = {
            "version": "1.0",
            "entrypoint": "test",
            "nodes": {
                "start": {"description": "開始"},
            },
            "exits": {
                "green_done": {"code": 0, "description": "完了"},
            },
            "start": "start",
            "transitions": {
                "start": {"success::done": "exit::green_done"},
            },
        }

        result = convert_yaml_structure(old_yaml)
        assert result.success

        # 変換後の YAML をファイルに書き込み
        yaml_file = tmp_path / "migrated.yml"
        with open(yaml_file, "w") as f:
            yaml.safe_dump(result.data, f)

        # パース可能であることを確認
        graph = load_transition_graph(yaml_file)
        assert graph is not None
        assert any(n.name == "exit.success.done" for n in graph.nodes)


class TestExitNodeE2EValidation:
    """終端ノード E2E バリデーションテスト。"""

    def test_invalid_exit_path_raises_error(self, invalid_fixtures: Path) -> None:
        """存在しない終端パスへの遷移はエラー。"""
        from railway.core.dag.validator import validate_graph

        yaml_path = invalid_fixtures / "invalid_exit_path.yml"
        graph = load_transition_graph(yaml_path)

        result = validate_graph(graph)

        # バリデーションエラーがある
        assert not result.is_valid
        assert len(result.errors) > 0


class TestRunHelperE2E:
    """run() ヘルパー関数の E2E テスト（v0.12.2 ExitContract）。"""

    def test_run_helper_executes_workflow(self) -> None:
        """run() ヘルパーでワークフローを実行。

        生成されたモジュールの run() 関数をシミュレート。
        """
        from railway.core.dag.runner import dag_runner
        from railway.core.dag.outcome import Outcome

        # モックノード
        def initialize(ctx):
            return {"step": 1, **ctx}, Outcome.success("done")

        def exit_success_done(ctx):
            return {"status": "completed", "original": ctx}

        # _node_name 属性設定（codegen が生成）
        initialize._node_name = "initialize"
        exit_success_done._node_name = "exit.success.done"

        # 生成コードをシミュレート
        START_NODE = initialize
        TRANSITION_TABLE = {
            "initialize::success::done": exit_success_done,
        }

        # run() ヘルパーをシミュレート
        # 生成コードでは、lambda に _node_name を付与するため、
        # ここでは start wrapper を使用
        def run(initial_context):
            def start_wrapper():
                return START_NODE(initial_context)

            start_wrapper._node_name = "initialize"
            return dag_runner(
                start=start_wrapper,
                transitions=TRANSITION_TABLE,
            )

        # テスト実行
        result = run({"user_id": 123})

        assert result.is_success
        assert result.context["status"] == "completed"
        assert result.context["original"]["user_id"] == 123

    @pytest.mark.asyncio
    async def test_run_async_helper_executes_workflow(self) -> None:
        """run_async() ヘルパーでワークフローを実行。"""
        from railway.core.dag.runner import async_dag_runner
        from railway.core.dag.outcome import Outcome

        # モック非同期ノード
        async def initialize(ctx):
            return {"step": 1, **ctx}, Outcome.success("done")

        async def exit_success_done(ctx):
            return {"status": "async_completed", "original": ctx}

        initialize._node_name = "initialize"
        exit_success_done._node_name = "exit.success.done"

        START_NODE = initialize
        TRANSITION_TABLE = {
            "initialize::success::done": exit_success_done,
        }

        # run_async() ヘルパーをシミュレート
        async def run_async(initial_context):
            async def start_wrapper():
                return await START_NODE(initial_context)

            start_wrapper._node_name = "initialize"
            return await async_dag_runner(
                start=start_wrapper,
                transitions=TRANSITION_TABLE,
            )

        # テスト実行
        result = await run_async({"user_id": 456})

        assert result.is_success
        assert result.context["status"] == "async_completed"
