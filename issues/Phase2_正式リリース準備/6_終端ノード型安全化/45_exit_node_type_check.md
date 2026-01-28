# Issue #45: 終端ノード返り値型チェック

**優先度**: P0
**依存**: #44
**ブロック**: #46

---

## 概要

`railway sync transition` 実行時、既存の終端ノードが `ExitContract` を返さない場合に警告を表示する。

## 背景

#44 でスケルトン生成を実装しても、既存のコードが不正な返り値型を持つ可能性がある。sync時に静的解析で警告することで、実行時エラーを防ぐ。

**フィードバックループの改善**:
```
railway sync transition 実行
    ↓
警告: 終端ノードの返り値型に問題があります
    ↓ 開発者が修正
再度 railway sync transition
    ↓
警告なし → 安全にコード生成
```

---

## 設計上の判断

### 名前ベース判定の採用

**採用理由**:
- sync 時のフィードバックは高速であるべき
- #44 のスケルトン生成で命名規則を統一しているため、名前ベースで十分
- 最終的なチェックは #46 の実行時エラーで補完

**限界と補完策**:

| ケース | 名前ベース判定 | 実行時チェック (#46) |
|--------|---------------|---------------------|
| `class MyResult(ExitContract)` | ✓ 検出 | ✓ 検出 |
| `class DoneResult(dict)` | ✗ 見逃し | ✓ 検出 |
| 型アノテーションなし | ✓ 警告 | ✓ 検出 |
| `-> dict` | ✓ 警告 | ✓ 検出 |

**結論**: 名前ベース判定は「早期フィードバック」として有効。見逃しは #46 で補完。

---

## TDD 実装フロー

### Phase 1: Red（失敗するテストを先に作成）

#### 1-1. データ型のテスト

```python
# tests/unit/core/dag/test_exit_node_type_checker.py

import pytest
from railway.core.dag.type_checker import TypeCheckResult


class TestTypeCheckResult:
    """TypeCheckResult のテスト（イミュータブルデータ）。"""

    def test_ok_creates_valid_result(self) -> None:
        result = TypeCheckResult.ok()
        assert result.is_valid is True
        assert result.warnings == ()

    def test_warn_creates_invalid_result_with_single_message(self) -> None:
        result = TypeCheckResult.warn("警告メッセージ")
        assert result.is_valid is False
        assert result.warnings == ("警告メッセージ",)

    def test_warn_creates_invalid_result_with_multiple_messages(self) -> None:
        result = TypeCheckResult.warn("警告1", "警告2")
        assert result.is_valid is False
        assert result.warnings == ("警告1", "警告2")

    def test_is_frozen(self) -> None:
        result = TypeCheckResult.ok()
        with pytest.raises((TypeError, AttributeError)):
            result.is_valid = False  # type: ignore

    def test_merge_combines_results(self) -> None:
        """複数の結果をマージできる。"""
        result1 = TypeCheckResult.warn("警告1")
        result2 = TypeCheckResult.warn("警告2")
        result3 = TypeCheckResult.ok()

        merged = TypeCheckResult.merge(result1, result2, result3)

        assert merged.is_valid is False
        assert merged.warnings == ("警告1", "警告2")

    def test_merge_all_ok_returns_ok(self) -> None:
        merged = TypeCheckResult.merge(
            TypeCheckResult.ok(),
            TypeCheckResult.ok(),
        )
        assert merged.is_valid is True
```

#### 1-2. 純粋関数のテスト

```python
# tests/unit/core/dag/test_exit_node_type_checker.py (続き)

import ast
from railway.core.dag.type_checker import (
    parse_source,
    find_function,
    extract_return_type_name,
    is_valid_exit_contract_type_name,
    check_function_return_type,
)


class TestParseSource:
    """parse_source のテスト（純粋関数）。"""

    def test_valid_source_returns_ast(self) -> None:
        source = "def foo(): pass"
        result = parse_source(source)
        assert result is not None
        assert isinstance(result, ast.Module)

    def test_invalid_source_returns_none(self) -> None:
        source = "def foo(: pass"  # 構文エラー
        result = parse_source(source)
        assert result is None


class TestFindFunction:
    """find_function のテスト（純粋関数）。"""

    def test_finds_function_by_name(self) -> None:
        source = "def done(ctx): pass"
        tree = ast.parse(source)
        func = find_function(tree, "done")
        assert func is not None
        assert func.name == "done"

    def test_returns_none_when_not_found(self) -> None:
        source = "def other(ctx): pass"
        tree = ast.parse(source)
        func = find_function(tree, "done")
        assert func is None

    def test_finds_async_function(self) -> None:
        source = "async def done(ctx): pass"
        tree = ast.parse(source)
        func = find_function(tree, "done")
        assert func is not None
        assert isinstance(func, ast.AsyncFunctionDef)

    def test_finds_nested_function(self) -> None:
        """クラス内の関数も検出する。"""
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
        tree = ast.parse(source)
        func = tree.body[0]
        name = extract_return_type_name(func.returns)
        assert name == expected

    def test_handles_optional_type(self) -> None:
        """Optional[T] は内部の型名を抽出。"""
        source = "def f() -> Optional[DoneResult]: pass"
        tree = ast.parse(source)
        func = tree.body[0]
        # Optional[DoneResult] の場合は DoneResult を返す
        name = extract_return_type_name(func.returns)
        assert name == "DoneResult"

    def test_handles_union_type(self) -> None:
        """Union[A, B] の場合は最初の型名を返す。"""
        source = "def f() -> Union[DoneResult, None]: pass"
        tree = ast.parse(source)
        func = tree.body[0]
        name = extract_return_type_name(func.returns)
        assert name == "DoneResult"


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
        assert is_valid_exit_contract_type_name(type_name) == expected


class TestCheckFunctionReturnType:
    """check_function_return_type のテスト（純粋関数）。"""

    def test_valid_exit_contract_return(self) -> None:
        source = "def done(ctx) -> DoneResult: pass"
        tree = ast.parse(source)
        func = tree.body[0]

        result = check_function_return_type(func, "test.py")

        assert result.is_valid is True

    def test_missing_return_annotation_warns(self) -> None:
        source = "def done(ctx): pass"
        tree = ast.parse(source)
        func = tree.body[0]

        result = check_function_return_type(func, "test.py")

        assert result.is_valid is False
        assert any("返り値型アノテーション" in w for w in result.warnings)

    def test_invalid_return_type_warns(self) -> None:
        source = "def done(ctx) -> dict: pass"
        tree = ast.parse(source)
        func = tree.body[0]

        result = check_function_return_type(func, "test.py")

        assert result.is_valid is False
        assert any("ExitContract" in w for w in result.warnings)

    def test_warning_includes_file_and_line(self) -> None:
        source = "def done(ctx) -> dict: pass"
        tree = ast.parse(source)
        func = tree.body[0]

        result = check_function_return_type(func, "src/nodes/exit/done.py")

        assert any("src/nodes/exit/done.py" in w for w in result.warnings)
        assert any(":1:" in w for w in result.warnings)  # 行番号
```

#### 1-3. 統合テスト（副作用を含む）

```python
# tests/unit/core/dag/test_exit_node_type_checker.py (続き)

from pathlib import Path
from railway.core.dag.type_checker import check_exit_node_return_type


class TestCheckExitNodeReturnType:
    """統合テスト（ファイル読み込みを含む）。"""

    def test_valid_exit_contract_return(self, tmp_path: Path) -> None:
        """ExitContract サブクラスを返す場合は OK。"""
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
        file_path = tmp_path / "nonexistent.py"
        result = check_exit_node_return_type(file_path, "done")
        assert result.is_valid is False
        assert any("ファイル" in w for w in result.warnings)

    def test_syntax_error_in_file(self, tmp_path: Path) -> None:
        """構文エラーがある場合は警告。"""
        code = "def done(: pass"  # 構文エラー
        file_path = tmp_path / "done.py"
        file_path.write_text(code)

        result = check_exit_node_return_type(file_path, "done")
        assert result.is_valid is False
        assert any("構文エラー" in w for w in result.warnings)

    def test_function_not_found(self, tmp_path: Path) -> None:
        """関数が見つからない場合は警告。"""
        code = "def other(ctx): pass"
        file_path = tmp_path / "done.py"
        file_path.write_text(code)

        result = check_exit_node_return_type(file_path, "done")
        assert result.is_valid is False
        assert any("見つかりません" in w for w in result.warnings)
```

### Phase 2: Green（最小実装）

#### 2-1. 型チェック結果（イミュータブル）

```python
# railway/core/dag/type_checker.py

"""終端ノードの返り値型チェック。

このモジュールは sync 時に終端ノードの返り値型を静的解析し、
ExitContract を返していない場合に警告を出す。

設計方針:
- 純粋関数で構成（ファイル読み込みは最小限に分離）
- イミュータブルなデータ構造
- AST ベースの静的解析（実行せずにチェック）

制限事項:
- 名前ベースの判定のため、実際の継承関係は検証しない
- 最終的な型安全性は実行時チェック (#46) で保証
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class TypeCheckResult:
    """型チェック結果（イミュータブル）。

    Attributes:
        is_valid: チェックに通過したか
        warnings: 警告メッセージ（タプル）

    Note:
        dataclass を採用した理由:
        - 内部処理用でユーザーに直接公開されない
        - シリアライズ不要
        - ValidationResult 等の既存内部型と一貫性がある
        - BaseModel より軽量
    """
    is_valid: bool
    warnings: tuple[str, ...]

    @classmethod
    def ok(cls) -> TypeCheckResult:
        """チェック通過の結果を生成。"""
        return cls(is_valid=True, warnings=())

    @classmethod
    def warn(cls, *warnings: str) -> TypeCheckResult:
        """警告ありの結果を生成。"""
        return cls(is_valid=False, warnings=warnings)

    @classmethod
    def merge(cls, *results: TypeCheckResult) -> TypeCheckResult:
        """複数の結果をマージ（純粋関数）。"""
        all_warnings: list[str] = []
        for r in results:
            all_warnings.extend(r.warnings)

        if all_warnings:
            return cls(is_valid=False, warnings=tuple(all_warnings))
        return cls.ok()
```

#### 2-2. 純粋関数群

```python
# railway/core/dag/type_checker.py (続き)

def parse_source(source: str) -> ast.Module | None:
    """ソースコードを AST にパース（純粋関数）。

    Args:
        source: Python ソースコード

    Returns:
        パースされた AST。構文エラー時は None。
    """
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def find_function(
    tree: ast.Module,
    function_name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """AST から関数定義を探す（純粋関数）。

    Args:
        tree: パース済み AST
        function_name: 探す関数名

    Returns:
        見つかった関数定義。見つからない場合は None。
    """
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == function_name:
                return node
    return None


def extract_return_type_name(returns: ast.expr | None) -> str | None:
    """返り値型アノテーションから型名を抽出（純粋関数）。

    Args:
        returns: 関数の returns 属性

    Returns:
        型名。アノテーションがない場合は None。

    Examples:
        - `def f() -> DoneResult` → "DoneResult"
        - `def f() -> module.DoneResult` → "DoneResult"
        - `def f() -> Optional[DoneResult]` → "DoneResult"
        - `def f()` → None
    """
    if returns is None:
        return None
    if isinstance(returns, ast.Name):
        return returns.id
    if isinstance(returns, ast.Attribute):
        return returns.attr
    if isinstance(returns, ast.Subscript):
        # Optional[T], Union[T, None] などの場合
        # 外側が Optional/Union なら内側の最初の型を抽出
        outer_name = extract_return_type_name(returns.value)
        if outer_name in ("Optional", "Union"):
            # subscript の slice から内部型を抽出
            return _extract_first_type_from_subscript(returns.slice)
        # その他の Generic 型の場合は外側の型名を返す
        return outer_name
    return None


def _extract_first_type_from_subscript(slice_node: ast.expr) -> str | None:
    """Subscript の slice から最初の型名を抽出（純粋関数）。

    Args:
        slice_node: Subscript.slice

    Returns:
        最初の型名。
    """
    # Python 3.9+ では Tuple が使われることがある
    if isinstance(slice_node, ast.Tuple):
        if slice_node.elts:
            return extract_return_type_name(slice_node.elts[0])
    # 単一の型の場合
    return extract_return_type_name(slice_node)


def is_valid_exit_contract_type_name(type_name: str | None) -> bool:
    """ExitContract 系の型名かどうか判定（純粋関数）。

    Args:
        type_name: 型名

    Returns:
        有効な ExitContract 系の型名なら True

    Note:
        厳密な継承チェックではなく、命名規則に基づく簡易判定。
        - ExitContract 自体
        - *Result で終わる型（スケルトン生成の命名規則）
        - *Contract で終わる型

        この判定は「早期フィードバック」を目的とし、
        見逃しは #46 の実行時チェックで補完される。
    """
    if type_name is None:
        return False
    return (
        type_name == "ExitContract"
        or type_name.endswith("Result")
        or type_name.endswith("Contract")
    )


def check_function_return_type(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    file_path: str,
) -> TypeCheckResult:
    """関数の返り値型をチェック（純粋関数）。

    Args:
        func: 関数定義 AST
        file_path: ファイルパス（警告メッセージ用）

    Returns:
        TypeCheckResult: チェック結果
    """
    if func.returns is None:
        return TypeCheckResult.warn(
            f"{file_path}:{func.lineno}: 関数 '{func.name}' に返り値型アノテーションがありません。"
            " ExitContract サブクラスを返すようにしてください。"
        )

    type_name = extract_return_type_name(func.returns)

    if is_valid_exit_contract_type_name(type_name):
        return TypeCheckResult.ok()

    return TypeCheckResult.warn(
        f"{file_path}:{func.lineno}: 関数 '{func.name}' の返り値型 '{type_name}' は "
        "ExitContract を継承していない可能性があります。"
        " ExitContract サブクラスを返すようにしてください。"
    )
```

#### 2-3. エントリーポイント（副作用を含む）

```python
# railway/core/dag/type_checker.py (続き)

def check_exit_node_return_type(
    file_path: Path,
    function_name: str,
) -> TypeCheckResult:
    """終端ノードの返り値型をチェック（副作用あり）。

    Args:
        file_path: Python ファイルパス
        function_name: チェック対象の関数名

    Returns:
        TypeCheckResult: チェック結果

    Note:
        この関数はファイル読み込みの副作用を含む。
        内部のチェックロジックは純粋関数で構成されている。
    """
    # ファイル読み込み（副作用）
    try:
        source = file_path.read_text()
    except OSError as e:
        return TypeCheckResult.warn(f"ファイル読み込みエラー: {file_path}: {e}")

    # 以下は純粋関数の組み合わせ
    tree = parse_source(source)
    if tree is None:
        return TypeCheckResult.warn(f"構文エラー: {file_path}")

    func = find_function(tree, function_name)
    if func is None:
        return TypeCheckResult.warn(
            f"関数 '{function_name}' が見つかりません: {file_path}"
        )

    return check_function_return_type(func, str(file_path))
```

#### 2-4. sync コマンドでの呼び出し

```python
# railway/cli/sync.py

def check_exit_nodes_return_types(
    graph: TransitionGraph,
    project_root: Path,
) -> TypeCheckResult:
    """既存の終端ノードの返り値型をチェック。

    Args:
        graph: 遷移グラフ
        project_root: プロジェクトルート

    Returns:
        TypeCheckResult: チェック結果（マージ済み）
    """
    results: list[TypeCheckResult] = []

    for node_def in graph.nodes:
        if not node_def.is_exit:
            continue

        file_path = _calculate_file_path(node_def, project_root)

        # ファイルが存在しない場合はスキップ（#44 で生成される）
        if not file_path.exists():
            continue

        result = check_exit_node_return_type(file_path, node_def.function)
        results.append(result)

    return TypeCheckResult.merge(*results) if results else TypeCheckResult.ok()
```

### Phase 3: Refactor

- 警告メッセージのフォーマット改善
- `--strict` オプションで警告をエラーにする
- 複数ファイルの並列チェック（オプション）

---

## 修正ファイル

| ファイル | 変更内容 |
|----------|----------|
| `railway/core/dag/type_checker.py` | 新規ファイル（型チェック機能） |
| `railway/cli/sync.py` | 型チェック呼び出しを追加 |
| `tests/unit/core/dag/test_exit_node_type_checker.py` | 新規テストファイル |

---

## 警告メッセージ例

```
$ railway sync transition --entry my_workflow

警告: 終端ノードの返り値型に問題があります:
  src/nodes/exit/success/done.py:15: 関数 'done' に返り値型アノテーションがありません。
    ExitContract サブクラスを返すようにしてください。
  src/nodes/exit/failure/error.py:10: 関数 'error' の返り値型 'dict' は
    ExitContract を継承していない可能性があります。
    ExitContract サブクラスを返すようにしてください。

生成完了: _railway/generated/my_workflow.py
```

---

## 受け入れ条件

### 機能
- [ ] 返り値型アノテーションがない場合に警告
- [ ] ExitContract 以外の返り値型の場合に警告
- [ ] 警告メッセージにファイルパスと行番号が含まれる
- [ ] 警告があってもコード生成は続行（破壊的変更は #46）
- [ ] async 関数にも対応
- [ ] `TypeCheckResult.merge()` で複数結果を集約

### TDD・関数型
- [ ] Red → Green → Refactor フェーズに従って実装
- [ ] 純粋関数のユニットテスト（パラメタライズ）
- [ ] 副作用を含む関数は分離
- [ ] `TypeCheckResult` はイミュータブル（`frozen=True`）
- [ ] 全テスト通過

---

*開発時のフィードバックループ改善*
