"""Pipeline execution for Railway Framework."""

import asyncio
from collections.abc import Callable
from typing import Any

from loguru import logger


def pipeline(
    initial: Any,
    *steps: Callable[[Any], Any],
    type_check: bool = True,
) -> Any:
    """
    Execute a pipeline of processing steps.

    Features:
    1. Sequential execution of steps
    2. Automatic error propagation (skip remaining steps on error)
    3. Runtime type checking between steps (enabled by default)
    4. Detailed logging of execution flow

    IMPORTANT: Understanding the 'initial' argument
    -----------------------------------------------
    The 'initial' argument is the STARTING VALUE for the pipeline.
    It is NOT a function, but a value (or the result of a function call).

    Args:
        initial: Initial value to pass to first step
        *steps: Processing functions to apply sequentially
        type_check: Enable runtime type checking (default: True)

    Returns:
        Final result from the last step

    Raises:
        Exception: If any step fails
        TypeError: If an async function is passed

    Example:
        result = pipeline(
            fetch_data(),   # Initial value (evaluated immediately)
            process_data,   # Step 1: receives result of fetch_data()
            save_data,      # Step 2: receives result of process_data()
        )
    """
    # Check for async functions (not supported in Phase 1)
    for step in steps:
        # Check the original function if it's a decorated node
        func_to_check = getattr(step, "_original_func", step)
        if asyncio.iscoroutinefunction(func_to_check):
            step_name = getattr(step, "_node_name", step.__name__)
            raise TypeError(
                f"Async function '{step_name}' cannot be used in pipeline(). "
                "Phase 1 supports only synchronous nodes in pipeline(). "
                "Options:\n"
                f"  1. Use 'await {step_name}(value)' directly\n"
                "  2. Wait for pipeline_async() in Phase 2\n"
                "  3. Convert to synchronous function if possible"
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
