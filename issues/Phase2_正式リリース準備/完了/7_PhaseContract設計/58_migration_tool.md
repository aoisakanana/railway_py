# Issue #58: マイグレーションツール

## 概要

`railway update` コマンドにフィールドベース依存関係への自動マイグレーション機能を追加する。
レガシープロジェクト（依存宣言なし）をフィールドベース依存関係パターンに変換する。

## 背景

フィールドベース依存関係は新しいパターンであり、既存プロジェクトは依存宣言がない。
`railway update` で:
1. ノードコードを解析し、使用しているフィールドを推論
2. `@node` デコレータに依存宣言を追加するガイダンスを提供
3. YAML は変更不要（依存情報を含まないため）

## 設計

### マイグレーションの範囲

| 対象 | 自動変換 | 手動対応 |
|------|---------|---------|
| YAML | **変更なし** | - |
| ノードコードの解析 | ✅ 自動 | - |
| 依存宣言の追加 | ❌ | ✅ ガイダンス提供 |
| フィールド使用の推論 | ✅（ベストエフォート） | 確認が必要 |

### 自動変換の流れ

1. **ノードコードの解析**: 各ノードが使用するフィールドを静的解析
2. **依存推論**: `ctx.field_name` のアクセスパターンから依存を推論
3. **ガイダンス生成**: `@node` デコレータに追加すべき宣言を報告

### 出力例

```bash
$ railway update --dry-run

マイグレーション: v0.12.3 → v0.13.0 (フィールドベース依存関係)

== ノードの依存推論 ==

src/nodes/check_host.py:check_host:
  使用フィールド: ctx.incident_id (読み取り)
  更新フィールド: ctx.hostname (書き込み)

  推奨:
  @node(requires=["incident_id"], provides=["hostname"])
  def check_host(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
      ...

src/nodes/escalate.py:escalate:
  使用フィールド: ctx.incident_id, ctx.hostname (読み取り)
  更新フィールド: ctx.escalated (書き込み)

  推奨:
  @node(requires=["incident_id"], optional=["hostname"], provides=["escalated"])
  def escalate(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
      if ctx.hostname:  # optional パターン検出
          ...

== 手動対応が必要 ==

1. 各ノードに依存宣言を追加してください（上記の推奨を参照）
2. `railway sync transition` で依存検証を実行してください

続行しますか？ [y/N]
```

## タスク

### 1. Red Phase: 失敗するテストを作成

`tests/unit/migrations/test_field_dependency_migration.py`:

```python
"""フィールドベース依存関係マイグレーションテスト。"""

import pytest
from railway.migrations.field_dependency import (
    analyze_node_dependencies,
    infer_requires,
    infer_provides,
    generate_migration_guidance,
    NodeAnalysis,
)


class TestAnalyzeNodeDependencies:
    """ノード依存解析テスト。"""

    def test_detects_field_reads(self, tmp_path) -> None:
        """フィールドの読み取りを検出する。"""
        node_file = tmp_path / "check_host.py"
        node_file.write_text('''
from railway import Contract, node
from railway.core.dag import Outcome

class Ctx(Contract):
    incident_id: str
    hostname: str | None = None

@node
def check_host(ctx: Ctx) -> tuple[Ctx, Outcome]:
    result = lookup(ctx.incident_id)  # incident_id を読み取り
    return ctx, Outcome.success("done")
''')

        analysis = analyze_node_dependencies(node_file)

        assert "check_host" in analysis
        assert "incident_id" in analysis["check_host"].reads

    def test_detects_field_writes(self, tmp_path) -> None:
        """フィールドの書き込みを検出する。"""
        node_file = tmp_path / "check_host.py"
        node_file.write_text('''
from railway import Contract, node
from railway.core.dag import Outcome

class Ctx(Contract):
    incident_id: str
    hostname: str | None = None

@node
def check_host(ctx: Ctx) -> tuple[Ctx, Outcome]:
    return ctx.model_copy(update={"hostname": "server1"}), Outcome.success("done")
''')

        analysis = analyze_node_dependencies(node_file)

        assert "hostname" in analysis["check_host"].writes

    def test_detects_optional_pattern(self, tmp_path) -> None:
        """optional パターンを検出する。"""
        node_file = tmp_path / "escalate.py"
        node_file.write_text('''
from railway import Contract, node
from railway.core.dag import Outcome

class Ctx(Contract):
    hostname: str | None = None

@node
def escalate(ctx: Ctx) -> tuple[Ctx, Outcome]:
    if ctx.hostname:  # optional パターン
        notify(ctx.hostname)
    return ctx, Outcome.success("done")
''')

        analysis = analyze_node_dependencies(node_file)

        assert "hostname" in analysis["escalate"].optional_reads


class TestInferDependencies:
    """依存推論テスト。"""

    def test_infer_requires_from_reads(self) -> None:
        """読み取りから requires を推論する。"""
        analysis = NodeAnalysis(
            name="check_host",
            reads=frozenset(["incident_id", "severity"]),
            optional_reads=frozenset(),
            writes=frozenset(),
        )

        requires = infer_requires(analysis)

        assert requires == frozenset(["incident_id", "severity"])

    def test_infer_optional_from_conditional_reads(self) -> None:
        """条件付き読み取りから optional を推論する。"""
        analysis = NodeAnalysis(
            name="escalate",
            reads=frozenset(["incident_id"]),
            optional_reads=frozenset(["hostname"]),
            writes=frozenset(),
        )

        requires = infer_requires(analysis)
        optional = frozenset(analysis.optional_reads)

        assert requires == frozenset(["incident_id"])
        assert optional == frozenset(["hostname"])

    def test_infer_provides_from_writes(self) -> None:
        """書き込みから provides を推論する。"""
        analysis = NodeAnalysis(
            name="check_host",
            reads=frozenset(),
            optional_reads=frozenset(),
            writes=frozenset(["hostname"]),
        )

        provides = infer_provides(analysis)

        assert provides == frozenset(["hostname"])


class TestGenerateMigrationGuidance:
    """マイグレーションガイダンス生成テスト。"""

    def test_generates_decorator_suggestion(self) -> None:
        """デコレータの提案を生成する。"""
        analysis = NodeAnalysis(
            name="check_host",
            reads=frozenset(["incident_id"]),
            optional_reads=frozenset(),
            writes=frozenset(["hostname"]),
        )

        guidance = generate_migration_guidance({"check_host": analysis})

        assert '@node(requires=["incident_id"], provides=["hostname"])' in guidance
        assert "def check_host" in guidance

    def test_includes_optional_in_guidance(self) -> None:
        """optional を含むガイダンスを生成する。"""
        analysis = NodeAnalysis(
            name="escalate",
            reads=frozenset(["incident_id"]),
            optional_reads=frozenset(["hostname"]),
            writes=frozenset(["escalated"]),
        )

        guidance = generate_migration_guidance({"escalate": analysis})

        assert 'optional=["hostname"]' in guidance


class TestMigrationIntegration:
    """マイグレーション統合テスト。"""

    def test_full_migration_flow(self, tmp_path) -> None:
        """完全なマイグレーションフローを実行する。"""
        from railway.migrations.field_dependency import migrate_to_field_dependency

        # テスト用ノードを作成
        nodes_dir = tmp_path / "nodes"
        nodes_dir.mkdir()
        (nodes_dir / "__init__.py").write_text("")
        (nodes_dir / "check_host.py").write_text('''
from railway import Contract, node
from railway.core.dag import Outcome

class Ctx(Contract):
    incident_id: str
    hostname: str | None = None

@node
def check_host(ctx: Ctx) -> tuple[Ctx, Outcome]:
    result = lookup(ctx.incident_id)
    return ctx.model_copy(update={"hostname": result}), Outcome.success("done")
''')

        result = migrate_to_field_dependency(nodes_dir, dry_run=True)

        assert result.guidance is not None
        assert "check_host" in result.guidance
        assert "requires" in result.guidance
        assert "provides" in result.guidance
```

### 2. Green Phase: マイグレーション実装

`railway/migrations/field_dependency.py`:

```python
"""フィールドベース依存関係マイグレーション。

ノードコードを解析し、依存宣言の追加をガイドする。
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
    source = file_path.read_text()
    tree = ast.parse(source)

    results = {}

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
        def __init__(self):
            self.in_conditional = False

        def visit_If(self, node):
            # if ctx.field: パターンを検出
            if isinstance(node.test, ast.Attribute):
                if isinstance(node.test.value, ast.Name) and node.test.value.id == "ctx":
                    optional_reads.add(node.test.attr)

            old_conditional = self.in_conditional
            self.in_conditional = True
            self.generic_visit(node)
            self.in_conditional = old_conditional

        def visit_Attribute(self, node):
            if isinstance(node.value, ast.Name) and node.value.id == "ctx":
                if self.in_conditional:
                    optional_reads.add(node.attr)
                else:
                    reads.add(node.attr)
            self.generic_visit(node)

        def visit_Call(self, node):
            # model_copy(update={...}) パターンを検出
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == "model_copy":
                    for keyword in node.keywords:
                        if keyword.arg == "update" and isinstance(keyword.value, ast.Dict):
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
    """マイグレーションガイダンスを生成する。"""
    lines = ["== ノードの依存推論 ==", ""]

    for name, analysis in analyses.items():
        requires = infer_requires(analysis)
        optional = analysis.optional_reads
        provides = infer_provides(analysis)

        lines.append(f"{name}:")

        if analysis.reads:
            lines.append(f"  使用フィールド: {', '.join(sorted(analysis.reads))}")
        if analysis.optional_reads:
            lines.append(f"  条件付き使用: {', '.join(sorted(analysis.optional_reads))}")
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
            decorator = '@node'

        lines.append(f"  {decorator}")
        lines.append(f"  def {name}(ctx: ...) -> tuple[..., Outcome]:")
        lines.append("      ...")
        lines.append("")

    lines.extend([
        "",
        "== 手動対応が必要 ==",
        "",
        "1. 各ノードに依存宣言を追加してください（上記の推奨を参照）",
        "2. `railway sync transition` で依存検証を実行してください",
    ])

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
        if py_file.name.startswith("_"):
            continue

        analyses = analyze_node_dependencies(py_file)
        all_analyses.update(analyses)
        analyzed_nodes.extend(analyses.keys())

    guidance = generate_migration_guidance(all_analyses)

    return MigrationResult(
        guidance=guidance,
        analyzed_nodes=tuple(analyzed_nodes),
    )
```

### 3. CLI 統合

`railway/cli/commands/update.py` を更新:

```python
def run_update(dry_run: bool = False, ...):
    """プロジェクトを最新バージョンに更新する。"""
    # ... 既存のマイグレーション ...

    # フィールドベース依存関係マイグレーション
    if needs_field_dependency_migration():
        from railway.migrations.field_dependency import migrate_to_field_dependency

        nodes_dir = Path("src/nodes")
        if nodes_dir.exists():
            result = migrate_to_field_dependency(nodes_dir, dry_run=dry_run)
            print(result.guidance)
```

### 4. Refactor Phase

- AST 解析の精度向上
- より多くのパターンの検出
- エラーハンドリングの改善

## 完了条件

- [ ] `railway update` がフィールドベース依存関係マイグレーションを実行する
- [ ] `--dry-run` で解析結果をプレビューできる
- [ ] ノードのフィールドアクセスが解析される
- [ ] 依存宣言のガイダンスが出力される
- [ ] すべてのテストが通過

## 依存関係

- Issue #50-57 がすべて完了していること

## 関連ファイル

- `railway/migrations/field_dependency.py` (新規)
- `railway/cli/commands/update.py` (更新)
- `tests/unit/migrations/test_field_dependency_migration.py` (新規)
