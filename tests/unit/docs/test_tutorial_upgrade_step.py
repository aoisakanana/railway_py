"""Tests for TUTORIAL upgrade step.

TDD Red Phase: テストを先に作成し、失敗することを確認。
"""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestTutorialUpgradeStep:
    """TUTORIAL.md のアップグレードステップテスト。"""

    @pytest.fixture
    def tutorial_content(self):
        """生成されたTUTORIAL.mdの内容を取得。"""
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

    def test_has_upgrade_step(self, tutorial_content):
        """アップグレードステップが存在する。"""
        has_step = (
            "アップグレード" in tutorial_content
            or "upgrade" in tutorial_content.lower()
        )
        assert has_step

    def test_shows_dry_run_preview(self, tutorial_content):
        """--dry-run プレビューの説明がある。"""
        assert "dry-run" in tutorial_content.lower()

    def test_shows_before_after_example(self, tutorial_content):
        """Before/After の例がある。"""
        has_example = (
            "Before" in tutorial_content or "After" in tutorial_content
        )
        assert has_example

    def test_shows_outcome_benefit(self, tutorial_content):
        """Outcome の恩恵が説明されている。"""
        assert "Outcome" in tutorial_content

    def test_step_9_exists(self, tutorial_content):
        """Step 9 が存在する。"""
        assert "Step 9" in tutorial_content

    def test_mentions_railway_update(self, tutorial_content):
        """railway update コマンドが記載されている。"""
        assert "railway update" in tutorial_content
