# Issue #16: pipeline型チェック（strictモード）

**Phase:** 1c
**優先度:** 中
**依存関係:** #05
**見積もり:** 1日

---

## 概要

pipeline関数にstrictモードを追加し、ノード間の型の整合性をランタイムでチェックする。
型ミスマッチを早期に検出し、デバッグを容易にする。

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/core/test_pipeline_strict.py
"""Tests for pipeline strict mode type checking."""
import pytest
from typing import List, Dict, Any


class TestPipelineStrictMode:
    """Test pipeline strict mode type checking."""

    def test_strict_mode_passes_matching_types(self):
        """Should pass when types match."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node

        @node
        def step1(x: int) -> int:
            return x + 1

        @node
        def step2(x: int) -> int:
            return x * 2

        result = pipeline(1, step1, step2, strict=True)
        assert result == 4

    def test_strict_mode_catches_type_mismatch(self):
        """Should raise TypeError on type mismatch."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node

        @node
        def returns_string(x: int) -> str:
            return str(x)

        @node
        def expects_int(x: int) -> int:
            return x * 2

        with pytest.raises(TypeError) as exc_info:
            pipeline(1, returns_string, expects_int, strict=True)

        assert "type mismatch" in str(exc_info.value).lower()

    def test_strict_mode_checks_initial_value(self):
        """Should check initial value type against first node."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node

        @node
        def expects_int(x: int) -> int:
            return x + 1

        with pytest.raises(TypeError):
            pipeline("not an int", expects_int, strict=True)

    def test_strict_mode_allows_subtype(self):
        """Should allow subtype (Liskov substitution)."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node

        @node
        def returns_dict(x: int) -> Dict[str, int]:
            return {"value": x}

        @node
        def expects_mapping(x: Dict[str, Any]) -> str:
            return str(x)

        # Dict[str, int] is subtype of Dict[str, Any]
        result = pipeline(1, returns_dict, expects_mapping, strict=True)
        assert result == "{'value': 1}"

    def test_strict_mode_off_by_default(self):
        """Should not check types when strict=False (default)."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node

        @node
        def returns_string(x: int) -> str:
            return str(x)

        @node
        def expects_int(x: int) -> int:
            # Will fail at runtime but not type-check time
            return int(x) * 2

        # Should not raise TypeError, may fail at runtime
        result = pipeline(1, returns_string, expects_int, strict=False)
        assert result == 2  # "1" -> int("1") * 2 = 2


class TestTypeCheckErrorMessages:
    """Test type check error message quality."""

    def test_error_shows_expected_and_actual(self):
        """Should show expected and actual types in error."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node

        @node
        def returns_list(x: int) -> List[int]:
            return [x]

        @node
        def expects_str(x: str) -> str:
            return x.upper()

        with pytest.raises(TypeError) as exc_info:
            pipeline(1, returns_list, expects_str, strict=True)

        error_msg = str(exc_info.value)
        assert "List" in error_msg or "list" in error_msg
        assert "str" in error_msg

    def test_error_shows_step_number(self):
        """Should show which step had the mismatch."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node

        @node
        def step1(x: int) -> int:
            return x + 1

        @node
        def step2(x: int) -> str:
            return str(x)

        @node
        def step3(x: int) -> int:  # Expects int, gets str
            return x * 2

        with pytest.raises(TypeError) as exc_info:
            pipeline(1, step1, step2, step3, strict=True)

        error_msg = str(exc_info.value)
        assert "step2" in error_msg.lower() or "step 2" in error_msg.lower() or "step3" in error_msg.lower()


class TestTypeCheckWithOptional:
    """Test type checking with Optional types."""

    def test_optional_type_handling(self):
        """Should handle Optional types correctly."""
        from railway.core.pipeline import pipeline
        from railway.core.decorators import node
        from typing import Optional

        @node
        def may_return_none(x: int) -> Optional[int]:
            return x if x > 0 else None

        @node
        def accepts_optional(x: Optional[int]) -> str:
            return str(x) if x else "none"

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
        from typing import Union

        @node
        def returns_int_or_str(x: int) -> Union[int, str]:
            return x if x > 0 else "negative"

        @node
        def accepts_int_or_str(x: Union[int, str]) -> str:
            return f"value: {x}"

        result = pipeline(5, returns_int_or_str, accepts_int_or_str, strict=True)
        assert result == "value: 5"
```

```bash
# 実行して失敗を確認
pytest tests/unit/core/test_pipeline_strict.py -v
# Expected: FAILED
```

### Step 2: Green（最小限の実装）

```python
# railway/core/type_check.py
"""Type checking utilities for pipeline strict mode."""
from typing import get_type_hints, Any, Union, get_origin, get_args
import typing


def check_type_compatibility(value: Any, expected_type: type) -> bool:
    """Check if value is compatible with expected type."""
    if expected_type is Any:
        return True

    # Handle None
    if value is None:
        origin = get_origin(expected_type)
        if origin is Union:
            args = get_args(expected_type)
            return type(None) in args
        return expected_type is type(None)

    # Get origin for generic types
    origin = get_origin(expected_type)

    # Handle Union types (including Optional)
    if origin is Union:
        args = get_args(expected_type)
        return any(check_type_compatibility(value, arg) for arg in args)

    # Handle generic types (List, Dict, etc.)
    if origin is not None:
        # Basic check against origin type
        if not isinstance(value, origin):
            return False
        # Could add deeper checking for generic args here
        return True

    # Simple isinstance check
    try:
        return isinstance(value, expected_type)
    except TypeError:
        # Some types can't be used with isinstance
        return True


def get_function_input_type(func: callable) -> type | None:
    """Get the input type of a function's first parameter."""
    try:
        hints = get_type_hints(func)
        # Get first parameter's type (excluding 'return')
        params = [k for k in hints.keys() if k != 'return']
        if params:
            return hints[params[0]]
    except Exception:
        pass
    return Any


def get_function_output_type(func: callable) -> type | None:
    """Get the return type of a function."""
    try:
        hints = get_type_hints(func)
        return hints.get('return', Any)
    except Exception:
        return Any


def format_type_error(
    step_num: int,
    step_name: str,
    expected_type: type,
    actual_type: type,
    actual_value: Any
) -> str:
    """Format a type mismatch error message."""
    return (
        f"Pipeline type mismatch at step {step_num} ({step_name}): "
        f"expected {_type_name(expected_type)}, "
        f"got {_type_name(actual_type)} (value: {repr(actual_value)[:50]})"
    )


def _type_name(t: type) -> str:
    """Get a readable name for a type."""
    if hasattr(t, '__name__'):
        return t.__name__
    return str(t)
```

```python
# railway/core/pipeline.py を更新
"""Pipeline function with strict mode support."""
from typing import Any, Callable, TypeVar
from loguru import logger
from railway.core.type_check import (
    check_type_compatibility,
    get_function_input_type,
    get_function_output_type,
    format_type_error,
)

T = TypeVar('T')


def pipeline(
    initial_value: Any,
    *steps: Callable[[Any], Any],
    strict: bool = False,
) -> Any:
    """
    Execute a pipeline of functions.

    Args:
        initial_value: The starting value for the pipeline.
        *steps: Functions to execute in sequence.
        strict: Enable runtime type checking between steps.

    Returns:
        The final result after all steps.

    Raises:
        TypeError: When strict=True and types don't match between steps.
    """
    if not steps:
        return initial_value

    logger.info(f"Pipeline starting with {len(steps)} steps")
    result = initial_value

    for i, step in enumerate(steps, 1):
        step_name = getattr(step, '_node_name', step.__name__)

        # Type check before execution (if strict mode)
        if strict:
            expected_type = get_function_input_type(step)
            if expected_type is not None:
                if not check_type_compatibility(result, expected_type):
                    raise TypeError(
                        format_type_error(
                            step_num=i,
                            step_name=step_name,
                            expected_type=expected_type,
                            actual_type=type(result),
                            actual_value=result,
                        )
                    )

        logger.info(f"Pipeline step {i}/{len(steps)}: {step_name}")

        try:
            result = step(result)
        except Exception as e:
            remaining = len(steps) - i
            if remaining > 0:
                logger.info(f"Skipping {remaining} remaining steps due to error")
            raise

    logger.info("Pipeline completed successfully")
    return result
```

```bash
# 実行して成功を確認
pytest tests/unit/core/test_pipeline_strict.py -v
# Expected: PASSED
```

---

## 完了条件

- [ ] `pipeline(..., strict=True)` で型チェックが有効になる
- [ ] 型ミスマッチ時にTypeErrorが発生する
- [ ] 初期値の型もチェックされる
- [ ] サブタイプは許容される
- [ ] Optional/Union型が正しく処理される
- [ ] エラーメッセージにステップ番号が含まれる
- [ ] エラーメッセージに期待型と実際の型が含まれる
- [ ] strict=False（デフォルト）では型チェックしない
- [ ] テストカバレッジ90%以上

---

## 次のIssue

- #17: 非同期ノード基本サポート
