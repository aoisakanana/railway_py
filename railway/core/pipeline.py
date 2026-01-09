"""Pipeline execution for Railway Framework."""

import asyncio
from collections.abc import Callable
from typing import Any

from loguru import logger

from railway.core.type_check import (
    check_type_compatibility,
    format_type_error,
    get_function_input_type,
)


def pipeline(
    initial: Any,
    *steps: Callable[[Any], Any],
    type_check: bool = True,
    strict: bool = False,
) -> Any:
    """
    Execute a pipeline of processing steps.

    Features:
    1. Sequential execution of steps
    2. Automatic error propagation (skip remaining steps on error)
    3. Runtime type checking between steps (enabled by default)
    4. Detailed logging of execution flow
    5. Strict mode type checking (optional)

    IMPORTANT: Understanding the 'initial' argument
    -----------------------------------------------
    The 'initial' argument is the STARTING VALUE for the pipeline.
    It is NOT a function, but a value (or the result of a function call).

    Args:
        initial: Initial value to pass to first step
        *steps: Processing functions to apply sequentially
        type_check: Enable runtime type checking (default: True)
        strict: Enable strict type checking between steps (default: False)

    Returns:
        Final result from the last step

    Raises:
        Exception: If any step fails
        TypeError: If an async function is passed or type mismatch in strict mode

    Example:
        result = pipeline(
            fetch_data(),   # Initial value (evaluated immediately)
            process_data,   # Step 1: receives result of fetch_data()
            save_data,      # Step 2: receives result of process_data()
        )
    """
    # Check for async functions
    for step in steps:
        # Check the original function if it's a decorated node
        is_async = getattr(step, "_is_async", False) or asyncio.iscoroutinefunction(
            getattr(step, "_original_func", step)
        )
        if is_async:
            step_name = getattr(step, "_node_name", step.__name__)
            raise TypeError(
                f"Async function '{step_name}' cannot be used in pipeline(). "
                "Use async_pipeline() for async nodes."
            )

    logger.debug(f"Pipeline starting with {len(steps)} steps")

    # Return initial value if no steps
    if not steps:
        return initial

    current_value = initial
    current_step = 0

    try:
        for i, step in enumerate(steps, 1):
            current_step = i
            step_name = getattr(step, "_node_name", step.__name__)

            # Type check before execution (if strict mode)
            if strict:
                expected_type = get_function_input_type(step)
                if expected_type is not None:
                    if not check_type_compatibility(current_value, expected_type):
                        raise TypeError(
                            format_type_error(
                                step_num=i,
                                step_name=step_name,
                                expected_type=expected_type,
                                actual_type=type(current_value),
                                actual_value=current_value,
                            )
                        )

            logger.debug(f"Pipeline step {i}/{len(steps)}: {step_name}")

            try:
                result = step(current_value)
                current_value = result
                logger.debug(f"Pipeline step {i}/{len(steps)}: Success")

            except Exception as e:
                logger.error(
                    f"Pipeline step {i}/{len(steps)} ({step_name}): "
                    f"Failed with {type(e).__name__}: {e}"
                )
                logger.info(f"Pipeline: Skipping remaining {len(steps) - i} steps")
                raise

        logger.debug("Pipeline completed successfully")
        return current_value

    except Exception:
        logger.error(f"Pipeline failed at step {current_step}/{len(steps)}")
        raise


async def async_pipeline(
    initial: Any,
    *steps: Callable[[Any], Any],
    strict: bool = False,
) -> Any:
    """
    Execute an asynchronous pipeline of processing steps.

    Supports both sync and async nodes. Async nodes are awaited automatically.

    Args:
        initial: Initial value to pass to first step
        *steps: Processing functions to apply sequentially (sync or async)
        strict: Enable strict type checking between steps (default: False)

    Returns:
        Final result from the last step

    Raises:
        Exception: If any step fails
        TypeError: If type mismatch in strict mode

    Example:
        result = await async_pipeline(
            "https://api.example.com",
            async_fetch,   # Async step 1
            process_data,  # Sync step 2
            async_save,    # Async step 3
        )
    """
    logger.debug(f"Async pipeline starting with {len(steps)} steps")

    # Return initial value if no steps
    if not steps:
        return initial

    current_value = initial
    current_step = 0

    try:
        for i, step in enumerate(steps, 1):
            current_step = i
            step_name = getattr(step, "_node_name", step.__name__)
            is_async = getattr(step, "_is_async", False) or asyncio.iscoroutinefunction(
                getattr(step, "_original_func", step)
            )

            # Type check before execution (if strict mode)
            if strict:
                expected_type = get_function_input_type(step)
                if expected_type is not None:
                    if not check_type_compatibility(current_value, expected_type):
                        raise TypeError(
                            format_type_error(
                                step_num=i,
                                step_name=step_name,
                                expected_type=expected_type,
                                actual_type=type(current_value),
                                actual_value=current_value,
                            )
                        )

            logger.debug(f"Async pipeline step {i}/{len(steps)}: {step_name}")

            try:
                if is_async:
                    result = await step(current_value)
                else:
                    result = step(current_value)
                current_value = result
                logger.debug(f"Async pipeline step {i}/{len(steps)}: Success")

            except Exception as e:
                logger.error(
                    f"Async pipeline step {i}/{len(steps)} ({step_name}): "
                    f"Failed with {type(e).__name__}: {e}"
                )
                logger.info(f"Async pipeline: Skipping remaining {len(steps) - i} steps")
                raise

        logger.debug("Async pipeline completed successfully")
        return current_value

    except Exception:
        logger.error(f"Async pipeline failed at step {current_step}/{len(steps)}")
        raise
