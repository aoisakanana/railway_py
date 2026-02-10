"""Tests for CLI name validation pure functions.

CLI入力バリデーション:
- エントリーポイント名: 単一識別子、Python予約語禁止
- ノード名: ドット区切り階層許容、スラッシュ拒否、各セグメント検証
- _is_valid_identifier: Unicode対応
- _suggest_valid_name: ハイフン → アンダースコア提案
"""

import pytest

from railway.core.dag.validator import (
    NameValidation,
    _is_valid_identifier,
    _suggest_valid_name,
    validate_entry_name,
    validate_node_name,
)


class TestIsValidIdentifierUnicode:
    """_is_valid_identifier の Unicode 対応テスト."""

    def test_unicode_identifier_valid(self) -> None:
        """Python が許容する Unicode 識別子は有効."""
        assert _is_valid_identifier("処理") is True

    def test_unicode_mixed_valid(self) -> None:
        """Unicode + ASCII 混合も有効."""
        assert _is_valid_identifier("処理_step") is True

    def test_existing_ascii_still_valid(self) -> None:
        """既存の ASCII テストと同じ挙動を維持."""
        assert _is_valid_identifier("start") is True
        assert _is_valid_identifier("check_time") is True
        assert _is_valid_identifier("_private") is True
        assert _is_valid_identifier("step1") is True

    def test_existing_invalid_still_rejected(self) -> None:
        """既存の無効パターンも同じ挙動を維持."""
        assert _is_valid_identifier("") is False
        assert _is_valid_identifier("1") is False
        assert _is_valid_identifier("1st") is False
        assert _is_valid_identifier("class") is False
        assert _is_valid_identifier("import") is False

    def test_hyphen_is_invalid(self) -> None:
        """ハイフン入りは無効."""
        assert _is_valid_identifier("my-workflow") is False


class TestSuggestValidNameHyphen:
    """_suggest_valid_name のハイフン対応テスト."""

    def test_hyphen_replaced_with_underscore(self) -> None:
        """ハイフンはアンダースコアに変換して提案."""
        assert _suggest_valid_name("my-workflow") == "my_workflow"

    def test_multiple_hyphens(self) -> None:
        """複数ハイフンもすべて変換."""
        assert _suggest_valid_name("my-long-name") == "my_long_name"

    def test_existing_suggestions_unchanged(self) -> None:
        """既存の提案ロジックに影響なし."""
        assert _suggest_valid_name("") == "unnamed"
        assert _suggest_valid_name("1") == "exit_1"
        assert _suggest_valid_name("1st") == "n_1st"
        assert _suggest_valid_name("class") == "class_"


class TestValidateEntryName:
    """validate_entry_name 関数のテスト."""

    def test_valid_simple_name(self) -> None:
        """正常な識別子は有効."""
        result = validate_entry_name("my_workflow")
        assert result.is_valid is True
        assert result.normalized == "my_workflow"
        assert result.error_message == ""

    def test_hyphen_rejected(self) -> None:
        """ハイフン入りは拒否、修正提案あり."""
        result = validate_entry_name("my-workflow")
        assert result.is_valid is False
        assert "my_workflow" in result.suggestion
        assert "ハイフン" in result.error_message or "-" in result.error_message

    def test_keyword_rejected(self) -> None:
        """Python 予約語は拒否."""
        result = validate_entry_name("import")
        assert result.is_valid is False
        assert "予約語" in result.error_message

    def test_class_keyword_rejected(self) -> None:
        """class も予約語として拒否."""
        result = validate_entry_name("class")
        assert result.is_valid is False

    def test_dot_rejected_for_entry(self) -> None:
        """エントリーポイント名にドットは使えない."""
        result = validate_entry_name("my.workflow")
        assert result.is_valid is False

    def test_slash_rejected_for_entry(self) -> None:
        """エントリーポイント名にスラッシュは使えない."""
        result = validate_entry_name("my/workflow")
        assert result.is_valid is False

    def test_unicode_valid(self) -> None:
        """Unicode 識別子は有効."""
        result = validate_entry_name("処理")
        assert result.is_valid is True

    def test_empty_rejected(self) -> None:
        """空文字列は拒否."""
        result = validate_entry_name("")
        assert result.is_valid is False

    def test_digit_start_rejected(self) -> None:
        """数字で始まる名前は拒否."""
        result = validate_entry_name("1workflow")
        assert result.is_valid is False

    def test_pure_function_no_side_effects(self) -> None:
        """純粋関数: 同じ入力に同じ出力."""
        result1 = validate_entry_name("my-workflow")
        result2 = validate_entry_name("my-workflow")
        assert result1 == result2


class TestValidateNodeName:
    """validate_node_name 関数のテスト."""

    def test_valid_simple_name(self) -> None:
        """単一識別子は有効."""
        result = validate_node_name("farewell")
        assert result.is_valid is True
        assert result.normalized == "farewell"

    def test_valid_dotted_name(self) -> None:
        """ドット区切りは有効."""
        result = validate_node_name("processing.validate")
        assert result.is_valid is True
        assert result.normalized == "processing.validate"

    def test_valid_deep_dotted_name(self) -> None:
        """深いドット区切りも有効."""
        result = validate_node_name("sub.deep.process")
        assert result.is_valid is True
        assert result.normalized == "sub.deep.process"

    def test_slash_rejected_with_suggestion(self) -> None:
        """スラッシュは拒否、ドット表記を提案."""
        result = validate_node_name("greeting/farewell")
        assert result.is_valid is False
        assert "greeting.farewell" in result.suggestion
        assert "/" in result.error_message

    def test_hyphen_in_segment_rejected(self) -> None:
        """セグメント内のハイフンは拒否."""
        result = validate_node_name("my-node")
        assert result.is_valid is False
        assert "my_node" in result.suggestion

    def test_keyword_segment_rejected(self) -> None:
        """セグメントが予約語の場合は拒否."""
        result = validate_node_name("class")
        assert result.is_valid is False
        assert "予約語" in result.error_message

    def test_keyword_in_dotted_segment_rejected(self) -> None:
        """ドット区切りの一部が予約語でも拒否."""
        result = validate_node_name("processing.import")
        assert result.is_valid is False

    def test_empty_segment_rejected(self) -> None:
        """空セグメント（連続ドット等）は拒否."""
        result = validate_node_name("processing..validate")
        assert result.is_valid is False

    def test_trailing_dot_rejected(self) -> None:
        """末尾ドットは拒否."""
        result = validate_node_name("processing.")
        assert result.is_valid is False

    def test_leading_dot_rejected(self) -> None:
        """先頭ドットは拒否."""
        result = validate_node_name(".processing")
        assert result.is_valid is False

    def test_unicode_valid(self) -> None:
        """Unicode ノード名は有効."""
        result = validate_node_name("処理")
        assert result.is_valid is True

    def test_pure_function_no_side_effects(self) -> None:
        """純粋関数: 同じ入力に同じ出力."""
        result1 = validate_node_name("greeting/farewell")
        result2 = validate_node_name("greeting/farewell")
        assert result1 == result2


class TestNameValidationImmutable:
    """NameValidation は frozen dataclass."""

    def test_frozen(self) -> None:
        """NameValidation は変更不可."""
        result = validate_entry_name("my_workflow")
        with pytest.raises(AttributeError):
            result.is_valid = False  # type: ignore[misc]
