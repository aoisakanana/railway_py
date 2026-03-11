"""AST ベースの Board パターン解析モジュール。

ノードのソースコードを AST 解析し、Board へのアクセスパターンを抽出する。
Issues 20-01 through 20-05.

設計原則:
- 純粋関数: 副作用なし、同じ入力に同じ出力
- イミュータブル: frozen=True の dataclass
- 安全な失敗: 構文エラー等は空の NodeAnalysis を返す
"""
from __future__ import annotations

import ast
from dataclasses import dataclass

# =========== 20-01: Result Types ===========


@dataclass(frozen=True)
class FieldAccess:
    """Board フィールドへのアクセス情報。

    Attributes:
        name: フィールド名
        line: ソースコード上の行番号
        is_conditional: 条件分岐内でのアクセスか
    """

    name: str
    line: int
    is_conditional: bool


@dataclass(frozen=True)
class BranchWrites:
    """特定の Outcome 分岐での書き込み情報。

    Attributes:
        outcome: Outcome 文字列（例: "success::done"）
        writes: 書き込まれるフィールド名の集合
    """

    outcome: str
    writes: frozenset[str]


@dataclass(frozen=True)
class AnalysisViolation:
    """Board 使用パターンの違反情報。

    Attributes:
        code: 違反コード（E012, E013, E014, E015）
        message: 説明メッセージ
        line: ソースコード上の行番号
        file_path: ファイルパス
    """

    code: str
    message: str
    line: int
    file_path: str


@dataclass(frozen=True)
class NodeAnalysis:
    """ノード解析の結果。

    Attributes:
        node_name: ノード名
        file_path: ファイルパス
        reads_required: 必須読み取りフィールド
        reads_optional: オプション読み取りフィールド
        branch_writes: 分岐ごとの書き込み情報
        all_writes: 全書き込みフィールド
        outcomes: 検出された Outcome 文字列
        violations: 検出された違反
    """

    node_name: str
    file_path: str
    reads_required: frozenset[str]
    reads_optional: frozenset[str]
    branch_writes: tuple[BranchWrites, ...]
    all_writes: frozenset[str]
    outcomes: tuple[str, ...]
    violations: tuple[AnalysisViolation, ...]

    @property
    def reads_all(self) -> frozenset[str]:
        """全読み取りフィールド（required + optional）。"""
        return self.reads_required | self.reads_optional

    @property
    def has_violations(self) -> bool:
        """違反があるか。"""
        return len(self.violations) > 0


# =========== 20-02: Basic Reads/Writes Extraction ===========


def _empty_analysis(file_path: str, node_name: str) -> NodeAnalysis:
    """空の NodeAnalysis を生成する。"""
    return NodeAnalysis(
        node_name=node_name,
        file_path=file_path,
        reads_required=frozenset(),
        reads_optional=frozenset(),
        branch_writes=(),
        all_writes=frozenset(),
        outcomes=(),
        violations=(),
    )


def analyze_node_file(
    file_path: str,
    source_code: str,
    node_name: str,
) -> NodeAnalysis:
    """ノードファイルを AST 解析して NodeAnalysis を返す。

    純粋関数。ファイル I/O は行わない。

    Args:
        file_path: ファイルパス（エラーメッセージ用）
        source_code: ソースコード文字列
        node_name: ノード名

    Returns:
        NodeAnalysis（構文エラー時は空の結果）
    """
    if not source_code.strip():
        return _empty_analysis(file_path, node_name)

    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return _empty_analysis(file_path, node_name)

    func_def = _find_node_function(tree)
    if func_def is None:
        return _empty_analysis(file_path, node_name)

    source_lines = tuple(source_code.splitlines())
    board_name = _get_board_param_name(func_def)

    # E015 check is part of violations, but we still need a board_name to analyze
    # If param is not "board", we still use whatever the first param is for analysis
    actual_board_name = board_name if board_name else "board"

    reads = _extract_reads(func_def.body, actual_board_name)
    writes = _extract_writes(func_def.body, actual_board_name)
    reads_required, reads_optional = _classify_reads(reads)
    branch_writes_result = _extract_branch_writes(func_def, actual_board_name)
    outcomes = _extract_all_outcomes(func_def)
    violations = _detect_violations(
        func_def, actual_board_name, file_path, source_lines
    )

    all_writes = frozenset(fa.name for fa in writes)

    return NodeAnalysis(
        node_name=node_name,
        file_path=file_path,
        reads_required=reads_required,
        reads_optional=reads_optional,
        branch_writes=branch_writes_result,
        all_writes=all_writes,
        outcomes=outcomes,
        violations=violations,
    )


def _find_node_function(tree: ast.Module) -> ast.FunctionDef | None:
    """AST から @node デコレータ付き関数を探す。

    Args:
        tree: AST モジュール

    Returns:
        関数定義。見つからなければ None
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            if _is_node_decorator(decorator):
                return node
    return None


def _is_node_decorator(decorator: ast.expr) -> bool:
    """デコレータが @node かどうか判定する。"""
    # @node
    if isinstance(decorator, ast.Name) and decorator.id == "node":
        return True
    # @node(...) - Call
    if isinstance(decorator, ast.Call):
        func = decorator.func
        if isinstance(func, ast.Name) and func.id == "node":
            return True
    return False


def _get_board_param_name(func_def: ast.FunctionDef) -> str:
    """関数の第一引数名を取得する。

    Args:
        func_def: 関数定義

    Returns:
        第一引数名。引数がなければ空文字列
    """
    args = func_def.args
    if args.args:
        return args.args[0].arg
    return ""


def _extract_reads(
    func_body: list[ast.stmt],
    board_name: str,
) -> tuple[FieldAccess, ...]:
    """関数本体から board の読み取りアクセスを抽出する。

    Args:
        func_body: AST 文のリスト
        board_name: board パラメータ名

    Returns:
        FieldAccess のタプル
    """
    visitor = _ReadExtractor(board_name)
    for stmt in func_body:
        visitor.visit(stmt)
    return tuple(visitor.reads)


def _extract_writes(
    func_body: list[ast.stmt],
    board_name: str,
) -> tuple[FieldAccess, ...]:
    """関数本体から board への書き込みアクセスを抽出する。

    Args:
        func_body: AST 文のリスト
        board_name: board パラメータ名

    Returns:
        FieldAccess のタプル
    """
    visitor = _WriteExtractor(board_name)
    for stmt in func_body:
        visitor.visit(stmt)
    return tuple(visitor.writes)


class _ReadExtractor(ast.NodeVisitor):
    """board.xxx の読み取りを抽出するビジター。"""

    def __init__(self, board_name: str) -> None:
        self.board_name = board_name
        self.reads: list[FieldAccess] = []
        self._conditional_depth = 0
        # Track assignment targets to exclude writes from reads
        self._in_assign_target = False

    def visit_If(self, node: ast.If) -> None:
        # Visit the test (condition) at current+1 depth (condition is conditional)
        self._conditional_depth += 1
        self.visit(node.test)
        self._conditional_depth -= 1

        # Visit the body at increased depth
        self._conditional_depth += 1
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)
        self._conditional_depth -= 1

    def visit_For(self, node: ast.For) -> None:
        self._conditional_depth += 1
        self.generic_visit(node)
        self._conditional_depth -= 1

    def visit_While(self, node: ast.While) -> None:
        self._conditional_depth += 1
        self.generic_visit(node)
        self._conditional_depth -= 1

    def visit_Try(self, node: ast.Try) -> None:
        self._conditional_depth += 1
        self.generic_visit(node)
        self._conditional_depth -= 1

    def visit_Assign(self, node: ast.Assign) -> None:
        # Don't count board.x = ... as a read
        # But do visit the value side
        for target in node.targets:
            if self._is_board_attr_store(target):
                # Skip the target (it's a write, not a read)
                pass
            else:
                self.visit(target)
        self.visit(node.value)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        # board.x += 1 is both read and write
        self.visit(node.target)
        self.visit(node.value)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if self._is_board_read(node):
            self.reads.append(
                FieldAccess(
                    name=node.attr,
                    line=node.lineno,
                    is_conditional=self._conditional_depth > 0,
                )
            )
        # Visit deeper (e.g., board.data.split)
        self.visit(node.value)

    def _is_board_read(self, node: ast.Attribute) -> bool:
        """board.xxx の読み取りか判定。"""
        return (
            isinstance(node.value, ast.Name)
            and node.value.id == self.board_name
        )

    def _is_board_attr_store(self, node: ast.expr) -> bool:
        """board.xxx = ... の左辺か判定。"""
        return (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == self.board_name
        )


class _WriteExtractor(ast.NodeVisitor):
    """board.xxx = value の書き込みを抽出するビジター。"""

    def __init__(self, board_name: str) -> None:
        self.board_name = board_name
        self.writes: list[FieldAccess] = []
        self._conditional_depth = 0

    def visit_If(self, node: ast.If) -> None:
        self._conditional_depth += 1
        self.generic_visit(node)
        self._conditional_depth -= 1

    def visit_For(self, node: ast.For) -> None:
        self._conditional_depth += 1
        self.generic_visit(node)
        self._conditional_depth -= 1

    def visit_While(self, node: ast.While) -> None:
        self._conditional_depth += 1
        self.generic_visit(node)
        self._conditional_depth -= 1

    def visit_Try(self, node: ast.Try) -> None:
        self._conditional_depth += 1
        self.generic_visit(node)
        self._conditional_depth -= 1

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == self.board_name
            ):
                self.writes.append(
                    FieldAccess(
                        name=target.attr,
                        line=target.lineno,
                        is_conditional=self._conditional_depth > 0,
                    )
                )
        # Continue visiting for nested assignments
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        target = node.target
        if (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == self.board_name
        ):
            self.writes.append(
                FieldAccess(
                    name=target.attr,
                    line=target.lineno,
                    is_conditional=self._conditional_depth > 0,
                )
            )
        self.generic_visit(node)


# =========== 20-03: Conditional Reads Classification ===========


def _classify_reads(
    reads: tuple[FieldAccess, ...],
) -> tuple[frozenset[str], frozenset[str]]:
    """読み取りアクセスを required / optional に分類する。

    - 条件分岐外で読み取り → required
    - 条件分岐内のみで読み取り → optional
    - 両方にある → required（required が勝つ）

    Args:
        reads: FieldAccess のタプル

    Returns:
        (reads_required, reads_optional) のタプル
    """
    unconditional: set[str] = set()
    conditional: set[str] = set()

    for access in reads:
        if access.is_conditional:
            conditional.add(access.name)
        else:
            unconditional.add(access.name)

    # unconditional に含まれるものは required
    required = frozenset(unconditional)
    # conditional のみのものが optional
    optional = frozenset(conditional - unconditional)

    return required, optional


# =========== 20-04: Outcome Branch Writes Tracking ===========


def _extract_branch_writes(
    func_def: ast.FunctionDef,
    board_name: str,
) -> tuple[BranchWrites, ...]:
    """関数定義から分岐ごとの書き込み情報を抽出する。

    各 return 文に到達するまでに書き込まれるフィールドを追跡する。

    Args:
        func_def: 関数定義
        board_name: board パラメータ名

    Returns:
        BranchWrites のタプル
    """
    collector = _BranchCollector(board_name)
    collector.collect_from_body(func_def.body, frozenset())
    return tuple(collector.branches)


def _extract_outcome_from_return(return_node: ast.Return) -> str | None:
    """return 文から Outcome 文字列を抽出する。

    Outcome.success("done") -> "success::done"
    Outcome.failure("not_found") -> "failure::not_found"

    Args:
        return_node: AST の return 文

    Returns:
        Outcome 文字列。Outcome でなければ None
    """
    if return_node.value is None:
        return None

    call = return_node.value
    if not isinstance(call, ast.Call):
        return None

    func = call.func
    if not isinstance(func, ast.Attribute):
        return None

    # Outcome.success(...) or Outcome.failure(...)
    if not (
        isinstance(func.value, ast.Name)
        and func.value.id == "Outcome"
        and func.attr in ("success", "failure")
    ):
        return None

    outcome_type = func.attr
    if call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
        detail = call.args[0].value
    else:
        detail = "done" if outcome_type == "success" else "error"

    return f"{outcome_type}::{detail}"


def _extract_all_outcomes(func_def: ast.FunctionDef) -> tuple[str, ...]:
    """関数定義から全 Outcome 文字列を抽出する。

    Args:
        func_def: 関数定義

    Returns:
        Outcome 文字列のタプル（重複なし）
    """
    outcomes: list[str] = []
    seen: set[str] = set()

    for node in ast.walk(func_def):
        if isinstance(node, ast.Return):
            outcome = _extract_outcome_from_return(node)
            if outcome is not None and outcome not in seen:
                outcomes.append(outcome)
                seen.add(outcome)

    return tuple(outcomes)


class _BranchCollector:
    """return 文に至るまでの書き込みを分岐ごとに収集する。"""

    def __init__(self, board_name: str) -> None:
        self.board_name = board_name
        self.branches: list[BranchWrites] = []

    def collect_from_body(
        self,
        stmts: list[ast.stmt],
        accumulated_writes: frozenset[str],
    ) -> bool:
        """文のリストを走査し、return に到達したら BranchWrites を記録する。

        Returns:
            True if all paths in this body return (i.e., body always returns)
        """
        current_writes = set(accumulated_writes)

        for stmt in stmts:
            # Collect writes from this statement
            stmt_writes = self._collect_stmt_writes(stmt)
            current_writes.update(stmt_writes)

            # Check for return
            if isinstance(stmt, ast.Return):
                outcome = _extract_outcome_from_return(stmt)
                if outcome is not None:
                    self.branches.append(
                        BranchWrites(
                            outcome=outcome,
                            writes=frozenset(current_writes),
                        )
                    )
                return True

            # Handle if/else branching
            if isinstance(stmt, ast.If):
                if_returned = self._handle_if(stmt, frozenset(current_writes))
                if if_returned:
                    # Both branches returned, so remaining code is unreachable
                    # But the if body already recorded its branches
                    return True

        return False

    def _handle_if(
        self,
        if_node: ast.If,
        accumulated_writes: frozenset[str],
    ) -> bool:
        """if/else 分岐を処理する。

        Returns:
            True if both if and else branches always return
        """
        if_returned = self.collect_from_body(
            if_node.body, accumulated_writes
        )

        if if_node.orelse:
            else_returned = self.collect_from_body(
                if_node.orelse, accumulated_writes
            )
            return if_returned and else_returned

        return False

    def _collect_stmt_writes(self, stmt: ast.stmt) -> frozenset[str]:
        """単一の文から board への書き込みフィールド名を収集する。

        If 文等の内部は再帰的に処理しない（分岐は _handle_if で処理）。
        """
        writes: set[str] = set()

        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == self.board_name
                ):
                    writes.add(target.attr)

        elif isinstance(stmt, ast.AugAssign):
            target = stmt.target
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == self.board_name
            ):
                writes.add(target.attr)

        return frozenset(writes)


# =========== 20-05: Violation Detection ===========


def _detect_violations(
    func_def: ast.FunctionDef,
    board_name: str,
    file_path: str,
    source_lines: tuple[str, ...],
) -> tuple[AnalysisViolation, ...]:
    """Board 使用パターンの違反を検出する。

    検出する違反:
    - E012: board が関数引数として渡されている
    - E013: board が別の変数に代入されている
    - E014: getattr/setattr で動的アクセス
    - E015: 第一引数名が "board" でない

    Args:
        func_def: 関数定義
        board_name: board パラメータ名（実際の引数名）
        file_path: ファイルパス
        source_lines: ソースコードの行タプル

    Returns:
        AnalysisViolation のタプル
    """
    violations: list[AnalysisViolation] = []

    # E015: first param not named "board"
    actual_name = _get_board_param_name(func_def)
    if actual_name and actual_name != "board":
        violations.append(
            AnalysisViolation(
                code="E015",
                message=f"Board パターンの第一引数は 'board' にしてください（現在: '{actual_name}'）",
                line=func_def.lineno,
                file_path=file_path,
            )
        )

    # Walk the function body for E012, E013, E014
    detector = _ViolationDetector(board_name, file_path, source_lines)
    for stmt in func_def.body:
        detector.visit(stmt)

    violations.extend(detector.violations)
    return tuple(violations)


def _is_riverboard_ignored(
    source_lines: tuple[str, ...],
    line: int,
) -> bool:
    """指定行に riverboard: ignore コメントがあるか判定する。

    Args:
        source_lines: ソースコードの行タプル
        line: 行番号（1-based）

    Returns:
        True if riverboard: ignore コメントがある
    """
    if line < 1 or line > len(source_lines):
        return False
    line_text = source_lines[line - 1]
    return "riverboard: ignore" in line_text


class _ViolationDetector(ast.NodeVisitor):
    """Board 使用パターンの違反を検出するビジター。"""

    def __init__(
        self,
        board_name: str,
        file_path: str,
        source_lines: tuple[str, ...],
    ) -> None:
        self.board_name = board_name
        self.file_path = file_path
        self.source_lines = source_lines
        self.violations: list[AnalysisViolation] = []

    def visit_Call(self, node: ast.Call) -> None:
        # E014: getattr(board, ...) or setattr(board, ...)
        if isinstance(node.func, ast.Name) and node.func.id in ("getattr", "setattr"):
            if (
                node.args
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == self.board_name
            ):
                if not _is_riverboard_ignored(self.source_lines, node.lineno):
                    self.violations.append(
                        AnalysisViolation(
                            code="E014",
                            message=f"'{node.func.id}(board, ...)' による動的アクセスは禁止です",
                            line=node.lineno,
                            file_path=self.file_path,
                        )
                    )

        # E012: board passed as function argument
        # Check positional args
        for arg in node.args:
            if isinstance(arg, ast.Name) and arg.id == self.board_name:
                # Exclude getattr/setattr (handled above)
                if isinstance(node.func, ast.Name) and node.func.id in (
                    "getattr",
                    "setattr",
                    "hasattr",
                ):
                    pass
                elif not _is_riverboard_ignored(self.source_lines, node.lineno):
                    self.violations.append(
                        AnalysisViolation(
                            code="E012",
                            message="board を関数引数として渡さないでください",
                            line=node.lineno,
                            file_path=self.file_path,
                        )
                    )

        # Check keyword args
        for kw in node.keywords:
            if isinstance(kw.value, ast.Name) and kw.value.id == self.board_name:
                if not _is_riverboard_ignored(self.source_lines, node.lineno):
                    self.violations.append(
                        AnalysisViolation(
                            code="E012",
                            message="board を関数引数として渡さないでください",
                            line=node.lineno,
                            file_path=self.file_path,
                        )
                    )

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        # E013: board alias assignment (b = board)
        if isinstance(node.value, ast.Name) and node.value.id == self.board_name:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if not _is_riverboard_ignored(self.source_lines, node.lineno):
                        self.violations.append(
                            AnalysisViolation(
                                code="E013",
                                message=f"board を別の変数 '{target.id}' に代入しないでください",
                                line=node.lineno,
                                file_path=self.file_path,
                            )
                        )
        self.generic_visit(node)
