"""Tests for exit node parsing (pure functions).

Note:
    TDD のベストプラクティスに従い、パブリック API (parse_nodes) 経由でテスト。
    内部関数 (_is_leaf_node, _parse_leaf_node) は実装詳細として隠蔽。
"""

import pytest
from railway.core.dag.parser import parse_nodes


class TestAutoResolve:
    """自動解決のテスト（parse_nodes 経由）。"""

    def test_auto_resolve_from_path(self) -> None:
        """パスから module/function を自動解決。"""
        nodes_data = {"start": {"description": "開始"}}
        result = parse_nodes(nodes_data)

        assert len(result) == 1
        assert result[0].module == "nodes.start"
        assert result[0].function == "start"
        assert result[0].name == "start"

    def test_explicit_module_override(self) -> None:
        """明示的な module 指定は自動解決より優先。"""
        nodes_data = {
            "check": {"module": "custom.module", "description": "カスタム"}
        }
        result = parse_nodes(nodes_data)

        assert result[0].module == "custom.module"
        assert result[0].function == "check"  # 自動解決

    def test_explicit_function_override(self) -> None:
        """明示的な function 指定は自動解決より優先。"""
        nodes_data = {
            "check": {"function": "custom_func", "description": "カスタム"}
        }
        result = parse_nodes(nodes_data)

        assert result[0].module == "nodes.check"  # 自動解決
        assert result[0].function == "custom_func"

    def test_both_explicit(self) -> None:
        """module と function 両方明示。"""
        nodes_data = {
            "check": {
                "module": "custom.module",
                "function": "custom_func",
                "description": "カスタム",
            }
        }
        result = parse_nodes(nodes_data)

        assert result[0].module == "custom.module"
        assert result[0].function == "custom_func"


class TestExitCodeResolve:
    """終了コード解決のテスト（parse_nodes 経由）。"""

    def test_success_exit_code_zero(self) -> None:
        """exit.success.* は exit_code=0。"""
        nodes_data = {
            "exit": {"success": {"done": {"description": "正常終了"}}}
        }
        result = parse_nodes(nodes_data)

        exit_done = result[0]
        assert exit_done.name == "exit.success.done"
        assert exit_done.is_exit is True
        assert exit_done.exit_code == 0

    def test_failure_exit_code_one(self) -> None:
        """exit.failure.* は exit_code=1。"""
        nodes_data = {
            "exit": {"failure": {"error": {"description": "異常終了"}}}
        }
        result = parse_nodes(nodes_data)

        exit_error = result[0]
        assert exit_error.is_exit is True
        assert exit_error.exit_code == 1

    def test_warning_exit_code_default_one(self) -> None:
        """exit.warning.* は exit_code=1（デフォルト）。"""
        nodes_data = {
            "exit": {"warning": {"low_disk": {"description": "警告"}}}
        }
        result = parse_nodes(nodes_data)

        assert result[0].is_exit is True
        assert result[0].exit_code == 1

    def test_explicit_exit_code_override(self) -> None:
        """明示的な exit_code は自動解決より優先。"""
        nodes_data = {
            "exit": {"warning": {"low_disk": {"description": "警告", "exit_code": 2}}}
        }
        result = parse_nodes(nodes_data)

        assert result[0].exit_code == 2

    def test_non_exit_node_no_exit_code(self) -> None:
        """通常ノードは exit_code=None。"""
        nodes_data = {"start": {"description": "開始"}}
        result = parse_nodes(nodes_data)

        assert result[0].is_exit is False
        assert result[0].exit_code is None


class TestLeafNodeDetection:
    """葉ノード判定のテスト（parse_nodes の振る舞いで検証）。"""

    def test_empty_value_is_leaf(self) -> None:
        """None または空 dict は葉ノード。"""
        nodes_data = {"exit": {"success": {"done": None}}}
        result = parse_nodes(nodes_data)

        assert len(result) == 1
        assert result[0].name == "exit.success.done"

    def test_reserved_keys_only_is_leaf(self) -> None:
        """予約キーのみを含む dict は葉ノード。"""
        nodes_data = {
            "check": {
                "description": "説明",
                "module": "m",
                "function": "f",
            }
        }
        result = parse_nodes(nodes_data)

        assert len(result) == 1
        assert result[0].name == "check"

    def test_non_reserved_key_is_intermediate(self) -> None:
        """予約キー以外があれば中間ノード。"""
        nodes_data = {
            "exit": {
                "success": {"done": {"description": "終了"}},
                "failure": {"error": {"description": "失敗"}},
            }
        }
        result = parse_nodes(nodes_data)

        # exit は中間ノード、done と error が葉ノード
        assert len(result) == 2
        names = {n.name for n in result}
        assert "exit.success.done" in names
        assert "exit.failure.error" in names


class TestNestedNodesParsing:
    """ネスト構造パーステスト。"""

    def test_parse_flat_nodes(self) -> None:
        """フラットなノード構造。"""
        nodes_data = {
            "start": {"description": "開始"},
            "process": {"description": "処理"},
        }

        result = parse_nodes(nodes_data)

        assert len(result) == 2
        names = {n.name for n in result}
        assert "start" in names
        assert "process" in names

    def test_parse_nested_exit_nodes(self) -> None:
        """ネストした終端ノード構造。"""
        nodes_data = {
            "exit": {
                "success": {
                    "done": {"description": "正常終了"},
                },
                "failure": {
                    "error": {"description": "異常終了"},
                },
            },
        }

        result = parse_nodes(nodes_data)

        assert len(result) == 2
        names = {n.name for n in result}
        assert "exit.success.done" in names
        assert "exit.failure.error" in names

    def test_parse_deep_nested_exit_nodes(self) -> None:
        """深いネストの終端ノード。"""
        nodes_data = {
            "exit": {
                "failure": {
                    "ssh": {
                        "handshake": {"description": "ハンドシェイク失敗"},
                    },
                },
            },
        }

        result = parse_nodes(nodes_data)

        assert len(result) == 1
        assert result[0].name == "exit.failure.ssh.handshake"
        assert result[0].module == "nodes.exit.failure.ssh.handshake"
        assert result[0].function == "handshake"

    def test_parse_mixed_flat_and_nested(self) -> None:
        """フラットとネストの混在。"""
        nodes_data = {
            "start": {"description": "開始"},
            "exit": {
                "success": {
                    "done": {"description": "正常終了"},
                },
            },
        }

        result = parse_nodes(nodes_data)

        assert len(result) == 2
        names = {n.name for n in result}
        assert "start" in names
        assert "exit.success.done" in names

    def test_empty_leaf_node(self) -> None:
        """空の葉ノード（description なし）。"""
        nodes_data = {
            "exit": {
                "success": {
                    "done": None,  # 空
                },
            },
        }

        result = parse_nodes(nodes_data)

        assert len(result) == 1
        assert result[0].name == "exit.success.done"
        assert result[0].description == ""


class TestParserWithFixtures:
    """フィクスチャを使用した統合テスト。"""

    def test_parse_basic_exit_fixture(self, exit_node_fixtures) -> None:
        """basic_exit.yml をパース。"""
        from railway.core.dag.parser import load_transition_graph

        yaml_path = exit_node_fixtures / "basic_exit.yml"
        graph = load_transition_graph(yaml_path)

        exit_done = next(
            (n for n in graph.nodes if n.name == "exit.success.done"),
            None,
        )
        assert exit_done is not None
        assert exit_done.is_exit is True
        assert exit_done.exit_code == 0

    def test_parse_auto_resolve_fixture(self, exit_node_fixtures) -> None:
        """auto_resolve.yml をパース。"""
        from railway.core.dag.parser import load_transition_graph

        yaml_path = exit_node_fixtures / "auto_resolve.yml"
        graph = load_transition_graph(yaml_path)

        start = next(
            (n for n in graph.nodes if n.name == "start_process"),
            None,
        )
        assert start is not None
        assert start.module == "nodes.start_process"
        assert start.function == "start_process"

    def test_parse_deep_nested_fixture(self, exit_node_fixtures) -> None:
        """deep_nested_exit.yml をパース。"""
        from railway.core.dag.parser import load_transition_graph

        yaml_path = exit_node_fixtures / "deep_nested_exit.yml"
        graph = load_transition_graph(yaml_path)

        ssh_handshake = next(
            (n for n in graph.nodes if n.name == "exit.failure.ssh.handshake"),
            None,
        )
        assert ssh_handshake is not None
        assert ssh_handshake.is_exit is True
        assert ssh_handshake.exit_code == 1

    def test_parse_custom_exit_code_fixture(self, exit_node_fixtures) -> None:
        """custom_exit_code.yml をパース。"""
        from railway.core.dag.parser import load_transition_graph

        yaml_path = exit_node_fixtures / "custom_exit_code.yml"
        graph = load_transition_graph(yaml_path)

        low_disk = next(
            (n for n in graph.nodes if n.name == "exit.warning.low_disk"),
            None,
        )
        assert low_disk is not None
        assert low_disk.exit_code == 2
