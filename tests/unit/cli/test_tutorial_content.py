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
        """TUTORIAL should show example of modifying workflow without changing Node."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                # Should show workflow modification concepts
                # For dag_runner: YAML edits, transitions, dag_runner
                # For typed_pipeline: multiple pipeline configurations
                has_workflow_modification = (
                    content.count("typed_pipeline") >= 2
                    or content.count("transitions") >= 2
                    or ("YAML" in content and "編集" in content)
                    or "dag_runner" in content
                )
                assert has_workflow_modification, "Should show workflow modification examples"
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
        """TUTORIAL should explicitly explain Node doesn't depend on workflow structure."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                # Should explain that Node implementation is independent
                # For dag_runner: nodes don't know about transitions (YAML defines them)
                # For typed_pipeline: nodes don't depend on pipeline structure
                node_independence = (
                    "Node修正不要" in content
                    or "実装は同じ" in content
                    or "純粋関数" in content
                    or ("ノード" in content and "状態" in content and "返す" in content)
                    or "遷移先はYAMLで定義" in content
                )
                assert node_independence, "Should explain node independence"

                # Should show workflow structure concepts
                workflow_structure = (
                    ("パイプライン" in content and "構成" in content)
                    or ("遷移" in content and "定義" in content)
                    or "遷移グラフ" in content
                )
                assert workflow_structure, "Should show workflow structure concepts"
            finally:
                os.chdir(original_cwd)
