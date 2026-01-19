"""Dependency resolution for typed pipeline execution.

This module provides the DependencyResolver class for resolving
node inputs based on Contract types, enabling the Output Model pattern.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Type

from loguru import logger
from pydantic import create_model

if TYPE_CHECKING:
    from railway.core.contract import Contract


class DependencyError(Exception):
    """Raised when a dependency cannot be resolved.

    This exception is raised when:
    - A required input type is not available in the resolver
    - A Tagged input references a node that hasn't been executed
    """

    pass


class DependencyResolver:
    """Resolves dependencies between nodes based on Contract types.

    The resolver stores execution results by their type and source node name,
    enabling automatic dependency injection when executing typed nodes.

    Example:
        resolver = DependencyResolver()
        resolver.register_result(users_result, source_name="fetch_users")

        # Later, resolve inputs for a node that needs UsersFetchResult
        inputs = resolver.resolve_inputs(process_users)
    """

    def __init__(self) -> None:
        """Initialize the resolver with empty result stores."""
        self._results: dict[Type[Contract], Contract] = {}
        self._named_results: dict[str, Contract] = {}

    def register_result(
        self, result: Contract, source_name: str | None = None
    ) -> None:
        """Register a node's result by its type and optionally by source name.

        Args:
            result: The Contract instance to register.
            source_name: Optional name of the source node (for Tagged resolution).
        """
        result_type = type(result)
        self._results[result_type] = result
        if source_name:
            self._named_results[source_name] = result

    def get_result(self, result_type: Type[Contract]) -> Contract:
        """Get a result by its Contract type.

        Args:
            result_type: The Contract type to retrieve.

        Returns:
            The registered Contract instance.

        Raises:
            DependencyError: If no result of the given type is available.
        """
        if result_type not in self._results:
            raise DependencyError(
                f"No result of type {result_type.__name__} available"
            )
        return self._results[result_type]

    def get_named_result(self, source_name: str) -> Contract:
        """Get a result by source node name.

        Args:
            source_name: The name of the source node.

        Returns:
            The registered Contract instance.

        Raises:
            DependencyError: If no result from the given source is available.
        """
        if source_name not in self._named_results:
            raise DependencyError(f"No result from node '{source_name}'")
        return self._named_results[source_name]

    def resolve_inputs(self, node_func: Callable) -> dict[str, Contract]:
        """Resolve inputs for a node from registered results.

        Uses the node's _node_inputs metadata to determine which Contract
        types are needed, then looks them up in the registered results.

        Supports both type-based resolution and Tagged resolution for
        disambiguating multiple outputs of the same type.

        Args:
            node_func: The decorated node function.

        Returns:
            Dictionary mapping parameter names to resolved Contract instances.

        Raises:
            DependencyError: If a required input cannot be resolved.
        """
        from railway.core.contract import Tagged

        inputs_spec = getattr(node_func, "_node_inputs", {})
        resolved: dict[str, Contract] = {}

        for param_name, spec in inputs_spec.items():
            if isinstance(spec, Tagged):
                # Tagged: resolve by source node name
                if spec.source not in self._named_results:
                    raise DependencyError(
                        f"No result from node '{spec.source}'"
                    )
                resolved[param_name] = self._named_results[spec.source]
            else:
                # Type-based: resolve by Contract type
                if spec in self._results:
                    resolved[param_name] = self._results[spec]
                else:
                    node_name = getattr(node_func, "_node_name", node_func.__name__)
                    raise DependencyError(
                        f"Cannot resolve input '{param_name}' of type "
                        f"{spec.__name__} for node '{node_name}'"
                    )

        return resolved


def typed_pipeline(
    *nodes: Callable,
    params: Contract | dict | None = None,
) -> Contract:
    """Execute a pipeline of typed nodes with automatic dependency resolution.

    This is the typed version of pipeline that uses Contract types for
    dependency injection. Nodes declare their inputs and outputs, and
    the pipeline automatically resolves dependencies.

    Args:
        *nodes: Node functions to execute in order.
        params: Initial parameters (Params Contract or dict).

    Returns:
        The output of the last node.

    Raises:
        ValueError: If no nodes are provided.
        DependencyError: If a node's dependencies cannot be resolved.

    Example:
        result = typed_pipeline(
            fetch_users,      # outputs UsersFetchResult
            process_users,    # inputs UsersFetchResult, outputs ProcessResult
            generate_report,  # inputs ProcessResult, outputs ReportResult
            params=FetchParams(user_id=1),
        )
    """
    from railway.core.contract import Params

    if not nodes:
        raise ValueError("Pipeline requires at least one node")

    resolver = DependencyResolver()

    # Register initial params
    if params is not None:
        if isinstance(params, dict):
            # Convert dict to dynamic Params Contract
            field_definitions = {k: (type(v), v) for k, v in params.items()}
            DynamicParams = create_model(
                "DynamicParams", __base__=Params, **field_definitions
            )
            params = DynamicParams(**params)
        resolver.register_result(params, source_name="_params")

    logger.debug(f"Typed pipeline starting with {len(nodes)} nodes")

    last_result: Contract | None = None

    for node_func in nodes:
        node_name = getattr(node_func, "_node_name", node_func.__name__)

        try:
            # Resolve inputs from previous results
            inputs = resolver.resolve_inputs(node_func)

            # Execute the node
            result = node_func(**inputs)

            # Register result for subsequent nodes
            if result is not None:
                resolver.register_result(result, source_name=node_name)
                last_result = result

        except DependencyError as e:
            logger.error(f"Dependency error at node '{node_name}': {e}")
            raise
        except Exception as e:
            logger.error(f"Pipeline failed at node '{node_name}': {e}")
            raise

    logger.debug("Typed pipeline completed successfully")
    return last_result  # type: ignore[return-value]


async def typed_async_pipeline(
    *nodes: Callable,
    params: Contract | dict | None = None,
) -> Contract:
    """Execute an async pipeline of typed nodes with automatic dependency resolution.

    Async version of typed_pipeline. Supports both sync and async nodes.

    Args:
        *nodes: Node functions to execute in order (sync or async).
        params: Initial parameters (Params Contract or dict).

    Returns:
        The output of the last node.

    Raises:
        ValueError: If no nodes are provided.
        DependencyError: If a node's dependencies cannot be resolved.

    Example:
        result = await typed_async_pipeline(
            async_fetch_users,
            process_users,
            async_generate_report,
            params=FetchParams(user_id=1),
        )
    """
    from railway.core.contract import Params

    if not nodes:
        raise ValueError("Pipeline requires at least one node")

    resolver = DependencyResolver()

    # Register initial params
    if params is not None:
        if isinstance(params, dict):
            field_definitions = {k: (type(v), v) for k, v in params.items()}
            DynamicParams = create_model(
                "DynamicParams", __base__=Params, **field_definitions
            )
            params = DynamicParams(**params)
        resolver.register_result(params, source_name="_params")

    logger.debug(f"Typed async pipeline starting with {len(nodes)} nodes")

    last_result: Contract | None = None

    for node_func in nodes:
        node_name = getattr(node_func, "_node_name", node_func.__name__)

        try:
            # Resolve inputs
            inputs = resolver.resolve_inputs(node_func)

            # Determine if async
            original = getattr(node_func, "_original_func", node_func)
            is_async = inspect.iscoroutinefunction(original)

            # Execute
            if is_async:
                result = await node_func(**inputs)
            else:
                result = node_func(**inputs)

            # Register result
            if result is not None:
                resolver.register_result(result, source_name=node_name)
                last_result = result

        except DependencyError as e:
            logger.error(f"Dependency error at node '{node_name}': {e}")
            raise
        except Exception as e:
            logger.error(f"Async pipeline failed at node '{node_name}': {e}")
            raise

    logger.debug("Typed async pipeline completed successfully")
    return last_result  # type: ignore[return-value]
