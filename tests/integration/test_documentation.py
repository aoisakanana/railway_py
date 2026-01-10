"""Tests to verify documentation accuracy."""
import pytest
from pathlib import Path


class TestDocumentationExists:
    """Test that all documentation files exist."""

    def test_readme_exists(self):
        """Should have README.md."""
        readme = Path(__file__).parent.parent.parent / "readme.md"
        assert readme.exists()


class TestDocstringCoverage:
    """Test that public APIs have docstrings."""

    def test_core_module_docstrings(self):
        """Core modules should have docstrings."""
        from railway.core import decorators, pipeline

        assert decorators.__doc__ is not None
        assert pipeline.__doc__ is not None

    def test_node_decorator_docstring(self):
        """@node decorator should have comprehensive docstring."""
        from railway.core.decorators import node

        assert node.__doc__ is not None
        assert "retry" in node.__doc__.lower()
        assert "log" in node.__doc__.lower()

    def test_pipeline_docstring(self):
        """pipeline function should have comprehensive docstring."""
        from railway.core.pipeline import pipeline

        assert pipeline.__doc__ is not None
        assert "initial" in pipeline.__doc__.lower()
        assert "step" in pipeline.__doc__.lower()

    def test_entry_point_docstring(self):
        """@entry_point decorator should have comprehensive docstring."""
        from railway.core.decorators import entry_point

        assert entry_point.__doc__ is not None

    def test_error_classes_docstrings(self):
        """Error classes should have docstrings."""
        from railway.core.errors import (
            RailwayError,
            ConfigurationError,
            NodeError,
            PipelineError,
        )

        assert RailwayError.__doc__ is not None
        assert ConfigurationError.__doc__ is not None
        assert NodeError.__doc__ is not None
        assert PipelineError.__doc__ is not None
