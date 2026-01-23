"""README.md の内容を検証するテスト。

TDD Red Phase: まずテストを書き、失敗を確認する。
"""
from pathlib import Path

import pytest


class TestReadmeVersionManagementSection:
    """READMEにバージョン管理セクションが含まれることを検証。"""

    @pytest.fixture
    def readme_content(self) -> str:
        """README.mdの内容を読み込む。"""
        readme_path = Path(__file__).parents[3] / "readme.md"
        return readme_path.read_text(encoding="utf-8")

    def test_has_version_management_section(self, readme_content: str):
        """バージョン管理セクションが存在する。"""
        assert "## バージョン管理" in readme_content

    def test_explains_project_yaml(self, readme_content: str):
        """project.yamlの説明がある。"""
        assert ".railway/project.yaml" in readme_content

    def test_has_railway_update_command(self, readme_content: str):
        """railway updateコマンドの説明がある。"""
        assert "railway update" in readme_content
        assert "--dry-run" in readme_content

    def test_has_railway_backup_command(self, readme_content: str):
        """railway backupコマンドの説明がある。"""
        assert "railway backup" in readme_content
        assert "backup list" in readme_content
        assert "backup restore" in readme_content

    def test_version_management_in_cli_commands(self, readme_content: str):
        """CLI Commandsセクションにバージョン管理がある。"""
        # CLI Commandsセクション内にバージョン管理コマンドがある
        cli_section_start = readme_content.find("## CLI Commands")
        # 次のH2セクション（## で始まる行）を探す
        remaining = readme_content[cli_section_start + len("## CLI Commands"):]
        next_h2 = remaining.find("\n## ")
        if next_h2 == -1:
            cli_section = readme_content[cli_section_start:]
        else:
            cli_section = readme_content[cli_section_start:cli_section_start + len("## CLI Commands") + next_h2]

        assert "railway update" in cli_section
        assert "railway backup" in cli_section

    def test_version_management_in_features(self, readme_content: str):
        """特徴セクションにバージョン管理がある。"""
        features_start = readme_content.find("## 特徴")
        features_end = readme_content.find("## ", features_start + 1)
        features_section = readme_content[features_start:features_end]

        assert "バージョン管理" in features_section

    def test_roadmap_updated(self, readme_content: str):
        """ロードマップがPhase 2完了を示している。"""
        assert "Phase 2" in readme_content
        # Phase 2が完了マークされている
        roadmap_section = readme_content[readme_content.find("## ロードマップ"):]
        assert "バージョン管理" in roadmap_section
        # Phase 2 ✅ が存在することを確認
        assert "Phase 2 ✅" in readme_content

    def test_design_decisions_explained(self, readme_content: str):
        """設計判断の説明がある。"""
        # 各機能に「なぜ」の説明がある
        has_design_table = (
            "| 判断 | 理由 |" in readme_content
            or "設計判断" in readme_content
        )
        assert has_design_table

    def test_compatibility_rules_documented(self, readme_content: str):
        """互換性ルールが文書化されている。"""
        assert "マイナー" in readme_content or "メジャー" in readme_content
        assert "互換" in readme_content
