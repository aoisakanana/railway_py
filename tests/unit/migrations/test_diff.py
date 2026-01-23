"""差分計算機能のテスト。

TDD Red Phase: まずテストを書き、失敗を確認する。
"""
from railway.migrations.diff import (
    count_diff_lines,
    generate_unified_diff,
    summarize_changes,
    find_added_sections,
)


class TestCountDiffLines:
    """count_diff_lines関数のテスト。"""

    def test_no_changes(self):
        """変更なしの場合。"""
        text = "Hello\nWorld"

        diff = count_diff_lines(text, text)

        assert diff.added == 0
        assert diff.removed == 0

    def test_additions_only(self):
        """追加のみの場合。"""
        original = "Hello"
        new = "Hello\nWorld"

        diff = count_diff_lines(original, new)

        assert diff.added == 1
        assert diff.removed == 0

    def test_deletions_only(self):
        """削除のみの場合。"""
        original = "Hello\nWorld"
        new = "Hello"

        diff = count_diff_lines(original, new)

        assert diff.added == 0
        assert diff.removed == 1

    def test_mixed_changes(self):
        """追加と削除の両方。"""
        original = "Hello\nWorld"
        new = "Hi\nWorld\nNew"

        diff = count_diff_lines(original, new)

        # "Hello" → "Hi" (1 removed, 1 added) + "New" (1 added)
        assert diff.added >= 1
        assert diff.removed >= 1

    def test_empty_to_content(self):
        """空から内容ありへの変更。"""
        original = ""
        new = "Line 1\nLine 2"

        diff = count_diff_lines(original, new)

        assert diff.added == 2
        assert diff.removed == 0


class TestGenerateUnifiedDiff:
    """generate_unified_diff関数のテスト。"""

    def test_generates_diff_format(self):
        """unified diff形式で生成される。"""
        original = "Hello\nWorld"
        new = "Hello\nEveryone"

        diff = generate_unified_diff(original, new, "old.txt", "new.txt")

        assert "--- old.txt" in diff
        assert "+++ new.txt" in diff
        assert "-World" in diff
        assert "+Everyone" in diff

    def test_empty_diff_for_identical(self):
        """同一内容の場合は空。"""
        text = "Hello\nWorld"

        diff = generate_unified_diff(text, text)

        assert diff == ""


class TestSummarizeChanges:
    """summarize_changes関数のテスト。"""

    def test_additions_summary(self):
        """追加のみの要約。"""
        original = "Hello"
        new = "Hello\nWorld\nNew"

        summaries = summarize_changes(original, new)

        assert any("追加" in s for s in summaries)

    def test_deletions_summary(self):
        """削除のみの要約。"""
        original = "Hello\nWorld"
        new = "Hello"

        summaries = summarize_changes(original, new)

        assert any("削除" in s for s in summaries)

    def test_detects_new_sections(self):
        """新しいセクションを検出する。"""
        original = "## Intro\n\nContent"
        new = "## Intro\n\nContent\n\n## New Section\n\nMore"

        summaries = summarize_changes(original, new)

        assert any("New Section" in s for s in summaries)


class TestFindAddedSections:
    """find_added_sections関数のテスト。"""

    def test_finds_new_sections(self):
        """追加されたセクションを検出する。"""
        original = "## Introduction\n\nContent"
        new = "## Introduction\n\nContent\n\n## New Section\n\nMore"

        sections = find_added_sections(original, new)

        assert "New Section" in sections

    def test_returns_empty_for_no_new_sections(self):
        """新しいセクションがない場合は空。"""
        original = "## Section\n\nContent"
        new = "## Section\n\nUpdated content"

        sections = find_added_sections(original, new)

        assert sections == []

    def test_finds_multiple_sections(self):
        """複数のセクションを検出する。"""
        original = "## First\n\nContent"
        new = "## First\n\n## Second\n\n## Third"

        sections = find_added_sections(original, new)

        assert "Second" in sections
        assert "Third" in sections
        assert len(sections) == 2

    def test_custom_marker(self):
        """カスタムマーカーを使用できる。"""
        original = "# H1\n\nContent"
        new = "# H1\n\n# H2\n\nMore"

        sections = find_added_sections(original, new, marker="# ")

        assert "H2" in sections
