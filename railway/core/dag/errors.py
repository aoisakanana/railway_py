"""DAG ランナー関連のエラー定義（Issue #46）。

v0.12.3 で導入された型安全性強制のためのカスタム例外。
"""
from __future__ import annotations


class ExitNodeTypeError(TypeError):
    """終端ノードが ExitContract を返さなかった場合のエラー。

    Attributes:
        node_name: 終端ノード名
        actual_type: 実際に返された型名
    """

    def __init__(self, node_name: str, actual_type: str) -> None:
        self.node_name = node_name
        self.actual_type = actual_type
        message = (
            f"終端ノード '{node_name}' は ExitContract を返す必要があります。"
            f" 戻り値の型: {actual_type}"
            f"\n\nヒント: `railway sync transition` を実行してスケルトンを生成してください。"
        )
        super().__init__(message)


class LegacyExitFormatError(ValueError):
    """レガシー exit 形式が使用された場合のエラー。

    Attributes:
        legacy_format: 使用されたレガシー形式
    """

    def __init__(self, legacy_format: str) -> None:
        self.legacy_format = legacy_format
        message = (
            f"レガシー exit 形式 '{legacy_format}' は v0.12.3 で廃止されました。"
            " 終端ノード関数を使用してください。"
            "\n\nヒント: `railway update` を実行してマイグレーションしてください。"
        )
        super().__init__(message)
