"""Retry policy for Railway Framework.

This module provides the RetryPolicy class for flexible retry configuration
with support for exception filtering and backoff strategies.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    """リトライポリシー（イミュータブル）

    ノードの実行失敗時のリトライ戦略を定義します。

    Attributes:
        max_retries: 最大リトライ回数
        retry_on: リトライ対象の例外タプル
        backoff: バックオフ戦略 ("fixed", "linear", "exponential")
        base_delay: 基本遅延時間（秒）
        max_delay: 最大遅延時間（秒）

    Example:
        # 基本的な使用
        @node(retry_policy=RetryPolicy(
            max_retries=3,
            retry_on=(ConnectionError, TimeoutError),
        ))
        def fetch_data():
            return requests.get(API_URL).json()

        # 指数バックオフ
        @node(retry_policy=RetryPolicy(
            max_retries=5,
            backoff="exponential",
            base_delay=1.0,
            max_delay=30.0,
        ))
        def fetch_with_backoff():
            return requests.get(API_URL).json()
    """

    max_retries: int = 3
    retry_on: tuple[type[Exception], ...] = (Exception,)
    backoff: str = "fixed"  # "fixed", "linear", "exponential"
    base_delay: float = 1.0
    max_delay: float = 60.0

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """リトライすべきか判定する

        Args:
            exception: 発生した例外
            attempt: 現在の試行回数（1から開始）

        Returns:
            リトライすべきならTrue
        """
        if attempt >= self.max_retries:
            return False
        return isinstance(exception, self.retry_on)

    def get_delay(self, attempt: int) -> float:
        """次のリトライまでの遅延時間を計算する

        Args:
            attempt: 現在の試行回数（1から開始）

        Returns:
            遅延時間（秒）
        """
        match self.backoff:
            case "fixed":
                delay = self.base_delay
            case "linear":
                delay = self.base_delay * attempt
            case "exponential":
                delay = self.base_delay * (2 ** (attempt - 1))
            case _:
                delay = self.base_delay
        return min(delay, self.max_delay)
