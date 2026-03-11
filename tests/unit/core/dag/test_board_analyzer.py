"""Tests for AST board analyzer (Issues 20-01 through 20-05)."""
from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError

from railway.core.dag.board_analyzer import (
    AnalysisViolation,
    BranchWrites,
    FieldAccess,
    NodeAnalysis,
    analyze_node_file,
)


# =========== 20-01: Type Tests ===========


class TestFieldAccessFrozen:
    def test_frozen(self) -> None:
        fa = FieldAccess(name="x", line=1, is_conditional=False)
        with pytest.raises(FrozenInstanceError):
            fa.name = "y"  # type: ignore[misc]

    def test_fields(self) -> None:
        fa = FieldAccess(name="hostname", line=10, is_conditional=True)
        assert fa.name == "hostname"
        assert fa.line == 10
        assert fa.is_conditional is True


class TestBranchWritesFrozen:
    def test_frozen(self) -> None:
        bw = BranchWrites(outcome="success::done", writes=frozenset({"x"}))
        with pytest.raises(FrozenInstanceError):
            bw.outcome = "failure::error"  # type: ignore[misc]

    def test_fields(self) -> None:
        bw = BranchWrites(outcome="success::done", writes=frozenset({"a", "b"}))
        assert bw.outcome == "success::done"
        assert bw.writes == frozenset({"a", "b"})


class TestAnalysisViolationFrozen:
    def test_frozen(self) -> None:
        v = AnalysisViolation(code="E012", message="msg", line=1, file_path="t.py")
        with pytest.raises(FrozenInstanceError):
            v.code = "E013"  # type: ignore[misc]

    def test_fields(self) -> None:
        v = AnalysisViolation(code="E012", message="board passed", line=5, file_path="test.py")
        assert v.code == "E012"
        assert v.message == "board passed"
        assert v.line == 5
        assert v.file_path == "test.py"


class TestNodeAnalysisProperties:
    def test_reads_all(self) -> None:
        na = NodeAnalysis(
            node_name="test",
            file_path="t.py",
            reads_required=frozenset({"a"}),
            reads_optional=frozenset({"b"}),
            branch_writes=(),
            all_writes=frozenset(),
            outcomes=(),
            violations=(),
        )
        assert na.reads_all == frozenset({"a", "b"})

    def test_reads_all_no_overlap(self) -> None:
        na = NodeAnalysis(
            node_name="test",
            file_path="t.py",
            reads_required=frozenset({"x", "y"}),
            reads_optional=frozenset({"z"}),
            branch_writes=(),
            all_writes=frozenset(),
            outcomes=(),
            violations=(),
        )
        assert na.reads_all == frozenset({"x", "y", "z"})

    def test_has_violations_false(self) -> None:
        na = NodeAnalysis(
            node_name="test",
            file_path="t.py",
            reads_required=frozenset(),
            reads_optional=frozenset(),
            branch_writes=(),
            all_writes=frozenset(),
            outcomes=(),
            violations=(),
        )
        assert na.has_violations is False

    def test_has_violations_true(self) -> None:
        na = NodeAnalysis(
            node_name="test",
            file_path="t.py",
            reads_required=frozenset(),
            reads_optional=frozenset(),
            branch_writes=(),
            all_writes=frozenset(),
            outcomes=(),
            violations=(AnalysisViolation("E012", "msg", 1, "t.py"),),
        )
        assert na.has_violations is True

    def test_frozen(self) -> None:
        na = NodeAnalysis(
            node_name="test",
            file_path="t.py",
            reads_required=frozenset(),
            reads_optional=frozenset(),
            branch_writes=(),
            all_writes=frozenset(),
            outcomes=(),
            violations=(),
        )
        with pytest.raises(FrozenInstanceError):
            na.node_name = "other"  # type: ignore[misc]


# =========== 20-02: Basic Reads/Writes ===========


class TestBasicReads:
    def test_simple_read(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    x = board.hostname
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert "hostname" in result.reads_all

    def test_multiple_reads(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    a = board.field_a
    b = board.field_b
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert "field_a" in result.reads_all
        assert "field_b" in result.reads_all

    def test_read_in_function_call(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    print(board.value)
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert "value" in result.reads_all

    def test_read_in_if_condition(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    if board.flag:
        pass
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert "flag" in result.reads_all

    def test_read_in_comparison(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    if board.count > 10:
        pass
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert "count" in result.reads_all

    def test_read_in_method_call(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    result = board.data.split(",")
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert "data" in result.reads_all

    def test_no_reads(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    board.result = "ok"
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        # "result" is a write, not a read
        assert "result" not in result.reads_all


class TestBasicWrites:
    def test_simple_write(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    board.result = "done"
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert "result" in result.all_writes

    def test_multiple_writes(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    board.a = 1
    board.b = 2
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert "a" in result.all_writes
        assert "b" in result.all_writes

    def test_write_in_if(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    if True:
        board.conditional_write = "yes"
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert "conditional_write" in result.all_writes

    def test_no_writes(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    x = board.value
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert result.all_writes == frozenset()


class TestAnalyzePurity:
    def test_pure_function(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    board.x = 1
    return Outcome.success("done")
'''
        r1 = analyze_node_file("test.py", source, "process")
        r2 = analyze_node_file("test.py", source, "process")
        assert r1.all_writes == r2.all_writes
        assert r1.reads_required == r2.reads_required

    def test_syntax_error_returns_empty(self) -> None:
        source = "def broken(:"
        result = analyze_node_file("test.py", source, "process")
        assert result.all_writes == frozenset()
        assert result.reads_required == frozenset()

    def test_no_node_function_returns_empty(self) -> None:
        source = '''
def helper():
    pass
'''
        result = analyze_node_file("test.py", source, "process")
        assert result.all_writes == frozenset()

    def test_empty_source_returns_empty(self) -> None:
        result = analyze_node_file("test.py", "", "process")
        assert result.all_writes == frozenset()
        assert result.reads_required == frozenset()

    def test_node_name_and_file_path_preserved(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    return Outcome.success("done")
'''
        result = analyze_node_file("my/path.py", source, "my_node")
        assert result.node_name == "my_node"
        assert result.file_path == "my/path.py"


# =========== 20-03: Conditional Reads ===========


class TestConditionalReads:
    def test_unconditional_read_is_required(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    x = board.incident_id
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert "incident_id" in result.reads_required

    def test_if_body_only_is_optional(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    if board.flag:
        x = board.hostname
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert "hostname" in result.reads_optional
        # flag is in if condition -> optional
        assert "flag" in result.reads_optional

    def test_both_locations_is_required(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    x = board.value
    if True:
        y = board.value
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert "value" in result.reads_required

    def test_else_branch_is_conditional(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    if True:
        pass
    else:
        x = board.fallback
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert "fallback" in result.reads_optional

    def test_nested_if_is_conditional(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    if True:
        if True:
            x = board.deep
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert "deep" in result.reads_optional

    def test_for_body_is_conditional(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    for item in []:
        x = board.in_loop
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert "in_loop" in result.reads_optional

    def test_try_body_is_conditional(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    try:
        x = board.in_try
    except Exception:
        pass
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert "in_try" in result.reads_optional

    def test_required_and_optional_separate(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    a = board.always_needed
    if board.flag:
        b = board.sometimes_needed
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert "always_needed" in result.reads_required
        assert "sometimes_needed" in result.reads_optional
        assert "always_needed" not in result.reads_optional
        assert "sometimes_needed" not in result.reads_required


# =========== 20-04: Outcome Branch Writes ===========


class TestBranchWrites:
    def test_single_outcome(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    board.result = "ok"
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert len(result.branch_writes) >= 1
        bw = result.branch_writes[0]
        assert "result" in bw.writes
        assert bw.outcome == "success::done"

    def test_if_else_different_outcomes(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    board.started = True
    if board.valid:
        board.result = "ok"
        return Outcome.success("done")
    board.error = "invalid"
    return Outcome.failure("invalid")
'''
        result = analyze_node_file("test.py", source, "process")
        assert len(result.branch_writes) == 2
        outcomes = {bw.outcome for bw in result.branch_writes}
        assert "success::done" in outcomes
        assert "failure::invalid" in outcomes
        # common write "started" should be in all branches
        for bw in result.branch_writes:
            assert "started" in bw.writes

    def test_outcomes_extracted(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    if board.x:
        return Outcome.success("found")
    return Outcome.failure("not_found")
'''
        result = analyze_node_file("test.py", source, "process")
        assert "success::found" in result.outcomes
        assert "failure::not_found" in result.outcomes

    def test_single_branch_includes_all_writes(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    board.a = 1
    board.b = 2
    board.c = 3
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert len(result.branch_writes) == 1
        bw = result.branch_writes[0]
        assert bw.writes == frozenset({"a", "b", "c"})

    def test_no_return_outcome_no_branches(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    board.x = 1
'''
        result = analyze_node_file("test.py", source, "process")
        assert len(result.branch_writes) == 0
        assert result.outcomes == ()


# =========== 20-05: Violation Detection ===========


class TestViolationDetection:
    def test_board_passed_as_arg_e012(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    helper(board)
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert any(v.code == "E012" for v in result.violations)

    def test_board_field_passed_is_ok(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    helper(board.hostname)
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert not any(v.code == "E012" for v in result.violations)

    def test_board_alias_e013(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    b = board
    b.x = 1
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert any(v.code == "E013" for v in result.violations)

    def test_getattr_e014(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    val = getattr(board, "field")
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert any(v.code == "E014" for v in result.violations)

    def test_setattr_e014(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    setattr(board, "field", 1)
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert any(v.code == "E014" for v in result.violations)

    def test_non_board_param_e015(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(ctx):
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert any(v.code == "E015" for v in result.violations)

    def test_riverboard_ignore_suppresses(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    helper(board)  # riverboard: ignore
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert not any(v.code == "E012" for v in result.violations)

    def test_no_violations_clean_code(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    x = board.input_data
    board.result = transform(x)
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert not result.has_violations

    def test_board_as_keyword_arg_e012(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    helper(data=board)
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert any(v.code == "E012" for v in result.violations)

    def test_board_param_named_board_no_violation(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    x = board.value
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        assert not any(v.code == "E015" for v in result.violations)

    def test_hasattr_not_violation(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    if hasattr(board, "field"):
        x = board.field
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        # hasattr is read-only, not dynamic access mutation
        assert not any(v.code == "E014" for v in result.violations)

    def test_violation_line_numbers(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    helper(board)
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        e012_violations = [v for v in result.violations if v.code == "E012"]
        assert len(e012_violations) == 1
        assert e012_violations[0].line == 7
        assert e012_violations[0].file_path == "test.py"

    def test_multiple_violations(self) -> None:
        source = '''
from railway import node
from railway.core.dag import Outcome

@node
def process(board):
    b = board
    helper(board)
    return Outcome.success("done")
'''
        result = analyze_node_file("test.py", source, "process")
        codes = {v.code for v in result.violations}
        assert "E012" in codes
        assert "E013" in codes
