"""Tests for スタブ生成の function: 尊重と同一 module 複数ノード対応 (v0.13.26 Issue 02).

- 明示 `function:` がスタブの関数名に反映される
- 同一 module を共有する複数ノードの全関数が 1 ファイルに生成される
- 生成後検証: sync 成功なら生成 transitions の全 import が関数レベルで解決可能
- 偽陽性ポリシー: 再エクスポート等の束縛は失敗にしない、判定不能（import *）は警告
"""
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from railway.core.dag.parser import load_transition_graph

_CUSTOM_YAML = '''version: "1.0"
entrypoint: custom
description: "custom"

nodes:
  work:
    module: custom_nodes.special
    function: perform
    description: "explicit function"
  exit:
    success:
      done:
        description: "done"

start: work

transitions:
  work:
    success::done: exit.success.done
'''

_MULTI_YAML = '''version: "1.0"
entrypoint: multi
description: "multi"

nodes:
  first_step:
    module: shared.ops
    function: first_step
    description: "1st"
  second_step:
    module: shared.ops
    function: second_step
    description: "2nd"
  exit:
    success:
      done:
        description: "done"

start: first_step

transitions:
  first_step:
    success::go: second_step
  second_step:
    success::done: exit.success.done
'''


def _write_yaml(project: Path, name: str, content: str) -> None:
    (project / "transition_graphs").mkdir(exist_ok=True)
    (project / f"transition_graphs/{name}_20260101000000.yml").write_text(content)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def project(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "transition_graphs").mkdir()
    (tmp_path / "_railway/generated").mkdir(parents=True)
    old = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(old)


class TestFunctionNameInStub:
    """明示 `function:` がスタブに反映される（単体）。"""

    def test_explicit_function_name_used(self, tmp_path: Path) -> None:
        from railway.core.dag.skeleton import SkeletonSpec, generate_regular_node_content
        spec = SkeletonSpec(
            node_name="work",
            module_path="custom_nodes.special",
            entrypoint="custom",
            is_exit_node=False,
            function_name="perform",
        )
        content = generate_regular_node_content(spec)
        assert "def perform(" in content
        assert "def work(" not in content

    def test_default_function_name_is_leaf(self, tmp_path: Path) -> None:
        """function_name 未指定は従来どおり node_name の leaf（回帰防止）。"""
        from railway.core.dag.skeleton import SkeletonSpec, generate_regular_node_content
        spec = SkeletonSpec(
            node_name="check_time",
            module_path="nodes.greeting.check_time",
            entrypoint="greeting",
            is_exit_node=False,
        )
        content = generate_regular_node_content(spec)
        assert "def check_time(" in content


class TestSyncGeneratesImportableStubs:
    """統合: sync 後、生成 transitions が import 可能（報告ケース）。"""

    def test_case1_explicit_function(self, runner: CliRunner, project: Path) -> None:
        from railway.cli.main import app
        _write_yaml(project, "custom", _CUSTOM_YAML)
        r = runner.invoke(app, ["sync", "transition", "--entry", "custom"])
        assert r.exit_code == 0, r.output

        stub = (project / "src/custom_nodes/special.py").read_text()
        assert "def perform(" in stub

    def test_case2_multi_nodes_same_module(
        self, runner: CliRunner, project: Path
    ) -> None:
        from railway.cli.main import app
        _write_yaml(project, "multi", _MULTI_YAML)
        r = runner.invoke(app, ["sync", "transition", "--entry", "multi"])
        assert r.exit_code == 0, r.output

        stub = (project / "src/shared/ops.py").read_text()
        assert "def first_step(" in stub
        assert "def second_step(" in stub

    @pytest.mark.parametrize("name,yaml_text", [
        ("custom", _CUSTOM_YAML), ("multi", _MULTI_YAML),
    ])
    def test_property_all_imports_resolvable(
        self, runner: CliRunner, project: Path, name: str, yaml_text: str
    ) -> None:
        """結果の性質: sync 成功なら生成 transitions の全ノード import が
        関数レベルで解決可能（`from nodes.` 以外の module も含む）。"""
        import ast as ast_mod
        from railway.cli.main import app
        _write_yaml(project, name, yaml_text)
        r = runner.invoke(app, ["sync", "transition", "--entry", name])
        assert r.exit_code == 0, r.output

        gen = (project / f"_railway/generated/{name}_transitions.py").read_text()
        for line in gen.splitlines():
            if not (line.startswith("from ") and " import " in line):
                continue
            module = line.split(" import ")[0].removeprefix("from ")
            if module.startswith("railway") or module in ("typing",):
                continue
            src_file = project / "src" / (module.replace(".", "/") + ".py")
            assert src_file.exists(), f"module 実体なし: {line}"
            imported = line.split(" import ")[1]
            names = [
                part.strip().split(" as ")[0] for part in imported.split(",")
            ]
            tree = ast_mod.parse(src_file.read_text())
            defined = {
                n.name for n in tree.body
                if isinstance(n, (ast_mod.FunctionDef, ast_mod.AsyncFunctionDef))
            }
            for fn in names:
                assert fn in defined, f"関数未定義: {fn} in {module}"


class TestMissingFunctionDetection:
    """既存ファイルの不足関数は上書きせず警告 + 失敗扱い。"""

    def test_existing_file_missing_function_fails_with_warning(
        self, runner: CliRunner, project: Path
    ) -> None:
        from railway.cli.main import app
        _write_yaml(project, "multi", _MULTI_YAML)
        ops = project / "src/shared/ops.py"
        ops.parent.mkdir(parents=True)
        ops.write_text(
            "from railway import node\n"
            "from railway.core.dag import Outcome\n\n\n"
            "@node\n"
            "def first_step(ctx=None):\n"
            '    return ctx, Outcome.success("go")\n'
        )
        r = runner.invoke(app, ["sync", "transition", "--entry", "multi"])
        assert r.exit_code == 1, f"不足関数があるのに成功扱い: {r.output}"
        combined = r.output + (r.stderr or "")
        assert "second_step" in combined, "不足関数名を具体的に通知すべき"
        # ユーザー実装は上書きされない
        assert "def second_step" not in ops.read_text()


class TestFalsePositivePolicy:
    """偽陽性ポリシー: 再エクスポートは成功、import * は警告どまり。"""

    def test_reexport_binding_succeeds(
        self, runner: CliRunner, project: Path
    ) -> None:
        from railway.cli.main import app
        _write_yaml(project, "custom", _CUSTOM_YAML)
        pkg = project / "src/custom_nodes"
        pkg.mkdir(parents=True)
        (pkg / "impl.py").write_text(
            "from railway import node\n"
            "from railway.core.dag import Outcome\n\n\n"
            "@node\n"
            "def perform(ctx=None):\n"
            '    return ctx, Outcome.success("done")\n'
        )
        (pkg / "special.py").write_text(
            "from custom_nodes.impl import perform\n\n"
            '__all__ = ["perform"]\n'
        )
        r = runner.invoke(app, ["sync", "transition", "--entry", "custom"])
        assert r.exit_code == 0, (
            f"再エクスポートによる束縛を失敗扱いにしてはならない: {r.output}"
        )

    def test_star_import_warns_but_succeeds(
        self, runner: CliRunner, project: Path
    ) -> None:
        from railway.cli.main import app
        _write_yaml(project, "custom", _CUSTOM_YAML)
        pkg = project / "src/custom_nodes"
        pkg.mkdir(parents=True)
        (pkg / "special.py").write_text("from custom_nodes.impl import *\n")
        r = runner.invoke(app, ["sync", "transition", "--entry", "custom"])
        assert r.exit_code == 0, (
            f"判定不能（import *）は失敗ではなく警告に落とすべき: {r.output}"
        )


class TestConventionalNodesRegression:
    """規約パスノードの従来挙動に回帰なし。"""

    def test_conventional_yaml_still_works(
        self, runner: CliRunner, project: Path
    ) -> None:
        from railway.cli.main import app
        _write_yaml(project, "plain", '''version: "1.0"
entrypoint: plain
description: "plain"
nodes:
  begin:
    description: "begin"
  exit:
    success:
      done:
        description: "done"
start: begin
transitions:
  begin:
    success::done: exit.success.done
''')
        r = runner.invoke(app, ["sync", "transition", "--entry", "plain"])
        assert r.exit_code == 0, r.output
        assert (project / "src/nodes/plain/begin.py").exists()
