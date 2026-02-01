"""Tests for exit node generation during railway new entry (Issue #62).

TDD: Red -> Green -> Refactor
"""

import pytest
from pathlib import Path


class TestGenerateExitNodesFromYaml:
    """YAML コンテンツからの終端ノード生成テスト。"""

    def test_generates_from_yaml_content(self, tmp_path: Path) -> None:
        """YAML コンテンツから終端ノードを生成する。"""
        from railway.cli.new import _generate_exit_nodes_from_yaml

        yaml_content = '''version: "1.0"
entrypoint: test
description: "テスト"

nodes:
  start:
    module: nodes.test.start
    function: start
    description: "開始"
  exit:
    success:
      done:
        description: "正常終了"

start: start

transitions:
  start:
    success::done: exit.success.done
'''
        (tmp_path / "src").mkdir()

        result = _generate_exit_nodes_from_yaml(yaml_content, tmp_path)

        assert len(result.generated) == 1
        assert (tmp_path / "src/nodes/exit/success/done.py").exists()

    def test_generates_multiple_exit_nodes(self, tmp_path: Path) -> None:
        """複数の終端ノードを生成する。"""
        from railway.cli.new import _generate_exit_nodes_from_yaml

        yaml_content = '''version: "1.0"
entrypoint: test
description: "テスト"

nodes:
  start:
    module: nodes.test.start
    function: start
    description: "開始"
  exit:
    success:
      done:
        description: "正常終了"
    failure:
      error:
        description: "エラー終了"

start: start

transitions:
  start:
    success::done: exit.success.done
    failure::error: exit.failure.error
'''
        (tmp_path / "src").mkdir()

        result = _generate_exit_nodes_from_yaml(yaml_content, tmp_path)

        assert len(result.generated) == 2
        assert (tmp_path / "src/nodes/exit/success/done.py").exists()
        assert (tmp_path / "src/nodes/exit/failure/error.py").exists()

    def test_skips_existing_exit_nodes(self, tmp_path: Path) -> None:
        """既存の終端ノードはスキップする。"""
        from railway.cli.new import _generate_exit_nodes_from_yaml

        yaml_content = '''version: "1.0"
entrypoint: test
description: "テスト"

nodes:
  start:
    module: nodes.test.start
    function: start
    description: "開始"
  exit:
    success:
      done:
        description: "正常終了"

start: start

transitions:
  start:
    success::done: exit.success.done
'''
        # 既存ファイルを作成
        exit_path = tmp_path / "src/nodes/exit/success/done.py"
        exit_path.parent.mkdir(parents=True)
        exit_path.write_text("# custom")

        result = _generate_exit_nodes_from_yaml(yaml_content, tmp_path)

        assert len(result.skipped) == 1
        assert len(result.generated) == 0
        assert exit_path.read_text() == "# custom"

    def test_generated_file_is_valid_python(self, tmp_path: Path) -> None:
        """生成されたファイルは有効な Python コード。"""
        from railway.cli.new import _generate_exit_nodes_from_yaml

        yaml_content = '''version: "1.0"
entrypoint: test
description: "テスト"

nodes:
  start:
    module: nodes.test.start
    function: start
    description: "開始"
  exit:
    success:
      done:
        description: "正常終了"

start: start

transitions:
  start:
    success::done: exit.success.done
'''
        (tmp_path / "src").mkdir()

        _generate_exit_nodes_from_yaml(yaml_content, tmp_path)

        file_path = tmp_path / "src/nodes/exit/success/done.py"
        content = file_path.read_text()

        # 構文チェック
        compile(content, "<string>", "exec")

        # ExitContract を使用している
        assert "ExitContract" in content
