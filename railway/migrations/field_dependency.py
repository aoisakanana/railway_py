"""フィールドベース依存関係マイグレーション。

ノードコードを解析し、依存宣言の追加をガイドする。
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NodeAnalysis:
    """ノードの依存解析結果。"""

    name: str
    reads: frozenset[str]
    optional_reads: frozenset[str]
    writes: frozenset[str]


@dataclass(frozen=True)
class MigrationResult:
    """マイグレーション結果。"""

    guidance: str
    analyzed_nodes: tuple[str, ...]
    warnings: tuple[str, ...] = ()


def analyze_node_dependencies(file_path: Path) -> dict[str, NodeAnalysis]:
    """ノードファイルを解析し、依存情報を抽出する。

    Args:
        file_path: ノードファイルのパス

    Returns:
        ノード名 → NodeAnalysis のマッピング
    """
    try:
        source = file_path.read_text()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return {}

    results: dict[str, NodeAnalysis] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # @node デコレータがあるか確認
            if _has_node_decorator(node):
                analysis = _analyze_function(node)
                results[node.name] = analysis

    return results


def _has_node_decorator(func: ast.FunctionDef) -> bool:
    """@node デコレータがあるか確認する。"""
    for decorator in func.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "node":
            return True
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name) and decorator.func.id == "node":
                return True
    return False


def _analyze_function(func: ast.FunctionDef) -> NodeAnalysis:
    """関数を解析し、フィールドアクセスを抽出する。"""
    reads: set[str] = set()
    optional_reads: set[str] = set()
    writes: set[str] = set()

    class FieldAccessVisitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.in_conditional = False
            self.conditional_fields: set[str] = set()

        def visit_If(self, node: ast.If) -> None:
            # if ctx.field: パターンを検出
            if isinstance(node.test, ast.Attribute):
                if isinstance(node.test.value, ast.Name) and node.test.value.id == "ctx":
                    optional_reads.add(node.test.attr)
                    self.conditional_fields.add(node.test.attr)

            old_conditional = self.in_conditional
            self.in_conditional = True
            self.generic_visit(node)
            self.in_conditional = old_conditional

        def visit_Attribute(self, node: ast.Attribute) -> None:
            if isinstance(node.value, ast.Name) and node.value.id == "ctx":
                field = node.attr
                if field not in self.conditional_fields:
                    if self.in_conditional:
                        optional_reads.add(field)
                    else:
                        reads.add(field)
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:
            # model_copy(update={...}) パターンを検出
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == "model_copy":
                    for keyword in node.keywords:
                        if keyword.arg == "update" and isinstance(
                            keyword.value, ast.Dict
                        ):
                            for key in keyword.value.keys:
                                if isinstance(key, ast.Constant):
                                    writes.add(key.value)
            self.generic_visit(node)

    visitor = FieldAccessVisitor()
    visitor.visit(func)

    # optional_reads は reads から除外
    reads = reads - optional_reads

    return NodeAnalysis(
        name=func.name,
        reads=frozenset(reads),
        optional_reads=frozenset(optional_reads),
        writes=frozenset(writes),
    )


def infer_requires(analysis: NodeAnalysis) -> frozenset[str]:
    """requires を推論する。"""
    return analysis.reads


def infer_provides(analysis: NodeAnalysis) -> frozenset[str]:
    """provides を推論する。"""
    return analysis.writes


def generate_migration_guidance(analyses: dict[str, NodeAnalysis]) -> str:
    """マイグレーションガイダンスを生成する。

    Args:
        analyses: ノード解析結果

    Returns:
        ガイダンス文字列
    """
    lines = ["== ノードの依存推論 ==", ""]

    if not analyses:
        lines.extend(
            [
                "解析対象のノードが見つかりませんでした。",
                "",
            ]
        )
    else:
        for name, analysis in sorted(analyses.items()):
            requires = infer_requires(analysis)
            optional = analysis.optional_reads
            provides = infer_provides(analysis)

            lines.append(f"{name}:")

            if analysis.reads:
                lines.append(f"  使用フィールド: {', '.join(sorted(analysis.reads))}")
            if analysis.optional_reads:
                lines.append(
                    f"  条件付き使用: {', '.join(sorted(analysis.optional_reads))}"
                )
            if analysis.writes:
                lines.append(f"  更新フィールド: {', '.join(sorted(analysis.writes))}")

            lines.append("")
            lines.append("  推奨:")

            # デコレータを生成
            params = []
            if requires:
                params.append(f'requires={sorted(requires)}')
            if optional:
                params.append(f'optional={sorted(optional)}')
            if provides:
                params.append(f'provides={sorted(provides)}')

            if params:
                decorator = f'@node({", ".join(params)})'
            else:
                decorator = "@node"

            lines.append(f"  {decorator}")
            lines.append(f"  def {name}(ctx: ...) -> tuple[..., Outcome]:")
            lines.append("      ...")
            lines.append("")

    lines.extend(
        [
            "",
            "== 手動対応が必要 ==",
            "",
            "1. 各ノードに依存宣言を追加してください（上記の推奨を参照）",
            "2. `railway sync transition` で依存検証を実行してください",
        ]
    )

    return "\n".join(lines)


def migrate_to_field_dependency(
    nodes_dir: Path,
    dry_run: bool = False,
) -> MigrationResult:
    """フィールドベース依存関係へマイグレーションする。

    Args:
        nodes_dir: ノードディレクトリ
        dry_run: True の場合、変更を適用しない

    Returns:
        MigrationResult
    """
    all_analyses: dict[str, NodeAnalysis] = {}
    analyzed_nodes: list[str] = []

    for py_file in nodes_dir.rglob("*.py"):
        # プライベートファイルをスキップ（__init__.py は除く）
        if py_file.name.startswith("_") and py_file.name != "__init__.py":
            continue
        # __init__.py もスキップ
        if py_file.name == "__init__.py":
            continue

        analyses = analyze_node_dependencies(py_file)
        all_analyses.update(analyses)
        analyzed_nodes.extend(analyses.keys())

    guidance = generate_migration_guidance(all_analyses)

    return MigrationResult(
        guidance=guidance,
        analyzed_nodes=tuple(analyzed_nodes),
    )
