"""Tests for trace module (Issue 25-01)."""
from __future__ import annotations

import pytest

from railway.core.dag.trace import (
    NodeTrace,
    WorkflowTrace,
    compute_mutations,
    should_trace,
)


class TestComputeMutations:
    """compute_mutations のテスト。"""

    def test_compute_mutations_new_field(self) -> None:
        """新規フィールドが追加された場合。"""
        before: dict[str, object] = {"a": 1}
        after: dict[str, object] = {"a": 1, "b": 2}
        result = compute_mutations(before, after)
        assert result == ("b",)

    def test_compute_mutations_changed_field(self) -> None:
        """フィールドの値が変更された場合。"""
        before: dict[str, object] = {"a": 1, "b": "old"}
        after: dict[str, object] = {"a": 1, "b": "new"}
        result = compute_mutations(before, after)
        assert result == ("b",)

    def test_compute_mutations_removed_field(self) -> None:
        """フィールドが削除された場合。"""
        before: dict[str, object] = {"a": 1, "b": 2}
        after: dict[str, object] = {"a": 1}
        result = compute_mutations(before, after)
        assert result == ("b",)

    def test_compute_mutations_no_change(self) -> None:
        """変更がない場合は空タプルを返す。"""
        before: dict[str, object] = {"a": 1, "b": 2}
        after: dict[str, object] = {"a": 1, "b": 2}
        result = compute_mutations(before, after)
        assert result == ()

    def test_compute_mutations_multiple_changes(self) -> None:
        """複数フィールドが変更された場合、ソート済みで返す。"""
        before: dict[str, object] = {"a": 1, "b": 2, "c": 3}
        after: dict[str, object] = {"a": 99, "b": 2, "d": 4}
        # a: 変更、c: 削除、d: 追加
        result = compute_mutations(before, after)
        assert result == ("a", "c", "d")

    def test_compute_mutations_empty_dicts(self) -> None:
        """空の辞書同士は変更なし。"""
        result = compute_mutations({}, {})
        assert result == ()

    def test_compute_mutations_from_empty(self) -> None:
        """空から始まり全フィールドが新規追加。"""
        before: dict[str, object] = {}
        after: dict[str, object] = {"x": 1, "y": 2}
        result = compute_mutations(before, after)
        assert result == ("x", "y")


class TestShouldTrace:
    """should_trace のテスト。"""

    def test_should_trace_cli_flag_true(self) -> None:
        """CLI フラグが True の場合。"""
        assert should_trace(cli_flag=True) is True

    def test_should_trace_cli_flag_false(self) -> None:
        """CLI フラグが False の場合。"""
        assert should_trace(cli_flag=False) is False

    def test_should_trace_env_true_values(self) -> None:
        """環境変数が真の値の場合。"""
        for val in ("1", "true", "yes", "True", "YES", "True"):
            assert should_trace(env_value=val) is True, f"Failed for env_value={val!r}"

    def test_should_trace_env_false(self) -> None:
        """環境変数が偽の値の場合。"""
        for val in ("0", "false", "no", ""):
            assert should_trace(env_value=val) is False, f"Failed for env_value={val!r}"

    def test_should_trace_default_false(self) -> None:
        """引数なしの場合はデフォルト False。"""
        assert should_trace() is False

    def test_should_trace_cli_overrides_env(self) -> None:
        """CLI フラグは環境変数より優先される。"""
        assert should_trace(cli_flag=True, env_value="0") is True
        assert should_trace(cli_flag=False, env_value="1") is False


class TestNodeTraceFrozen:
    """NodeTrace が frozen であることを確認。"""

    def test_node_trace_frozen(self) -> None:
        """NodeTrace は変更不可。"""
        trace = NodeTrace(
            node_name="start",
            before={"a": 1},
            after={"a": 2},
            outcome="success::done",
            mutations=("a",),
        )
        with pytest.raises(AttributeError):
            trace.node_name = "other"  # type: ignore[misc]


class TestWorkflowTraceFrozen:
    """WorkflowTrace が frozen であることを確認。"""

    def test_workflow_trace_frozen(self) -> None:
        """WorkflowTrace は変更不可。"""
        trace = WorkflowTrace(
            traces=(),
            initial_fields=(),
            execution_path=(),
        )
        with pytest.raises(AttributeError):
            trace.traces = ()  # type: ignore[misc]


class TestNodeTraceCreation:
    """NodeTrace の生成テスト。"""

    def test_node_trace_fields(self) -> None:
        """NodeTrace のフィールドが正しく設定される。"""
        trace = NodeTrace(
            node_name="process",
            before={"x": 1},
            after={"x": 2, "y": 3},
            outcome="process::success::done",
            mutations=("x", "y"),
        )
        assert trace.node_name == "process"
        assert trace.before == {"x": 1}
        assert trace.after == {"x": 2, "y": 3}
        assert trace.outcome == "process::success::done"
        assert trace.mutations == ("x", "y")


class TestWorkflowTraceCreation:
    """WorkflowTrace の生成テスト。"""

    def test_workflow_trace_fields(self) -> None:
        """WorkflowTrace のフィールドが正しく設定される。"""
        node_trace = NodeTrace(
            node_name="start",
            before={},
            after={"a": 1},
            outcome="start::success::done",
            mutations=("a",),
        )
        trace = WorkflowTrace(
            traces=(node_trace,),
            initial_fields=(),
            execution_path=("start", "exit.success.done"),
        )
        assert len(trace.traces) == 1
        assert trace.traces[0].node_name == "start"
        assert trace.execution_path == ("start", "exit.success.done")
