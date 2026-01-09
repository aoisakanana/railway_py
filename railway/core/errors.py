"""Custom error types for Railway Framework."""

from typing import Any, Dict, Optional


class RailwayError(Exception):
    """Base exception for all Railway Framework errors."""

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        hint: Optional[str] = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.hint = hint
        self.retryable = retryable

    def full_message(self) -> str:
        """Get full formatted error message."""
        parts = []

        if self.code:
            parts.append(f"[{self.code}]")

        parts.append(self.message)

        if self.hint:
            parts.append(f"\nヒント: {self.hint}")

        return " ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "hint": self.hint,
            "retryable": self.retryable,
        }


class ConfigurationError(RailwayError):
    """Error related to configuration issues."""

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        hint: Optional[str] = None,
        config_key: Optional[str] = None,
    ):
        if hint is None:
            hint = "設定ファイル（config/*.yaml）または環境変数を確認してください。"

        super().__init__(message, code=code, hint=hint, retryable=False)
        self.config_key = config_key

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["config_key"] = self.config_key
        return d


class NodeError(RailwayError):
    """Error that occurred in a node."""

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        hint: Optional[str] = None,
        retryable: bool = True,
        node_name: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message, code=code, hint=hint, retryable=retryable)
        self.node_name = node_name
        self.original_error = original_error

    def full_message(self) -> str:
        """Get full formatted error message with node info."""
        parts = []

        if self.code:
            parts.append(f"[{self.code}]")

        if self.node_name:
            parts.append(f"[{self.node_name}]")

        parts.append(self.message)

        if self.hint:
            parts.append(f"\nヒント: {self.hint}")

        return " ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["node_name"] = self.node_name
        if self.original_error:
            d["original_error"] = {
                "type": type(self.original_error).__name__,
                "message": str(self.original_error),
            }
        return d


class PipelineError(RailwayError):
    """Error that occurred in a pipeline."""

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        hint: Optional[str] = None,
        step_number: Optional[int] = None,
        step_name: Optional[str] = None,
        total_steps: Optional[int] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message, code=code, hint=hint, retryable=False)
        self.step_number = step_number
        self.step_name = step_name
        self.total_steps = total_steps
        self.original_error = original_error

    @property
    def remaining_steps(self) -> Optional[int]:
        """Get number of remaining steps after failure."""
        if self.step_number is not None and self.total_steps is not None:
            return self.total_steps - self.step_number
        return None

    def full_message(self) -> str:
        """Get full formatted error message with pipeline info."""
        parts = []

        if self.code:
            parts.append(f"[{self.code}]")

        if self.step_name and self.step_number:
            parts.append(f"Step {self.step_number} ({self.step_name}):")

        parts.append(self.message)

        if self.remaining_steps is not None and self.remaining_steps > 0:
            parts.append(f"(残り {self.remaining_steps} ステップはスキップされました)")

        if self.hint:
            parts.append(f"\nヒント: {self.hint}")

        return " ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["step_number"] = self.step_number
        d["step_name"] = self.step_name
        d["total_steps"] = self.total_steps
        d["remaining_steps"] = self.remaining_steps
        return d


class NetworkError(RailwayError):
    """Error related to network operations."""

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        hint: Optional[str] = None,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
    ):
        if hint is None:
            hint = "ネットワーク接続を確認してください。APIエンドポイントが正しいか確認してください。"

        super().__init__(message, code=code, hint=hint, retryable=True)
        self.url = url
        self.status_code = status_code

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["url"] = self.url
        d["status_code"] = self.status_code
        return d


class ValidationError(RailwayError):
    """Error related to data validation."""

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        hint: Optional[str] = None,
        field: Optional[str] = None,
        value: Any = None,
    ):
        if hint is None:
            hint = "入力データの形式を確認してください。"

        super().__init__(message, code=code, hint=hint, retryable=False)
        self.field = field
        self.value = value

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["field"] = self.field
        d["value"] = repr(self.value) if self.value is not None else None
        return d


class RailwayTimeoutError(RailwayError):
    """Error when operation times out."""

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        hint: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        if hint is None:
            hint = "タイムアウト値を増やすか、処理を分割してください。"

        super().__init__(message, code=code, hint=hint, retryable=True)
        self.timeout_seconds = timeout_seconds

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["timeout_seconds"] = self.timeout_seconds
        return d
