# Issue #10: DAGランナー実装

**Phase:** 2c
**優先度:** 高
**依存関係:** #03.1（フィクスチャ）, #04, #07
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

### ユーザビリティ向上: Outcome クラス

> **Note:** このセクションの機能は **Issue #15** で実装されます。
> Issue #10 では State Enum を直接返す実装のみをサポートします。

ノードの戻り値を簡潔に記述するため、`Outcome` クラスと `@node` デコレータの自動マッピングを提供：

```python
# Issue #15 で実装される機能のプレビュー
from railway import node, Outcome

@node(state_enum=MyWorkflowState)
def fetch_data(ctx: InputContext) -> tuple[OutputContext, Outcome]:
    try:
        data = api.get("/data")
        return OutputContext(data=data), Outcome.success("done")
        # => 自動的に MyWorkflowState.FETCH_DATA_SUCCESS_DONE に変換
    except HTTPError:
        return OutputContext(), Outcome.failure("http")
        # => 自動的に MyWorkflowState.FETCH_DATA_FAILURE_HTTP に変換
```

**Issue #10 での推奨パターン（State Enum 直接使用）:**

```python
from _railway.generated.my_workflow_transitions import MyWorkflowState

@node
def fetch_data(ctx: InputContext) -> tuple[OutputContext, MyWorkflowState]:
    try:
        data = api.get("/data")
        return OutputContext(data=data), MyWorkflowState.FETCH_DATA_SUCCESS_DONE
    except HTTPError:
        return OutputContext(), MyWorkflowState.FETCH_DATA_FAILURE_HTTP
```

---

## TDD実装手順

### Step 1: Red（テストを書く）

> **Note:** すべてのテストで Contract を使用。dict は非対応。

```python
# tests/unit/core/dag/test_runner.py
"""Tests for DAG runner with Contract-only context."""
import pytest
from railway import Contract


class TestDagRunner:
    """Test dag_runner function with Contract context."""

    def test_simple_workflow(self):
        """Should execute a simple linear workflow."""
        from railway.core.dag.runner import dag_runner
        from railway.core.dag.state import NodeOutcome, ExitOutcome

        class WorkflowContext(Contract):
            value: int

        class State(NodeOutcome):
            A_SUCCESS = "a::success::done"
            B_SUCCESS = "b::success::done"

        class Exit(ExitOutcome):
            DONE = "exit::green::done"

        def node_a() -> tuple[WorkflowContext, State]:
            return WorkflowContext(value=1), State.A_SUCCESS

        def node_b(ctx: WorkflowContext) -> tuple[WorkflowContext, State]:
            # Contract はイミュータブル、model_copy で新規生成
            return ctx.model_copy(update={"value": 2}), State.B_SUCCESS

        transitions = {
            State.A_SUCCESS: node_b,
            State.B_SUCCESS: Exit.DONE,
        }

        result = dag_runner(
            start=node_a,
            transitions=transitions,
        )

        assert result.exit_code == Exit.DONE
        assert result.context.value == 2
        assert result.iterations == 2

    def test_branching_workflow(self):
        """Should handle conditional branching."""
        from railway.core.dag.runner import dag_runner
        from railway.core.dag.state import NodeOutcome, ExitOutcome

        class BranchContext(Contract):
            path: str

        class State(NodeOutcome):
            CHECK_TRUE = "check::success::true"
            CHECK_FALSE = "check::success::false"
            PATH_A = "path_a::success::done"
            PATH_B = "path_b::success::done"

        class Exit(ExitOutcome):
            DONE_A = "exit::green::done_a"
            DONE_B = "exit::green::done_b"

        call_log = []

        def check(condition: bool) -> tuple[BranchContext, State]:
            call_log.append("check")
            if condition:
                return BranchContext(path="a"), State.CHECK_TRUE
            else:
                return BranchContext(path="b"), State.CHECK_FALSE

        def path_a(ctx: BranchContext) -> tuple[BranchContext, State]:
            call_log.append("path_a")
            return ctx, State.PATH_A

        def path_b(ctx: BranchContext) -> tuple[BranchContext, State]:
            call_log.append("path_b")
            return ctx, State.PATH_B

        transitions = {
            State.CHECK_TRUE: path_a,
            State.CHECK_FALSE: path_b,
            State.PATH_A: Exit.DONE_A,
            State.PATH_B: Exit.DONE_B,
        }

        # Test true branch
        result = dag_runner(
            start=lambda: check(True),
            transitions=transitions,
        )

        assert result.exit_code == Exit.DONE_A
        assert call_log == ["check", "path_a"]

    def test_max_iterations_limit(self):
        """Should stop when max iterations reached."""
        from railway.core.dag.runner import dag_runner, MaxIterationsError
        from railway.core.dag.state import NodeOutcome

        class LoopContext(Contract):
            count: int = 0

        class State(NodeOutcome):
            LOOP = "loop::success::continue"

        def loop_node(ctx: LoopContext) -> tuple[LoopContext, State]:
            return ctx.model_copy(update={"count": ctx.count + 1}), State.LOOP

        transitions = {
            State.LOOP: loop_node,
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
        from railway.core.dag.state import NodeOutcome

        class EmptyContext(Contract):
            pass

        class State(NodeOutcome):
            KNOWN = "node::success::known"
            UNKNOWN = "node::failure::unknown"

        def node() -> tuple[EmptyContext, State]:
            return EmptyContext(), State.UNKNOWN

        transitions = {
            State.KNOWN: lambda x: (x, State.KNOWN),
        }

        with pytest.raises(UndefinedStateError):
            dag_runner(
                start=node,
                transitions=transitions,
                strict=True,
            )

    def test_passes_context_between_nodes(self):
        """Should pass context from one node to the next."""
        from railway.core.dag.runner import dag_runner
        from railway.core.dag.state import NodeOutcome, ExitOutcome

        class ChainContext(Contract):
            from_a: bool = False
            from_b: bool = False

        class State(NodeOutcome):
            A = "a::success::done"
            B = "b::success::done"

        class Exit(ExitOutcome):
            DONE = "exit::green::done"

        def node_a() -> tuple[ChainContext, State]:
            return ChainContext(from_a=True), State.A

        def node_b(ctx: ChainContext) -> tuple[ChainContext, State]:
            assert ctx.from_a is True
            return ctx.model_copy(update={"from_b": True}), State.B

        transitions = {
            State.A: node_b,
            State.B: Exit.DONE,
        }

        result = dag_runner(start=node_a, transitions=transitions)

        assert result.context.from_a is True
        assert result.context.from_b is True


class TestDagRunnerResult:
    """Test DagRunnerResult data type."""

    def test_result_properties(self):
        """Should have expected properties."""
        from railway.core.dag.runner import DagRunnerResult
        from railway.core.dag.state import ExitOutcome

        class ResultContext(Contract):
            key: str

        class Exit(ExitOutcome):
            DONE = "exit::green::done"

        result = DagRunnerResult(
            exit_code=Exit.DONE,
            context=ResultContext(key="value"),
            iterations=3,
            execution_path=("node_a", "node_b", "node_c"),
        )

        assert result.exit_code == Exit.DONE
        assert result.context.key == "value"
        assert result.iterations == 3
        assert len(result.execution_path) == 3

    def test_result_is_success(self):
        """Should determine success based on exit code."""
        from railway.core.dag.runner import DagRunnerResult
        from railway.core.dag.state import ExitOutcome

        class EmptyContext(Contract):
            pass

        class Exit(ExitOutcome):
            GREEN = "exit::green::done"
            RED = "exit::red::error"

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


class TestDagRunnerContractOnly:
    """Test that dag_runner ONLY supports Contract context."""

    def test_workflow_with_contract_context(self):
        """Should work with Contract-based context."""
        from railway.core.dag.runner import dag_runner
        from railway.core.dag.state import NodeOutcome, ExitOutcome

        class WorkflowContext(Contract):
            value: int
            processed: bool = False

        class State(NodeOutcome):
            A_SUCCESS = "a::success::done"
            B_SUCCESS = "b::success::done"

        class Exit(ExitOutcome):
            DONE = "exit::green::done"

        def node_a() -> tuple[WorkflowContext, State]:
            return WorkflowContext(value=1), State.A_SUCCESS

        def node_b(ctx: WorkflowContext) -> tuple[WorkflowContext, State]:
            # Contract is immutable, use model_copy
            return ctx.model_copy(update={"processed": True}), State.B_SUCCESS

        transitions = {
            State.A_SUCCESS: node_b,
            State.B_SUCCESS: Exit.DONE,
        }

        result = dag_runner(start=node_a, transitions=transitions)

        assert result.is_success
        assert isinstance(result.context, WorkflowContext)
        assert result.context.processed is True


class TestDagRunnerAsync:
    """Test async dag_runner."""

    @pytest.mark.asyncio
    async def test_async_workflow(self):
        """Should execute async nodes."""
        from railway.core.dag.runner import async_dag_runner
        from railway.core.dag.state import NodeOutcome, ExitOutcome

        class AsyncContext(Contract):
            is_async: bool

        class State(NodeOutcome):
            A = "a::success::done"

        class Exit(ExitOutcome):
            DONE = "exit::green::done"

        async def async_node() -> tuple[AsyncContext, State]:
            return AsyncContext(is_async=True), State.A

        transitions = {
            State.A: Exit.DONE,
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
        from railway.core.dag.runner import dag_runner

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

Note: This runner ONLY supports Contract context.
      dict context is NOT supported.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar

from loguru import logger

from railway.core.dag.state import NodeOutcome, ExitOutcome
from railway.core.contract import Contract


# Context type: Contract only (dict is NOT supported)
ContextT = TypeVar("ContextT", bound=Contract)


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
        exit_code: The exit outcome that terminated the workflow
        context: Final context from the last node (Contract only)
        iterations: Number of nodes executed
        execution_path: Tuple of node names in execution order
    """
    exit_code: ExitOutcome
    context: Contract
    iterations: int
    execution_path: tuple[str, ...]

    @property
    def is_success(self) -> bool:
        """Check if the workflow completed successfully."""
        return self.exit_code.is_success


def dag_runner(
    start: Callable[[], tuple[Any, NodeOutcome]],
    transitions: dict[NodeOutcome, Callable | ExitOutcome],
    max_iterations: int = 100,
    strict: bool = True,
    on_step: Callable[[str, NodeOutcome, Any], None] | None = None,
) -> DagRunnerResult:
    """
    Execute a DAG workflow.

    The runner executes nodes in sequence, using the transition table
    to determine the next node based on each node's returned state.

    Args:
        start: Initial node function (returns (context, state))
        transitions: Mapping of states to next nodes or exits
        max_iterations: Maximum number of node executions
        strict: Raise error on undefined states
        on_step: Optional callback for each step (node_name, state, context)

    Returns:
        DagRunnerResult with exit code and final context

    Raises:
        MaxIterationsError: If max iterations exceeded
        UndefinedStateError: If strict and undefined state encountered
    """
    logger.debug(f"DAGワークフロー開始: max_iterations={max_iterations}")

    execution_path: list[str] = []
    iteration = 0

    # Execute start node
    context, state = start()
    node_name = state.node_name
    execution_path.append(node_name)
    iteration += 1

    logger.debug(f"[{iteration}] {node_name} -> {state}")

    if on_step:
        on_step(node_name, state, context)

    # Execution loop
    while iteration < max_iterations:
        # Look up next step
        next_step = transitions.get(state)

        if next_step is None:
            if strict:
                raise UndefinedStateError(
                    f"未定義の状態です: {state} "
                    f"(ノード: {node_name})"
                )
            else:
                logger.warning(f"未定義の状態: {state}")
                break

        # Check if it's an exit
        if isinstance(next_step, ExitOutcome):
            logger.debug(f"DAGワークフロー終了: {next_step}")
            return DagRunnerResult(
                exit_code=next_step,
                context=context,
                iterations=iteration,
                execution_path=tuple(execution_path),
            )

        # Execute next node
        iteration += 1
        context, state = next_step(context)
        node_name = state.node_name
        execution_path.append(node_name)

        logger.debug(f"[{iteration}] {node_name} -> {state}")

        if on_step:
            on_step(node_name, state, context)

    # Max iterations reached
    raise MaxIterationsError(
        f"最大イテレーション数 ({max_iterations}) に達しました。"
        f"実行パス: {' -> '.join(execution_path[-10:])}"
    )


async def async_dag_runner(
    start: Callable[[], tuple[Any, NodeOutcome]],
    transitions: dict[NodeOutcome, Callable | ExitOutcome],
    max_iterations: int = 100,
    strict: bool = True,
    on_step: Callable[[str, NodeOutcome, Any], None] | None = None,
) -> DagRunnerResult:
    """
    Execute a DAG workflow with async support.

    Same as dag_runner but awaits async nodes.
    """
    import asyncio
    import inspect

    logger.debug(f"非同期DAGワークフロー開始: max_iterations={max_iterations}")

    execution_path: list[str] = []
    iteration = 0

    # Execute start node
    if asyncio.iscoroutinefunction(start):
        context, state = await start()
    else:
        context, state = start()

    node_name = state.node_name
    execution_path.append(node_name)
    iteration += 1

    if on_step:
        on_step(node_name, state, context)

    # Execution loop
    while iteration < max_iterations:
        next_step = transitions.get(state)

        if next_step is None:
            if strict:
                raise UndefinedStateError(f"未定義の状態です: {state}")
            break

        if isinstance(next_step, ExitOutcome):
            return DagRunnerResult(
                exit_code=next_step,
                context=context,
                iterations=iteration,
                execution_path=tuple(execution_path),
            )

        iteration += 1

        if asyncio.iscoroutinefunction(next_step):
            context, state = await next_step(context)
        else:
            context, state = next_step(context)

        node_name = state.node_name
        execution_path.append(node_name)

        if on_step:
            on_step(node_name, state, context)

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
- [ ] テストカバレッジ90%以上

---

## 次のIssue

- #11: ステップコールバック
