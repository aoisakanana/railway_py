"""Tests for README documentation - dag_runner as default."""
from pathlib import Path

import pytest


class TestReadmeDefault:
    """Test README uses dag_runner as default."""

    @pytest.fixture
    def readme_content(self):
        readme_path = Path(__file__).parent.parent.parent.parent / "readme.md"
        return readme_path.read_text()

    def test_dag_runner_is_primary(self, readme_content):
        """dag_runner should appear before typed_pipeline."""
        dag_pos = readme_content.find("dag_runner")
        pipeline_pos = readme_content.find("typed_pipeline")
        assert dag_pos > 0, "dag_runner should be mentioned"
        assert dag_pos < pipeline_pos, "dag_runner should appear first"

    def test_quick_start_uses_dag(self, readme_content):
        """Quick start should use dag_runner."""
        # Find the quick start section (## クイックスタート to next ## heading)
        qs_start = readme_content.find("## クイックスタート")
        # Find the next ## (not ###) heading
        remaining = readme_content[qs_start + len("## クイックスタート"):]
        next_h2 = remaining.find("\n## ")
        if next_h2 == -1:
            quick_start = readme_content[qs_start:]
        else:
            quick_start = readme_content[qs_start:qs_start + len("## クイックスタート") + next_h2]

        assert "railway new entry" in quick_start
        assert "--mode linear" not in quick_start

    def test_mentions_outcome(self, readme_content):
        """Should mention Outcome class."""
        assert "Outcome" in readme_content

    def test_references_linear_readme(self, readme_content):
        """Should reference readme_linear.md."""
        assert "readme_linear" in readme_content.lower()


class TestReadmeLinearExists:
    """Test readme_linear.md exists."""

    @pytest.fixture
    def readme_linear_content(self):
        readme_linear = Path(__file__).parent.parent.parent.parent / "readme_linear.md"
        return readme_linear.read_text()

    def test_file_exists(self):
        readme_linear = Path(__file__).parent.parent.parent.parent / "readme_linear.md"
        assert readme_linear.exists()

    def test_mentions_typed_pipeline(self, readme_linear_content):
        content = readme_linear_content
        assert "typed_pipeline" in content

    def test_mentions_linear_mode(self, readme_linear_content):
        content = readme_linear_content
        assert "--mode linear" in content

    def test_references_dag_in_readme(self, readme_linear_content):
        """Should reference main README for dag_runner."""
        content = readme_linear_content
        assert "readme.md" in content.lower() or "dag_runner" in content
