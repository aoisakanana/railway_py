"""Custom error types for Railway Framework."""

from dataclasses import dataclass
from typing import Any


class RailwayError(Exception):
    """Base exception for all Railway Framework errors."""

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        hint: str | None = None,
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

    def to_dict(self) -> dict[str, Any]:
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
        code: str | None = None,
        hint: str | None = None,
        config_key: str | None = None,
    ):
        if hint is None:
            hint = "設定ファイル（config/*.yaml）または環境変数を確認してください。"

        super().__init__(message, code=code, hint=hint, retryable=False)
        self.config_key = config_key

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["config_key"] = self.config_key
        return d


class NodeError(RailwayError):
    """Error that occurred in a node."""

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        hint: str | None = None,
        retryable: bool = True,
        node_name: str | None = None,
        original_error: Exception | None = None,
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

    def to_dict(self) -> dict[str, Any]:
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
        code: str | None = None,
        hint: str | None = None,
        step_number: int | None = None,
        step_name: str | None = None,
        total_steps: int | None = None,
        original_error: Exception | None = None,
    ):
        super().__init__(message, code=code, hint=hint, retryable=False)
        self.step_number = step_number
        self.step_name = step_name
        self.total_steps = total_steps
        self.original_error = original_error

    @property
    def remaining_steps(self) -> int | None:
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

    def to_dict(self) -> dict[str, Any]:
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
        code: str | None = None,
        hint: str | None = None,
        url: str | None = None,
        status_code: int | None = None,
    ):
        if hint is None:
            hint = "ネットワーク接続を確認してください。APIエンドポイントが正しいか確認してください。"

        super().__init__(message, code=code, hint=hint, retryable=True)
        self.url = url
        self.status_code = status_code

    def to_dict(self) -> dict[str, Any]:
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
        code: str | None = None,
        hint: str | None = None,
        field: str | None = None,
        value: Any = None,
    ):
        if hint is None:
            hint = "入力データの形式を確認してください。"

        super().__init__(message, code=code, hint=hint, retryable=False)
        self.field = field
        self.value = value

    def to_dict(self) -> dict[str, Any]:
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
        code: str | None = None,
        hint: str | None = None,
        timeout_seconds: float | None = None,
    ):
        if hint is None:
            hint = "タイムアウト値を増やすか、処理を分割してください。"

        super().__init__(message, code=code, hint=hint, retryable=True)
        self.timeout_seconds = timeout_seconds

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["timeout_seconds"] = self.timeout_seconds
        return d


# =============================================================================
# Error Catalog (Pure Functions for User-Friendly Messages)
# =============================================================================


@dataclass(frozen=True)
class ErrorInfo:
    """エラー情報（イミュータブル）。"""

    code: str
    title: str
    message_template: str
    hint_template: str | None = None


# ドキュメントベースURL
DOC_BASE_URL = "https://github.com/your-org/railway-framework/wiki/errors"


# エラーカタログ（イミュータブル）
ERROR_CATALOG: dict[str, ErrorInfo] = {
    "E001": ErrorInfo(
        code="E001",
        title="開始ノードの引数エラー",
        message_template="開始ノード '{node_name}' は引数を受け取る必要があります。",
        hint_template="def {node_name}(ctx: Context | None = None) -> tuple[Context, Outcome]:",
    ),
    "E002": ErrorInfo(
        code="E002",
        title="モジュールが見つかりません",
        message_template="モジュール '{module}' が見つかりません。",
        hint_template="YAML の module パスを確認してください: {expected_path}",
    ),
    "E003": ErrorInfo(
        code="E003",
        title="無効な識別子",
        message_template="'{identifier}' は Python の識別子として使用できません。",
        hint_template="'{suggestion}' に変更してください。",
    ),
    "E004": ErrorInfo(
        code="E004",
        title="終端ノードの戻り値エラー",
        message_template="終端ノード '{node_name}' は ExitContract を返す必要があります。",
        hint_template="return {class_name}Result(...) のように ExitContract サブクラスを返してください。",
    ),
}


def format_error(code: str, **kwargs: Any) -> str:
    """エラーメッセージをフォーマット（純粋関数）。

    Args:
        code: エラーコード
        **kwargs: テンプレート変数

    Returns:
        フォーマットされたエラーメッセージ
    """
    info = ERROR_CATALOG.get(code)
    if info is None:
        return f"Unknown error: {code}"

    lines = [
        f"Error [{info.code}]: {info.title}",
        "",
        info.message_template.format(**kwargs),
    ]

    if info.hint_template:
        try:
            hint = info.hint_template.format(**kwargs)
            lines.extend([
                "",
                "Hint:",
                f"  {hint}",
            ])
        except KeyError:
            # テンプレート変数が不足している場合はヒントをスキップ
            pass

    # ドキュメントリンク
    lines.extend([
        "",
        f"詳細: {DOC_BASE_URL}/{code}",
    ])

    return "\n".join(lines)
