"""Tests for Python identifier validation.

Issue #68: 終端ノードファイル名の制約
- 数字のみの識別子は無効
- 数字で始まる識別子は無効
- Python キーワードは無効
- 修正提案を返す
"""

import pytest

from railway.core.dag.validator import (
    IdentifierValidation,
    validate_python_identifiers,
    _is_valid_identifier,
    _suggest_valid_name,
)


class TestIdentifierValidation:
    """識別子検証のテスト。"""

    def test_valid_identifiers(self):
        """有効な識別子は検証をパス。"""
        result = validate_python_identifiers(
            ("start", "exit.success.done", "check_time")
        )
        assert result.is_valid is True
        assert result.invalid_identifiers == ()

    def test_numeric_only_identifier_is_invalid(self):
        """数字のみの識別子は無効。"""
        result = validate_python_identifiers(("exit.green.1",))
        assert result.is_valid is False
        assert "1" in result.invalid_identifiers

    def test_suggests_prefixed_name(self):
        """無効な識別子に対して修正提案を返す。"""
        result = validate_python_identifiers(("exit.green.1",))
        assert "exit_1" in result.suggestions

    def test_numeric_start_is_invalid(self):
        """数字で始まる識別子は無効。"""
        result = validate_python_identifiers(("1st_node",))
        assert result.is_valid is False

    def test_keyword_is_invalid(self):
        """Python キーワードは無効。"""
        result = validate_python_identifiers(("class", "def"))
        assert result.is_valid is False
        assert "class" in result.invalid_identifiers
        assert "def" in result.invalid_identifiers


class TestIsValidIdentifier:
    """_is_valid_identifier 関数のテスト。"""

    def test_valid_snake_case(self):
        """snake_case は有効。"""
        assert _is_valid_identifier("check_time") is True

    def test_valid_single_word(self):
        """単一の単語は有効。"""
        assert _is_valid_identifier("start") is True

    def test_numeric_only_invalid(self):
        """数字のみは無効。"""
        assert _is_valid_identifier("1") is False
        assert _is_valid_identifier("123") is False

    def test_numeric_start_invalid(self):
        """数字で始まるのは無効。"""
        assert _is_valid_identifier("1st") is False

    def test_keyword_invalid(self):
        """Python キーワードは無効。"""
        assert _is_valid_identifier("class") is False
        assert _is_valid_identifier("for") is False
        assert _is_valid_identifier("if") is False

    def test_underscore_start_valid(self):
        """アンダースコアで始まるのは有効。"""
        assert _is_valid_identifier("_private") is True

    def test_with_numbers_valid(self):
        """数字を含む（先頭以外）は有効。"""
        assert _is_valid_identifier("step1") is True
        assert _is_valid_identifier("exit_1") is True


class TestSuggestValidName:
    """_suggest_valid_name 関数のテスト。"""

    def test_numeric_only_adds_prefix(self):
        """数字のみには exit_ プレフィックスを付ける。"""
        assert _suggest_valid_name("1") == "exit_1"
        assert _suggest_valid_name("123") == "exit_123"

    def test_numeric_start_adds_prefix(self):
        """数字で始まる場合は n_ プレフィックスを付ける。"""
        assert _suggest_valid_name("1st") == "n_1st"

    def test_keyword_adds_suffix(self):
        """その他の無効な名前にはサフィックスを付ける。"""
        # キーワードの場合（パターンに合わないため）
        assert _suggest_valid_name("class") == "class_"
