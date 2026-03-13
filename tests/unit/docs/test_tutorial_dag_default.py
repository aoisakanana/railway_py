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

    def test_no_linear_tutorial_reference(self, tutorial_content):
        """Should NOT reference TUTORIAL_linear.md (removed)."""
        assert "TUTORIAL_linear" not in tutorial_content

    def test_tutorial_linear_not_generated(self):
        """TUTORIAL_linear.md should NOT be generated."""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)
            assert not (project_path / "TUTORIAL_linear.md").exists()
