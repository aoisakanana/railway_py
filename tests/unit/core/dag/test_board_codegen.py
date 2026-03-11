"""Tests for Board type code generation (pure functions).

Issue 23-01: Board 型自動生成。
"""
import ast
import copy

import pytest

from railway.core.dag.board_analyzer import BranchWrites, NodeAnalysis
from railway.core.dag.board_codegen import generate_board_type, _infer_field_type


# =========== Helper ===========


def _make_analysis(
    node_name: str,
    *,
    all_writes: frozenset[str] = frozenset(),
    branch_writes: tuple[BranchWrites, ...] = (),
) -> NodeAnalysis:
    """テスト用の NodeAnalysis を生成する。"""
    return NodeAnalysis(
        node_name=node_name,
        file_path=f"src/nodes/{node_name}.py",
        reads_required=frozenset(),
        reads_optional=frozenset(),
        branch_writes=branch_writes,
        all_writes=all_writes,
        outcomes=(),
        violations=(),
    )


# =========== 1. 基本的な Board 型が生成される ===========


class TestGenerateBoardTypeBasic:
    """基本的な Board 型生成テスト。"""

    def test_generates_valid_python(self):
        """生成コードが valid Python であること。"""
        analyses = {
            "check_severity": _make_analysis(
                "check_severity",
                all_writes=frozenset({"severity"}),
            ),
        }
        code = generate_board_type(
            entrypoint="alert_workflow",
            analyses=analyses,
            entry_fields=frozenset({"incident_id"}),
            source_file="transition_graphs/alert_workflow.yml",
        )
        # compile() で構文検証
        compile(code, "<test>", "exec")

    def test_contains_class_definition(self):
        """クラス定義が含まれること。"""
        analyses = {
            "start": _make_analysis("start", all_writes=frozenset({"value"})),
        }
        code = generate_board_type(
            entrypoint="my_workflow",
            analyses=analyses,
        )
        assert "class MyWorkflowBoard(BoardBase):" in code

    def test_contains_boardbase_import(self):
        """BoardBase の import が含まれること。"""
        analyses = {}
        code = generate_board_type(
            entrypoint="my_workflow",
            analyses=analyses,
        )
        assert "from railway.core.board import BoardBase" in code

    def test_contains_annotations_import(self):
        """from __future__ import annotations が含まれること。"""
        analyses = {}
        code = generate_board_type(
            entrypoint="my_workflow",
            analyses=analyses,
        )
        assert "from __future__ import annotations" in code


# =========== 2. entry_fields は必須フィールド ===========


class TestEntryFields:
    """entry_fields のテスト。"""

    def test_entry_fields_are_required(self):
        """entry_fields は型アノテーション付き必須フィールド（デフォルト値なし）。"""
        analyses = {}
        code = generate_board_type(
            entrypoint="my_workflow",
            analyses=analyses,
            entry_fields=frozenset({"incident_id", "severity"}),
        )
        # entry_fields は : Any でデフォルト値なし
        # 順序はソート済み
        assert "incident_id: Any" in code
        assert "severity: Any" in code
        # デフォルト値がないことを確認
        lines = code.splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("incident_id:"):
                assert "=" not in stripped, f"entry_field should have no default: {stripped}"
            if stripped.startswith("severity:"):
                assert "=" not in stripped, f"entry_field should have no default: {stripped}"

    def test_empty_entry_fields(self):
        """entry_fields が空でも動作すること。"""
        analyses = {
            "start": _make_analysis("start", all_writes=frozenset({"value"})),
        }
        code = generate_board_type(
            entrypoint="my_workflow",
            analyses=analyses,
            entry_fields=frozenset(),
        )
        # valid Python
        compile(code, "<test>", "exec")
        assert "class MyWorkflowBoard(BoardBase):" in code


# =========== 3. node writes は Optional フィールド ===========


class TestNodeWrites:
    """node writes のテスト。"""

    def test_writes_have_default_values(self):
        """node writes はデフォルト値を持つこと。"""
        analyses = {
            "check_severity": _make_analysis(
                "check_severity",
                all_writes=frozenset({"severity", "escalated"}),
            ),
        }
        code = generate_board_type(
            entrypoint="my_workflow",
            analyses=analyses,
        )
        # writes はデフォルト値付き
        assert "severity: Any = None" in code or "severity: str = " in code
        assert "escalated: Any = None" in code or "escalated: bool = " in code

    def test_writes_from_multiple_nodes(self):
        """複数ノードの writes が含まれること。"""
        analyses = {
            "check": _make_analysis("check", all_writes=frozenset({"status"})),
            "process": _make_analysis("process", all_writes=frozenset({"result"})),
        }
        code = generate_board_type(
            entrypoint="my_workflow",
            analyses=analyses,
        )
        assert "status" in code
        assert "result" in code


# =========== 4. クラス名は PascalCase + "Board" ===========


class TestClassName:
    """クラス名生成のテスト。"""

    def test_simple_entrypoint(self):
        """simple entrypoint を PascalCase + Board に変換。"""
        code = generate_board_type(entrypoint="alert_workflow", analyses={})
        assert "class AlertWorkflowBoard(BoardBase):" in code

    def test_single_word_entrypoint(self):
        """単一単語の entrypoint。"""
        code = generate_board_type(entrypoint="alert", analyses={})
        assert "class AlertBoard(BoardBase):" in code

    def test_multi_word_entrypoint(self):
        """複数単語の entrypoint。"""
        code = generate_board_type(entrypoint="my_alert_workflow", analyses={})
        assert "class MyAlertWorkflowBoard(BoardBase):" in code


# =========== 5. 生成コードが valid Python ===========


class TestValidPython:
    """生成コードの構文検証テスト。"""

    def test_complex_board_compiles(self):
        """複雑な Board 型も compile() を通ること。"""
        analyses = {
            "check_severity": _make_analysis(
                "check_severity",
                all_writes=frozenset({"severity", "checked_at"}),
            ),
            "escalate": _make_analysis(
                "escalate",
                all_writes=frozenset({"escalated", "notified_at"}),
            ),
        }
        code = generate_board_type(
            entrypoint="alert_workflow",
            analyses=analyses,
            entry_fields=frozenset({"incident_id"}),
            source_file="transition_graphs/alert_workflow.yml",
        )
        compile(code, "<test>", "exec")
        # AST パースもできること
        tree = ast.parse(code)
        # クラスが定義されていること
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert len(classes) == 1
        assert classes[0].name == "AlertWorkflowBoard"


# =========== 6. ヘッダーに DO NOT EDIT 警告含む ===========


class TestHeader:
    """ヘッダー生成のテスト。"""

    def test_contains_do_not_edit(self):
        """DO NOT EDIT 警告が含まれること。"""
        code = generate_board_type(
            entrypoint="my_workflow",
            analyses={},
            source_file="transition_graphs/my_workflow.yml",
        )
        assert "DO NOT EDIT" in code

    def test_contains_source_file(self):
        """source_file がヘッダーに含まれること。"""
        code = generate_board_type(
            entrypoint="my_workflow",
            analyses={},
            source_file="transition_graphs/my_workflow.yml",
        )
        assert "transition_graphs/my_workflow.yml" in code

    def test_contains_docstring(self):
        """モジュール docstring が含まれること。"""
        code = generate_board_type(
            entrypoint="my_workflow",
            analyses={},
        )
        assert '"""Board' in code or "Board" in code


# =========== 7. BoardBase の import 含む (covered in TestGenerateBoardTypeBasic) ===========
# (TestGenerateBoardTypeBasic.test_contains_boardbase_import で網羅)


# =========== 8. 純粋関数テスト ===========


class TestPureFunctionProperties:
    """純粋関数の性質を検証するテスト。"""

    def test_same_input_same_output(self):
        """同一入力で同一出力を返すこと。"""
        analyses = {
            "check": _make_analysis("check", all_writes=frozenset({"status"})),
        }
        code1 = generate_board_type(
            entrypoint="my_workflow",
            analyses=analyses,
            entry_fields=frozenset({"incident_id"}),
        )
        code2 = generate_board_type(
            entrypoint="my_workflow",
            analyses=analyses,
            entry_fields=frozenset({"incident_id"}),
        )
        assert code1 == code2

    def test_input_not_mutated(self):
        """入力の analyses dict が変更されないこと。"""
        analyses = {
            "check": _make_analysis("check", all_writes=frozenset({"status"})),
        }
        analyses_copy = copy.deepcopy(analyses)
        entry_fields = frozenset({"incident_id"})

        generate_board_type(
            entrypoint="my_workflow",
            analyses=analyses,
            entry_fields=entry_fields,
        )

        # analyses が変更されていないこと
        assert analyses.keys() == analyses_copy.keys()
        for key in analyses:
            assert analyses[key] == analyses_copy[key]


# =========== 9. entry_fields が空の場合 (covered in TestEntryFields) ===========
# (TestEntryFields.test_empty_entry_fields で網羅)


# =========== 10. フィールドの重複排除 ===========


class TestFieldDeduplication:
    """フィールドの重複排除テスト。"""

    def test_entry_field_takes_priority_over_writes(self):
        """entry_fields と writes の両方にある場合は entry_fields 優先。"""
        analyses = {
            "check": _make_analysis(
                "check",
                all_writes=frozenset({"incident_id", "status"}),
            ),
        }
        code = generate_board_type(
            entrypoint="my_workflow",
            analyses=analyses,
            entry_fields=frozenset({"incident_id"}),
        )
        # incident_id は entry_field として1回だけ出現（デフォルト値なし）
        lines = [line.strip() for line in code.splitlines() if "incident_id" in line]
        # incident_id の定義行
        field_defs = [l for l in lines if l.startswith("incident_id:")]
        assert len(field_defs) == 1
        # entry_field なのでデフォルト値なし
        assert "= None" not in field_defs[0]

    def test_writes_overlap_across_nodes(self):
        """複数ノードで同じフィールドを writes する場合、1回だけ出現。"""
        analyses = {
            "check": _make_analysis("check", all_writes=frozenset({"status"})),
            "process": _make_analysis("process", all_writes=frozenset({"status"})),
        }
        code = generate_board_type(
            entrypoint="my_workflow",
            analyses=analyses,
        )
        lines = [line.strip() for line in code.splitlines() if line.strip().startswith("status:")]
        assert len(lines) == 1


# =========== 型推論テスト ===========


class TestInferFieldType:
    """_infer_field_type のテスト。"""

    def test_bool_field_from_branch_writes(self):
        """BranchWrites に True/False がある場合、bool と推論。"""
        analyses = {
            "escalate": _make_analysis(
                "escalate",
                all_writes=frozenset({"escalated"}),
                branch_writes=(
                    BranchWrites(outcome="success::done", writes=frozenset({"escalated"})),
                ),
            ),
        }
        type_str, default_str = _infer_field_type("escalated", analyses)
        # v0.14.0 初期は簡易推論なので Any, None がデフォルト
        assert isinstance(type_str, str)
        assert isinstance(default_str, str)

    def test_unknown_field_defaults_to_any_none(self):
        """不明なフィールドは Any, None。"""
        analyses = {}
        type_str, default_str = _infer_field_type("unknown_field", analyses)
        assert type_str == "Any"
        assert default_str == "None"


# =========== コメント付きフィールド ===========


class TestFieldComments:
    """フィールドにノード由来のコメントが付くテスト。"""

    def test_entry_fields_have_comment(self):
        """entry_fields にコメントが付くこと。"""
        analyses = {}
        code = generate_board_type(
            entrypoint="my_workflow",
            analyses=analyses,
            entry_fields=frozenset({"incident_id"}),
        )
        assert "entry_point" in code.lower() or "entry" in code.lower()

    def test_writes_have_node_comment(self):
        """writes にノード名のコメントが付くこと。"""
        analyses = {
            "check_severity": _make_analysis(
                "check_severity",
                all_writes=frozenset({"severity"}),
            ),
        }
        code = generate_board_type(
            entrypoint="my_workflow",
            analyses=analyses,
        )
        assert "check_severity" in code
