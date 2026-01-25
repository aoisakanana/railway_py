"""Tests for railway new node documentation in README.

このテストスイートは以下を保証する：
1. コマンドの存在がドキュメント化されている
2. 利点（恩恵）が明示されている
3. 使い分けガイダンスがある
4. コード例が正確
"""

import pytest


class TestReadmeNewNodeSection:
    """Test that README has railway new node documentation."""

    @pytest.fixture
    def readme_content(self):
        """Read README.md content."""
        from pathlib import Path

        readme_path = Path(__file__).parents[3] / "readme.md"
        return readme_path.read_text()

    def test_readme_has_node_creation_section(self, readme_content):
        """README should have a node creation section.

        重要性: ユーザーがコマンドを発見できる。
        """
        assert "ノードの作成" in readme_content or "Node Creation" in readme_content

    def test_readme_shows_benefit_comparison(self, readme_content):
        """README should show benefit comparison table.

        重要性: 手動作成との違いが明確になる。
        """
        # 表形式で比較されていること
        has_comparison = (
            "手動" in readme_content
            or "3ファイル" in readme_content
            or "同時生成" in readme_content
        )
        assert has_comparison, "Should show benefits compared to manual creation"

    def test_readme_shows_railway_new_node_dag(self, readme_content):
        """README should show railway new node command for dag mode."""
        assert "railway new node" in readme_content
        assert "dag" in readme_content.lower()

    def test_readme_shows_railway_new_node_linear(self, readme_content):
        """README should show --mode linear option."""
        assert "--mode linear" in readme_content

    def test_readme_shows_generated_files(self, readme_content):
        """README should explain what files are generated.

        重要性: 何が生成されるか事前に知れる。
        """
        assert "_context.py" in readme_content or "context" in readme_content.lower()

    def test_readme_shows_dag_code_example(self, readme_content):
        """README should show dag node code example."""
        assert "tuple[" in readme_content
        assert "Outcome" in readme_content

    def test_readme_shows_mode_selection_guide(self, readme_content):
        """README should explain when to use which mode.

        重要性: ユーザーが適切なモードを選べる。
        """
        has_guidance = (
            "どちら" in readme_content or "用途" in readme_content or "場面" in readme_content
        )
        assert has_guidance, "Should have mode selection guidance"

    def test_readme_shows_linear_code_example(self, readme_content):
        """README should show linear node code example."""
        assert "Optional[" in readme_content
        assert "Output:" in readme_content or "Output]" in readme_content

    def test_readme_shows_typing_import(self, readme_content):
        """README should show typing import for Optional."""
        assert "from typing import Optional" in readme_content
