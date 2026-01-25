# Issue #11: ステップコールバック

**Phase:** 2c
**優先度:** 中
**依存関係:** #10（DAGランナー）
**見積もり:** 0.5日

> **Note:** #10 が #15（Outcome）に依存するため、#15 への直接依存は不要です。

---

## 概要

DAGランナーの各ステップで呼び出されるコールバック機構を実装する。
監査ログ、メトリクス収集、デバッグなどの用途に使用される。

---

## TDD実装手順

### Step 1: Red（テストを書く）

> **Note:** すべてのテストで Contract + Outcome + 文字列キー を使用。

```python
# tests/unit/core/dag/test_callbacks.py
"""Tests for step callbacks with Contract + Outcome (string keys)."""
import pytest
from railway import Contract
from railway.core.dag.outcome import Outcome


class TestOnStepCallback:
    """Test on_step callback functionality with Contract context."""

    def test_callback_called_for_each_step(self):
        """Should call callback for each node execution."""
        from railway.core.dag.runner import dag_runner, Exit
        from railway.core.decorators import node

        class StepContext(Contract):
            step: int

        @node
        def node_a() -> tuple[StepContext, Outcome]:
            return StepContext(step=1), Outcome.success("done")

        @node
        def node_b(ctx: StepContext) -> tuple[StepContext, Outcome]:
            return StepContext(step=2), Outcome.success("done")

        transitions = {
            "node_a::success::done": node_b,
            "node_b::success::done": Exit.GREEN,
        }

        callback_log = []

        def on_step(node_name: str, state_string: str, context: Contract):
            callback_log.append({
                "node": node_name,
                "state": state_string,
                "context": context.model_dump(),
            })

        dag_runner(start=node_a, transitions=transitions, on_step=on_step)

        assert len(callback_log) == 2
        assert callback_log[0]["node"] == "node_a"
        assert callback_log[0]["state"] == "node_a::success::done"
        assert callback_log[1]["node"] == "node_b"

    def test_callback_receives_context(self):
        """Should pass current context to callback."""
        from railway.core.dag.runner import dag_runner, Exit
        from railway.core.decorators import node

        class KeyContext(Contract):
            key: str

        @node
        def node_a() -> tuple[KeyContext, Outcome]:
            return KeyContext(key="value"), Outcome.success("done")

        transitions = {"node_a::success::done": Exit.GREEN}

        received_context = {}

        def on_step(node_name: str, state_string: str, context: Contract):
            received_context.update(context.model_dump())

        dag_runner(start=node_a, transitions=transitions, on_step=on_step)

        assert received_context["key"] == "value"


class TestStepRecorder:
    """Test built-in StepRecorder callback with Contract context."""

    def test_records_execution_history(self):
        """Should record complete execution history."""
        from railway.core.dag.callbacks import StepRecorder
        from railway.core.dag.runner import dag_runner, Exit
        from railway.core.decorators import node

        class EmptyContext(Contract):
            pass

        @node
        def start() -> tuple[EmptyContext, Outcome]:
            return EmptyContext(), Outcome.success("done")

        recorder = StepRecorder()

        dag_runner(
            start=start,
            transitions={"start::success::done": Exit.GREEN},
            on_step=recorder,
        )

        history = recorder.get_history()
        assert len(history) == 1
        assert history[0].node_name == "start"

    def test_recorder_timestamps(self):
        """Should record timestamps for each step."""
        from railway.core.dag.callbacks import StepRecorder
        from railway.core.dag.runner import dag_runner, Exit
        from railway.core.decorators import node

        class EmptyContext(Contract):
            pass

        @node
        def start() -> tuple[EmptyContext, Outcome]:
            return EmptyContext(), Outcome.success("done")

        recorder = StepRecorder()

        dag_runner(
            start=start,
            transitions={"start::success::done": Exit.GREEN},
            on_step=recorder,
        )

        history = recorder.get_history()
        assert history[0].timestamp is not None

    def test_recorder_to_dict(self):
        """Should export history as dict for serialization."""
        from railway.core.dag.callbacks import StepRecorder
        from railway.core.dag.runner import dag_runner, Exit
        from railway.core.decorators import node

        class DataContext(Contract):
            x: int

        @node
        def start() -> tuple[DataContext, Outcome]:
            return DataContext(x=1), Outcome.success("done")

        recorder = StepRecorder()

        dag_runner(
            start=start,
            transitions={"start::success::done": Exit.GREEN},
            on_step=recorder,
        )

        data = recorder.to_dict()
        assert "steps" in data
        assert len(data["steps"]) == 1


class TestAuditLogger:
    """Test audit logging callback."""

    def test_logs_to_loguru(self):
        """Should log steps to loguru."""
        from railway.core.dag.callbacks import AuditLogger
        from railway.core.dag.runner import dag_runner, Exit
        from railway.core.decorators import node
        from unittest.mock import patch

        class EmptyContext(Contract):
            pass

        @node
        def start() -> tuple[EmptyContext, Outcome]:
            return EmptyContext(), Outcome.success("done")

        with patch("railway.core.dag.callbacks.logger") as mock_logger:
            audit = AuditLogger(workflow_id="test-123")

            dag_runner(
                start=start,
                transitions={"start::success::done": Exit.GREEN},
                on_step=audit,
            )

            mock_logger.info.assert_called()
```

```bash
pytest tests/unit/core/dag/test_callbacks.py -v
# Expected: FAILED (ImportError)
```

### Step 2: Green（最小限の実装）

```python
# railway/core/dag/callbacks.py
"""
Step callbacks for DAG workflow monitoring.

Provides reusable callback implementations for common use cases
like logging, recording, and auditing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from loguru import logger


class StepCallback(Protocol):
    """Protocol for step callbacks."""

    def __call__(
        self,
        node_name: str,
        state_string: str,  # 状態文字列 (e.g., "node::success::done")
        context: Any,
    ) -> None:
        """Called after each step execution."""
        ...


@dataclass(frozen=True)
class StepRecord:
    """Record of a single step execution."""
    node_name: str
    state: str
    context_snapshot: dict
    timestamp: datetime

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "node_name": self.node_name,
            "state": self.state,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context_snapshot,
        }


class StepRecorder:
    """
    Records execution history for debugging and analysis.

    Usage:
        recorder = StepRecorder()
        result = dag_runner(start=..., on_step=recorder)
        history = recorder.get_history()
    """

    def __init__(self):
        self._history: list[StepRecord] = []

    def __call__(
        self,
        node_name: str,
        state_string: str,
        context: Any,
    ) -> None:
        """Record a step execution."""
        # Create context snapshot (Contract のみサポート)
        if hasattr(context, "model_dump"):
            snapshot = context.model_dump()
        else:
            snapshot = {"value": str(context)}

        record = StepRecord(
            node_name=node_name,
            state=state_string,
            context_snapshot=snapshot,
            timestamp=datetime.now(),
        )
        self._history.append(record)

    def get_history(self) -> tuple[StepRecord, ...]:
        """Get immutable history of recorded steps."""
        return tuple(self._history)

    def to_dict(self) -> dict:
        """Export history for serialization."""
        return {
            "steps": [record.to_dict() for record in self._history],
            "total_steps": len(self._history),
        }

    def clear(self) -> None:
        """Clear recorded history."""
        self._history.clear()


class AuditLogger:
    """
    Logs step executions for audit purposes.

    Usage:
        audit = AuditLogger(workflow_id="incident-123")
        result = dag_runner(start=..., on_step=audit)
    """

    def __init__(self, workflow_id: str | None = None):
        self.workflow_id = workflow_id or "unknown"

    def __call__(
        self,
        node_name: str,
        state_string: str,
        context: Any,
    ) -> None:
        """Log step execution."""
        logger.info(
            f"[{self.workflow_id}] ステップ実行: "
            f"node={node_name}, state={state_string}"
        )


class CompositeCallback:
    """
    Combines multiple callbacks into one.

    Usage:
        callback = CompositeCallback(recorder, audit_logger)
        result = dag_runner(start=..., on_step=callback)
    """

    def __init__(self, *callbacks: StepCallback):
        self._callbacks = callbacks

    def __call__(
        self,
        node_name: str,
        state_string: str,
        context: Any,
    ) -> None:
        """Call all registered callbacks."""
        for callback in self._callbacks:
            callback(node_name, state_string, context)
```

```bash
pytest tests/unit/core/dag/test_callbacks.py -v
# Expected: PASSED
```

---

## 完了条件

- [ ] `on_step` コールバックが各ステップで呼ばれる
- [ ] `StepRecorder` が履歴を記録
- [ ] `AuditLogger` がログ出力
- [ ] `CompositeCallback` が複数コールバックを合成
- [ ] `StepRecord` がイミュータブル
- [ ] テストカバレッジ90%以上

---

## 次のIssue

- #12: プロジェクトテンプレート更新
