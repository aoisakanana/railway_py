"""Railway Framework for Python.

A Railway Oriented Programming framework that provides:
- @node decorator for processing functions
- @entry_point decorator for CLI entry points
- pipeline() function for chaining operations
"""

from railway.core.decorators import entry_point, node, Retry
from railway.core.pipeline import async_pipeline, pipeline

__version__ = "0.1.0"
__all__ = [
    "entry_point",
    "node",
    "Retry",
    "pipeline",
    "async_pipeline",
]
