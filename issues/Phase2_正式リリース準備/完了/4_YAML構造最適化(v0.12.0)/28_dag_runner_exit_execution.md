# Issue #28: dag_runner の終端ノード実行

**Phase:** 2
**優先度:** 高
**依存関係:** Issue #27（codegen の終端ノード対応 - EXIT_CODES 生成）
**見積もり:** 0.5日

---

## 概要

`dag_runner` が終端ノード（`nodes.exit` 配下）に到達した際、その関数を実行する。
終端ノードの返り値（コンテキスト）がエントリーポイントの返り値となる。

---

## 設計変更

### 終端ノードの返り値

**通常ノード:** `tuple[Context, Outcome]` を返す
**終端ノード:** `Context` のみを返す（Outcome は不要、遷移先がないため）

```python
# 通常ノード
@node
def process(ctx: InputContext) -> tuple[OutputContext, Outcome]:
    return OutputContext(...), Outcome.success("done")

# 終端ノード
@node
def done(ctx: ProcessContext) -> FinalSummary:
    """終端ノードは Context のみを返す。"""
    return FinalSummary(status="completed", count=ctx.count)
```

### dag_runner の exit_code フォーマット

**変更前:**
```python
exit_code="exit::green::success"  # 単純な名前
```

**変更後:**
```python
exit_code="exit::green::exit.success.done"  # フルパス
```

これにより、どの終端ノードで終了したかを正確に識別できる。

---

## API 変更

```python
def dag_runner(
    start: Callable[[], tuple[Any, Outcome]],
    transitions: dict[str, Callable],
    exit_codes: dict[str, int] | None = None,  # ← 新規パラメータ
    max_iterations: int = 100,
    strict: bool = True,
    on_step: Callable[[str, str, Any], None] | None = None,
) -> DagRunnerResult:
    """DAG ワークフローを実行する。

    Args:
        start: 開始ノード関数（引数なしで呼び出される）
        transitions: 状態 → 次ノード/終端ノード のマッピング
        exit_codes: 終端ノード名 → 終了コード のマッピング（新規）
        max_iterations: 最大反復回数
        strict: 未定義状態でエラーを発生させるか
        on_step: ステップコールバック

    Returns:
        DagRunnerResult

    Note:
        開始ノードは引数なしで呼び出されます（Callable[[], tuple[Any, Outcome]]）。

        **推奨:** Issue #31 の run() ヘルパーを使用してください:

        >>> from src.transitions.my_workflow import run
        >>> result = run({"user_id": 123})

        **上級者向け:** lambda でラップして直接 dag_runner を呼び出すことも可能:

        >>> dag_runner(
        ...     start=lambda: my_start_node(initial_ctx),
        ...     transitions=TRANSITION_TABLE,
        ...     exit_codes=EXIT_CODES,
        ... )
    """
```

---

## 実装

```python
def dag_runner(
    start: Callable[[], tuple[Any, Outcome]],
    transitions: dict[str, Callable],
    exit_codes: dict[str, int] | None = None,
    max_iterations: int = 100,
    strict: bool = True,
    on_step: Callable[[str, str, Any], None] | None = None,
) -> DagRunnerResult:
    """DAG ワークフローを実行する（不変データ構造を使用）。"""
    exit_codes = exit_codes or {}

    # 開始ノード実行
    context, outcome = start()
    node_name = _get_node_name(start)
    state_string = outcome.to_state_string(node_name)
    execution_path: tuple[str, ...] = (node_name,)
    iteration = 1

    if on_step:
        on_step(node_name, state_string, context)

    while iteration < max_iterations:
        next_step = transitions.get(state_string)

        if next_step is None:
            if strict:
                raise UndefinedStateError(state_string)
            # strict=False: 遷移先がなければ終了
            return DagRunnerResult(
                exit_code=state_string,
                context=context,
                iterations=iteration,
                execution_path=execution_path,
            )

        # 次のノードを実行
        iteration += 1
        next_node_name = _get_node_name(next_step)

        # 終端ノード判定
        if next_node_name in exit_codes:
            # 終端ノードは Context のみを返す
            final_context = next_step(context)
            execution_path = (*execution_path, next_node_name)

            exit_code_value = exit_codes[next_node_name]
            color = "green" if exit_code_value == 0 else "red"

            if on_step:
                # 終端ノードの state_string は exit:: 形式
                exit_state = f"exit::{color}::{next_node_name}"
                on_step(next_node_name, exit_state, final_context)

            return DagRunnerResult(
                exit_code=f"exit::{color}::{next_node_name}",
                context=final_context,
                iterations=iteration,
                execution_path=execution_path,
            )

        # 通常ノード
        context, outcome = next_step(context)
        node_name = next_node_name
        state_string = outcome.to_state_string(node_name)
        execution_path = (*execution_path, node_name)

        if on_step:
            on_step(node_name, state_string, context)

    raise MaxIterationsError(max_iterations)
```

---

## TDD 実装手順

### Step 1: 終端ノード実行テスト（Red）

```python
# tests/unit/dag/test_runner_exit.py
"""Tests for dag_runner exit node execution."""

import pytest
from railway.core.dag.runner import dag_runner, DagRunnerResult
from railway.core.dag.outcome import Outcome


class TestDagRunnerExitNode:
    """dag_runner の終端ノード実行テスト。"""

    def test_executes_exit_node_function(self) -> None:
        """終端ノード関数が実行される。"""
        execution_log: list[str] = []

        def start():
            execution_log.append("start")
            return {"count": 1}, Outcome.success("done")

        def exit_success_done(ctx):
            """終端ノードは Context のみを返す。"""
            execution_log.append("exit.success.done")
            return {"summary": "completed", "original_count": ctx["count"]}

        transitions = {
            "start::success::done": exit_success_done,
        }
        exit_codes = {
            "exit.success.done": 0,
        }

        # exit_success_done に _node_name 属性を設定
        exit_success_done._node_name = "exit.success.done"

        result = dag_runner(
            start=start,
            transitions=transitions,
            exit_codes=exit_codes,
        )

        assert "start" in execution_log
        assert "exit.success.done" in execution_log
        assert result.context["summary"] == "completed"
        assert result.context["original_count"] == 1
        assert result.is_success is True

    def test_exit_node_returns_final_context(self) -> None:
        """終端ノードの返り値が最終コンテキストになる。"""

        def start():
            return {"initial": True}, Outcome.success("done")

        def exit_success_done(ctx):
            return {
                "status": "completed",
                "original": ctx,
            }

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "start::success::done": exit_success_done,
        }
        exit_codes = {
            "exit.success.done": 0,
        }

        result = dag_runner(
            start=start,
            transitions=transitions,
            exit_codes=exit_codes,
        )

        assert result.context["status"] == "completed"
        assert result.context["original"]["initial"] is True

    def test_exit_code_zero_is_green(self) -> None:
        """終了コード 0 は green。"""

        def start():
            return {}, Outcome.success("done")

        def exit_success_done(ctx):
            return ctx

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "start::success::done": exit_success_done,
        }
        exit_codes = {
            "exit.success.done": 0,
        }

        result = dag_runner(
            start=start,
            transitions=transitions,
            exit_codes=exit_codes,
        )

        assert "green" in result.exit_code
        assert "exit.success.done" in result.exit_code
        assert result.is_success is True

    def test_exit_code_nonzero_is_red(self) -> None:
        """終了コード 0 以外は red。"""

        def start():
            return {}, Outcome.failure("error")

        def exit_failure_error(ctx):
            return ctx

        exit_failure_error._node_name = "exit.failure.error"

        transitions = {
            "start::failure::error": exit_failure_error,
        }
        exit_codes = {
            "exit.failure.error": 1,
        }

        result = dag_runner(
            start=start,
            transitions=transitions,
            exit_codes=exit_codes,
        )

        assert "red" in result.exit_code
        assert "exit.failure.error" in result.exit_code
        assert result.is_success is False

    def test_on_step_called_for_exit_node(self) -> None:
        """on_step コールバックが終端ノードでも呼ばれる。"""
        step_log: list[tuple[str, str]] = []

        def start():
            return {}, Outcome.success("done")

        def exit_success_done(ctx):
            return ctx

        exit_success_done._node_name = "exit.success.done"

        def on_step(node_name: str, state: str, ctx) -> None:
            step_log.append((node_name, state))

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

        assert ("start", "start::success::done") in step_log
        # 終端ノードは exit:: 形式
        assert any(
            "exit.success.done" in node and "exit::green" in state
            for node, state in step_log
        )

    def test_execution_path_includes_exit_node(self) -> None:
        """execution_path に終端ノードが含まれる。"""

        def start():
            return {}, Outcome.success("done")

        def exit_success_done(ctx):
            return ctx

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "start::success::done": exit_success_done,
        }
        exit_codes = {
            "exit.success.done": 0,
        }

        result = dag_runner(
            start=start,
            transitions=transitions,
            exit_codes=exit_codes,
        )

        assert "start" in result.execution_path
        assert "exit.success.done" in result.execution_path

    def test_backward_compatible_without_exit_codes(self) -> None:
        """exit_codes なしでも動作（後方互換）。"""

        def start():
            return {}, Outcome.success("done")

        def process(ctx):
            return ctx, Outcome.success("complete")

        transitions = {
            "start::success::done": process,
            # process::success::complete に遷移先がない → strict=False で終了
        }

        result = dag_runner(
            start=start,
            transitions=transitions,
            strict=False,  # 遷移先がなくてもエラーにしない
        )

        # 遷移先がないため終了
        assert result.exit_code == "process::success::complete"

    def test_custom_exit_code(self) -> None:
        """カスタム終了コード。"""

        def start():
            return {}, Outcome.success("warn")

        def exit_warning_low_disk(ctx):
            return {"warning": "disk space low"}

        exit_warning_low_disk._node_name = "exit.warning.low_disk"

        transitions = {
            "start::success::warn": exit_warning_low_disk,
        }
        exit_codes = {
            "exit.warning.low_disk": 2,  # カスタム終了コード
        }

        result = dag_runner(
            start=start,
            transitions=transitions,
            exit_codes=exit_codes,
        )

        # 0 以外は red
        assert "red" in result.exit_code
        assert "exit.warning.low_disk" in result.exit_code


class TestDagRunnerExitNodeAsync:
    """async_dag_runner の終端ノード実行テスト。"""

    @pytest.mark.asyncio
    async def test_async_executes_exit_node(self) -> None:
        """非同期版でも終端ノードが実行される。"""
        from railway.core.dag.runner import async_dag_runner

        async def start():
            return {"count": 1}, Outcome.success("done")

        async def exit_success_done(ctx):
            return {"summary": "completed"}

        exit_success_done._node_name = "exit.success.done"

        transitions = {
            "start::success::done": exit_success_done,
        }
        exit_codes = {
            "exit.success.done": 0,
        }

        result = await async_dag_runner(
            start=start,
            transitions=transitions,
            exit_codes=exit_codes,
        )

        assert result.context["summary"] == "completed"
        assert result.is_success is True
```

---

## 完了条件

- [ ] `exit_codes` パラメータ追加
- [ ] 終端ノード関数を実行
- [ ] 終端ノードは `Context` のみを返す（`Outcome` なし）
- [ ] 終端ノードの返り値が `result.context` になる
- [ ] 終了コードから green/red を判定
- [ ] `exit_code` フォーマットにノードのフルパスを含める
- [ ] `on_step` コールバックが終端ノードでも呼ばれる
- [ ] `execution_path` に終端ノードが含まれる
- [ ] 後方互換性（exit_codes なしでも動作）
- [ ] async_dag_runner も対応
- [ ] 既存テスト通過
- [ ] 新規テスト通過

---

## 関連 Issue

- Issue #27: codegen の終端ノード対応（前提）
- Issue #30: E2E 統合テスト
- ADR-004: Exit ノードの設計と例外処理
