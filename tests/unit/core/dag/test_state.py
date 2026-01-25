"""Tests for NodeOutcome base class."""
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


class TestExitOutcome:
    """Test ExitOutcome base class."""

    def test_create_exit_enum(self):
        """Should create an Enum subclass of ExitOutcome."""
        from railway.core.dag.state import ExitOutcome

        class MyExit(ExitOutcome):
            SUCCESS = "exit::green::resolved"
            ERROR = "exit::red::error"

        assert issubclass(MyExit, Enum)
        assert MyExit.SUCCESS.value == "exit::green::resolved"

    def test_exit_color(self):
        """Should extract exit color."""
        from railway.core.dag.state import ExitOutcome

        class MyExit(ExitOutcome):
            GREEN = "exit::green::done"
            RED = "exit::red::failed"

        assert MyExit.GREEN.color == "green"
        assert MyExit.RED.color == "red"

    def test_exit_is_success(self):
        """Should determine if exit is successful."""
        from railway.core.dag.state import ExitOutcome

        class MyExit(ExitOutcome):
            GREEN = "exit::green::done"
            RED = "exit::red::failed"

        assert MyExit.GREEN.is_success is True
        assert MyExit.RED.is_success is False

    def test_exit_name(self):
        """Should extract exit name."""
        from railway.core.dag.state import ExitOutcome

        class MyExit(ExitOutcome):
            RESOLVED = "exit::green::resolved"

        assert MyExit.RESOLVED.exit_name == "resolved"


class TestStateHelpers:
    """Test helper functions for state creation."""

    def test_make_success_state(self):
        """Should create a success state string."""
        from railway.core.dag.state import make_state

        state = make_state("fetch_data", "success", "done")
        assert state == "fetch_data::success::done"

    def test_make_failure_state(self):
        """Should create a failure state string."""
        from railway.core.dag.state import make_state

        state = make_state("fetch_data", "failure", "http_error")
        assert state == "fetch_data::failure::http_error"

    def test_make_exit_state(self):
        """Should create an exit state string."""
        from railway.core.dag.state import make_exit

        exit_state = make_exit("green", "resolved")
        assert exit_state == "exit::green::resolved"

    def test_parse_state(self):
        """Should parse a state string into components."""
        from railway.core.dag.state import parse_state

        node, outcome, detail = parse_state("fetch_data::success::done")
        assert node == "fetch_data"
        assert outcome == "success"
        assert detail == "done"

    def test_parse_state_invalid(self):
        """Should raise error for invalid state format."""
        from railway.core.dag.state import StateFormatError, parse_state

        with pytest.raises(StateFormatError):
            parse_state("invalid_format")

        with pytest.raises(StateFormatError):
            parse_state("only::two")

    def test_parse_exit(self):
        """Should parse an exit state string."""
        from railway.core.dag.state import parse_exit

        color, name = parse_exit("exit::green::resolved")
        assert color == "green"
        assert name == "resolved"

    def test_parse_exit_invalid(self):
        """Should raise error for invalid exit format."""
        from railway.core.dag.state import StateFormatError, parse_exit

        with pytest.raises(StateFormatError):
            parse_exit("not_exit::green::done")

        with pytest.raises(StateFormatError):
            parse_exit("exit::only")
