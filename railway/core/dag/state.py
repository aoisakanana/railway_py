"""
State types for DAG nodes.

Provides base class for node state enums.

Note: This module is for internal use by codegen.
Users should use Outcome class for node return values.

v0.12.2: Removed deprecated functions and ExitOutcome class
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
