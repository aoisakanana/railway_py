"""Tests for type checking support (PEP 561)."""

from pathlib import Path


class TestPyTypedMarker:
    """Test py.typed marker file exists."""

    def test_py_typed_marker_exists(self):
        """Verify py.typed marker file exists in railway package."""
        import railway

        package_dir = Path(railway.__file__).parent
        py_typed = package_dir / "py.typed"
        assert py_typed.exists(), f"py.typed not found at {py_typed}"

    def test_py_typed_is_file(self):
        """Verify py.typed is a file (not directory)."""
        import railway

        package_dir = Path(railway.__file__).parent
        py_typed = package_dir / "py.typed"
        assert py_typed.is_file(), "py.typed should be a file"


class TestTypeExports:
    """Test that key types are properly exported."""

    def test_contract_is_exported(self):
        """Contract should be importable from railway."""
        from railway import Contract

        assert Contract is not None

    def test_params_is_exported(self):
        """Params should be importable from railway."""
        from railway import Params

        assert Params is not None

    def test_node_decorator_is_exported(self):
        """node decorator should be importable from railway."""
        from railway import node

        assert callable(node)

    def test_typed_pipeline_is_exported(self):
        """typed_pipeline should be importable from railway."""
        from railway import typed_pipeline

        assert callable(typed_pipeline)

    def test_entry_point_is_exported(self):
        """entry_point should be importable from railway."""
        from railway import entry_point

        assert callable(entry_point)
