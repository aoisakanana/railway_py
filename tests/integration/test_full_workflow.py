"""Integration tests for complete Railway Framework workflow."""
import pytest
import tempfile
import os
from pathlib import Path
from typer.testing import CliRunner


runner = CliRunner()


class TestProjectCreationWorkflow:
    """Test complete project creation workflow."""

    def test_init_new_node_run(self):
        """Should create project, add node, and run."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            # 1. Initialize project
            result = runner.invoke(app, ["init", "my_project"])
            assert result.exit_code == 0

            project_dir = Path(tmpdir) / "my_project"
            os.chdir(project_dir)

            # 2. Create a node
            result = runner.invoke(app, ["new", "node", "fetch_data"])
            assert result.exit_code == 0
            assert (project_dir / "src" / "nodes" / "fetch_data.py").exists()

            # 3. Create an entry point
            result = runner.invoke(app, ["new", "entry", "main"])
            assert result.exit_code == 0
            assert (project_dir / "src" / "main.py").exists()

            # 4. List components
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            assert "fetch_data" in result.stdout or "main" in result.stdout


class TestNodeDecoratorIntegration:
    """Test @node decorator in realistic scenarios."""

    def test_node_with_logging_and_retry(self):
        """Should log and retry on failure."""
        from railway.core.decorators import node, Retry
        from unittest.mock import patch

        call_count = 0

        @node(
            retry=Retry(max_attempts=3, min_wait=0.01, max_wait=0.02),
            log_input=True,
            log_output=True,
            name="fetch_api_data"
        )
        def fetch_data(url: str) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Connection failed")
            return {"data": "success", "url": url}

        with patch("railway.core.decorators.logger"):
            result = fetch_data("https://api.example.com")

        assert result == {"data": "success", "url": "https://api.example.com"}
        assert call_count == 2


class TestPipelineIntegration:
    """Test pipeline in realistic scenarios."""

    def test_data_processing_pipeline(self):
        """Should process data through multiple steps."""
        from railway.core.decorators import node
        from railway.core.pipeline import pipeline
        from unittest.mock import patch

        @node
        def fetch(source: str) -> dict:
            return {"source": source, "data": [1, 2, 3, 4, 5]}

        @node
        def transform(data: dict) -> dict:
            data["data"] = [x * 2 for x in data["data"]]
            return data

        @node
        def validate(data: dict) -> dict:
            if not data["data"]:
                raise ValueError("Empty data")
            return data

        @node
        def summarize(data: dict) -> str:
            total = sum(data["data"])
            return f"Source: {data['source']}, Total: {total}"

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                result = pipeline(
                    "test_source",
                    fetch,
                    transform,
                    validate,
                    summarize
                )

        assert result == "Source: test_source, Total: 30"

    def test_pipeline_error_handling(self):
        """Should handle errors gracefully in pipeline."""
        from railway.core.decorators import node
        from railway.core.pipeline import pipeline
        from unittest.mock import patch

        @node
        def step1(x: int) -> int:
            return x + 1

        @node
        def step2_fails(x: int) -> int:
            raise ValueError(f"Cannot process {x}")

        @node
        def step3(x: int) -> int:
            return x * 2

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                with pytest.raises(ValueError, match="Cannot process"):
                    pipeline(1, step1, step2_fails, step3)


class TestSettingsIntegration:
    """Test settings management integration."""

    def test_settings_from_yaml(self):
        """Should load settings from registry."""
        from railway.core.config import reset_settings, register_settings_provider
        from types import SimpleNamespace

        # Create test settings
        test_settings = SimpleNamespace(
            api=SimpleNamespace(
                base_url="https://api.test.com",
                timeout=60
            ),
            retry=SimpleNamespace(
                default=SimpleNamespace(
                    max_attempts=5,
                    min_wait=1.0,
                    max_wait=30.0
                )
            )
        )

        def get_test_settings():
            return test_settings

        reset_settings()
        register_settings_provider(get_test_settings)

        # Import settings proxy and test
        from railway.core.config import settings

        assert settings.api.base_url == "https://api.test.com"
        assert settings.api.timeout == 60
        assert settings.retry.default.max_attempts == 5

        reset_settings()  # Clean up


class TestEntryPointIntegration:
    """Test @entry_point decorator integration."""

    def test_entry_point_with_typer_options(self):
        """Should work with typer options."""
        from railway.core.decorators import entry_point
        from typer.testing import CliRunner
        import typer

        app = typer.Typer()

        @entry_point
        def main(
            name: str = typer.Option("World", help="Name to greet"),
            count: int = typer.Option(1, help="Number of times"),
        ) -> str:
            result = f"Hello, {name}!" * count
            print(result)
            return result

        app.command()(main)
        runner = CliRunner()

        result = runner.invoke(app, ["--name", "Alice", "--count", "2"])
        assert "Hello, Alice!Hello, Alice!" in result.stdout


class TestErrorHandlingIntegration:
    """Test error handling integration."""

    def test_custom_errors_with_hints(self):
        """Should provide helpful error messages."""
        from railway.core.errors import (
            ConfigurationError,
            NodeError,
            PipelineError,
        )

        # Configuration error
        config_error = ConfigurationError(
            "Missing API key",
            config_key="api.key"
        )
        assert "設定" in config_error.hint

        # Node error
        node_error = NodeError(
            "Request failed",
            node_name="fetch_data",
            code="N001",
            hint="Check network connection"
        )
        full_msg = node_error.full_message()
        assert "N001" in full_msg
        assert "fetch_data" in full_msg

        # Pipeline error
        pipeline_error = PipelineError(
            "Step failed",
            step_number=2,
            step_name="transform",
            total_steps=5
        )
        assert pipeline_error.remaining_steps == 3


class TestAsyncIntegration:
    """Test async functionality integration."""

    @pytest.mark.asyncio
    async def test_async_pipeline_workflow(self):
        """Should execute async pipeline workflow."""
        from railway.core.decorators import node
        from railway.core.pipeline import async_pipeline
        from unittest.mock import patch
        import asyncio

        @node
        async def async_fetch(url: str) -> dict:
            await asyncio.sleep(0.01)
            return {"url": url, "data": "fetched"}

        @node
        async def async_process(data: dict) -> dict:
            await asyncio.sleep(0.01)
            data["processed"] = True
            return data

        @node
        def sync_validate(data: dict) -> dict:
            if "processed" not in data:
                raise ValueError("Not processed")
            return data

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                result = await async_pipeline(
                    "https://api.example.com",
                    async_fetch,
                    async_process,
                    sync_validate
                )

        assert result["processed"] is True


class TestGeneratedProjectStructure:
    """Test that generated project has correct structure."""

    def test_generated_project_has_all_files(self):
        """Should generate all required files."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            runner.invoke(app, ["init", "test_project"])

            project_dir = Path(tmpdir) / "test_project"

            # Check core structure
            assert (project_dir / "src").is_dir()
            assert (project_dir / "src" / "__init__.py").exists()
            assert (project_dir / "tests").is_dir()
            assert (project_dir / "config").is_dir()

            # Check config files
            assert (project_dir / "config" / "development.yaml").exists()

            # Check project files
            assert (project_dir / "pyproject.toml").exists()
            assert (project_dir / ".env.example").exists()

            # Check documentation
            assert (project_dir / "TUTORIAL.md").exists()

    def test_generated_node_has_test(self):
        """Should generate test file for node."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            runner.invoke(app, ["init", "test_project"])

            project_dir = Path(tmpdir) / "test_project"
            os.chdir(project_dir)

            runner.invoke(app, ["new", "node", "my_node"])

            # Check node file
            assert (project_dir / "src" / "nodes" / "my_node.py").exists()

            # Check test file
            assert (project_dir / "tests" / "nodes" / "test_my_node.py").exists()
