"""Tests for README upgrade section.

TDD Red Phase: テストを先に作成し、失敗することを確認。
"""

import pytest
from pathlib import Path


class TestReadmeUpgradeSection:
    """README.md のアップグレードセクションテスト。"""

    @pytest.fixture
    def readme_content(self):
        """README.mdの内容を取得。"""
        readme_path = Path(__file__).parents[3] / "readme.md"
        return readme_path.read_text()

    def test_has_upgrade_section(self, readme_content):
        """アップグレードセクションが存在する。"""
        has_section = (
            "アップグレード" in readme_content
            or "upgrade" in readme_content.lower()
        )
        assert has_section

    def test_shows_dry_run_command(self, readme_content):
        """--dry-run コマンドが記載されている。"""
        assert "railway update --dry-run" in readme_content

    def test_shows_benefit_comparison(self, readme_content):
        """恩恵の比較表がある。"""
        # 問題と解決策の対比がある
        has_comparison = (
            "dag_runner" in readme_content.lower()
            or "DAG" in readme_content
        )
        assert has_comparison

    def test_shows_pattern_examples(self, readme_content):
        """旧形式パターンの例がある。"""
        assert "dict" in readme_content
        assert "Outcome" in readme_content

    def test_shows_migration_command(self, readme_content):
        """マイグレーションコマンドが記載されている。"""
        assert "railway update" in readme_content

    def test_has_upgrade_steps(self, readme_content):
        """アップグレード手順が記載されている。"""
        # プレビュー、実行、修正の手順
        has_steps = (
            "プレビュー" in readme_content
            or "--dry-run" in readme_content
        )
        assert has_steps

    def test_mentions_typed_pipeline_or_dag_runner(self, readme_content):
        """typed_pipeline または dag_runner への移行が記載されている。"""
        has_new_api = (
            "typed_pipeline" in readme_content
            or "dag_runner" in readme_content
        )
        assert has_new_api
