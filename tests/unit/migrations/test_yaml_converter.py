"""Tests for YAML structure conversion utilities."""

import copy

import pytest

from railway.migrations.yaml_converter import (
    ConversionResult,
    ExitMapping,
    TransitionExtractionResult,
    _build_exit_tree,
    _convert_nested_exits,
    _convert_transition_target,
    _detect_exits_format,
    _extract_exit_mappings,
    _extract_detail_name,
    _extract_transitions_from_nodes,
    _infer_new_exit_path,
    convert_yaml_structure,
)


class TestDetectExitsFormat:
    """exits 形式検出のテスト。"""

    def test_detect_legacy_flat_with_code(self) -> None:
        """code キーを持つフラット形式を検出する。"""
        exits = {
            "green_success": {"code": 0, "description": "正常終了"},
            "red_timeout": {"code": 1, "description": "タイムアウト"},
        }
        result = _detect_exits_format(exits)
        assert result.format == "legacy_flat"

    def test_detect_legacy_flat_with_description_only(self) -> None:
        """description のみのフラット形式を検出する。"""
        exits = {"success": {"description": "正常終了"}}
        result = _detect_exits_format(exits)
        assert result.format == "legacy_flat"

    def test_detect_legacy_flat_code_without_description(self) -> None:
        """code のみ（description なし）のフラット形式を検出する。"""
        exits = {"green_success": {"code": 0}}
        result = _detect_exits_format(exits)
        assert result.format == "legacy_flat"

    def test_detect_nested_format(self) -> None:
        """ネスト形式を検出する。"""
        exits = {
            "success": {
                "done": {"description": "正常終了", "exit_code": 0},
            },
            "failure": {
                "error": {"description": "エラー", "exit_code": 1},
            },
        }
        result = _detect_exits_format(exits)
        assert result.format == "nested"

    def test_detect_nested_deep_format(self) -> None:
        """深いネスト形式を検出する。"""
        exits = {
            "failure": {
                "ssh": {
                    "handshake": {"description": "SSHハンドシェイク失敗"},
                    "authentication": {"description": "SSH認証失敗"},
                },
            },
        }
        result = _detect_exits_format(exits)
        assert result.format == "nested"

    def test_detect_nested_single_category(self) -> None:
        """success のみのネスト形式を検出する。"""
        exits = {
            "success": {
                "done": {"description": "正常終了"},
            },
        }
        result = _detect_exits_format(exits)
        assert result.format == "nested"

    def test_detect_unknown_format_string_value(self) -> None:
        """値が文字列の不明な形式を検出する。"""
        exits = {"something": "string_value"}
        result = _detect_exits_format(exits)
        assert result.format == "unknown"

    def test_detect_unknown_format_int_value(self) -> None:
        """値が整数の不明な形式を検出する。"""
        exits = {"success": 0, "failure": 1}
        result = _detect_exits_format(exits)
        assert result.format == "unknown"

    def test_detect_empty_exits(self) -> None:
        """空の exits を処理する。"""
        result = _detect_exits_format({})
        assert result.format == "unknown"

    def test_detect_mixed_format_returns_unknown(self) -> None:
        """フラットとネストが混在する exits は unknown を返す。"""
        exits = {
            "green_success": {"code": 0, "description": "正常終了"},
            "failure": {
                "error": {"description": "エラー終了"},
            },
        }
        result = _detect_exits_format(exits)
        assert result.format == "unknown"

    def test_result_is_immutable(self) -> None:
        """結果がイミュータブルであることを確認する。"""
        result = _detect_exits_format({})
        with pytest.raises(AttributeError):
            result.format = "nested"  # type: ignore[misc]


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


class TestConvertNestedExits:
    """ネスト形式 exits の変換テスト。"""

    def test_convert_simple_nested_exits(self) -> None:
        """基本的なネスト形式を変換する。"""
        exits = {
            "success": {
                "done": {"description": "正常終了", "exit_code": 0},
            },
            "failure": {
                "error": {"description": "エラー終了", "exit_code": 1},
            },
        }
        exit_tree, warnings = _convert_nested_exits(exits)

        assert exit_tree == {
            "success": {
                "done": {"description": "正常終了"},
            },
            "failure": {
                "error": {"description": "エラー終了"},
            },
        }
        assert warnings == ()

    def test_convert_deep_nested_exits(self) -> None:
        """深いネスト形式を変換する。"""
        exits = {
            "failure": {
                "ssh": {
                    "handshake": {"description": "SSHハンドシェイク失敗"},
                    "authentication": {"description": "SSH認証失敗"},
                },
            },
        }
        exit_tree, warnings = _convert_nested_exits(exits)

        assert exit_tree == {
            "failure": {
                "ssh": {
                    "handshake": {"description": "SSHハンドシェイク失敗"},
                    "authentication": {"description": "SSH認証失敗"},
                },
            },
        }

    def test_exit_code_is_stripped(self) -> None:
        """exit_code フィールドは削除される。"""
        exits = {
            "success": {
                "done": {"description": "正常終了", "exit_code": 0},
            },
        }
        exit_tree, _ = _convert_nested_exits(exits)

        assert "exit_code" not in exit_tree["success"]["done"]

    def test_preserves_description(self) -> None:
        """description は保持される。"""
        exits = {
            "success": {
                "done": {"description": "カスタム説明"},
            },
        }
        exit_tree, _ = _convert_nested_exits(exits)

        assert exit_tree["success"]["done"]["description"] == "カスタム説明"

    def test_preserves_extra_fields(self) -> None:
        """description 以外のカスタムフィールドも保持される（exit_code 以外）。"""
        exits = {
            "warning": {
                "low_disk": {
                    "description": "ディスク容量警告",
                    "exit_code": 2,
                    "severity": "medium",
                },
            },
        }
        exit_tree, _ = _convert_nested_exits(exits)

        assert exit_tree["warning"]["low_disk"]["severity"] == "medium"
        assert "exit_code" not in exit_tree["warning"]["low_disk"]

    def test_leaf_node_with_description_and_nested_dict(self) -> None:
        """description とネスト dict を同時に持つノードはリーフとして扱う。"""
        exits = {
            "success": {
                "done": {
                    "description": "正常終了",
                    "metadata": {"key": "value"},
                },
            },
        }
        exit_tree, _ = _convert_nested_exits(exits)

        assert exit_tree["success"]["done"]["description"] == "正常終了"
        assert exit_tree["success"]["done"]["metadata"] == {"key": "value"}

    def test_non_dict_values_are_ignored(self) -> None:
        """dict でない値は無視される。"""
        exits = {
            "success": {
                "done": {"description": "正常終了"},
                "extra_string": "ignored",
            },
        }
        exit_tree, _ = _convert_nested_exits(exits)

        assert "done" in exit_tree["success"]
        assert "extra_string" not in exit_tree["success"]


class TestConvertYamlStructureWithNestedExits:
    """convert_yaml_structure がネスト形式を正しく処理するテスト。"""

    def test_nested_exits_converted_to_nodes_exit(self) -> None:
        """ネスト形式 exits が nodes.exit に変換される。"""
        yaml_data = {
            "version": "1.0",
            "entrypoint": "test",
            "start": "step1",
            "nodes": {
                "step1": {"description": "ステップ1"},
            },
            "transitions": {
                "step1": {
                    "success::done": "exit.success.done",
                },
            },
            "exits": {
                "success": {
                    "done": {"description": "正常終了", "exit_code": 0},
                },
                "failure": {
                    "error": {"description": "エラー終了", "exit_code": 1},
                },
            },
        }
        result = convert_yaml_structure(yaml_data)

        assert result.success is True
        assert "exits" not in result.data
        assert result.data["nodes"]["exit"] == {
            "success": {"done": {"description": "正常終了"}},
            "failure": {"error": {"description": "エラー終了"}},
        }

    def test_nested_preserves_existing_transitions(self) -> None:
        """ネスト形式でも既存のトップレベル transitions はそのまま保持される。"""
        yaml_data = {
            "version": "1.0",
            "entrypoint": "test",
            "start": "step1",
            "nodes": {"step1": {"description": "ステップ1"}},
            "transitions": {
                "step1": {"success::done": "exit.success.done"},
            },
            "exits": {
                "success": {
                    "done": {"description": "正常終了", "exit_code": 0},
                },
            },
        }
        result = convert_yaml_structure(yaml_data)

        assert result.success is True
        assert result.data["transitions"]["step1"]["success::done"] == "exit.success.done"

    def test_legacy_flat_still_works(self) -> None:
        """既存のフラット形式の変換が壊れていないことを確認（回帰テスト）。"""
        yaml_data = {
            "version": "1.0",
            "entrypoint": "test",
            "start": "step1",
            "nodes": {"step1": {"description": "ステップ1"}},
            "transitions": {
                "step1": {"success::done": "exit::green_success"},
            },
            "exits": {
                "green_success": {"code": 0, "description": "正常終了"},
            },
        }
        result = convert_yaml_structure(yaml_data)

        assert result.success is True
        assert "exit" in result.data["nodes"]

    def test_nested_exits_without_nodes_key(self) -> None:
        """yaml_data に nodes キーがない場合でも nodes.exit が生成される。"""
        yaml_data = {
            "version": "1.0",
            "entrypoint": "test",
            "start": "step1",
            "transitions": {
                "step1": {"success::done": "exit.success.done"},
            },
            "exits": {
                "success": {
                    "done": {"description": "正常終了", "exit_code": 0},
                },
            },
        }
        result = convert_yaml_structure(yaml_data)

        assert result.success is True
        assert "nodes" in result.data
        assert "exit" in result.data["nodes"]

    def test_unknown_format_returns_failure(self) -> None:
        """不明な形式は ConversionResult.fail を返す。"""
        yaml_data = {
            "exits": {"something": "not_a_dict"},
            "nodes": {},
        }
        result = convert_yaml_structure(yaml_data)

        assert result.success is False
        assert "未知" in result.error

    def test_original_dict_not_modified(self) -> None:
        """convert_yaml_structure が元の dict を変更しないことを確認。"""
        yaml_data = {
            "version": "1.0",
            "entrypoint": "test",
            "start": "step1",
            "nodes": {"step1": {"description": "ステップ1"}},
            "transitions": {
                "step1": {"success::done": "exit.success.done"},
            },
            "exits": {
                "success": {
                    "done": {"description": "正常終了", "exit_code": 0},
                },
            },
        }
        original = copy.deepcopy(yaml_data)
        convert_yaml_structure(yaml_data)

        assert yaml_data == original, "元の dict が変更された"


class TestExtractTransitionsFromNodes:
    """nodes 内 transitions の抽出テスト。"""

    def test_extract_nested_transitions(self) -> None:
        """nodes 内の transitions をトップレベルに抽出する。"""
        nodes = {
            "step1": {
                "description": "ステップ1",
                "transitions": {
                    "success::done": "step2",
                    "failure::error": "exit.failure.error",
                },
            },
            "step2": {
                "description": "ステップ2",
                "transitions": {
                    "success::done": "exit.success.done",
                },
            },
        }
        result = _extract_transitions_from_nodes(nodes)

        assert result.extracted is True
        assert result.transitions == {
            "step1": {
                "success::done": "step2",
                "failure::error": "exit.failure.error",
            },
            "step2": {
                "success::done": "exit.success.done",
            },
        }

    def test_nodes_without_transitions_unchanged(self) -> None:
        """transitions を持たない nodes はそのまま返す。"""
        nodes = {
            "step1": {"description": "ステップ1"},
        }
        result = _extract_transitions_from_nodes(nodes)

        assert result.extracted is False
        assert result.transitions == {}
        assert result.nodes == nodes

    def test_transitions_removed_from_nodes(self) -> None:
        """抽出後の nodes から transitions キーが削除される。"""
        nodes = {
            "step1": {
                "description": "ステップ1",
                "transitions": {"success::done": "step2"},
            },
        }
        result = _extract_transitions_from_nodes(nodes)

        assert "transitions" not in result.nodes["step1"]
        assert result.nodes["step1"]["description"] == "ステップ1"

    def test_exit_nodes_are_skipped(self) -> None:
        """exit ノードの transitions は抽出しない。"""
        nodes = {
            "step1": {
                "description": "ステップ1",
                "transitions": {"success::done": "exit.success.done"},
            },
            "exit": {
                "success": {
                    "done": {"description": "正常終了"},
                },
            },
        }
        result = _extract_transitions_from_nodes(nodes)

        assert "exit" not in result.transitions
        assert result.transitions == {
            "step1": {"success::done": "exit.success.done"},
        }

    def test_mixed_nodes_with_and_without_transitions(self) -> None:
        """transitions がある nodes とない nodes が混在する場合。"""
        nodes = {
            "step1": {
                "description": "ステップ1",
                "transitions": {"success::done": "step2"},
            },
            "step2": {
                "description": "ステップ2",
            },
        }
        result = _extract_transitions_from_nodes(nodes)

        assert result.extracted is True
        assert "step1" in result.transitions
        assert "step2" not in result.transitions

    def test_extract_from_empty_nodes(self) -> None:
        """nodes が空の場合、すべて空で extracted=False が返る。"""
        result = _extract_transitions_from_nodes({})

        assert result.extracted is False
        assert result.transitions == {}
        assert result.nodes == {}

    def test_does_not_modify_original_nodes(self) -> None:
        """元の nodes dict を変更しないことを確認。"""
        nodes = {
            "step1": {
                "description": "ステップ1",
                "transitions": {"success::done": "step2"},
            },
        }
        original = copy.deepcopy(nodes)
        _extract_transitions_from_nodes(nodes)

        assert nodes == original

    def test_result_is_immutable(self) -> None:
        """結果がイミュータブルであることを確認。"""
        nodes = {"step1": {"description": "test"}}
        result = _extract_transitions_from_nodes(nodes)
        with pytest.raises(AttributeError):
            result.extracted = True  # type: ignore[misc]


class TestConvertYamlWithNestedTransitions:
    """convert_yaml_structure がネスト transitions を処理するテスト。"""

    def test_full_conversion_with_nested_transitions_and_exits(self) -> None:
        """バグ報告と同じ構造の YAML を正しく変換する。"""
        yaml_data = {
            "version": "1.0",
            "entrypoint": "convert_test",
            "description": "変換テスト用ワークフロー",
            "start": "step1",
            "nodes": {
                "step1": {
                    "description": "ステップ1",
                    "transitions": {
                        "success::done": "step2",
                        "failure::error": "exit.failure.error",
                    },
                },
                "step2": {
                    "description": "ステップ2",
                    "transitions": {
                        "success::done": "exit.success.done",
                        "failure::error": "exit.failure.error",
                    },
                },
            },
            "exits": {
                "success": {
                    "done": {"description": "正常終了", "exit_code": 0},
                },
                "failure": {
                    "error": {"description": "エラー終了", "exit_code": 1},
                },
            },
        }
        result = convert_yaml_structure(yaml_data)

        assert result.success is True
        assert "exits" not in result.data
        assert "exit" in result.data["nodes"]
        assert "transitions" in result.data
        assert "step1" in result.data["transitions"]
        assert "step2" in result.data["transitions"]
        assert "transitions" not in result.data["nodes"]["step1"]
        assert "transitions" not in result.data["nodes"]["step2"]

    def test_merge_toplevel_and_node_transitions(self) -> None:
        """トップレベルとノード内の transitions が競合する場合、ノード内が優先される。"""
        yaml_data = {
            "version": "1.0",
            "entrypoint": "test",
            "start": "step1",
            "nodes": {
                "step1": {
                    "description": "ステップ1",
                    "transitions": {
                        "success::done": "exit.success.done",
                    },
                },
            },
            "transitions": {
                "step1": {
                    "success::done": "step2",
                },
            },
            "exits": {
                "success": {
                    "done": {"description": "正常終了", "exit_code": 0},
                },
            },
        }
        result = convert_yaml_structure(yaml_data)

        assert result.success is True
        assert result.data["transitions"]["step1"]["success::done"] == "exit.success.done"

    def test_merge_generates_warning_on_conflict(self) -> None:
        """トップレベルとノード内 transitions の競合時に警告が出る。"""
        yaml_data = {
            "version": "1.0",
            "entrypoint": "test",
            "start": "step1",
            "nodes": {
                "step1": {
                    "description": "ステップ1",
                    "transitions": {
                        "success::done": "exit.success.done",
                    },
                },
            },
            "transitions": {
                "step1": {
                    "success::done": "step2",
                },
            },
            "exits": {
                "success": {
                    "done": {"description": "正常終了", "exit_code": 0},
                },
            },
        }
        result = convert_yaml_structure(yaml_data)

        assert result.success is True
        assert any("step1" in w for w in result.warnings)

    def test_merge_preserves_toplevel_extra_keys_for_same_node(self) -> None:
        """同じノードのトップレベル transitions にしかないキーはマージで保持される。"""
        yaml_data = {
            "version": "1.0",
            "entrypoint": "test",
            "start": "step1",
            "nodes": {
                "step1": {
                    "description": "ステップ1",
                    "transitions": {
                        "success::done": "exit.success.done",
                    },
                },
            },
            "transitions": {
                "step1": {
                    "success::done": "step2",
                    "failure::error": "exit.failure.error",
                },
            },
            "exits": {
                "success": {
                    "done": {"description": "正常終了", "exit_code": 0},
                },
                "failure": {
                    "error": {"description": "エラー終了", "exit_code": 1},
                },
            },
        }
        result = convert_yaml_structure(yaml_data)

        assert result.success is True
        assert result.data["transitions"]["step1"]["success::done"] == "exit.success.done"
        assert result.data["transitions"]["step1"]["failure::error"] == "exit.failure.error"

    def test_toplevel_transitions_without_conflict_preserved(self) -> None:
        """競合しないトップレベル transitions は保持される。"""
        yaml_data = {
            "version": "1.0",
            "entrypoint": "test",
            "start": "step1",
            "nodes": {
                "step1": {
                    "description": "ステップ1",
                    "transitions": {
                        "success::done": "step2",
                    },
                },
                "step2": {
                    "description": "ステップ2",
                },
            },
            "transitions": {
                "step2": {
                    "success::done": "exit.success.done",
                },
            },
            "exits": {
                "success": {
                    "done": {"description": "正常終了", "exit_code": 0},
                },
            },
        }
        result = convert_yaml_structure(yaml_data)

        assert result.success is True
        assert "step1" in result.data["transitions"]
        assert result.data["transitions"]["step2"]["success::done"] == "exit.success.done"
