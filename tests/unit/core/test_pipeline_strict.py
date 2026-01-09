"""Tests for pipeline strict mode type checking."""

import pytest
from typing import Any, Dict, List, Optional, Union


class TestPipelineStrictMode:
    """Test pipeline strict mode type checking."""

    def test_strict_mode_passes_matching_types(self):
        """Should pass when types match."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node
        from unittest.mock import patch

        @node
        def step1(x: int) -> int:
            return x + 1

        @node
        def step2(x: int) -> int:
            return x * 2

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                result = pipeline(1, step1, step2, strict=True)

        assert result == 4

    def test_strict_mode_catches_type_mismatch(self):
        """Should raise TypeError on type mismatch."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node
        from unittest.mock import patch

        @node
        def returns_string(x: int) -> str:
            return str(x)

        @node
        def expects_int(x: int) -> int:
            return x * 2

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                with pytest.raises(TypeError) as exc_info:
                    pipeline(1, returns_string, expects_int, strict=True)

        assert "type mismatch" in str(exc_info.value).lower()

    def test_strict_mode_checks_initial_value(self):
        """Should check initial value type against first node."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node
        from unittest.mock import patch

        @node
        def expects_int(x: int) -> int:
            return x + 1

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                with pytest.raises(TypeError):
                    pipeline("not an int", expects_int, strict=True)

    def test_strict_mode_allows_subtype(self):
        """Should allow subtype (Liskov substitution)."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node
        from unittest.mock import patch

        @node
        def returns_dict(x: int) -> Dict[str, int]:
            return {"value": x}

        @node
        def expects_mapping(x: Dict[str, Any]) -> str:
            return str(x)

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                result = pipeline(1, returns_dict, expects_mapping, strict=True)

        assert result == "{'value': 1}"

    def test_strict_mode_off_by_default(self):
        """Should not check types when strict=False (default)."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node
        from unittest.mock import patch

        @node
        def returns_string(x: int) -> str:
            return str(x)

        @node
        def expects_int(x: int) -> int:
            return int(x) * 2

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                result = pipeline(1, returns_string, expects_int, strict=False)

        assert result == 2


class TestTypeCheckErrorMessages:
    """Test type check error message quality."""

    def test_error_shows_expected_and_actual(self):
        """Should show expected and actual types in error."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node
        from unittest.mock import patch

        @node
        def returns_list(x: int) -> List[int]:
            return [x]

        @node
        def expects_str(x: str) -> str:
            return x.upper()

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                with pytest.raises(TypeError) as exc_info:
                    pipeline(1, returns_list, expects_str, strict=True)

        error_msg = str(exc_info.value)
        assert "list" in error_msg.lower()
        assert "str" in error_msg.lower()

    def test_error_shows_step_number(self):
        """Should show which step had the mismatch."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node
        from unittest.mock import patch

        @node
        def step1(x: int) -> int:
            return x + 1

        @node
        def step2(x: int) -> str:
            return str(x)

        @node
        def step3(x: int) -> int:
            return x * 2

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                with pytest.raises(TypeError) as exc_info:
                    pipeline(1, step1, step2, step3, strict=True)

        error_msg = str(exc_info.value).lower()
        assert "step" in error_msg


class TestTypeCheckWithOptional:
    """Test type checking with Optional types."""

    def test_optional_type_handling(self):
        """Should handle Optional types correctly."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node
        from unittest.mock import patch

        @node
        def may_return_none(x: int) -> Optional[int]:
            return x if x > 0 else None

        @node
        def accepts_optional(x: Optional[int]) -> str:
            return str(x) if x else "none"

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                result = pipeline(1, may_return_none, accepts_optional, strict=True)
                assert result == "1"

                result = pipeline(-1, may_return_none, accepts_optional, strict=True)
                assert result == "none"


class TestTypeCheckWithUnion:
    """Test type checking with Union types."""

    def test_union_type_handling(self):
        """Should handle Union types correctly."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node
        from unittest.mock import patch

        @node
        def returns_int_or_str(x: int) -> Union[int, str]:
            return x if x > 0 else "negative"

        @node
        def accepts_int_or_str(x: Union[int, str]) -> str:
            return f"value: {x}"

        with patch("railway.core.decorators.logger"):
            with patch("railway.core.pipeline.logger"):
                result = pipeline(5, returns_int_or_str, accepts_int_or_str, strict=True)

        assert result == "value: 5"
