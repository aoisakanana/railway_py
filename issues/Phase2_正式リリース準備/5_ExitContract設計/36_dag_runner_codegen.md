# Issue #36: dag_runner・codegen の ExitContract 対応

**優先度**: P0
**依存**: #35
**ブロック**: #37

---

## 概要

`dag_runner` と `codegen` を ExitContract ベースに変更する。

## 変更内容

### 1. dag_runner の変更

**削除** (`runner.py`):
- `Exit` クラス（`Exit.GREEN`, `Exit.RED`, `Exit.YELLOW`, `Exit.code()`）
- `DagRunnerResult` クラス
- `exit_codes` パラメータ

**変更**:
- 返り値を `ExitContract` に
- 終端ノードが `ExitContract` を返すことを期待
- 後方互換: Context のみ返す場合は `DefaultExitContract` でラップ

**終端ノード検出ロジック**:
```python
def _is_exit_node(node_name: str) -> bool:
    """終端ノードかどうかを判定する。

    判定条件:
    - "exit." で始まる（新形式: exit.success.done）
    - "_exit_" で始まる（codegen 生成形式: _exit_success_done）
    """
    return node_name.startswith("exit.") or node_name.startswith("_exit_")
```

**exit_state の導出ロジック**:
```python
# 終端ノード名から exit_state を導出
# "exit.success.done" → "success.done"
# "_exit_failure_timeout" → "failure.timeout"
def _derive_exit_state(node_name: str) -> str:
    """終端ノード名から exit_state を導出する。"""
    # "exit." プレフィックスを除去
    if node_name.startswith("exit."):
        return node_name[5:]
    # "_exit_" プレフィックスを除去し、"_" を "." に変換
    if node_name.startswith("_exit_"):
        return node_name[6:].replace("_", ".")
    return node_name
```

**dag_runner の変更**:
```python
# Before
def dag_runner(..., exit_codes: dict[str, int] | None = None) -> DagRunnerResult:
    ...
    return DagRunnerResult(exit_code="exit::green::done", context=ctx, ...)

# After
def dag_runner(...) -> ExitContract:
    ...
    # 遷移先を取得
    next_node = transitions.get(state_string)
    next_node_name = _get_node_name(next_node)

    # 終端ノードかどうかを判定
    if _is_exit_node(next_node_name):
        # 終端ノードを実行（Context のみ受け取り、ExitContract または任意の値を返す）
        result = next_node(context)
        execution_path.append(next_node_name)

        # 結果を処理
        if isinstance(result, ExitContract):
            # ExitContract を返した場合: execution_path と iterations を追加
            return result.model_copy(update={
                "execution_path": tuple(execution_path),
                "iterations": iteration,
            })
        else:
            # 後方互換: Context のみ返す場合は DefaultExitContract でラップ
            exit_state = _derive_exit_state(next_node_name)
            return DefaultExitContract(
                exit_state=exit_state,
                context=result,
                execution_path=tuple(execution_path),
                iterations=iteration,
            )

    # 通常ノードの処理（既存ロジック）
    ...
```

### 2. codegen の変更

**削除**:
- `generate_exit_enum()` 呼び出し
- `generate_exit_codes()` 呼び出し
- `ExitOutcome` インポート
- `Exit` インポート

**変更**:
- `run()` / `run_async()` の返り値を `ExitContract` に
- フレームワークインポートを更新

```python
# Before
from railway.core.dag.runner import dag_runner, DagRunnerResult, Exit
from railway.core.dag.state import ExitOutcome

def run(...) -> DagRunnerResult:
    return dag_runner(..., exit_codes=EXIT_CODES)

# After
from railway.core.dag.runner import dag_runner
from railway.core.contract.exit import ExitContract

def run(...) -> ExitContract:
    return dag_runner(...)
```

### 3. TRANSITION_TABLE の変更

終端ノードへの遷移は関数参照に（Exit.code() 使用を廃止）:

```python
# Before
TRANSITION_TABLE = {
    "node::success::done": Exit.code("green", "done"),
}

# After
TRANSITION_TABLE = {
    "node::success::done": _exit_success_done,  # 終端ノード関数
}
```

## テスト

### dag_runner テスト

```python
# tests/unit/core/dag/test_runner_exit_contract.py
import pytest
from railway import ExitContract, DefaultExitContract, Contract, node
from railway.core.dag import Outcome, dag_runner


class StartContext(Contract):
    """開始ノード用 Context。"""
    value: str = "test"


class DoneResult(ExitContract):
    """テスト用の成功 ExitContract。"""
    data: str
    exit_state: str = "success.done"


class TimeoutResult(ExitContract):
    """テスト用の失敗 ExitContract。"""
    error: str
    exit_state: str = "failure.timeout"


class TestDagRunnerExitContract:
    """dag_runner が ExitContract を返すことのテスト。"""

    def test_returns_exit_contract(self) -> None:
        """終端ノードが ExitContract を返す場合、そのまま返す。"""
        @node
        def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.success("done")

        @node(name="exit.success.done")
        def done(ctx: StartContext) -> DoneResult:
            return DoneResult(data="completed")

        result = dag_runner(
            start=start,
            transitions={"start::success::done": done},
        )

        assert isinstance(result, DoneResult)
        assert result.data == "completed"
        assert result.is_success is True
        assert result.exit_state == "success.done"
        assert result.exit_code == 0  # 自動導出
        assert "start" in result.execution_path
        assert "exit.success.done" in result.execution_path

    def test_backward_compat_context_only(self) -> None:
        """Context のみ返す終端ノードは DefaultExitContract でラップ。"""
        @node
        def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.success("done")

        @node(name="exit.success.done")
        def done(ctx: StartContext) -> dict:
            return {"key": "value"}  # ExitContract ではない

        result = dag_runner(
            start=start,
            transitions={"start::success::done": done},
        )

        assert isinstance(result, DefaultExitContract)
        assert result.context == {"key": "value"}
        assert result.exit_state == "success.done"
        assert result.is_success is True

    def test_exit_state_derived_from_node_name(self) -> None:
        """exit_state は終端ノード名から導出される（後方互換用）。"""
        @node
        def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.failure("timeout")

        @node(name="exit.failure.timeout")
        def timeout(ctx: StartContext) -> dict:
            return {"error": "timeout"}

        result = dag_runner(
            start=start,
            transitions={"start::failure::timeout": timeout},
        )

        assert result.exit_state == "failure.timeout"
        assert result.is_failure is True

    def test_custom_exit_contract_preserves_fields(self) -> None:
        """ユーザー定義 ExitContract のフィールドが保持される。"""
        @node
        def start() -> tuple[StartContext, Outcome]:
            return StartContext(), Outcome.failure("timeout")

        @node(name="exit.failure.timeout")
        def timeout(ctx: StartContext) -> TimeoutResult:
            return TimeoutResult(error="API timeout after 30s")

        result = dag_runner(
            start=start,
            transitions={"start::failure::timeout": timeout},
        )

        assert isinstance(result, TimeoutResult)
        assert result.error == "API timeout after 30s"
        assert result.exit_state == "failure.timeout"
        assert result.exit_code == 1  # 自動導出


class TestIsExitNode:
    """_is_exit_node 関数のテスト（純粋関数として独立テスト）。"""

    def test_exit_dot_prefix_is_exit_node(self) -> None:
        """'exit.' で始まるノードは終端ノード。"""
        from railway.core.dag.runner import _is_exit_node
        assert _is_exit_node("exit.success.done") is True
        assert _is_exit_node("exit.failure.timeout") is True

    def test_underscore_exit_prefix_is_exit_node(self) -> None:
        """'_exit_' で始まるノードは終端ノード。"""
        from railway.core.dag.runner import _is_exit_node
        assert _is_exit_node("_exit_success_done") is True
        assert _is_exit_node("_exit_failure_error") is True

    def test_regular_node_is_not_exit_node(self) -> None:
        """通常ノードは終端ノードではない。"""
        from railway.core.dag.runner import _is_exit_node
        assert _is_exit_node("start") is False
        assert _is_exit_node("process") is False
        assert _is_exit_node("finalize") is False


class TestDeriveExitState:
    """_derive_exit_state 関数のテスト（純粋関数として独立テスト）。"""

    def test_removes_exit_dot_prefix(self) -> None:
        """'exit.' プレフィックスを除去する。"""
        from railway.core.dag.runner import _derive_exit_state
        assert _derive_exit_state("exit.success.done") == "success.done"

    def test_removes_underscore_exit_prefix(self) -> None:
        """'_exit_' プレフィックスを除去し '.' に変換。"""
        from railway.core.dag.runner import _derive_exit_state
        assert _derive_exit_state("_exit_failure_timeout") == "failure.timeout"

    def test_handles_deep_nested_path(self) -> None:
        """深いネストパスを正しく処理する。"""
        from railway.core.dag.runner import _derive_exit_state
        assert _derive_exit_state("exit.failure.ssh.handshake") == "failure.ssh.handshake"

    def test_returns_as_is_if_no_prefix(self) -> None:
        """プレフィックスがない場合はそのまま返す。"""
        from railway.core.dag.runner import _derive_exit_state
        assert _derive_exit_state("custom_state") == "custom_state"
```

### codegen テスト

```python
# tests/unit/codegen/test_transition_code_exit_contract.py
import pytest
from railway.codegen.transition_code import generate_transition_code
from railway.core.dag.parser import parse_yaml


class TestCodegenExitContract:
    """codegen が ExitContract ベースのコードを生成することのテスト。"""

    @pytest.fixture
    def exit_node_graph(self, tmp_path):
        """終端ノードを含む YAML を準備。"""
        yaml_content = '''
version: "1.0"
nodes:
  start:
    outcomes: [success.done, failure.error]
  exit:
    success:
      done: {}
    failure:
      error: {}
'''
        yaml_path = tmp_path / "test.yml"
        yaml_path.write_text(yaml_content)
        graph = parse_yaml(yaml_path)
        return graph, yaml_path

    def test_does_not_generate_exit_enum(self, exit_node_graph) -> None:
        """Exit Enum を生成しない。"""
        graph, yaml_path = exit_node_graph
        code = generate_transition_code(graph, str(yaml_path))

        assert "class Exit(" not in code
        assert "Exit.GREEN" not in code
        assert "Exit.RED" not in code
        assert "Exit.code(" not in code

    def test_does_not_generate_exit_codes(self, exit_node_graph) -> None:
        """EXIT_CODES 辞書を生成しない。"""
        graph, yaml_path = exit_node_graph
        code = generate_transition_code(graph, str(yaml_path))

        assert "EXIT_CODES" not in code
        assert "ExitOutcome" not in code

    def test_run_returns_exit_contract(self, exit_node_graph) -> None:
        """run() の返り値型が ExitContract。"""
        graph, yaml_path = exit_node_graph
        code = generate_transition_code(graph, str(yaml_path))

        assert "def run(" in code
        assert "-> ExitContract:" in code
        assert "from railway import ExitContract" in code or \
               "from railway.core.contract.exit import ExitContract" in code

    def test_generates_exit_node_functions(self, exit_node_graph) -> None:
        """終端ノード関数が生成される。"""
        graph, yaml_path = exit_node_graph
        code = generate_transition_code(graph, str(yaml_path))

        assert "def _exit_success_done(" in code
        assert "def _exit_failure_error(" in code

    def test_transition_table_uses_function_refs(self, exit_node_graph) -> None:
        """TRANSITION_TABLE が Exit.code() ではなく関数参照を使用。"""
        graph, yaml_path = exit_node_graph
        code = generate_transition_code(graph, str(yaml_path))

        # Exit.code() を使用していない
        assert "Exit.code(" not in code
        # 関数参照を使用
        assert "_exit_success_done" in code
        assert "_exit_failure_error" in code
```

## TDD 実装フロー

### Phase 1: Red（テスト作成）

1. `tests/unit/core/dag/test_runner_exit_contract.py` を作成
2. `tests/unit/codegen/test_transition_code_exit_contract.py` を作成
3. テストが失敗することを確認

### Phase 2: Green（最小実装）

1. `_is_exit_node()` 純粋関数を追加
2. `_derive_exit_state()` 純粋関数を追加
3. `dag_runner()` を修正
4. `async_dag_runner()` を修正
5. codegen を修正

### Phase 3: Refactor

1. 不要な `Exit`, `DagRunnerResult` を削除
2. ドキュメント更新

---

## 受け入れ条件

### runner.py
- [ ] `Exit` クラスが削除されている
- [ ] `DagRunnerResult` クラスが削除されている
- [ ] `exit_codes` パラメータが削除されている
- [ ] `_is_exit_node()` 関数が追加されている（純粋関数）
- [ ] `_derive_exit_state()` 関数が追加されている（純粋関数）
- [ ] `dag_runner()` が `ExitContract` を返す
- [ ] `async_dag_runner()` が `ExitContract` を返す
- [ ] 後方互換（Context のみ返す終端ノード）が動作

### codegen
- [ ] codegen が `Exit Enum` を生成しない
- [ ] codegen が `EXIT_CODES` を生成しない
- [ ] `run()` / `run_async()` が `ExitContract` を返す

### テスト
- [ ] TDD フェーズに従って実装（Red → Green → Refactor）
- [ ] 全テストがパス

---

*コア変更・dag_runner と codegen を同時に修正*
