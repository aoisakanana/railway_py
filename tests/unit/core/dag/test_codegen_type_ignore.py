"""生成コードの type: ignore テスト。

TDD: Red → Green → Refactor
このテストは生成コードが mypy 対応であることを検証する。
"""

from pathlib import Path


class TestCodegenTypeIgnore:
    """codegen の type: ignore 生成テスト"""

    def test_run_function_has_type_ignore_for_node_name(self) -> None:
        """run() 関数の _node_name 代入に type: ignore がある"""
        from railway.core.dag.codegen import generate_run_helper

        code = generate_run_helper()

        # _node_name 代入行を抽出
        lines_with_node_name = [
            line for line in code.split("\n")
            if "._node_name" in line and "=" in line
        ]

        # 少なくとも 2 行（run と run_async）
        assert len(lines_with_node_name) >= 2, "Should have _node_name assignments"

        # 各行に type: ignore がある
        for line in lines_with_node_name:
            assert "type: ignore[attr-defined]" in line, f"Missing type: ignore in: {line}"

    def test_run_helper_is_pure_function(self) -> None:
        """generate_run_helper は純粋関数（引数なし、同じ出力）"""
        from railway.core.dag.codegen import generate_run_helper

        result1 = generate_run_helper()
        result2 = generate_run_helper()

        assert result1 == result2, "Pure function should return same result"

    def test_run_helper_returns_valid_python(self) -> None:
        """生成されるコードは有効な Python である"""
        from railway.core.dag.codegen import generate_run_helper

        code = generate_run_helper()

        # 構文チェック
        try:
            compile(code, "<string>", "exec")
        except SyntaxError as e:
            raise AssertionError(f"Generated code has syntax error: {e}")


class TestNodeNameAttributesTypeIgnore:
    """generate_node_name_attributes の type: ignore テスト"""

    def test_node_name_attributes_have_type_ignore(self, tmp_path: Path) -> None:
        """モジュールレベルの _node_name 代入にも type: ignore がある"""
        from railway.core.dag.codegen import generate_node_name_assignments
        from railway.core.dag.parser import parse_transition_graph

        yaml_content = """
version: "1.0"
entrypoint: test
description: "test"
nodes:
  start:
    module: nodes.start
    function: start
    description: "start"
  exit:
    success:
      done:
        description: "done"
start: start
transitions:
  start:
    success::done: exit.success.done
"""
        graph = parse_transition_graph(yaml_content)
        code = generate_node_name_assignments(graph)

        # _node_name 代入行を抽出
        lines_with_node_name = [
            line for line in code.split("\n")
            if "._node_name" in line and "=" in line
        ]

        # 少なくとも 2 行（start と exit ノード）
        assert len(lines_with_node_name) >= 2, "Should have _node_name assignments"

        # 各行に type: ignore がある
        for line in lines_with_node_name:
            assert "type: ignore[attr-defined]" in line, f"Missing type: ignore in: {line}"
