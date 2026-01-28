"""Tests for NodeOutcome base class (v0.12.2: simplified).

v0.12.2: Removed tests for deleted ExitOutcome, make_state, make_exit, parse_state, parse_exit.
"""
from enum import Enum

import pytest


class TestNodeOutcome:
    """Test NodeOutcome base class."""

    def test_create_outcome_enum(self):
        """Should create an Enum subclass of NodeOutcome."""
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            SUCCESS = "my_node::success::done"
            FAILURE = "my_node::failure::error"

        assert issubclass(MyState, Enum)
        assert issubclass(MyState, NodeOutcome)
        assert MyState.SUCCESS.value == "my_node::success::done"

    def test_outcome_is_string_enum(self):
        """NodeOutcome should be a string enum."""
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            SUCCESS = "node::success"

        assert isinstance(MyState.SUCCESS, str)
        assert MyState.SUCCESS == "node::success"

    def test_outcome_node_name(self):
        """Should extract node name from outcome."""
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            FETCH_SUCCESS = "fetch_data::success::done"
            FETCH_FAILURE = "fetch_data::failure::http"

        assert MyState.FETCH_SUCCESS.node_name == "fetch_data"
        assert MyState.FETCH_FAILURE.node_name == "fetch_data"

    def test_outcome_type(self):
        """Should extract outcome type (success/failure)."""
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            OK = "node::success::done"
            ERR = "node::failure::error"

        assert MyState.OK.outcome_type == "success"
        assert MyState.ERR.outcome_type == "failure"
        assert MyState.OK.is_success is True
        assert MyState.ERR.is_success is False
        assert MyState.OK.is_failure is False
        assert MyState.ERR.is_failure is True

    def test_outcome_detail(self):
        """Should extract detail from outcome."""
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            SUCCESS_EXIST = "check::success::exist"
            SUCCESS_NOT_EXIST = "check::success::not_exist"

        assert MyState.SUCCESS_EXIST.detail == "exist"
        assert MyState.SUCCESS_NOT_EXIST.detail == "not_exist"

    def test_outcome_hashable(self):
        """NodeOutcome should be hashable."""
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            A = "node::success::a"
            B = "node::success::b"

        state_set = {MyState.A, MyState.B}
        assert MyState.A in state_set
        assert len(state_set) == 2

    def test_outcome_comparison(self):
        """Should support equality comparison."""
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            A = "node::success::a"

        assert MyState.A == "node::success::a"
        assert MyState.A == MyState.A


class TestStateFormatError:
    """Test StateFormatError exception."""

    def test_state_format_error_is_value_error(self):
        """StateFormatError should be a ValueError."""
        from railway.core.dag.state import StateFormatError

        assert issubclass(StateFormatError, ValueError)
