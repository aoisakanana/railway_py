"""バージョン互換性チェックのテスト。

TDD Red Phase: まずテストを書き、失敗を確認する。
"""
import pytest

from railway.core.version_checker import (
    CompatibilityLevel,
    CompatibilityResult,
    check_compatibility,
    get_compatibility_message,
    format_compatibility_warning,
    format_compatibility_error,
)


class TestCompatibilityResult:
    """CompatibilityResultのテスト。"""

    def test_is_compatible_true_for_full(self):
        """FULLレベルはis_compatible=True。"""
        result = CompatibilityResult(
            level=CompatibilityLevel.FULL,
            project_version="0.9.0",
            current_version="0.9.0",
        )
        assert result.is_compatible is True

    def test_is_compatible_false_for_minor_diff(self):
        """MINOR_DIFFレベルはis_compatible=False。"""
        result = CompatibilityResult(
            level=CompatibilityLevel.MINOR_DIFF,
            project_version="0.8.0",
            current_version="0.9.0",
        )
        assert result.is_compatible is False

    def test_requires_confirmation_for_minor_diff(self):
        """MINOR_DIFFは確認が必要。"""
        result = CompatibilityResult(
            level=CompatibilityLevel.MINOR_DIFF,
            project_version="0.8.0",
            current_version="0.9.0",
        )
        assert result.requires_confirmation is True

    def test_requires_confirmation_for_unknown(self):
        """UNKNOWNは確認が必要。"""
        result = CompatibilityResult(
            level=CompatibilityLevel.UNKNOWN,
            project_version=None,
            current_version="0.9.0",
        )
        assert result.requires_confirmation is True

    def test_is_blocked_for_major_diff(self):
        """MAJOR_DIFFはブロック。"""
        result = CompatibilityResult(
            level=CompatibilityLevel.MAJOR_DIFF,
            project_version="0.9.0",
            current_version="1.0.0",
        )
        assert result.is_blocked is True

    def test_result_is_immutable(self):
        """CompatibilityResultはイミュータブル。"""
        result = CompatibilityResult(
            level=CompatibilityLevel.FULL,
            project_version="0.9.0",
            current_version="0.9.0",
        )
        with pytest.raises(Exception):
            result.level = CompatibilityLevel.MAJOR_DIFF


class TestCheckCompatibility:
    """check_compatibility関数のテスト。"""

    def test_same_version_is_full(self):
        """同じバージョンはFULL互換。"""
        result = check_compatibility("0.9.0", "0.9.0")
        assert result.level == CompatibilityLevel.FULL

    def test_patch_difference_is_full(self):
        """パッチバージョン差はFULL互換。"""
        result = check_compatibility("0.9.0", "0.9.5")
        assert result.level == CompatibilityLevel.FULL

    def test_minor_upgrade_is_minor_diff(self):
        """マイナーバージョンアップはMINOR_DIFF。"""
        result = check_compatibility("0.8.0", "0.9.0")
        assert result.level == CompatibilityLevel.MINOR_DIFF

    def test_minor_downgrade_is_minor_diff(self):
        """マイナーバージョンダウンもMINOR_DIFF。"""
        result = check_compatibility("0.10.0", "0.9.0")
        assert result.level == CompatibilityLevel.MINOR_DIFF

    def test_major_upgrade_is_major_diff(self):
        """メジャーバージョンアップはMAJOR_DIFF。"""
        result = check_compatibility("0.9.0", "1.0.0")
        assert result.level == CompatibilityLevel.MAJOR_DIFF

    def test_major_downgrade_is_major_diff(self):
        """メジャーバージョンダウンもMAJOR_DIFF。"""
        result = check_compatibility("2.0.0", "1.0.0")
        assert result.level == CompatibilityLevel.MAJOR_DIFF

    def test_none_version_is_unknown(self):
        """Noneバージョンは UNKNOWN。"""
        result = check_compatibility(None, "0.9.0")
        assert result.level == CompatibilityLevel.UNKNOWN

    def test_result_contains_versions(self):
        """結果にバージョン情報が含まれる。"""
        result = check_compatibility("0.8.0", "0.9.0")
        assert result.project_version == "0.8.0"
        assert result.current_version == "0.9.0"

    def test_is_referentially_transparent(self):
        """同じ入力には同じ結果（参照透過性）。"""
        result1 = check_compatibility("0.8.0", "0.9.0")
        result2 = check_compatibility("0.8.0", "0.9.0")
        assert result1 == result2


class TestGetCompatibilityMessage:
    """get_compatibility_message関数のテスト。"""

    def test_full_returns_none(self):
        """FULLはNoneを返す。"""
        assert get_compatibility_message(CompatibilityLevel.FULL) is None

    def test_minor_diff_returns_message(self):
        """MINOR_DIFFはメッセージを返す。"""
        message = get_compatibility_message(CompatibilityLevel.MINOR_DIFF)
        assert message is not None
        assert "マイナーバージョン" in message

    def test_major_diff_returns_message(self):
        """MAJOR_DIFFはメッセージを返す。"""
        message = get_compatibility_message(CompatibilityLevel.MAJOR_DIFF)
        assert message is not None
        assert "メジャーバージョン" in message

    def test_unknown_returns_message(self):
        """UNKNOWNはメッセージを返す。"""
        message = get_compatibility_message(CompatibilityLevel.UNKNOWN)
        assert message is not None
        assert "バージョン情報がありません" in message


class TestFormatMessages:
    """メッセージフォーマット関数のテスト。"""

    def test_format_warning_contains_versions(self):
        """警告メッセージにバージョンが含まれる。"""
        result = CompatibilityResult(
            level=CompatibilityLevel.MINOR_DIFF,
            project_version="0.8.0",
            current_version="0.9.0",
        )
        warning = format_compatibility_warning(result)
        assert "0.8.0" in warning
        assert "0.9.0" in warning

    def test_format_warning_handles_none_version(self):
        """警告メッセージはNoneバージョンを「不明」と表示。"""
        result = CompatibilityResult(
            level=CompatibilityLevel.UNKNOWN,
            project_version=None,
            current_version="0.9.0",
        )
        warning = format_compatibility_warning(result)
        assert "不明" in warning

    def test_format_error_contains_update_instruction(self):
        """エラーメッセージにupdate指示が含まれる。"""
        result = CompatibilityResult(
            level=CompatibilityLevel.MAJOR_DIFF,
            project_version="0.9.0",
            current_version="1.0.0",
        )
        error = format_compatibility_error(result)
        assert "railway update" in error
