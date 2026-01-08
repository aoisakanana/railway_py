"""Test project structure and imports."""


class TestProjectImports:
    """Test that all modules can be imported."""

    def test_import_railway(self):
        """Should be able to import railway package."""
        import railway

        assert railway is not None

    def test_import_railway_core(self):
        """Should be able to import core modules."""
        from railway.core import config, decorators, pipeline

        assert decorators is not None
        assert pipeline is not None
        assert config is not None

    def test_import_railway_cli(self):
        """Should be able to import CLI modules."""
        from railway.cli import main

        assert main is not None

    def test_version_defined(self):
        """Should have version defined."""
        import railway

        assert hasattr(railway, "__version__")
        assert railway.__version__ == "0.1.0"


class TestCoreModuleExports:
    """Test core module exports."""

    def test_decorators_module_exists(self):
        """Decorators module should exist."""
        from railway.core import decorators

        assert hasattr(decorators, "__doc__")

    def test_pipeline_module_exists(self):
        """Pipeline module should exist."""
        from railway.core import pipeline

        assert hasattr(pipeline, "__doc__")

    def test_config_module_exists(self):
        """Config module should exist."""
        from railway.core import config

        assert hasattr(config, "__doc__")
