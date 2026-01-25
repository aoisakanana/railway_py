"""
Step callbacks for DAG workflow monitoring.

Provides reusable callback implementations for common use cases
like logging, recording, and auditing.
"""
from __future__ import annotations

from dataclasses import dataclass
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
    """Record of a single step execution.

    Attributes:
        node_name: Name of the executed node
        state: State string returned by the node
        context_snapshot: Snapshot of context at execution time
        timestamp: Time of execution
    """

    node_name: str
    state: str
    context_snapshot: dict
    timestamp: datetime

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "node_name": self.node_name,
            "state": self.state,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context_snapshot,
        }


class StepRecorder:
    """
    Records execution history for debugging and analysis.

    Captures each step's node name, state, context, and timestamp.
    Useful for debugging, testing, and post-execution analysis.

    Usage:
        recorder = StepRecorder()
        result = dag_runner(start=..., on_step=recorder)
        history = recorder.get_history()
    """

    def __init__(self) -> None:
        """Initialize empty recorder."""
        self._history: list[StepRecord] = []

    def __call__(
        self,
        node_name: str,
        state_string: str,
        context: Any,
    ) -> None:
        """Record a step execution.

        Args:
            node_name: Name of the executed node
            state_string: State string returned by the node
            context: Current context (Contract only)
        """
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
        """Get immutable history of recorded steps.

        Returns:
            Tuple of StepRecord instances in execution order
        """
        return tuple(self._history)

    def to_dict(self) -> dict:
        """Export history for serialization.

        Returns:
            Dictionary with steps and metadata
        """
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

    Outputs structured log messages via loguru for each step,
    including workflow ID for correlation.

    Usage:
        audit = AuditLogger(workflow_id="incident-123")
        result = dag_runner(start=..., on_step=audit)
    """

    def __init__(self, workflow_id: str | None = None) -> None:
        """Initialize audit logger.

        Args:
            workflow_id: Optional identifier for the workflow run
        """
        self.workflow_id = workflow_id or "unknown"

    def __call__(
        self,
        node_name: str,
        state_string: str,
        context: Any,
    ) -> None:
        """Log step execution.

        Args:
            node_name: Name of the executed node
            state_string: State string returned by the node
            context: Current context (unused in logging)
        """
        logger.info(
            f"[{self.workflow_id}] ステップ実行: "
            f"node={node_name}, state={state_string}"
        )


class CompositeCallback:
    """
    Combines multiple callbacks into one.

    Allows running multiple callbacks for each step without
    modifying the dag_runner call.

    Usage:
        callback = CompositeCallback(recorder, audit_logger)
        result = dag_runner(start=..., on_step=callback)
    """

    def __init__(self, *callbacks: StepCallback) -> None:
        """Initialize with callbacks to compose.

        Args:
            *callbacks: Variable number of callback instances
        """
        self._callbacks = callbacks

    def __call__(
        self,
        node_name: str,
        state_string: str,
        context: Any,
    ) -> None:
        """Call all registered callbacks.

        Args:
            node_name: Name of the executed node
            state_string: State string returned by the node
            context: Current context
        """
        for callback in self._callbacks:
            callback(node_name, state_string, context)
