"""終端ノードの返り値型チェック（Issue #45）。

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


# =============================================================================
# 純粋関数群
# =============================================================================


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
        # 外側の型名を返す（簡易実装）
        return extract_return_type_name(returns.value)
    return None


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


# =============================================================================
# エントリーポイント（副作用を含む）
# =============================================================================


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
