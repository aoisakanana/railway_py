"""Tests for スタブ生成の module: 尊重 (v0.13.25 Issue 03, master 0ec2946 のバックポート).

- YAML の明示 `module:` を持つノードのスタブは module パスに生成される
- module 省略ノードは従来どおり規約パス（回帰防止）
- 生成 transitions の import と生成物ファイルが整合する
- init 同梱 hello YAML は規約パス（nodes.hello.greet）を使う
"""
from pathlib import Path

import pytest

from railway.core.dag.parser import load_transition_graph


_EXPLICIT_MODULE_YAML = '''version: "1.0"
entrypoint: hello
description: "explicit module"

nodes:
  greet:
    module: nodes.greet
    function: greet
    description: "greet"

  exit:
    success:
      done:
        description: "done"

start: greet

transitions:
  greet:
    success::done: exit.success.done
'''

_CONVENTION_YAML = '''version: "1.0"
entrypoint: hello
description: "convention module"

nodes:
  greet:
    description: "greet"

  exit:
    success:
      done:
        description: "done"

start: greet

transitions:
  greet:
    success::done: exit.success.done
'''


def _load_graph(tmp_path: Path, yaml_text: str):
    yaml_path = tmp_path / "hello_20260101000000.yml"
    yaml_path.write_text(yaml_text)
    return load_transition_graph(yaml_path)


class TestHasExplicitModule:
    """_has_explicit_module 純粋関数（master 0ec2946 と同一構造）。"""

    def test_explicit_module_detected(self, tmp_path: Path) -> None:
        from railway.cli.sync import _has_explicit_module
        graph = _load_graph(tmp_path, _EXPLICIT_MODULE_YAML)
        greet = next(n for n in graph.nodes if n.name == "greet")
        assert _has_explicit_module(greet, "hello") is True

    def test_convention_module_not_explicit(self, tmp_path: Path) -> None:
        from railway.cli.sync import _has_explicit_module
        graph = _load_graph(tmp_path, _CONVENTION_YAML)
        greet = next(n for n in graph.nodes if n.name == "greet")
        assert _has_explicit_module(greet, "hello") is False


class TestStubGenerationHonorsModule:
    """スタブ生成が module: を尊重する。"""

    def test_explicit_module_stub_at_module_path(self, tmp_path: Path) -> None:
        from railway.cli.sync import sync_regular_nodes
        graph = _load_graph(tmp_path, _EXPLICIT_MODULE_YAML)
        result = sync_regular_nodes(graph, tmp_path)

        assert (tmp_path / "src/nodes/greet.py").exists(), (
            "module: nodes.greet のスタブは src/nodes/greet.py に生成されるべき"
        )
        assert not (tmp_path / "src/nodes/hello/greet.py").exists(), (
            "規約パスに誤ったスタブを生成してはならない"
        )
        assert (tmp_path / "src/nodes/greet.py") in result.generated

    def test_explicit_module_existing_file_skipped(self, tmp_path: Path) -> None:
        from railway.cli.sync import sync_regular_nodes
        graph = _load_graph(tmp_path, _EXPLICIT_MODULE_YAML)
        target = tmp_path / "src/nodes/greet.py"
        target.parent.mkdir(parents=True)
        target.write_text("# user implementation\n")

        result = sync_regular_nodes(graph, tmp_path)
        assert target.read_text() == "# user implementation\n", "既存実装を上書きしない"
        assert target in result.skipped

    def test_convention_module_unchanged(self, tmp_path: Path) -> None:
        """module 省略ノードは従来どおり規約パス（回帰防止）。"""
        from railway.cli.sync import sync_regular_nodes
        graph = _load_graph(tmp_path, _CONVENTION_YAML)
        sync_regular_nodes(graph, tmp_path)
        assert (tmp_path / "src/nodes/hello/greet.py").exists()


class TestGeneratedImportsResolvable:
    """生成 transitions の import 対象ファイルが sync 後すべて実在する（結果の性質）。"""

    @pytest.mark.parametrize("yaml_text", [_EXPLICIT_MODULE_YAML, _CONVENTION_YAML])
    def test_all_node_imports_have_files(self, tmp_path: Path, yaml_text: str) -> None:
        from railway.core.dag.codegen import generate_transition_code
        from railway.cli.sync import sync_exit_nodes, sync_regular_nodes

        graph = _load_graph(tmp_path, yaml_text)
        sync_regular_nodes(graph, tmp_path)
        sync_exit_nodes(graph, tmp_path)
        code = generate_transition_code(graph, "hello.yml")

        for line in code.splitlines():
            if line.startswith("from nodes.") and " import " in line:
                module = line.split(" import ")[0].removeprefix("from ")
                expected = tmp_path / "src" / (module.replace(".", "/") + ".py")
                assert expected.exists(), (
                    f"import 対象が存在しない: {line} -> {expected}"
                )


class TestInitHelloYamlConvention:
    """init 同梱 hello YAML は現行規約（nodes.hello.greet）を使う。"""

    def test_sample_yaml_uses_convention_path(self) -> None:
        from railway.cli.init import _get_sample_transition_yaml
        yaml_text = _get_sample_transition_yaml()
        assert "module: nodes.hello.greet" in yaml_text
        assert "module: nodes.greet\n" not in yaml_text
