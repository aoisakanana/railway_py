"""
State and outcome types for DAG nodes.

Provides base classes for node states and exit outcomes,
along with helper functions for state manipulation.

Note: This module is for internal use. Users should use:
- Outcome class (Issue #15) for node return values
- Exit constants (Issue #10) for transition table exits
"""
from __future__ import annotations

from enum import Enum


class StateFormatError(ValueError):
    """Error when state format is invalid."""

    pass


class NodeOutcome(str, Enum):
    """
    Base class for node outcome enums.

    Subclasses represent the possible states a node can return.
    The value format is: {node_name}::{outcome_type}::{detail}

    Example:
        class FetchAlertState(NodeOutcome):
            SUCCESS_DONE = "fetch_alert::success::done"
            FAILURE_HTTP = "fetch_alert::failure::http"
    """

    @property
    def node_name(self) -> str:
        """Extract the node name from the state value."""
        parts = self.value.split("::")
        return parts[0] if len(parts) >= 1 else ""

    @property
    def outcome_type(self) -> str:
        """Extract the outcome type (success/failure)."""
        parts = self.value.split("::")
        return parts[1] if len(parts) >= 2 else ""

    @property
    def detail(self) -> str:
        """Extract the detail part of the state."""
        parts = self.value.split("::")
        return parts[2] if len(parts) >= 3 else ""

    @property
    def is_success(self) -> bool:
        """Check if this is a success outcome."""
        return self.outcome_type == "success"

    @property
    def is_failure(self) -> bool:
        """Check if this is a failure outcome."""
        return self.outcome_type == "failure"


class ExitOutcome(str, Enum):
    """
    Base class for exit outcome enums.

    The value format is: exit::{color}::{name}
    Color is typically 'green' (success) or 'red' (failure).

    Example:
        class WorkflowExit(ExitOutcome):
            SUCCESS = "exit::green::resolved"
            ERROR = "exit::red::unhandled"
    """

    @property
    def color(self) -> str:
        """Extract the exit color (green/red)."""
        parts = self.value.split("::")
        return parts[1] if len(parts) >= 2 else ""

    @property
    def exit_name(self) -> str:
        """Extract the exit name."""
        parts = self.value.split("::")
        return parts[2] if len(parts) >= 3 else ""

    @property
    def is_success(self) -> bool:
        """Check if this is a successful exit."""
        return self.color == "green"


def make_state(node_name: str, outcome_type: str, detail: str) -> str:
    """
    Create a state string from components.

    Args:
        node_name: Name of the node
        outcome_type: 'success' or 'failure'
        detail: Specific detail (e.g., 'done', 'http_error')

    Returns:
        Formatted state string
    """
    return f"{node_name}::{outcome_type}::{detail}"


def make_exit(color: str, name: str) -> str:
    """
    Create an exit state string.

    Args:
        color: 'green' or 'red'
        name: Exit name (e.g., 'resolved', 'error')

    Returns:
        Formatted exit string
    """
    return f"exit::{color}::{name}"


def parse_state(state: str) -> tuple[str, str, str]:
    """
    Parse a state string into components.

    Args:
        state: State string in format {node}::{outcome}::{detail}

    Returns:
        Tuple of (node_name, outcome_type, detail)

    Raises:
        StateFormatError: If format is invalid
    """
    parts = state.split("::")
    if len(parts) != 3:
        raise StateFormatError(
            f"状態文字列の形式が不正です: '{state}' " "(期待: 'node::outcome::detail')"
        )
    return parts[0], parts[1], parts[2]


def parse_exit(exit_state: str) -> tuple[str, str]:
    """
    Parse an exit state string.

    Args:
        exit_state: Exit string in format exit::{color}::{name}

    Returns:
        Tuple of (color, name)

    Raises:
        StateFormatError: If format is invalid
    """
    parts = exit_state.split("::")
    if len(parts) != 3 or parts[0] != "exit":
        raise StateFormatError(
            f"終了状態の形式が不正です: '{exit_state}' " "(期待: 'exit::color::name')"
        )
    return parts[1], parts[2]
