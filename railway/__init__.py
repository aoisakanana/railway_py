"""Railway Framework for Python.

A Railway Oriented Programming framework that provides:
- @node decorator for processing functions
- @entry_point decorator for CLI entry points
- pipeline() function for chaining operations
- Contract base class for type-safe data exchange
"""

from importlib.metadata import version

from railway.core.contract import Contract, Params, Tagged, validate_contract
from railway.core.decorators import entry_point, node, Retry
from railway.core.pipeline import async_pipeline, pipeline
from railway.core.registry import get_contract, register_contract
from railway.core.resolver import (
    DependencyError,
    DependencyResolver,
    typed_async_pipeline,
    typed_pipeline,
)

__version__ = version("railway-framework")
__all__ = [
    # Core decorators
    "entry_point",
    "node",
    "Retry",
    # Pipeline (legacy linear)
    "pipeline",
    "async_pipeline",
    # Pipeline (typed with dependency resolution)
    "typed_pipeline",
    "typed_async_pipeline",
    "DependencyResolver",
    "DependencyError",
    # Contracts
    "Contract",
    "Params",
    "Tagged",
    "validate_contract",
    "register_contract",
    "get_contract",
]
