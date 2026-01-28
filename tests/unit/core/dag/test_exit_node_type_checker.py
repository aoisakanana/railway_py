"""Issue #45: 終端ノード返り値型チェックのテスト。

TDD Red Phase: 失敗するテストを先に作成。
"""
import ast
from pathlib import Path

import pytest


class TestTypeCheckResult:
    """TypeCheckResult のテスト（イミュータブルデータ）。"""

    def test_ok_creates_valid_result(self) -> None:
        from railway.core.dag.type_checker import TypeCheckResult

        result = TypeCheckResult.ok()
        assert result.is_valid is True
        assert result.warnings == ()

    def test_warn_creates_invalid_result_with_single_message(self) -> None:
        from railway.core.dag.type_checker import TypeCheckResult

        result = TypeCheckResult.warn("警告メッセージ")
        assert result.is_valid is False
        assert result.warnings == ("警告メッセージ",)

    def test_warn_creates_invalid_result_with_multiple_messages(self) -> None:
        from railway.core.dag.type_checker import TypeCheckResult

        result = TypeCheckResult.warn("警告1", "警告2")
        assert result.is_valid is False
        assert result.warnings == ("警告1", "警告2")

    def test_is_frozen(self) -> None:
        from railway.core.dag.type_checker import TypeCheckResult

        result = TypeCheckResult.ok()
        with pytest.raises((TypeError, AttributeError)):
            result.is_valid = False  # type: ignore

    def test_merge_combines_results(self) -> None:
        """複数の結果をマージできる。"""
        from railway.core.dag.type_checker import TypeCheckResult

        result1 = TypeCheckResult.warn("警告1")
        result2 = TypeCheckResult.warn("警告2")
        result3 = TypeCheckResult.ok()

        merged = TypeCheckResult.merge(result1, result2, result3)

        assert merged.is_valid is False
        assert merged.warnings == ("警告1", "警告2")

    def test_merge_all_ok_returns_ok(self) -> None:
        from railway.core.dag.type_checker import TypeCheckResult

        merged = TypeCheckResult.merge(
            TypeCheckResult.ok(),
            TypeCheckResult.ok(),
        )
        assert merged.is_valid is True


class TestParseSource:
    """parse_source のテスト（純粋関数）。"""

    def test_valid_source_returns_ast(self) -> None:
        from railway.core.dag.type_checker import parse_source

        source = "def foo(): pass"
        result = parse_source(source)
        assert result is not None
        assert isinstance(result, ast.Module)

    def test_invalid_source_returns_none(self) -> None:
        from railway.core.dag.type_checker import parse_source

        source = "def foo(: pass"  # 構文エラー
        result = parse_source(source)
        assert result is None


class TestFindFunction:
    """find_function のテスト（純粋関数）。"""

    def test_finds_function_by_name(self) -> None:
        from railway.core.dag.type_checker import find_function

        source = "def done(ctx): pass"
        tree = ast.parse(source)
        func = find_function(tree, "done")
        assert func is not None
        assert func.name == "done"

    def test_returns_none_when_not_found(self) -> None:
        from railway.core.dag.type_checker import find_function

        source = "def other(ctx): pass"
        tree = ast.parse(source)
        func = find_function(tree, "done")
        assert func is None

    def test_finds_async_function(self) -> None:
        from railway.core.dag.type_checker import find_function

        source = "async def done(ctx): pass"
        tree = ast.parse(source)
        func = find_function(tree, "done")
        assert func is not None
        assert isinstance(func, ast.AsyncFunctionDef)

    def test_finds_nested_function(self) -> None:
        """クラス内の関数も検出する。"""
        from railway.core.dag.type_checker import find_function

        source = """
class MyClass:
    def done(self): pass
"""
        tree = ast.parse(source)
        func = find_function(tree, "done")
        assert func is not None


class TestExtractReturnTypeName:
    """extract_return_type_name のテスト（純粋関数）。"""

    @pytest.mark.parametrize(
        "source,expected",
        [
            ("def f() -> DoneResult: pass", "DoneResult"),
            ("def f() -> module.DoneResult: pass", "DoneResult"),
            ("def f() -> pkg.module.DoneResult: pass", "DoneResult"),
            ("def f(): pass", None),
        ],
    )
    def test_extracts_return_type_name(self, source: str, expected: str | None) -> None:
        from railway.core.dag.type_checker import extract_return_type_name

        tree = ast.parse(source)
        func = tree.body[0]
        name = extract_return_type_name(func.returns)
        assert name == expected


class TestIsValidExitContractTypeName:
    """is_valid_exit_contract_type_name のテスト（純粋関数）。"""

    @pytest.mark.parametrize(
        "type_name,expected",
        [
            ("ExitContract", True),
            ("SuccessDoneResult", True),  # *Result パターン
            ("FailureTimeoutResult", True),
            ("DoneContract", True),  # *Contract パターン
            ("MyExitContract", True),
            ("dict", False),
            ("str", False),
            ("None", False),
            ("Any", False),
            (None, False),
        ],
    )
    def test_validates_type_name(
        self, type_name: str | None, expected: bool
    ) -> None:
        from railway.core.dag.type_checker import is_valid_exit_contract_type_name

        assert is_valid_exit_contract_type_name(type_name) == expected


class TestCheckFunctionReturnType:
    """check_function_return_type のテスト（純粋関数）。"""

    def test_valid_exit_contract_return(self) -> None:
        from railway.core.dag.type_checker import check_function_return_type

        source = "def done(ctx) -> DoneResult: pass"
        tree = ast.parse(source)
        func = tree.body[0]

        result = check_function_return_type(func, "test.py")

        assert result.is_valid is True

    def test_missing_return_annotation_warns(self) -> None:
        from railway.core.dag.type_checker import check_function_return_type

        source = "def done(ctx): pass"
        tree = ast.parse(source)
        func = tree.body[0]

        result = check_function_return_type(func, "test.py")

        assert result.is_valid is False
        assert any("返り値型アノテーション" in w for w in result.warnings)

    def test_invalid_return_type_warns(self) -> None:
        from railway.core.dag.type_checker import check_function_return_type

        source = "def done(ctx) -> dict: pass"
        tree = ast.parse(source)
        func = tree.body[0]

        result = check_function_return_type(func, "test.py")

        assert result.is_valid is False
        assert any("ExitContract" in w for w in result.warnings)

    def test_warning_includes_file_and_line(self) -> None:
        from railway.core.dag.type_checker import check_function_return_type

        source = "def done(ctx) -> dict: pass"
        tree = ast.parse(source)
        func = tree.body[0]

        result = check_function_return_type(func, "src/nodes/exit/done.py")

        assert any("src/nodes/exit/done.py" in w for w in result.warnings)
        assert any(":1:" in w for w in result.warnings)  # 行番号


class TestCheckExitNodeReturnType:
    """統合テスト（ファイル読み込みを含む）。"""

    def test_valid_exit_contract_return(self, tmp_path: Path) -> None:
        """ExitContract サブクラスを返す場合は OK。"""
        from railway.core.dag.type_checker import check_exit_node_return_type

        code = '''
from railway import ExitContract, node

class DoneResult(ExitContract):
    exit_state: str = "success.done"

@node(name="exit.success.done")
def done(ctx) -> DoneResult:
    return DoneResult()
'''
        file_path = tmp_path / "done.py"
        file_path.write_text(code)

        result = check_exit_node_return_type(file_path, "done")
        assert result.is_valid is True

    def test_missing_return_type_annotation(self, tmp_path: Path) -> None:
        """返り値型アノテーションがない場合は警告。"""
        from railway.core.dag.type_checker import check_exit_node_return_type

        code = '''
from railway import node

@node(name="exit.success.done")
def done(ctx):
    return {"status": "ok"}
'''
        file_path = tmp_path / "done.py"
        file_path.write_text(code)

        result = check_exit_node_return_type(file_path, "done")
        assert result.is_valid is False
        assert any("返り値型アノテーション" in w for w in result.warnings)

    def test_non_exit_contract_return_type(self, tmp_path: Path) -> None:
        """ExitContract 以外の返り値型は警告。"""
        from railway.core.dag.type_checker import check_exit_node_return_type

        code = '''
from railway import node

@node(name="exit.success.done")
def done(ctx) -> dict:
    return {"status": "ok"}
'''
        file_path = tmp_path / "done.py"
        file_path.write_text(code)

        result = check_exit_node_return_type(file_path, "done")
        assert result.is_valid is False
        assert any("ExitContract" in w for w in result.warnings)

    def test_file_not_found(self, tmp_path: Path) -> None:
        """ファイルが存在しない場合は警告。"""
        from railway.core.dag.type_checker import check_exit_node_return_type

        file_path = tmp_path / "nonexistent.py"
        result = check_exit_node_return_type(file_path, "done")
        assert result.is_valid is False
        assert any("ファイル" in w for w in result.warnings)

    def test_syntax_error_in_file(self, tmp_path: Path) -> None:
        """構文エラーがある場合は警告。"""
        from railway.core.dag.type_checker import check_exit_node_return_type

        code = "def done(: pass"  # 構文エラー
        file_path = tmp_path / "done.py"
        file_path.write_text(code)

        result = check_exit_node_return_type(file_path, "done")
        assert result.is_valid is False
        assert any("構文エラー" in w for w in result.warnings)

    def test_function_not_found(self, tmp_path: Path) -> None:
        """関数が見つからない場合は警告。"""
        from railway.core.dag.type_checker import check_exit_node_return_type

        code = "def other(ctx): pass"
        file_path = tmp_path / "done.py"
        file_path.write_text(code)

        result = check_exit_node_return_type(file_path, "done")
        assert result.is_valid is False
        assert any("見つかりません" in w for w in result.warnings)
