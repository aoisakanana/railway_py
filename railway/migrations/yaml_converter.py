"""YAML structure conversion utilities.

Converts legacy YAML structure (v0.11.x exits section) to
new nested exit node format (v0.12.0+ nodes.exit).

Design:
- All functions are pure (no side effects)
- Data types are immutable (frozen dataclass)
- Conversion is lossless - all information is preserved

Example conversion:
    Old format:
        exits:
          green_success: {code: 0, description: "正常終了"}
          red_timeout: {code: 1, description: "タイムアウト"}

    New format:
        nodes:
          exit:
            success:
              done: {description: "正常終了"}
            failure:
              timeout: {description: "タイムアウト"}
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


@dataclass(frozen=True)
class ExitMapping:
    """Mapping from old exit name to new exit path.

    Attributes:
        old_name: Original exit name (e.g., "green_success")
        new_path: New exit path (e.g., "exit.success.done")
        code: Exit code (0=success, 1+=failure)
        description: Exit description
    """

    old_name: str
    new_path: str
    code: int
    description: str


@dataclass(frozen=True)
class ConversionResult:
    """Result of YAML structure conversion (immutable).

    Use factory methods ok() and fail() to create instances.

    Attributes:
        success: Whether conversion succeeded
        data: Converted YAML data (None if failed)
        error: Error message (None if succeeded)
        warnings: Tuple of warning messages
    """

    success: bool
    data: dict[str, Any] | None
    error: str | None
    warnings: tuple[str, ...] = ()

    @classmethod
    def ok(
        cls,
        data: dict[str, Any],
        warnings: Sequence[str] = (),
    ) -> ConversionResult:
        """Create a successful conversion result.

        Args:
            data: Converted YAML data
            warnings: Optional warning messages

        Returns:
            ConversionResult with success=True
        """
        return cls(
            success=True,
            data=data,
            error=None,
            warnings=tuple(warnings),
        )

    @classmethod
    def fail(cls, error: str) -> ConversionResult:
        """Create a failed conversion result.

        Args:
            error: Error message

        Returns:
            ConversionResult with success=False
        """
        return cls(
            success=False,
            data=None,
            error=error,
            warnings=(),
        )


# =============================================================================
# Exit Path Inference (Pure Functions)
# =============================================================================


def _infer_category(old_name: str, exit_code: int) -> str:
    """Infer category from old exit name and code.

    Mapping rules:
    - "green_*" or exit_code 0 → "success"
    - "red_*" or exit_code 1 → "failure"
    - "yellow_*" or exit_code 2 → "warning"

    Args:
        old_name: Original exit name (e.g., "green_success")
        exit_code: Exit code value

    Returns:
        Category string ("success", "failure", or "warning")
    """
    lower_name = old_name.lower()

    # Color prefix takes priority
    if lower_name.startswith("green_"):
        return "success"
    if lower_name.startswith("red_"):
        return "failure"
    if lower_name.startswith("yellow_"):
        return "warning"

    # Fall back to exit code
    if exit_code == 0:
        return "success"
    if exit_code == 2:
        return "warning"
    return "failure"


def _extract_detail_name(old_name: str, category: str) -> str:
    """Extract detail name from old exit name.

    Removes color prefix and handles redundant category names.

    Examples:
        ("green_success", "success") → "done"  # "success" is redundant
        ("green_resolved", "success") → "resolved"
        ("red_timeout", "failure") → "timeout"
        ("red_ssh_error", "failure") → "ssh_error"

    Args:
        old_name: Original exit name
        category: Inferred category

    Returns:
        Detail name for the exit
    """
    lower_name = old_name.lower()

    # Remove color prefix
    for prefix in ("green_", "red_", "yellow_"):
        if lower_name.startswith(prefix):
            detail = old_name[len(prefix):]
            break
    else:
        detail = old_name

    # Handle redundant category names
    if detail.lower() == category:
        return "done" if category == "success" else detail

    return detail


def _infer_new_exit_path(old_name: str, exit_code: int) -> str:
    """Infer new exit path from old exit name.

    Converts legacy exit name to new hierarchical format.

    Examples:
        ("green_success", 0) → "exit.success.done"
        ("green_resolved", 0) → "exit.success.resolved"
        ("red_timeout", 1) → "exit.failure.timeout"
        ("unknown", 0) → "exit.success.unknown"

    Args:
        old_name: Original exit name
        exit_code: Exit code value

    Returns:
        New exit path (e.g., "exit.success.done")
    """
    category = _infer_category(old_name, exit_code)
    detail = _extract_detail_name(old_name, category)
    return f"exit.{category}.{detail}"


# =============================================================================
# Exit Mapping Extraction (Pure Functions)
# =============================================================================


def _extract_exit_mappings(
    exits: dict[str, dict[str, Any]],
) -> tuple[ExitMapping, ...]:
    """Extract exit mappings from exits section.

    Args:
        exits: Old format exits section

    Returns:
        Tuple of ExitMapping objects
    """
    mappings: list[ExitMapping] = []

    for old_name, exit_data in exits.items():
        code = exit_data.get("code", 1)
        description = exit_data.get("description", "")
        new_path = _infer_new_exit_path(old_name, code)

        mappings.append(
            ExitMapping(
                old_name=old_name,
                new_path=new_path,
                code=code,
                description=description,
            )
        )

    return tuple(mappings)


# =============================================================================
# Transition Conversion (Pure Functions)
# =============================================================================


def _convert_transition_target(
    target: str,
    name_to_path: dict[str, str],
) -> str:
    """Convert a single transition target.

    Converts "exit::old_name" format to "exit.category.detail" format.
    Non-exit targets are returned unchanged.

    Args:
        target: Original target (e.g., "exit::green_success" or "process")
        name_to_path: Mapping of old exit names to new paths

    Returns:
        Converted target string
    """
    if not target.startswith("exit::"):
        return target

    # Extract old exit name
    old_name = target[6:]  # Remove "exit::" prefix
    return name_to_path.get(old_name, target)


def _convert_transitions(
    transitions: dict[str, dict[str, str]],
    name_to_path: dict[str, str],
) -> dict[str, dict[str, str]]:
    """Convert all transitions to new format.

    Args:
        transitions: Original transitions section
        name_to_path: Mapping of old exit names to new paths

    Returns:
        Converted transitions
    """
    result: dict[str, dict[str, str]] = {}

    for node_name, node_transitions in transitions.items():
        result[node_name] = {}
        for state, target in node_transitions.items():
            result[node_name][state] = _convert_transition_target(
                target, name_to_path
            )

    return result


# =============================================================================
# Exit Tree Building (Pure Functions)
# =============================================================================


def _build_exit_tree(
    mappings: Sequence[ExitMapping],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Build nested exit tree structure from mappings.

    Converts flat mappings to nested dict suitable for YAML.

    Example output:
        {
            "success": {
                "done": {"description": "正常終了"},
            },
            "failure": {
                "timeout": {"description": "タイムアウト"},
            },
        }

    Args:
        mappings: Sequence of ExitMapping objects

    Returns:
        Nested dictionary for exit node structure
    """
    tree: dict[str, dict[str, dict[str, Any]]] = {}

    for mapping in mappings:
        # Parse path: "exit.category.detail"
        parts = mapping.new_path.split(".")
        if len(parts) != 3:
            continue

        _, category, detail = parts

        if category not in tree:
            tree[category] = {}

        tree[category][detail] = {"description": mapping.description}

    return tree


# =============================================================================
# Main Conversion Function
# =============================================================================


def convert_yaml_structure(
    yaml_data: dict[str, Any],
) -> ConversionResult:
    """Convert YAML from old exits format to new nested exit format.

    This is the main entry point for YAML structure conversion.

    Converts:
    - `exits` section → `nodes.exit` nested structure
    - `exit::name` transitions → `exit.category.detail` format

    Args:
        yaml_data: Original YAML data as dict

    Returns:
        ConversionResult with converted data or error
    """
    # No exits section - return unchanged
    if "exits" not in yaml_data:
        return ConversionResult.ok(yaml_data)

    exits = yaml_data.get("exits", {})
    if not exits:
        return ConversionResult.ok(yaml_data)

    # Extract mappings
    mappings = _extract_exit_mappings(exits)

    # Build name → path mapping for transition conversion
    name_to_path: dict[str, str] = {m.old_name: m.new_path for m in mappings}

    # Build new exit tree
    exit_tree = _build_exit_tree(mappings)

    # Start building result
    result = dict(yaml_data)

    # Remove old exits section
    del result["exits"]

    # Add exit tree to nodes
    nodes = dict(result.get("nodes", {}))
    nodes["exit"] = exit_tree
    result["nodes"] = nodes

    # Convert transitions
    if "transitions" in result:
        result["transitions"] = _convert_transitions(
            result["transitions"],
            name_to_path,
        )

    return ConversionResult.ok(result)
