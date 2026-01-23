"""Tests for RetryPolicy functionality.

This module tests the RetryPolicy class and its integration
with the @node decorator for flexible retry configuration.
"""

import time

import pytest

from railway import node
from railway.core.retry import RetryPolicy


class TestRetryPolicy:
    """RetryPolicy クラスのテスト"""

    def test_should_retry_on_specified_exception(self) -> None:
        """指定した例外でリトライする"""
        policy = RetryPolicy(max_retries=3, retry_on=(ConnectionError,))
        assert policy.should_retry(ConnectionError(), attempt=1) is True
        assert policy.should_retry(ValueError(), attempt=1) is False

    def test_should_not_retry_after_max_retries(self) -> None:
        """最大リトライ回数を超えたらリトライしない"""
        policy = RetryPolicy(max_retries=3)
        assert policy.should_retry(Exception(), attempt=3) is False
        assert policy.should_retry(Exception(), attempt=4) is False

    def test_should_retry_within_max_retries(self) -> None:
        """最大リトライ回数以内ならリトライする"""
        policy = RetryPolicy(max_retries=3)
        assert policy.should_retry(Exception(), attempt=1) is True
        assert policy.should_retry(Exception(), attempt=2) is True

    def test_fixed_backoff(self) -> None:
        """固定バックオフの遅延計算"""
        policy = RetryPolicy(backoff="fixed", base_delay=2.0)
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 2.0
        assert policy.get_delay(3) == 2.0

    def test_linear_backoff(self) -> None:
        """線形バックオフの遅延計算"""
        policy = RetryPolicy(backoff="linear", base_delay=1.0)
        assert policy.get_delay(1) == 1.0
        assert policy.get_delay(2) == 2.0
        assert policy.get_delay(3) == 3.0

    def test_exponential_backoff(self) -> None:
        """指数バックオフの遅延計算"""
        policy = RetryPolicy(backoff="exponential", base_delay=1.0)
        assert policy.get_delay(1) == 1.0
        assert policy.get_delay(2) == 2.0
        assert policy.get_delay(3) == 4.0
        assert policy.get_delay(4) == 8.0

    def test_max_delay_cap(self) -> None:
        """最大遅延時間の上限"""
        policy = RetryPolicy(backoff="exponential", base_delay=10.0, max_delay=30.0)
        assert policy.get_delay(1) == 10.0
        assert policy.get_delay(2) == 20.0
        assert policy.get_delay(3) == 30.0  # 40 だが上限で30
        assert policy.get_delay(10) == 30.0  # 上限でキャップ

    def test_immutable(self) -> None:
        """RetryPolicy はイミュータブル"""
        policy = RetryPolicy(max_retries=3)
        with pytest.raises(AttributeError):
            policy.max_retries = 5  # type: ignore[misc]


class TestNodeWithRetryPolicy:
    """@node(retry_policy=...) のテスト"""

    def test_retries_on_specified_exception(self) -> None:
        """RetryPolicy で指定した例外のみリトライ"""
        attempts: list[int] = []

        @node(retry_policy=RetryPolicy(max_retries=3, retry_on=(ConnectionError,), base_delay=0.01))
        def flaky() -> str:
            attempts.append(1)
            if len(attempts) < 3:
                raise ConnectionError()
            return "success"

        result = flaky()
        assert result == "success"
        assert len(attempts) == 3

    def test_no_retry_on_unspecified_exception(self) -> None:
        """指定外の例外はリトライしない"""
        attempts: list[int] = []

        @node(retry_policy=RetryPolicy(max_retries=3, retry_on=(ConnectionError,)))
        def fail() -> str:
            attempts.append(1)
            raise ValueError("not retryable")

        with pytest.raises(ValueError):
            fail()
        assert len(attempts) == 1

    def test_backward_compatible_retries_param(self) -> None:
        """後方互換: retries パラメータも動作する（既存のRetry）"""
        from railway.core.decorators import Retry

        attempts: list[int] = []

        @node(retry=Retry(max_attempts=3, min_wait=0.01, max_wait=0.1))
        def flaky() -> str:
            attempts.append(1)
            if len(attempts) < 3:
                raise ValueError()
            return "success"

        result = flaky()
        assert result == "success"
        assert len(attempts) == 3

    def test_shorthand_retries_with_retry_on(self) -> None:
        """ショートハンド: retries + retry_on の組み合わせ"""
        attempts: list[int] = []

        @node(retries=3, retry_on=(ConnectionError,), retry_delay=0.01)
        def flaky() -> str:
            attempts.append(1)
            if len(attempts) < 3:
                raise ConnectionError()
            return "success"

        result = flaky()
        assert result == "success"
        assert len(attempts) == 3

    def test_shorthand_does_not_retry_unspecified(self) -> None:
        """ショートハンド: retry_on に含まれない例外はリトライしない"""
        attempts: list[int] = []

        @node(retries=3, retry_on=(ConnectionError,))
        def fail() -> str:
            attempts.append(1)
            raise ValueError("not retryable")

        with pytest.raises(ValueError):
            fail()
        assert len(attempts) == 1

    def test_exponential_backoff_timing(self) -> None:
        """指数バックオフで遅延が増加する"""
        start_times: list[float] = []

        @node(
            retry_policy=RetryPolicy(
                max_retries=3,
                backoff="exponential",
                base_delay=0.05,
            )
        )
        def timed_flaky() -> str:
            start_times.append(time.time())
            if len(start_times) < 3:
                raise ConnectionError()
            return "success"

        timed_flaky()

        # 2回目は約0.05秒後、3回目は約0.1秒後
        assert len(start_times) == 3
        delay1 = start_times[1] - start_times[0]
        delay2 = start_times[2] - start_times[1]
        assert delay1 >= 0.04  # 0.05 - margin
        assert delay2 >= 0.08  # 0.10 - margin


class TestRetryPolicyDefaults:
    """RetryPolicy のデフォルト値テスト"""

    def test_default_values(self) -> None:
        """デフォルト値が正しい"""
        policy = RetryPolicy()
        assert policy.max_retries == 3
        assert policy.retry_on == (Exception,)
        assert policy.backoff == "fixed"
        assert policy.base_delay == 1.0
        assert policy.max_delay == 60.0

    def test_custom_values(self) -> None:
        """カスタム値が設定できる"""
        policy = RetryPolicy(
            max_retries=5,
            retry_on=(ConnectionError, TimeoutError),
            backoff="exponential",
            base_delay=0.5,
            max_delay=30.0,
        )
        assert policy.max_retries == 5
        assert policy.retry_on == (ConnectionError, TimeoutError)
        assert policy.backoff == "exponential"
        assert policy.base_delay == 0.5
        assert policy.max_delay == 30.0
