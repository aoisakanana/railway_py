"""Tests for railway run --trace CLI option (Issue 25-03)."""
from __future__ import annotations

from railway.core.dag.trace import NodeTrace, WorkflowTrace
from railway.cli.run import format_trace_output


class TestFormatTraceOutput:
    """format_trace_output のテスト。"""

    def test_format_trace_output_single_node(self) -> None:
        """単一ノードのトレース出力。"""
        trace = WorkflowTrace(
            traces=(
                NodeTrace(
                    node_name="start",
                    before={},
                    after={"value": 42},
                    outcome="start::success::done",
                    mutations=("value",),
                ),
            ),
            initial_fields=(),
            execution_path=("start",),
        )
        output = format_trace_output(trace)
        assert "[trace] start:" in output
        assert "mutations: value" in output

    def test_format_trace_output_multiple_nodes(self) -> None:
        """複数ノードのトレース出力。"""
        trace = WorkflowTrace(
            traces=(
                NodeTrace(
                    node_name="start",
                    before={},
                    after={"a": 1},
                    outcome="start::success::done",
                    mutations=("a",),
                ),
                NodeTrace(
                    node_name="process",
                    before={"a": 1},
                    after={"a": 1, "b": 2},
                    outcome="process::success::done",
                    mutations=("b",),
                ),
                NodeTrace(
                    node_name="exit.success.done",
                    before={"a": 1, "b": 2},
                    after={"a": 1, "b": 2},
                    outcome="exit::success.done",
                    mutations=(),
                ),
            ),
            initial_fields=(),
            execution_path=("start", "process", "exit.success.done"),
        )
        output = format_trace_output(trace)
        assert "[trace] start:" in output
        assert "[trace] process:" in output
        assert "[trace] exit.success.done:" in output
        assert "mutations: a" in output
        assert "mutations: b" in output

    def test_format_trace_output_no_mutations(self) -> None:
        """ミューテーションがないノードの出力。"""
        trace = WorkflowTrace(
            traces=(
                NodeTrace(
                    node_name="noop",
                    before={"x": 1},
                    after={"x": 1},
                    outcome="noop::success::done",
                    mutations=(),
                ),
            ),
            initial_fields=("x",),
            execution_path=("noop",),
        )
        output = format_trace_output(trace)
        assert "[trace] noop:" in output
        assert "mutations: (none)" in output

    def test_format_trace_output_is_pure(self) -> None:
        """format_trace_output は純粋関数（同じ入力で同じ出力）。"""
        trace = WorkflowTrace(
            traces=(
                NodeTrace(
                    node_name="start",
                    before={},
                    after={"value": 1},
                    outcome="start::success::done",
                    mutations=("value",),
                ),
            ),
            initial_fields=(),
            execution_path=("start",),
        )
        output1 = format_trace_output(trace)
        output2 = format_trace_output(trace)
        assert output1 == output2

    def test_format_trace_output_multiple_mutations(self) -> None:
        """複数のミューテーションがカンマ区切りで出力される。"""
        trace = WorkflowTrace(
            traces=(
                NodeTrace(
                    node_name="start",
                    before={},
                    after={"a": 1, "b": 2, "c": 3},
                    outcome="start::success::done",
                    mutations=("a", "b", "c"),
                ),
            ),
            initial_fields=(),
            execution_path=("start",),
        )
        output = format_trace_output(trace)
        assert "mutations: a, b, c" in output
