# Issue #10: DAGランナー実装

**Phase:** 2c
**優先度:** 高
**依存関係:** #03.1（フィクスチャ）, #04, #07, #15（Outcome クラス）
**見積もり:** 1.5日

---

## 概要

生成された遷移テーブルを使用してDAGワークフローを実行するランナーを実装する。
ノードは状態を返し、ランナーが遷移先を決定する。

---

## 設計原則

### Phase1との整合性

DAGランナーはPhase1のOutput Model Pattern (ADR-001) と整合性を保ちます：
- **Contractのみ使用**: コンテキストは `Contract` 型のみ（dict は非対応）
- **純粋関数**: ノードは同じ入力に対して同じ出力
- **型安全性**: Pydantic + mypyによる検証
- **イミュータビリティ**: Contract は `frozen=True`

#### ADR-001 Output Model Pattern の復習

Phase1で確立したOutput Model Patternでは：
1. ノードは `Contract` を出力として返す
2. Contractは `frozen=True` でイミュータブル
3. 次のノードは前のノードの出力を入力として受け取る

DAGランナーではこれを拡張し、**戻り値を `(Contract, State)` のタプルとする**：
```python
# Phase1 (typed_pipeline)
@node
def fetch_data() -> DataContract:
    return DataContract(data="...")

# Phase2 (dag_runner)
@node
def fetch_data() -> tuple[DataContract, Top2State]:
    return DataContract(data="..."), Top2State.FETCH_DATA_SUCCESS_DONE
```

#### 重要: dict は非対応

後方互換性より型安全性を優先し、**dict は完全に非対応**とします：

```python
# ✅ 唯一のサポート形式
@node
def fetch_data() -> tuple[MyContract, MyState]:
    return MyContract(data="..."), MyState.FETCH_DATA_SUCCESS_DONE

# ❌ 非対応（dict は使用不可）
@node
def fetch_data() -> tuple[dict, MyState]:  # 型エラー
    return {"data": "..."}, MyState.FETCH_DATA_SUCCESS_DONE
```

**理由:**
1. **型安全性**: dict はキータイポを検出できない
2. **イミュータビリティ**: dict は変更可能（関数型パラダイム違反）
3. **シリアライズ**: Contract は `model_dump()` で自動変換
4. **一貫性**: Phase1 の Contract 原則を徹底

### ノードはステートレス

```python
# 推奨: Contractを使用した型安全なノード
from railway import Contract, node
from _railway.generated.top2_transitions import Top2State

class WorkflowContext(Contract):
    """ワークフローのコンテキスト"""
    incident_id: str
    session_id: str | None = None
    hostname: str | None = None

@node
def fetch_alert(params: AlertParams) -> tuple[WorkflowContext, Top2State]:
    """型安全なノード - Phase1のContract原則に準拠"""
    ctx = WorkflowContext(incident_id=params.incident_id)
    return ctx, Top2State.FETCH_ALERT_SUCCESS_DONE
```

```python
# 後方互換: dictも許容（新規開発では非推奨）
@node
def fetch_alert_legacy(incident_id: str) -> tuple[dict, Top2State]:
    return {"incident_id": incident_id}, Top2State.FETCH_ALERT_SUCCESS_DONE
```

### ランナーが遷移を制御

```python
# ランナーは遷移テーブルを参照して次のステップを決定
result = dag_runner(
    start=lambda: fetch_alert(incident_id),
    transitions=TRANSITION_TABLE,
    max_iterations=20,
)
```

### シンプルなAPI: Outcome クラスのみ

dag_runner は **Outcome クラス + 文字列キー** のみをサポートします（シンプル！）：

```python
from railway import node
from railway.core.dag.outcome import Outcome

@node
def fetch_data(ctx: InputContext) -> tuple[OutputContext, Outcome]:
    try:
        data = api.get("/data")
        return OutputContext(data=data), Outcome.success("done")
    except HTTPError:
        return OutputContext(), Outcome.failure("http")
```

dag_runner は Outcome から自動的に状態文字列を生成：
- `Outcome.success("done")` → `"fetch_data::success::done"`
- `Outcome.failure("http")` → `"fetch_data::failure::http"`

遷移テーブルは **文字列キー** を使用：

```python
from railway.core.dag.runner import Exit

transitions = {
    "fetch_data::success::done": process_data,
    "fetch_data::failure::http": Exit.RED,
    "process_data::success::complete": Exit.GREEN,
}
```

### Exit 定数クラス

終了コードは `Exit` クラスの定数として定義：

```python
class Exit:
    """終了コード定数"""
    GREEN = "exit::green::done"      # 正常終了（成功）
    YELLOW = "exit::yellow::warning" # 警告終了
    RED = "exit::red::error"         # 異常終了（失敗）

    @staticmethod
    def code(color: str, detail: str = "done") -> str:
        """カスタム終了コードを生成"""
        return f"exit::{color}::{detail}"
```

**Note:** State Enum は生成コード内部でのみ使用。ユーザーは Outcome と文字列キーのみを使用します。

---

## TDD実装手順

### Step 1: Red（テストを書く）

> **Note:** すべてのテストで Contract + Outcome + 文字列キー を使用。

```python
# tests/unit/core/dag/test_runner.py
"""Tests for DAG runner with Contract + Outcome (string keys only)."""
import pytest
from railway import Contract
from railway.core.dag.outcome import Outcome


class TestDagRunner:
    """Test dag_runner function with Contract and Outcome."""

    def test_simple_workflow(self):
        """Should execute a simple linear workflow."""
        from railway.core.dag.runner import dag_runner, Exit

        class WorkflowContext(Contract):
            value: int

        def node_a() -> tuple[WorkflowContext, Outcome]:
            return WorkflowContext(value=1), Outcome.success("done")

        def node_b(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            # Contract はイミュータブル、model_copy で新規生成
            return ctx.model_copy(update={"value": 2}), Outcome.success("done")

        # 文字列キーのみ（シンプル！）
        transitions = {
            "node_a::success::done": node_b,
            "node_b::success::done": Exit.GREEN,
        }

        result = dag_runner(
            start=node_a,
            transitions=transitions,
        )

        assert result.exit_code == Exit.GREEN
        assert result.context.value == 2
        assert result.iterations == 2

    def test_branching_workflow(self):
        """Should handle conditional branching."""
        from railway.core.dag.runner import dag_runner, Exit

        class BranchContext(Contract):
            path: str

        call_log = []

        def check(condition: bool) -> tuple[BranchContext, Outcome]:
            call_log.append("check")
            if condition:
                return BranchContext(path="a"), Outcome.success("true")
            else:
                return BranchContext(path="b"), Outcome.success("false")

        def path_a(ctx: BranchContext) -> tuple[BranchContext, Outcome]:
            call_log.append("path_a")
            return ctx, Outcome.success("done")

        def path_b(ctx: BranchContext) -> tuple[BranchContext, Outcome]:
            call_log.append("path_b")
            return ctx, Outcome.success("done")

        transitions = {
            "check::success::true": path_a,
            "check::success::false": path_b,
            "path_a::success::done": Exit.code("green", "done_a"),
            "path_b::success::done": Exit.code("green", "done_b"),
        }

        # Test true branch
        call_log.clear()
        result = dag_runner(
            start=lambda: check(True),
            transitions=transitions,
        )

        assert result.exit_code == "exit::green::done_a"
        assert call_log == ["check", "path_a"]

    def test_max_iterations_limit(self):
        """Should stop when max iterations reached."""
        from railway.core.dag.runner import dag_runner, MaxIterationsError

        class LoopContext(Contract):
            count: int = 0

        def loop_node(ctx: LoopContext) -> tuple[LoopContext, Outcome]:
            return ctx.model_copy(update={"count": ctx.count + 1}), Outcome.success("continue")

        transitions = {
            "loop_node::success::continue": loop_node,
        }

        with pytest.raises(MaxIterationsError):
            dag_runner(
                start=lambda: loop_node(LoopContext()),
                transitions=transitions,
                max_iterations=5,
            )

    def test_undefined_state_error(self):
        """Should error on undefined state."""
        from railway.core.dag.runner import dag_runner, UndefinedStateError

        class EmptyContext(Contract):
            pass

        def node() -> tuple[EmptyContext, Outcome]:
            return EmptyContext(), Outcome.failure("unknown")

        transitions = {
            "node::success::known": lambda x: (x, Outcome.success("done")),
        }

        with pytest.raises(UndefinedStateError):
            dag_runner(
                start=node,
                transitions=transitions,
                strict=True,
            )

    def test_passes_context_between_nodes(self):
        """Should pass context from one node to the next."""
        from railway.core.dag.runner import dag_runner, Exit

        class ChainContext(Contract):
            from_a: bool = False
            from_b: bool = False

        def node_a() -> tuple[ChainContext, Outcome]:
            return ChainContext(from_a=True), Outcome.success("done")

        def node_b(ctx: ChainContext) -> tuple[ChainContext, Outcome]:
            assert ctx.from_a is True
            return ctx.model_copy(update={"from_b": True}), Outcome.success("done")

        transitions = {
            "node_a::success::done": node_b,
            "node_b::success::done": Exit.GREEN,
        }

        result = dag_runner(start=node_a, transitions=transitions)

        assert result.context.from_a is True
        assert result.context.from_b is True


class TestDagRunnerResult:
    """Test DagRunnerResult data type."""

    def test_result_properties(self):
        """Should have expected properties."""
        from railway.core.dag.runner import DagRunnerResult, Exit

        class ResultContext(Contract):
            key: str

        result = DagRunnerResult(
            exit_code=Exit.GREEN,
            context=ResultContext(key="value"),
            iterations=3,
            execution_path=("node_a", "node_b", "node_c"),
        )

        assert result.exit_code == Exit.GREEN
        assert result.context.key == "value"
        assert result.iterations == 3
        assert len(result.execution_path) == 3

    def test_result_is_success(self):
        """Should determine success based on exit code (green = success)."""
        from railway.core.dag.runner import DagRunnerResult, Exit

        class EmptyContext(Contract):
            pass

        success_result = DagRunnerResult(
            exit_code=Exit.GREEN,
            context=EmptyContext(),
            iterations=1,
            execution_path=(),
        )
        assert success_result.is_success is True

        failure_result = DagRunnerResult(
            exit_code=Exit.RED,
            context=EmptyContext(),
            iterations=1,
            execution_path=(),
        )
        assert failure_result.is_success is False

        warning_result = DagRunnerResult(
            exit_code=Exit.YELLOW,
            context=EmptyContext(),
            iterations=1,
            execution_path=(),
        )
        # yellowも成功扱い（警告付き成功）
        assert warning_result.is_success is True


class TestDagRunnerWithOutcome:
    """Test dag_runner with Outcome class (string keys only)."""

    def test_workflow_with_outcome(self):
        """Should work with Outcome and string transition keys."""
        from railway.core.dag.runner import dag_runner, Exit

        class WorkflowContext(Contract):
            value: int

        def node_a() -> tuple[WorkflowContext, Outcome]:
            return WorkflowContext(value=1), Outcome.success("done")

        def node_b(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx.model_copy(update={"value": 2}), Outcome.success("complete")

        transitions = {
            "node_a::success::done": node_b,
            "node_b::success::complete": Exit.GREEN,
        }

        result = dag_runner(start=node_a, transitions=transitions)

        assert result.is_success
        assert result.context.value == 2

    def test_failure_path(self):
        """Should handle failure outcomes correctly."""
        from railway.core.dag.runner import dag_runner, Exit

        class FailContext(Contract):
            error_type: str = ""

        def check() -> tuple[FailContext, Outcome]:
            return FailContext(error_type="validation"), Outcome.failure("validation")

        def handle_error(ctx: FailContext) -> tuple[FailContext, Outcome]:
            return ctx, Outcome.success("handled")

        transitions = {
            "check::success::done": Exit.GREEN,
            "check::failure::validation": handle_error,
            "handle_error::success::handled": Exit.YELLOW,
        }

        result = dag_runner(start=check, transitions=transitions)

        assert result.exit_code == Exit.YELLOW
        assert result.context.error_type == "validation"


class TestDagRunnerAsync:
    """Test async dag_runner."""

    @pytest.mark.asyncio
    async def test_async_workflow(self):
        """Should execute async nodes."""
        from railway.core.dag.runner import async_dag_runner, Exit

        class AsyncContext(Contract):
            is_async: bool

        async def async_node() -> tuple[AsyncContext, Outcome]:
            return AsyncContext(is_async=True), Outcome.success("done")

        transitions = {
            "async_node::success::done": Exit.GREEN,
        }

        result = await async_dag_runner(
            start=async_node,
            transitions=transitions,
        )

        assert result.is_success
        assert result.context.is_async is True


class TestDagRunnerIntegration:
    """Integration tests using test YAML fixtures."""

    def test_with_simple_yaml_workflow(self, simple_yaml):
        """Should execute workflow from simple test YAML.

        Note: Uses tests/fixtures/transition_graphs/simple_20250125000000.yml
        """
        from railway.core.dag.parser import load_transition_graph

        # Parse the test YAML
        graph = load_transition_graph(simple_yaml)

        assert graph.entrypoint == "simple"
        assert len(graph.nodes) == 1
        # Further integration tests would mock the nodes

    def test_with_branching_yaml_workflow(self, branching_yaml):
        """Should parse branching workflow from test YAML.

        Note: Uses tests/fixtures/transition_graphs/branching_20250125000000.yml
        """
        from railway.core.dag.parser import load_transition_graph

        graph = load_transition_graph(branching_yaml)

        assert graph.entrypoint == "branching"
        assert len(graph.nodes) == 5  # 5 nodes in branching workflow
```

```bash
pytest tests/unit/core/dag/test_runner.py -v
# Expected: FAILED (ImportError)
```

### Step 2: Green（最小限の実装）

```python
# railway/core/dag/runner.py
"""
DAG workflow runner.

Executes workflows defined by transition tables,
routing between nodes based on their returned states.

Note: This runner ONLY supports Contract context and string keys.
      dict context is NOT supported.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from loguru import logger

from railway.core.dag.outcome import Outcome
from railway.core.contract import Contract


# Context type: Contract only (dict is NOT supported)
ContextT = TypeVar("ContextT", bound=Contract)


class Exit:
    """
    終了コード定数。

    遷移テーブルの値として使用します。

    Example:
        transitions = {
            "node::success::done": Exit.GREEN,
            "node::failure::error": Exit.RED,
        }
    """
    GREEN = "exit::green::done"      # 正常終了（成功）
    YELLOW = "exit::yellow::warning" # 警告終了（成功扱い）
    RED = "exit::red::error"         # 異常終了（失敗）

    @staticmethod
    def code(color: str, detail: str = "done") -> str:
        """カスタム終了コードを生成"""
        return f"exit::{color}::{detail}"


class MaxIterationsError(Exception):
    """Raised when max iterations limit is reached."""
    pass


class UndefinedStateError(Exception):
    """Raised when a node returns an undefined state."""
    pass


@dataclass(frozen=True)
class DagRunnerResult:
    """
    Result of DAG workflow execution.

    Attributes:
        exit_code: The exit code string (e.g., "exit::green::done")
        context: Final context from the last node (Contract only)
        iterations: Number of nodes executed
        execution_path: Tuple of node names in execution order
    """
    exit_code: str
    context: Contract
    iterations: int
    execution_path: tuple[str, ...]

    @property
    def is_success(self) -> bool:
        """Check if the workflow completed successfully (green or yellow)."""
        return "::green::" in self.exit_code or "::yellow::" in self.exit_code


def dag_runner(
    start: Callable[[], tuple[Any, Outcome]],
    transitions: dict[str, Callable | str],
    max_iterations: int = 100,
    strict: bool = True,
    on_step: Callable[[str, str, Any], None] | None = None,
) -> DagRunnerResult:
    """
    Execute a DAG workflow.

    The runner executes nodes in sequence, using the transition table
    to determine the next node based on each node's returned state.

    Nodes return Outcome, and the runner generates state strings automatically:
    - Outcome.success("done") → "node_name::success::done"
    - Outcome.failure("error") → "node_name::failure::error"

    Args:
        start: Initial node function (returns (context, Outcome))
        transitions: Mapping of state strings to next nodes or exit codes
        max_iterations: Maximum number of node executions
        strict: Raise error on undefined states
        on_step: Optional callback for each step (node_name, state_string, context)

    Returns:
        DagRunnerResult with exit code and final context

    Raises:
        MaxIterationsError: If max iterations exceeded
        UndefinedStateError: If strict and undefined state encountered

    Example:
        transitions = {
            "fetch::success::done": process,
            "fetch::failure::http": Exit.RED,
            "process::success::done": Exit.GREEN,
        }
        result = dag_runner(start=fetch, transitions=transitions)
    """
    logger.debug(f"DAGワークフロー開始: max_iterations={max_iterations}")

    execution_path: list[str] = []
    iteration = 0

    # Execute start node
    context, outcome = start()
    node_name = _get_node_name(start)
    state_string = outcome.to_state_string(node_name)

    execution_path.append(node_name)
    iteration += 1

    logger.debug(f"[{iteration}] {node_name} -> {state_string}")

    if on_step:
        on_step(node_name, state_string, context)

    # Execution loop
    while iteration < max_iterations:
        # Look up next step
        next_step = transitions.get(state_string)

        if next_step is None:
            if strict:
                raise UndefinedStateError(
                    f"未定義の状態です: {state_string} "
                    f"(ノード: {node_name})"
                )
            else:
                logger.warning(f"未定義の状態: {state_string}")
                break

        # Check if it's an exit (string starting with "exit::")
        if isinstance(next_step, str) and next_step.startswith("exit::"):
            logger.debug(f"DAGワークフロー終了: {next_step}")
            return DagRunnerResult(
                exit_code=next_step,
                context=context,
                iterations=iteration,
                execution_path=tuple(execution_path),
            )

        # Execute next node
        iteration += 1
        context, outcome = next_step(context)
        node_name = _get_node_name(next_step)
        state_string = outcome.to_state_string(node_name)

        execution_path.append(node_name)

        logger.debug(f"[{iteration}] {node_name} -> {state_string}")

        if on_step:
            on_step(node_name, state_string, context)

    # Max iterations reached
    raise MaxIterationsError(
        f"最大イテレーション数 ({max_iterations}) に達しました。"
        f"実行パス: {' -> '.join(execution_path[-10:])}"
    )


def _get_node_name(func: Callable) -> str:
    """Get node name from function."""
    # Check for @node decorator metadata
    if hasattr(func, "_node_name"):
        return func._node_name
    return getattr(func, "__name__", "unknown")


async def async_dag_runner(
    start: Callable[[], tuple[Any, Outcome]],
    transitions: dict[str, Callable | str],
    max_iterations: int = 100,
    strict: bool = True,
    on_step: Callable[[str, str, Any], None] | None = None,
) -> DagRunnerResult:
    """
    Execute a DAG workflow with async support.

    Same as dag_runner but awaits async nodes.
    """
    import asyncio

    logger.debug(f"非同期DAGワークフロー開始: max_iterations={max_iterations}")

    execution_path: list[str] = []
    iteration = 0

    # Execute start node
    if asyncio.iscoroutinefunction(start):
        context, outcome = await start()
    else:
        context, outcome = start()

    node_name = _get_node_name(start)
    state_string = outcome.to_state_string(node_name)
    execution_path.append(node_name)
    iteration += 1

    if on_step:
        on_step(node_name, state_string, context)

    # Execution loop
    while iteration < max_iterations:
        next_step = transitions.get(state_string)

        if next_step is None:
            if strict:
                raise UndefinedStateError(f"未定義の状態です: {state_string}")
            break

        # Check if it's an exit
        if isinstance(next_step, str) and next_step.startswith("exit::"):
            return DagRunnerResult(
                exit_code=next_step,
                context=context,
                iterations=iteration,
                execution_path=tuple(execution_path),
            )

        iteration += 1

        if asyncio.iscoroutinefunction(next_step):
            context, outcome = await next_step(context)
        else:
            context, outcome = next_step(context)

        node_name = _get_node_name(next_step)
        state_string = outcome.to_state_string(node_name)
        execution_path.append(node_name)

        if on_step:
            on_step(node_name, state_string, context)

    raise MaxIterationsError(f"最大イテレーション数 ({max_iterations}) に達しました")
```

```bash
pytest tests/unit/core/dag/test_runner.py -v
# Expected: PASSED
```

### Step 3: Refactor

- 実行トレース機能の強化
- メトリクス収集の追加
- コンテキストのイミュータブル化オプション

---

## 完了条件

- [ ] `dag_runner()` が線形ワークフローを実行
- [ ] 条件分岐が正しく動作
- [ ] `max_iterations` で無限ループを防止
- [ ] 未定義状態でエラー（strictモード）
- [ ] コンテキストがノード間で渡される
- [ ] `DagRunnerResult` が実行結果を保持
- [ ] `async_dag_runner()` が非同期ノードをサポート
- [ ] `on_step` コールバックが動作
- [ ] **Outcome クラスから状態文字列を自動生成**
- [ ] **Exit 定数クラスで終了コードを定義**
- [ ] **遷移テーブルは文字列キーのみ**（シンプル！）
- [ ] テストカバレッジ90%以上

---

## 次のIssue

- #11: ステップコールバック
