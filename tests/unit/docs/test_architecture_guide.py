"""Tests for architecture documentation."""
import pytest
from pathlib import Path


class TestADRExists:
    """Test that ADR files exist and contain required content."""

    @pytest.fixture
    def docs_dir(self):
        """Get docs directory."""
        return Path(__file__).parent.parent.parent.parent / "docs" / "adr"

    def test_adr_002_exists(self, docs_dir):
        """ADR-002 should exist."""
        adr_path = docs_dir / "002_execution_models.md"
        assert adr_path.exists()

    def test_adr_002_content(self, docs_dir):
        """ADR-002 should contain key sections."""
        content = (docs_dir / "002_execution_models.md").read_text()
        assert "typed_pipeline" in content
        assert "dag_runner" in content
        assert "相互排他" in content or "mutually exclusive" in content.lower()

    def test_adr_003_exists(self, docs_dir):
        """ADR-003 should exist."""
        adr_path = docs_dir / "003_decorator_responsibilities.md"
        assert adr_path.exists()

    def test_adr_003_content(self, docs_dir):
        """ADR-003 should contain key sections."""
        content = (docs_dir / "003_decorator_responsibilities.md").read_text()
        assert "@entry_point" in content
        assert "@node" in content
        assert "責務" in content or "responsibilit" in content.lower()


class TestReadmeArchitectureSection:
    """Test README has architecture section."""

    @pytest.fixture
    def readme_content(self):
        """Read README.md content."""
        readme_path = Path(__file__).parent.parent.parent.parent / "readme.md"
        return readme_path.read_text()

    def test_readme_has_execution_model_comparison(self, readme_content):
        """README should compare typed_pipeline vs dag_runner."""
        assert "typed_pipeline" in readme_content
        assert "dag_runner" in readme_content

    def test_readme_has_when_to_use(self, readme_content):
        """README should explain when to use each model."""
        # Either Japanese or English
        has_guidance = (
            "使い分け" in readme_content
            or "when to use" in readme_content.lower()
            or "どちらを" in readme_content
        )
        assert has_guidance
