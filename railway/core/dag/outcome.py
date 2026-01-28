"""
Outcome class for simplified node return values.

Provides a clean API for expressing success/failure outcomes
without directly referencing the generated State Enum.

v0.12.2: Removed unused map_to_state and is_outcome functions
"""
from __future__ import annotations

from dataclasses import dataclass


class OutcomeMappingError(Exception):
    """Raised when Outcome cannot be mapped to State Enum."""

    pass


@dataclass(frozen=True, slots=True)
class Outcome:
    """
    Represents the outcome of a node execution.

    Use Outcome.success() or Outcome.failure() to create instances.
    dag_runner will automatically convert these to state strings.

    Example:
        @node
        def fetch_data() -> tuple[Context, Outcome]:
            if data_found:
                return ctx, Outcome.success("found")
            else:
                return ctx, Outcome.failure("not_found")

        # dag_runner automatically generates "fetch_data::success::found"
    """

    outcome_type: str  # "success" or "failure"
    detail: str

    @classmethod
    def success(cls, detail: str = "done") -> Outcome:
        """Create a success outcome.

        Args:
            detail: Specific success detail (e.g., "done", "found", "cached")

        Returns:
            Outcome instance representing success
        """
        return cls(outcome_type="success", detail=detail)

    @classmethod
    def failure(cls, detail: str = "error") -> Outcome:
        """Create a failure outcome.

        Args:
            detail: Specific failure detail (e.g., "http", "timeout", "validation")

        Returns:
            Outcome instance representing failure
        """
        return cls(outcome_type="failure", detail=detail)

    @property
    def is_success(self) -> bool:
        """Check if this is a success outcome."""
        return self.outcome_type == "success"

    @property
    def is_failure(self) -> bool:
        """Check if this is a failure outcome."""
        return self.outcome_type == "failure"

    def to_state_string(self, node_name: str) -> str:
        """Convert to state string format.

        Args:
            node_name: Name of the node

        Returns:
            State string in format: {node_name}::{outcome_type}::{detail}
        """
        return f"{node_name}::{self.outcome_type}::{self.detail}"
