"""Railway Framework for Python.

A Railway Oriented Programming framework that provides:
- @node decorator for processing functions
- @entry_point decorator for CLI entry points
- pipeline() function for chaining operations
- Contract base class for type-safe data exchange
- ExitContract for type-safe workflow termination
"""

from importlib.metadata import version

from railway.core.board import BoardBase, WorkflowResult
from railway.core.contract import Contract, Params, Tagged, validate_contract
from railway.core.decorators import Retry, entry_point, node
from railway.core.exit_contract import ExitContract
from railway.core.pipeline import async_pipeline, pipeline
from railway.core.registry import get_contract, register_contract
from railway.core.resolver import (
    DependencyError,
    DependencyResolver,
    typed_async_pipeline,
    typed_pipeline,
)
from railway.core.retry import RetryPolicy

__version__ = version("railway-framework")
__all__ = [
    # Core decorators
    "entry_point",
    "node",
    "Retry",
    "RetryPolicy",
    # Pipeline (legacy linear) — v0.14.3: CLI scaffolding は削除済み。
    # コアライブラリ関数として残存。削除判断は resolver.py のコメント参照。
    "pipeline",
    "async_pipeline",
    # Pipeline (typed with dependency resolution) — 同上
    "typed_pipeline",
    "typed_async_pipeline",
    "DependencyResolver",
    "DependencyError",
    # Board pattern (DAG workflow)
    "BoardBase",
    "WorkflowResult",
    # Contracts
    "Contract",
    "Params",
    "Tagged",
    "validate_contract",
    "register_contract",
    "get_contract",
    # ExitContract (for DAG workflow termination)
    "ExitContract",
]
