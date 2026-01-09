"""Type checking utilities for pipeline strict mode."""

from typing import Any, Callable, Union, get_args, get_origin, get_type_hints


def check_type_compatibility(value: Any, expected_type: type) -> bool:
    """
    Check if value is compatible with expected type.

    Args:
        value: The value to check.
        expected_type: The expected type.

    Returns:
        True if compatible, False otherwise.
    """
    if expected_type is Any:
        return True

    # Handle None
    if value is None:
        origin = get_origin(expected_type)
        if origin is Union:
            args = get_args(expected_type)
            return type(None) in args
        return expected_type is type(None)

    # Get origin for generic types
    origin = get_origin(expected_type)

    # Handle Union types (including Optional)
    if origin is Union:
        args = get_args(expected_type)
        return any(check_type_compatibility(value, arg) for arg in args)

    # Handle generic types (List, Dict, etc.)
    if origin is not None:
        # Basic check against origin type
        if not isinstance(value, origin):
            return False
        return True

    # Simple isinstance check
    try:
        return isinstance(value, expected_type)
    except TypeError:
        # Some types can't be used with isinstance
        return True


def get_function_input_type(func: Callable) -> type | None:
    """
    Get the input type of a function's first parameter.

    Args:
        func: The function to inspect.

    Returns:
        The type of the first parameter, or Any if not specified.
    """
    # Get original function if wrapped
    original = getattr(func, "_original_func", func)

    try:
        hints = get_type_hints(original)
        # Get first parameter's type (excluding 'return')
        params = [k for k in hints.keys() if k != "return"]
        if params:
            return hints[params[0]]
    except Exception:
        pass
    return Any


def get_function_output_type(func: Callable) -> type | None:
    """
    Get the return type of a function.

    Args:
        func: The function to inspect.

    Returns:
        The return type, or Any if not specified.
    """
    # Get original function if wrapped
    original = getattr(func, "_original_func", func)

    try:
        hints = get_type_hints(original)
        return hints.get("return", Any)
    except Exception:
        return Any


def format_type_error(
    step_num: int,
    step_name: str,
    expected_type: type,
    actual_type: type,
    actual_value: Any,
) -> str:
    """
    Format a type mismatch error message.

    Args:
        step_num: The step number in the pipeline.
        step_name: The name of the step.
        expected_type: The expected type.
        actual_type: The actual type of the value.
        actual_value: The actual value.

    Returns:
        Formatted error message.
    """
    return (
        f"Pipeline type mismatch at step {step_num} ({step_name}): "
        f"expected {_type_name(expected_type)}, "
        f"got {_type_name(actual_type)} (value: {repr(actual_value)[:50]})"
    )


def _type_name(t: type) -> str:
    """
    Get a readable name for a type.

    Args:
        t: The type to get name for.

    Returns:
        Human-readable type name.
    """
    if hasattr(t, "__name__"):
        return t.__name__
    return str(t)
