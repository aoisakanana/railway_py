"""Tests for TUTORIAL.md content - ensuring key benefits are communicated."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestTutorialTransitionIndependence:
    """Test that TUTORIAL explains Node independence from pipeline transitions."""

    def test_tutorial_explains_node_independence(self):
        """TUTORIAL should explain that Nodes don't depend on pipeline structure."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                # Should explain that Node implementation doesn't change when pipeline changes
                assert "遷移" in content or "構成" in content or "変更" in content
            finally:
                os.chdir(original_cwd)

    def test_tutorial_shows_pipeline_modification_example(self):
        """TUTORIAL should show example of modifying pipeline without changing Node."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                # Should show multiple pipeline configurations
                # e.g., typed_pipeline appearing multiple times showing different configs
                pipeline_count = content.count("typed_pipeline")
                assert pipeline_count >= 2, "Should show at least 2 pipeline configurations"
            finally:
                os.chdir(original_cwd)

    def test_tutorial_mentions_contract_as_interface(self):
        """TUTORIAL should explain that Contract is the interface between Nodes."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                # Should mention Contract as the key concept
                assert "Contract" in content
                # Should mention that Node only knows about its input/output Contract
                assert "契約" in content or "入出力" in content
            finally:
                os.chdir(original_cwd)

    def test_tutorial_explains_refactoring_safety(self):
        """TUTORIAL should explain that pipeline refactoring is safe."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                # Should mention benefits like:
                # - Safe refactoring
                # - Independent testing
                # - Team development
                has_benefit = (
                    "リファクタ" in content
                    or "安全" in content
                    or "独立" in content
                    or "影響" in content
                )
                assert has_benefit, "Should mention refactoring safety or independence"
            finally:
                os.chdir(original_cwd)

    def test_tutorial_explains_node_independence_from_pipeline(self):
        """TUTORIAL should explicitly explain Node doesn't depend on pipeline structure."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                # Should explain that Node implementation doesn't change
                assert "Node修正不要" in content or "実装は同じ" in content

                # Should show comparison table or explicit benefit
                assert "パイプライン" in content and "構成" in content
            finally:
                os.chdir(original_cwd)
