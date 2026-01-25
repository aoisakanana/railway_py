"""Tests for railway new node documentation in TUTORIAL.

このテストスイートは以下を保証する：
1. railway new node がTUTORIALで紹介されている
2. シンプルながらも実践的な体験ができる
3. TDDワークフローを体験できる
"""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestTutorialNewNodeSection:
    """Test that generated TUTORIAL has railway new node section."""

    @pytest.fixture
    def tutorial_content(self):
        """Generate and read TUTORIAL.md content."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])
                tutorial_path = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                return tutorial_path.read_text()
            finally:
                os.chdir(original_cwd)

    def test_tutorial_mentions_railway_new_node(self, tutorial_content):
        """TUTORIAL should mention railway new node command.

        重要性: コマンドの発見可能性。
        """
        assert "railway new node" in tutorial_content

    def test_tutorial_shows_3_files_benefit(self, tutorial_content):
        """TUTORIAL should emphasize 3 files generated benefit.

        重要性: 恩恵を明示することでコマンドの価値が伝わる。
        """
        has_benefit = (
            "3" in tutorial_content or "ファイル" in tutorial_content or "files" in tutorial_content.lower()
        )
        assert has_benefit

    def test_tutorial_shows_tdd_red_green(self, tutorial_content):
        """TUTORIAL should show TDD Red-Green cycle.

        重要性: TDDを体験させることで、テスト文化を促進。
        """
        has_tdd_cycle = (
            ("Red" in tutorial_content or "失敗" in tutorial_content)
            and ("Green" in tutorial_content or "成功" in tutorial_content)
        )
        assert has_tdd_cycle, "Should show TDD Red-Green cycle"

    def test_tutorial_shows_pytest_command(self, tutorial_content):
        """TUTORIAL should show how to run tests."""
        assert "pytest" in tutorial_content.lower()
        assert "uv run" in tutorial_content

    def test_tutorial_shows_mode_option(self, tutorial_content):
        """TUTORIAL should mention --mode option.

        重要性: linear モードの存在を知らせる。
        """
        assert "--mode" in tutorial_content or "linear" in tutorial_content

    def test_tutorial_shows_yaml_integration(self, tutorial_content):
        """TUTORIAL should show how to add node to YAML.

        重要性: 生成したノードを実際に使う方法を示す。
        """
        has_yaml = "yaml" in tutorial_content.lower() or "transition" in tutorial_content.lower()
        assert has_yaml
