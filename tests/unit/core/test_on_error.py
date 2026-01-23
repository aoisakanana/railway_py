"""Tests for on_error callback in typed_pipeline.

This module tests the error handling callback functionality
that allows pipeline-level error recovery and control.
"""

import traceback

import pytest

from railway import node, typed_pipeline, Contract


class TestOnErrorCallback:
    """on_error コールバックのテスト"""

    def test_no_on_error_propagates_exception(self) -> None:
        """on_error 未指定時は例外がそのまま伝播する"""

        @node
        def fail() -> str:
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            typed_pipeline(fail)

    def test_on_error_can_return_fallback(self) -> None:
        """on_error でフォールバック値を返せる"""

        class Result(Contract):
            value: int

        @node
        def fail() -> Result:
            raise ValueError("test error")

        @node(inputs={"data": Result})
        def process(data: Result) -> Result:
            return Result(value=data.value * 2)

        def handle(error: Exception, step: str) -> Result:
            return Result(value=10)  # フォールバック

        result = typed_pipeline(fail, process, on_error=handle)
        assert result.value == 20  # 10 * 2

    def test_on_error_can_reraise(self) -> None:
        """on_error で再送出できる"""

        @node
        def fail() -> str:
            raise ValueError("original")

        def handle(error: Exception, step: str) -> str:
            raise  # 再送出

        with pytest.raises(ValueError, match="original"):
            typed_pipeline(fail, on_error=handle)

    def test_on_error_receives_step_name(self) -> None:
        """on_error にステップ名が渡される"""
        received_step = None

        class Result(Contract):
            value: str

        @node
        def my_failing_step() -> Result:
            raise ValueError()

        def handle(error: Exception, step: str) -> Result:
            nonlocal received_step
            received_step = step
            return Result(value="fallback")

        typed_pipeline(my_failing_step, on_error=handle)
        assert received_step == "my_failing_step"

    def test_on_error_match_specific_exception(self) -> None:
        """on_error で例外タイプごとに処理を分岐できる"""

        class Result(Contract):
            value: str

        @node
        def fail_connection() -> Result:
            raise ConnectionError("network")

        @node
        def fail_validation() -> Result:
            raise ValueError("invalid")

        def handle(error: Exception, step: str) -> Result:
            match error:
                case ConnectionError():
                    return Result(value="cached_data")
                case _:
                    raise

        # ConnectionError → フォールバック
        result = typed_pipeline(fail_connection, on_error=handle)
        assert result.value == "cached_data"

        # ValueError → 再送出
        with pytest.raises(ValueError):
            typed_pipeline(fail_validation, on_error=handle)

    def test_on_error_preserves_stack_trace(self) -> None:
        """on_error で再送出時にスタックトレースが保持される"""

        @node
        def deep_fail() -> str:
            def inner() -> None:
                raise ValueError("deep error")

            inner()
            return "never"

        def handle(error: Exception, step: str) -> str:
            raise

        with pytest.raises(ValueError) as exc_info:
            typed_pipeline(deep_fail, on_error=handle)

        # スタックトレースに inner が含まれる
        tb_str = "".join(traceback.format_tb(exc_info.value.__traceback__))
        assert "inner" in tb_str

    def test_on_error_with_params(self) -> None:
        """on_error が params 付きパイプラインでも動作する"""

        class Params(Contract):
            user_id: int

        class Result(Contract):
            value: str

        @node(inputs={"p": Params})
        def fail_with_params(p: Params) -> Result:
            raise ValueError(f"failed for user {p.user_id}")

        def handle(error: Exception, step: str) -> Result:
            return Result(value="fallback")

        result = typed_pipeline(
            fail_with_params, params=Params(user_id=123), on_error=handle
        )
        assert result.value == "fallback"

    def test_on_error_at_specific_step(self) -> None:
        """複数ステップの途中で失敗した場合もハンドリングできる"""

        class Step1Result(Contract):
            data: str

        class Step2Result(Contract):
            processed: str

        @node
        def step1() -> Step1Result:
            return Step1Result(data="initial")

        @node(inputs={"s1": Step1Result})
        def step2(s1: Step1Result) -> Step2Result:
            raise ConnectionError("network error at step2")

        def handle(error: Exception, step: str) -> Step2Result:
            if step == "step2" and isinstance(error, ConnectionError):
                return Step2Result(processed="recovered")
            raise

        result = typed_pipeline(step1, step2, on_error=handle)
        assert result.processed == "recovered"

    def test_on_error_none_is_default(self) -> None:
        """on_error=None はデフォルト動作（例外伝播）と同じ"""

        @node
        def fail() -> str:
            raise ValueError("test")

        with pytest.raises(ValueError, match="test"):
            typed_pipeline(fail, on_error=None)
