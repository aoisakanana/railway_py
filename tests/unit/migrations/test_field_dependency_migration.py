"""フィールドベース依存関係マイグレーションテスト。

TDD Red Phase: このテストは最初は失敗する
"""

import pytest
from pathlib import Path

from railway.migrations.field_dependency import (
    analyze_node_dependencies,
    infer_requires,
    infer_provides,
    generate_migration_guidance,
    migrate_to_field_dependency,
    NodeAnalysis,
)


class TestAnalyzeNodeDependencies:
    """ノード依存解析テスト。"""

    def test_detects_field_reads(self, tmp_path: Path) -> None:
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

    def test_detects_field_writes(self, tmp_path: Path) -> None:
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

    def test_detects_optional_pattern(self, tmp_path: Path) -> None:
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

    def test_ignores_non_node_functions(self, tmp_path: Path) -> None:
        """@node デコレータのない関数は無視する。"""
        node_file = tmp_path / "helpers.py"
        node_file.write_text('''
def helper_function(ctx):
    return ctx.incident_id
''')

        analysis = analyze_node_dependencies(node_file)

        assert len(analysis) == 0

    def test_handles_node_decorator_with_args(self, tmp_path: Path) -> None:
        """引数付き @node デコレータを処理する。"""
        node_file = tmp_path / "my_node.py"
        node_file.write_text('''
from railway import Contract, node
from railway.core.dag import Outcome


class Ctx(Contract):
    field_a: str


@node(name="custom_name")
def my_node(ctx: Ctx) -> tuple[Ctx, Outcome]:
    x = ctx.field_a
    return ctx, Outcome.success("done")
''')

        analysis = analyze_node_dependencies(node_file)

        assert "my_node" in analysis
        assert "field_a" in analysis["my_node"].reads


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

        # Python の sorted() はシングルクォートでリストを出力する
        assert "requires=['incident_id']" in guidance
        assert "provides=['hostname']" in guidance
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

        assert "optional=['hostname']" in guidance

    def test_empty_analysis_generates_minimal_guidance(self) -> None:
        """解析結果が空の場合もガイダンスを生成する。"""
        guidance = generate_migration_guidance({})

        assert "ノードの依存推論" in guidance


class TestMigrationIntegration:
    """マイグレーション統合テスト。"""

    def test_full_migration_flow(self, tmp_path: Path) -> None:
        """完全なマイグレーションフローを実行する。"""
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

    def test_skips_private_files(self, tmp_path: Path) -> None:
        """プライベートファイル（_で始まる）をスキップする。"""
        nodes_dir = tmp_path / "nodes"
        nodes_dir.mkdir()
        (nodes_dir / "__init__.py").write_text("")
        (nodes_dir / "_private.py").write_text('''
from railway import node

@node
def private_node(ctx):
    return ctx.secret_field
''')

        result = migrate_to_field_dependency(nodes_dir, dry_run=True)

        assert "private_node" not in result.guidance

    def test_handles_subdirectories(self, tmp_path: Path) -> None:
        """サブディレクトリのノードも解析する。"""
        nodes_dir = tmp_path / "nodes"
        sub_dir = nodes_dir / "alert"
        sub_dir.mkdir(parents=True)
        (nodes_dir / "__init__.py").write_text("")
        (sub_dir / "__init__.py").write_text("")
        (sub_dir / "check_severity.py").write_text('''
from railway import Contract, node
from railway.core.dag import Outcome


class Ctx(Contract):
    severity: str


@node
def check_severity(ctx: Ctx) -> tuple[Ctx, Outcome]:
    return ctx, Outcome.success(ctx.severity)
''')

        result = migrate_to_field_dependency(nodes_dir, dry_run=True)

        assert "check_severity" in result.guidance
        assert "severity" in result.guidance
