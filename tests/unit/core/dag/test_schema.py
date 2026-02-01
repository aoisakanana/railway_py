"""Tests for YAML schema validation.

Issue #71: YAML スキーマの追加
- 新形式 YAML は検証をパス
- 旧形式 YAML は legacy として検出
- 無効な YAML はエラーを返す
"""

import pytest

from railway.core.dag.schema import (
    SchemaValidation,
    validate_yaml_schema,
)


class TestYamlSchema:
    """YAML スキーマ検証のテスト。"""

    def test_valid_v1_yaml(self):
        """新形式 YAML は検証をパス。"""
        data = {
            "version": "1.0",
            "entrypoint": "greeting",
            "nodes": {"start": {"description": "開始"}},
            "start": "start",
            "transitions": {},
        }
        result = validate_yaml_schema(data)
        assert result.is_valid
        assert result.schema_version == "v1"

    def test_legacy_yaml_detected(self):
        """旧形式 YAML は legacy として検出。"""
        data = {
            "version": "1.0",
            "entrypoint": "greeting",
            "nodes": {},
            "exits": {"success": {"code": 0}},
            "start": "start",
            "transitions": {},
        }
        result = validate_yaml_schema(data)
        assert result.schema_version == "legacy"

    def test_invalid_yaml_returns_errors(self):
        """無効な YAML はエラーを返す。"""
        data = {"version": "1.0"}  # 必須フィールド不足
        result = validate_yaml_schema(data)
        assert not result.is_valid
        assert len(result.errors) > 0


class TestSchemaValidation:
    """SchemaValidation のテスト。"""

    def test_schema_validation_is_immutable(self):
        """SchemaValidation は immutable。"""
        result = SchemaValidation(
            is_valid=True,
            errors=(),
            schema_version="v1",
        )
        # NamedTuple は immutable
        with pytest.raises(AttributeError):
            result.is_valid = False  # type: ignore


class TestSchemaVersionDetection:
    """スキーマバージョン検出のテスト。"""

    def test_exits_section_means_legacy(self):
        """exits セクションがあれば legacy。"""
        data = {
            "version": "1.0",
            "entrypoint": "test",
            "nodes": {},
            "exits": {"success": {"code": 0}},
            "start": "start",
            "transitions": {},
        }
        result = validate_yaml_schema(data)
        assert result.schema_version == "legacy"

    def test_no_exits_means_v1(self):
        """exits セクションがなければ v1。"""
        data = {
            "version": "1.0",
            "entrypoint": "test",
            "nodes": {"start": {}},
            "start": "start",
            "transitions": {},
        }
        result = validate_yaml_schema(data)
        assert result.schema_version == "v1"
