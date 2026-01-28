"""Tests for YAML structure conversion utilities."""

import pytest
from railway.migrations.yaml_converter import (
    convert_yaml_structure,
    _extract_exit_mappings,
    _infer_new_exit_path,
    _extract_detail_name,
    _convert_transition_target,
    _build_exit_tree,
    ConversionResult,
    ExitMapping,
)


class TestInferNewExitPath:
    """exit パス推論テスト。"""

    @pytest.mark.parametrize(
        ("old_name", "exit_code", "expected"),
        [
            ("green_success", 0, "exit.success.done"),
            ("green_resolved", 0, "exit.success.resolved"),
            ("green_done", 0, "exit.success.done"),
            ("red_timeout", 1, "exit.failure.timeout"),
            ("red_error", 1, "exit.failure.error"),
            ("yellow_warning", 2, "exit.warning.warning"),
            ("unknown", 0, "exit.success.unknown"),
            ("unknown", 1, "exit.failure.unknown"),
        ],
    )
    def test_infers_correct_path(
        self,
        old_name: str,
        exit_code: int,
        expected: str,
    ) -> None:
        """旧 exit 名から正しいパスを推論。"""
        result = _infer_new_exit_path(old_name, exit_code)
        assert result == expected


class TestExtractDetailName:
    """詳細名抽出テスト。"""

    @pytest.mark.parametrize(
        ("old_name", "category", "expected"),
        [
            ("green_success", "success", "done"),  # success は冗長
            ("green_resolved", "success", "resolved"),
            ("red_timeout", "failure", "timeout"),
            ("red_ssh_error", "failure", "ssh_error"),
            ("yellow_low_disk", "warning", "low_disk"),
        ],
    )
    def test_extracts_detail_name(
        self,
        old_name: str,
        category: str,
        expected: str,
    ) -> None:
        """詳細名を正しく抽出。"""
        result = _extract_detail_name(old_name, category)
        assert result == expected


class TestExtractExitMappings:
    """exit マッピング抽出テスト。"""

    def test_extracts_mappings_from_exits(self) -> None:
        """exits セクションからマッピングを抽出。"""
        exits = {
            "green_success": {"code": 0, "description": "正常終了"},
            "red_timeout": {"code": 1, "description": "タイムアウト"},
        }

        result = _extract_exit_mappings(exits)

        assert len(result) == 2
        assert any(m.old_name == "green_success" for m in result)
        assert any(m.new_path == "exit.success.done" for m in result)


class TestConvertTransitionTarget:
    """遷移先変換テスト。"""

    def test_converts_exit_target(self) -> None:
        """exit:: プレフィックスを新形式に変換。"""
        name_to_path = {"green_success": "exit.success.done"}

        result = _convert_transition_target("exit::green_success", name_to_path)

        assert result == "exit.success.done"

    def test_keeps_node_target_unchanged(self) -> None:
        """ノードへの遷移はそのまま。"""
        result = _convert_transition_target("process", {})

        assert result == "process"


class TestBuildExitTree:
    """exit ツリー構築テスト。"""

    def test_builds_nested_structure(self) -> None:
        """ネストした構造を構築。"""
        mappings = (
            ExitMapping("green_success", "exit.success.done", 0, "正常終了"),
            ExitMapping("red_timeout", "exit.failure.timeout", 1, "タイムアウト"),
        )

        result = _build_exit_tree(mappings)

        assert "success" in result
        assert "done" in result["success"]
        assert result["success"]["done"]["description"] == "正常終了"
        assert "failure" in result
        assert "timeout" in result["failure"]


class TestConvertYamlStructure:
    """YAML 構造変換の統合テスト。"""

    def test_converts_complete_structure(self) -> None:
        """完全な構造を変換。"""
        old_yaml = {
            "version": "1.0",
            "entrypoint": "test",
            "nodes": {
                "process": {
                    "module": "nodes.process",
                    "function": "process",
                    "description": "処理",
                },
            },
            "exits": {
                "green_success": {"code": 0, "description": "正常終了"},
                "red_timeout": {"code": 1, "description": "タイムアウト"},
            },
            "start": "process",
            "transitions": {
                "process": {
                    "success::done": "exit::green_success",
                    "failure::timeout": "exit::red_timeout",
                },
            },
        }

        result = convert_yaml_structure(old_yaml)

        assert result.success
        assert "exits" not in result.data
        assert "exit" in result.data["nodes"]
        assert result.data["transitions"]["process"]["success::done"] == "exit.success.done"

    def test_no_exits_section_returns_unchanged(self) -> None:
        """exits セクションがなければ変更なし。"""
        yaml_data = {
            "version": "1.0",
            "nodes": {"start": {"description": "開始"}},
        }

        result = convert_yaml_structure(yaml_data)

        assert result.success
        assert result.data == yaml_data

    def test_result_is_immutable(self) -> None:
        """結果はイミュータブル。"""
        result = ConversionResult.ok({"test": 1})

        with pytest.raises(AttributeError):
            result.success = False


class TestConversionResultFactory:
    """ConversionResult ファクトリテスト。"""

    def test_ok_creates_success_result(self) -> None:
        """ok() は成功結果を作成。"""
        result = ConversionResult.ok({"key": "value"})

        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None

    def test_fail_creates_failure_result(self) -> None:
        """fail() は失敗結果を作成。"""
        result = ConversionResult.fail("エラーメッセージ")

        assert result.success is False
        assert result.data is None
        assert result.error == "エラーメッセージ"

    def test_ok_with_warnings(self) -> None:
        """ok() は警告付きで作成可能。"""
        result = ConversionResult.ok(
            {"key": "value"},
            warnings=("警告1", "警告2"),
        )

        assert result.success is True
        assert len(result.warnings) == 2
