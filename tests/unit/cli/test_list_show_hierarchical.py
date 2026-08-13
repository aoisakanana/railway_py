"""Tests for list/show の階層ノード対応と記法統一 (v0.13.25 Issue 04).

- discovery の再帰化（rglob）とドット記法正規化
- show のドット記法受理（スラッシュは後方互換）
- 完全名 exact match 優先・短縮名一意解決・複数一致は候補列挙エラー
- Statistics の「N test files」表記
- show の Output が戻り値注釈を表示する
"""
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner


_NODE_TEMPLATE = '''"""{desc}"""
from railway import node
from railway.core.dag.outcome import Outcome


@node
def {func}(ctx: dict) -> tuple[dict, Outcome]:
    return ctx, Outcome.success("done")
'''


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def project(tmp_path: Path):
    """階層ノードを含むプロジェクト構造。"""
    src = tmp_path / "src"
    nodes = src / "nodes"
    for rel, func in [
        ("check_status.py", "check_status"),          # フラット
        ("processing/validate.py", "validate"),       # 階層
        ("sub/deep/process.py", "process"),           # 深い階層
        ("exit/success/done.py", "done"),             # exit 配下（一覧対象外）
    ]:
        p = nodes / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_NODE_TEMPLATE.format(desc=f"node {func}", func=func))
    (src / "hello.py").write_text('"""entry"""\nfrom railway import entry_point\n')
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_a.py").write_text("def test_a():\n    assert True\n")
    (tmp_path / "tests/test_b.py").write_text(
        "def test_b1():\n    assert True\n\ndef test_b2():\n    assert True\n"
    )
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n")
    old = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(old)


class TestListHierarchical:
    """list が階層ノードを発見する。"""

    def test_hierarchical_nodes_listed_with_dot_names(
        self, runner: CliRunner, project: Path
    ) -> None:
        from railway.cli.main import app
        result = runner.invoke(app, ["list"])
        assert "check_status" in result.stdout
        assert "processing.validate" in result.stdout
        assert "sub.deep.process" in result.stdout

    def test_exit_subtree_not_listed(self, runner: CliRunner, project: Path) -> None:
        from railway.cli.main import app
        result = runner.invoke(app, ["list"])
        assert "exit.success.done" not in result.stdout

    def test_statistics_node_count_accurate(
        self, runner: CliRunner, project: Path
    ) -> None:
        from railway.cli.main import app
        result = runner.invoke(app, ["list"])
        assert "3 nodes" in result.stdout, f"実数 3 と一致すべき: {result.stdout}"

    def test_statistics_test_files_label(
        self, runner: CliRunner, project: Path
    ) -> None:
        from railway.cli.main import app
        result = runner.invoke(app, ["list"])
        assert "2 test files" in result.stdout, (
            f"ファイル数は 'test files' と表記すべき: {result.stdout}"
        )


class TestShowDotNotation:
    """show のドット記法受理と解決規則。"""

    def test_dot_notation_resolves(self, runner: CliRunner, project: Path) -> None:
        from railway.cli.main import app
        result = runner.invoke(app, ["show", "node", "processing.validate"])
        assert result.exit_code == 0, result.stdout
        assert "validate" in result.stdout

    def test_slash_notation_still_works(
        self, runner: CliRunner, project: Path
    ) -> None:
        from railway.cli.main import app
        result = runner.invoke(app, ["show", "node", "processing/validate"])
        assert result.exit_code == 0

    def test_short_name_unique_resolves(
        self, runner: CliRunner, project: Path
    ) -> None:
        from railway.cli.main import app
        result = runner.invoke(app, ["show", "node", "process"])
        assert result.exit_code == 0
        assert "sub/deep/process.py" in result.stdout

    def test_short_name_ambiguous_lists_candidates(
        self, runner: CliRunner, project: Path
    ) -> None:
        from railway.cli.main import app
        # 2つ目の validate を作って曖昧にする
        p = project / "src/nodes/other/validate.py"
        p.parent.mkdir(parents=True)
        p.write_text(_NODE_TEMPLATE.format(desc="other validate", func="validate"))

        result = runner.invoke(app, ["show", "node", "validate"])
        assert result.exit_code == 1
        combined = result.stdout + (result.stderr or "")
        assert "processing.validate" in combined
        assert "other.validate" in combined

    def test_exact_full_name_beats_short_name(
        self, runner: CliRunner, project: Path
    ) -> None:
        """フラット validate.py と processing/validate.py 共存時、
        'validate' は完全名 exact match（フラット側）に解決される。"""
        from railway.cli.main import app
        flat = project / "src/nodes/validate.py"
        flat.write_text(_NODE_TEMPLATE.format(desc="flat validate", func="validate"))

        result = runner.invoke(app, ["show", "node", "validate"])
        assert result.exit_code == 0
        assert "src/nodes/validate.py" in result.stdout


class TestShowOutputAnnotation:
    """show の Output が戻り値注釈を表示する（UX-4 後半）。"""

    def test_return_annotation_displayed(
        self, runner: CliRunner, project: Path
    ) -> None:
        from railway.cli.main import app
        result = runner.invoke(app, ["show", "node", "check_status"])
        assert result.exit_code == 0
        assert "(untyped)" not in result.stdout
        assert "tuple[dict, Outcome]" in result.stdout


class TestContractsRecursiveDiscovery:
    """contracts の discovery も再帰化されている（Issue 04 Refactor）。"""

    def test_nested_contract_listed(self, runner: CliRunner, project: Path) -> None:
        from railway.cli.main import app
        p = project / "src/contracts/processing/validate_context.py"
        p.parent.mkdir(parents=True)
        p.write_text(
            '"""contract"""\n'
            "from railway import Contract\n\n\n"
            "class ValidateContext(Contract):\n"
            "    value: str\n"
        )
        result = runner.invoke(app, ["list", "contracts"])
        assert "ValidateContext" in result.stdout


class TestListDescriptionFallback:
    """モジュール docstring がないノードは関数 docstring を表示 (v0.13.26 NEW-6)。"""

    def test_function_docstring_fallback(self, runner: CliRunner, project: Path) -> None:
        from railway.cli.main import app
        p = project / "src/nodes/nodoc.py"
        p.write_text(
            "from railway import node\n"
            "from railway.core.dag.outcome import Outcome\n\n\n"
            "@node\n"
            "def nodoc(ctx: dict) -> tuple[dict, Outcome]:\n"
            '    """関数側の説明テキスト"""\n'
            '    return ctx, Outcome.success("done")\n'
        )
        result = runner.invoke(app, ["list"])
        assert "関数側の説明テキスト" in result.stdout
        line = next(l for l in result.stdout.splitlines() if "nodoc" in l)
        assert "No description" not in line
