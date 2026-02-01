"""YAML schema validation for transition graphs.

純粋関数によるスキーマ検証。
jsonschema パッケージはオプション依存。
"""

from typing import Any, NamedTuple


class SchemaValidation(NamedTuple):
    """スキーマ検証結果（イミュータブル）。"""

    is_valid: bool
    errors: tuple[str, ...]
    schema_version: str


# 新形式（v0.13.0+）の必須フィールド
V1_REQUIRED_FIELDS = frozenset({"version", "entrypoint", "nodes", "start", "transitions"})

# 旧形式の識別フィールド
LEGACY_IDENTIFIER = "exits"


def validate_yaml_schema(data: dict[str, Any]) -> SchemaValidation:
    """YAML データをスキーマで検証（純粋関数）。

    Args:
        data: パース済み YAML データ

    Returns:
        SchemaValidation: 検証結果
    """
    # スキーマバージョン判定
    schema_version = _detect_schema_version(data)

    # バリデーション
    errors = _validate_required_fields(data, schema_version)

    return SchemaValidation(
        is_valid=len(errors) == 0,
        errors=tuple(errors),
        schema_version=schema_version,
    )


def _detect_schema_version(data: dict[str, Any]) -> str:
    """スキーマバージョンを検出（純粋関数）。

    Args:
        data: YAML データ

    Returns:
        "v1" または "legacy"
    """
    if LEGACY_IDENTIFIER in data:
        return "legacy"
    return "v1"


def _validate_required_fields(data: dict[str, Any], schema_version: str) -> list[str]:
    """必須フィールドを検証（純粋関数）。

    Args:
        data: YAML データ
        schema_version: スキーマバージョン

    Returns:
        エラーメッセージのリスト
    """
    errors: list[str] = []

    if schema_version == "v1":
        missing = V1_REQUIRED_FIELDS - set(data.keys())
        for field in sorted(missing):
            errors.append(f"必須フィールド '{field}' がありません")
    else:
        # legacy 形式
        legacy_required = frozenset({"version", "entrypoint", "nodes", "exits", "start", "transitions"})
        missing = legacy_required - set(data.keys())
        for field in sorted(missing):
            errors.append(f"必須フィールド '{field}' がありません（レガシー形式）")

    return errors
