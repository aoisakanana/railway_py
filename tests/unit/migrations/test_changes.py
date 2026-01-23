"""変更定義型のテスト。

TDD Red Phase: まずテストを書き、失敗を確認する。
"""
import pytest

from railway.migrations.changes import (
    ChangeType,
    FileChange,
    ConfigChange,
    CodeGuidance,
    MigrationDefinition,
)


class TestChangeTypeEnum:
    """ChangeType Enumのテスト。"""

    def test_has_file_create(self):
        """FILE_CREATEが存在する。"""
        assert ChangeType.FILE_CREATE.value == "file_create"

    def test_has_file_update(self):
        """FILE_UPDATEが存在する。"""
        assert ChangeType.FILE_UPDATE.value == "file_update"

    def test_has_file_delete(self):
        """FILE_DELETEが存在する。"""
        assert ChangeType.FILE_DELETE.value == "file_delete"

    def test_has_config_merge(self):
        """CONFIG_MERGEが存在する。"""
        assert ChangeType.CONFIG_MERGE.value == "config_merge"

    def test_has_code_guidance(self):
        """CODE_GUIDANCEが存在する。"""
        assert ChangeType.CODE_GUIDANCE.value == "code_guidance"


class TestFileChangeImmutability:
    """FileChangeのイミュータブル性テスト。"""

    def test_is_frozen(self):
        """FileChangeは変更不可。"""
        change = FileChange.create("test.py", "content", "desc")

        with pytest.raises(Exception):
            change.path = "other.py"


class TestFileChangeFactories:
    """FileChangeファクトリメソッドのテスト。"""

    def test_create_sets_correct_type(self):
        """createメソッドがFILE_CREATEを設定する。"""
        change = FileChange.create("test.py", "content", "新規作成")

        assert change.change_type == ChangeType.FILE_CREATE
        assert change.path == "test.py"
        assert change.content == "content"

    def test_update_sets_correct_type(self):
        """updateメソッドがFILE_UPDATEを設定する。"""
        change = FileChange.update("test.py", "template.j2", "更新")

        assert change.change_type == ChangeType.FILE_UPDATE
        assert change.path == "test.py"
        assert change.template == "template.j2"

    def test_delete_sets_correct_type(self):
        """deleteメソッドがFILE_DELETEを設定する。"""
        change = FileChange.delete("test.py", "削除")

        assert change.change_type == ChangeType.FILE_DELETE
        assert change.path == "test.py"

    def test_create_generates_default_description(self):
        """createはデフォルトの説明を生成する。"""
        change = FileChange.create("test.py", "content")

        assert "test.py" in change.description


class TestConfigChangeImmutability:
    """ConfigChangeのイミュータブル性テスト。"""

    def test_is_frozen(self):
        """ConfigChangeは変更不可。"""
        change = ConfigChange(
            path="config.yaml",
            additions={"key": "value"},
        )

        with pytest.raises(Exception):
            change.path = "other.yaml"


class TestConfigChangeDescription:
    """ConfigChangeの説明生成テスト。"""

    def test_description_shows_additions_count(self):
        """descriptionは追加キー数を表示する。"""
        change = ConfigChange(
            path="config.yaml",
            additions={"key1": "v1", "key2": "v2"},
        )

        assert "追加" in change.description
        assert "2" in change.description

    def test_description_shows_renames_count(self):
        """descriptionはリネームキー数を表示する。"""
        change = ConfigChange(
            path="config.yaml",
            renames={"old": "new"},
        )

        assert "リネーム" in change.description
        assert "1" in change.description

    def test_description_shows_deletions_count(self):
        """descriptionは削除キー数を表示する。"""
        change = ConfigChange(
            path="config.yaml",
            deletions=["deprecated1", "deprecated2"],
        )

        assert "削除" in change.description
        assert "2" in change.description


class TestCodeGuidanceImmutability:
    """CodeGuidanceのイミュータブル性テスト。"""

    def test_is_frozen(self):
        """CodeGuidanceは変更不可。"""
        guidance = CodeGuidance(
            description="test",
            pattern=r"old",
            replacement="new",
        )

        with pytest.raises(Exception):
            guidance.pattern = r"other"


class TestCodeGuidanceMatches:
    """CodeGuidance.matchesメソッドのテスト。"""

    def test_finds_matching_lines(self):
        """マッチする行を見つける。"""
        content = '@node(log_input=True)\ndef my_node(): ...'
        guidance = CodeGuidance(
            description="log_input → log_inputs",
            pattern=r"log_input=",
            replacement="log_inputs=",
        )

        matches = guidance.matches(content)

        assert len(matches) == 1
        assert matches[0][0] == 1  # line number
        assert "log_input" in matches[0][1]  # original line
        assert "log_inputs" in matches[0][2]  # suggested line

    def test_returns_empty_for_no_match(self):
        """マッチしない場合は空リストを返す。"""
        content = '@node(log_outputs=True)'
        guidance = CodeGuidance(
            description="test",
            pattern=r"log_input=",
            replacement="log_inputs=",
        )

        matches = guidance.matches(content)

        assert len(matches) == 0


class TestMigrationDefinitionImmutability:
    """MigrationDefinitionのイミュータブル性テスト。"""

    def test_is_frozen(self):
        """MigrationDefinitionは変更不可。"""
        migration = MigrationDefinition(
            from_version="0.9.0",
            to_version="0.10.0",
            description="Test",
        )

        with pytest.raises(Exception):
            migration.from_version = "0.8.0"


class TestMigrationDefinitionProperties:
    """MigrationDefinitionのプロパティテスト。"""

    def test_total_changes_counts_file_and_config_changes(self):
        """total_changesがファイル変更と設定変更を合計する。"""
        migration = MigrationDefinition(
            from_version="0.9.0",
            to_version="0.10.0",
            description="Test",
            file_changes=(
                FileChange.create("a.py", ""),
                FileChange.create("b.py", ""),
            ),
            config_changes=(
                ConfigChange(path="config.yaml", additions={"key": "value"}),
            ),
        )

        assert migration.total_changes == 3

    def test_has_breaking_changes_when_warnings_exist(self):
        """警告がある場合has_breaking_changesがTrue。"""
        migration = MigrationDefinition(
            from_version="0.9.0",
            to_version="1.0.0",
            description="Breaking",
            warnings=("APIが削除されました",),
        )

        assert migration.has_breaking_changes is True

    def test_has_breaking_changes_when_guidance_exists(self):
        """ガイダンスがある場合has_breaking_changesがTrue。"""
        migration = MigrationDefinition(
            from_version="0.9.0",
            to_version="0.10.0",
            description="With guidance",
            code_guidance=(
                CodeGuidance(
                    description="test",
                    pattern=r"old",
                    replacement="new",
                ),
            ),
        )

        assert migration.has_breaking_changes is True

    def test_has_breaking_changes_false_when_no_warnings_or_guidance(self):
        """警告もガイダンスもない場合has_breaking_changesがFalse。"""
        migration = MigrationDefinition(
            from_version="0.9.0",
            to_version="0.10.0",
            description="Simple",
        )

        assert migration.has_breaking_changes is False
