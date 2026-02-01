"""Tests for error catalog and formatting.

Issue #70: エラーメッセージの改善
- エラーカタログが実装されている
- ユーザーフレンドリーなメッセージが表示される
- Hint が表示される
"""

import pytest

from railway.core.errors import (
    ErrorInfo,
    ERROR_CATALOG,
    format_error,
)


class TestErrorCatalog:
    """エラーカタログのテスト。"""

    def test_format_error_with_valid_code(self):
        """有効なエラーコードでメッセージが生成される。"""
        result = format_error("E001", node_name="start")
        assert "E001" in result
        assert "start" in result
        assert "Hint:" in result

    def test_format_error_with_unknown_code(self):
        """未知のエラーコードでもクラッシュしない。"""
        result = format_error("E999")
        assert "Unknown error" in result

    def test_all_catalog_entries_have_required_fields(self):
        """カタログの全エントリに必須フィールドがある。"""
        for code, info in ERROR_CATALOG.items():
            assert info.code == code
            assert info.title
            assert info.message_template


class TestErrorInfo:
    """ErrorInfo のテスト。"""

    def test_error_info_is_frozen(self):
        """ErrorInfo は immutable。"""
        info = ErrorInfo(
            code="E001",
            title="テストエラー",
            message_template="テストメッセージ: {value}",
        )
        with pytest.raises((AttributeError, TypeError)):
            info.code = "E002"  # type: ignore


class TestFormatError:
    """format_error 関数のテスト。"""

    def test_format_error_includes_title(self):
        """フォーマットされたエラーにタイトルが含まれる。"""
        result = format_error("E001", node_name="start")
        # タイトルが含まれる
        assert "開始ノード" in result or "引数" in result

    def test_format_error_includes_hint(self):
        """フォーマットされたエラーに Hint が含まれる。"""
        result = format_error("E001", node_name="start")
        assert "Hint:" in result

    def test_format_error_includes_doc_url(self):
        """フォーマットされたエラーにドキュメントURLが含まれる。"""
        result = format_error("E001", node_name="start")
        assert "詳細:" in result


class TestErrorCodes:
    """エラーコードのテスト。"""

    def test_e001_start_node_argument(self):
        """E001: 開始ノードの引数エラー。"""
        assert "E001" in ERROR_CATALOG
        info = ERROR_CATALOG["E001"]
        assert "開始" in info.title or "引数" in info.title

    def test_e002_module_not_found(self):
        """E002: モジュールが見つかりません。"""
        assert "E002" in ERROR_CATALOG
        info = ERROR_CATALOG["E002"]
        assert "モジュール" in info.title

    def test_e003_invalid_identifier(self):
        """E003: 無効な識別子。"""
        assert "E003" in ERROR_CATALOG
        info = ERROR_CATALOG["E003"]
        assert "識別子" in info.title

    def test_e004_exit_node_return(self):
        """E004: 終端ノードの戻り値エラー。"""
        assert "E004" in ERROR_CATALOG
        info = ERROR_CATALOG["E004"]
        assert "終端" in info.title or "戻り値" in info.title
