"""Tests for TUTORIAL documentation - dag_runner as default."""
import tempfile
from pathlib import Path

import pytest


class TestTutorialDagDefault:
    """Test TUTORIAL uses dag_runner as default."""

    @pytest.fixture
    def tutorial_content(self):
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)
            content = (project_path / "TUTORIAL.md").read_text()
            yield content

    def test_dag_runner_is_primary(self, tutorial_content):
        """dag_runner should appear before typed_pipeline."""
        dag_pos = tutorial_content.find("dag_runner")
        pipeline_pos = tutorial_content.find("typed_pipeline")
        # dag_runner should be mentioned first
        assert dag_pos > 0, "dag_runner should be mentioned"
        if pipeline_pos != -1:
            assert dag_pos < pipeline_pos, "dag_runner should appear first"

    def test_uses_outcome_class(self, tutorial_content):
        """Should use Outcome class."""
        assert "Outcome" in tutorial_content
        assert "Outcome.success" in tutorial_content

    def test_has_branching_example(self, tutorial_content):
        """Should have conditional branching example."""
        assert "条件分岐" in tutorial_content or "branching" in tutorial_content.lower()

    def test_references_linear_tutorial(self, tutorial_content):
        """Should reference TUTORIAL_linear.md."""
        assert "TUTORIAL_linear" in tutorial_content


class TestTutorialLinearExists:
    """Test TUTORIAL_linear.md exists in generated project."""

    @pytest.fixture
    def project_path(self):
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)
            yield project_path

    def test_file_exists(self, project_path):
        tutorial_linear = project_path / "TUTORIAL_linear.md"
        assert tutorial_linear.exists()

    def test_mentions_typed_pipeline(self, project_path):
        content = (project_path / "TUTORIAL_linear.md").read_text()
        assert "typed_pipeline" in content

    def test_mentions_linear_mode(self, project_path):
        content = (project_path / "TUTORIAL_linear.md").read_text()
        assert "--mode linear" in content

    def test_mentions_etl(self, project_path):
        content = (project_path / "TUTORIAL_linear.md").read_text()
        assert "ETL" in content
