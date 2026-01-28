# Issue #30: E2E 統合テスト

**Phase:** 2
**優先度:** 高
**依存関係:** Issue #26, #27, #28, #31, #33（validator, codegen, dag_runner, run helper, migration）
**見積もり:** 0.25日

---

## 概要

終端ノード機能の E2E（End-to-End）統合テストを実装する。
YAML → パース → codegen → dag_runner → 終端ノード実行 の全フローを検証。

---

## テスト対象フロー

```
┌─────────────────────────────────────────────────────────────┐
│                      E2E テストフロー                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────┐    ┌────────┐    ┌─────────┐    ┌──────────┐ │
│  │  YAML   │───►│ Parser │───►│ Codegen │───►│ Runner   │ │
│  │Fixture  │    │        │    │         │    │          │ │
│  └─────────┘    └────────┘    └─────────┘    └──────────┘ │
│                                                     │       │
│                                                     ▼       │
│                                              ┌──────────┐   │
│                                              │ Exit Node│   │
│                                              │ Executed │   │
│                                              └──────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## テストケース

### 1. 基本フロー: YAML → 終端ノード実行

```python
# tests/e2e/test_exit_node_workflow.py
"""E2E tests for exit node workflow."""

import pytest
from pathlib import Path
import tempfile
import importlib.util
import sys

from railway.core.dag.parser import load_transition_graph
from railway.core.dag.codegen import generate_transition_code
from railway.core.dag.runner import dag_runner
from railway.core.dag.outcome import Outcome


class TestExitNodeE2EWorkflow:
    """終端ノード E2E ワークフローテスト。"""

    def test_yaml_to_exit_node_execution(self, exit_node_fixtures) -> None:
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
        assert "EXIT_CODES" in code
        assert "exit.success.done" in code

        # 4. 生成コードが有効な Python
        compile(code, "<generated>", "exec")

    def test_multiple_exits_workflow(self, exit_node_fixtures) -> None:
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

    def test_deep_nested_exit_workflow(self, exit_node_fixtures) -> None:
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

    def test_auto_resolve_workflow(self, exit_node_fixtures) -> None:
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

    def test_custom_exit_code_workflow(self, exit_node_fixtures) -> None:
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
    """終端ノード E2E ランタイムテスト。"""

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
        exit_codes = {
            "exit.success.done": 0,
        }

        # 実行
        result = dag_runner(
            start=start,
            transitions=transitions,
            exit_codes=exit_codes,
        )

        # 検証
        assert execution_log == ["start", "process", "exit.success.done"]
        assert result.context["status"] == "completed"
        assert result.context["steps"] == 2
        assert result.is_success is True
        assert "green" in result.exit_code
        assert "exit.success.done" in result.exit_code
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
        exit_codes = {
            "exit.failure.timeout": 1,
        }

        result = dag_runner(
            start=start,
            transitions=transitions,
            exit_codes=exit_codes,
        )

        assert result.is_success is False
        assert "red" in result.exit_code
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
        exit_codes = {
            "exit.success.done": 0,
        }

        dag_runner(
            start=start,
            transitions=transitions,
            exit_codes=exit_codes,
            on_step=on_step,
        )

        # 2 回呼ばれる（start, exit.success.done）
        assert len(step_history) == 2

        # start ノード
        assert step_history[0]["node"] == "start"
        assert step_history[0]["state"] == "start::success::done"

        # exit ノード
        assert step_history[1]["node"] == "exit.success.done"
        assert "exit::green" in step_history[1]["state"]
        assert step_history[1]["ctx"]["final"] is True


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

    def test_invalid_exit_path_raises_error(self, invalid_fixtures) -> None:
        """存在しない終端パスへの遷移はエラー。"""
        from railway.core.dag.validator import validate_graph

        yaml_path = invalid_fixtures / "invalid_exit_path.yml"
        graph = load_transition_graph(yaml_path)

        result = validate_graph(graph)

        # バリデーションエラーがある
        assert not result.is_valid
        assert len(result.errors) > 0


class TestRunHelperE2E:
    """run() ヘルパー関数の E2E テスト。"""

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
        EXIT_CODES = {
            "exit.success.done": 0,
        }

        # run() ヘルパーをシミュレート
        def run(initial_context):
            return dag_runner(
                start=lambda: START_NODE(initial_context),
                transitions=TRANSITION_TABLE,
                exit_codes=EXIT_CODES,
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
        EXIT_CODES = {
            "exit.success.done": 0,
        }

        # run_async() ヘルパーをシミュレート
        async def run_async(initial_context):
            return await async_dag_runner(
                start=lambda: START_NODE(initial_context),
                transitions=TRANSITION_TABLE,
                exit_codes=EXIT_CODES,
            )

        # テスト実行
        result = await run_async({"user_id": 456})

        assert result.is_success
        assert result.context["status"] == "async_completed"
```

---

## 実装手順

### Step 1: テストディレクトリ作成

```bash
mkdir -p tests/e2e
touch tests/e2e/__init__.py
```

### Step 2: E2E テスト実装

上記のテストコードを `tests/e2e/test_exit_node_workflow.py` に実装。

### Step 3: conftest.py にフィクスチャパス追加（既に #23 で実装済み）

### Step 4: テスト実行

```bash
pytest tests/e2e/ -v
```

---

## テスト戦略

### テストカテゴリ

| カテゴリ | 目的 | 例 |
|---------|------|-----|
| **パース検証** | YAML → TransitionGraph が正しい | `test_yaml_to_exit_node_execution` |
| **ランタイム検証** | dag_runner が終端ノードを実行 | `test_exit_node_execution_with_mock_nodes` |
| **バリデーション** | 不正な構成がエラーになる | `test_invalid_exit_path_raises_error` |
| **コールバック** | on_step が正しく呼ばれる | `test_on_step_callback_with_exit_node` |

### モック vs 実ファイル

- **パース検証:** フィクスチャ YAML を使用
- **ランタイム検証:** メモリ内モックノードを使用
- **理由:** ファイルシステム依存を減らし、テストを高速化

---

## 完了条件

- [ ] `tests/e2e/test_exit_node_workflow.py` 作成
- [ ] YAML → パース → codegen 統合テスト
- [ ] dag_runner 終端ノード実行テスト
- [ ] 複数終端ノードテスト
- [ ] 深いネストテスト
- [ ] 自動解決テスト
- [ ] カスタム終了コードテスト
- [ ] on_step コールバックテスト
- [ ] バリデーションエラーテスト
- [ ] run() ヘルパーテスト
- [ ] run_async() ヘルパーテスト
- [ ] すべてのテスト通過

---

## 関連 Issue

- Issue #23: テスト用 YAML フィクスチャ（前提）
- Issue #26: バリデーション更新（前提）
- Issue #27: codegen の終端ノード対応（前提）
- Issue #28: dag_runner の終端ノード実行（前提）
- Issue #31: codegen に run() ヘルパー追加（前提）
- Issue #29: 終端ノードドキュメント追加（後続）
