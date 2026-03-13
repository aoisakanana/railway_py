"""Tests for linear mode removal (Issue 34-01).

--mode linear CLI機能が完全に削除されていることを保証する:
1. EntryMode enum が存在しない
2. NodeMode enum が存在しない
3. linear テンプレート関数が存在しない
4. new コマンドに --mode オプションが存在しない
5. init で TUTORIAL_linear.md が生成されない
6. TUTORIAL から linear 関連の参照が削除されている
"""

import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestLinearEnumsRemoved:
    """EntryMode, NodeMode enum が存在しないこと。"""

    def test_entry_mode_not_exists(self) -> None:
        """EntryMode enum が railway.cli.new に存在しないこと。"""
        import railway.cli.new as new_module

        assert not hasattr(new_module, "EntryMode")

    def test_node_mode_not_exists(self) -> None:
        """NodeMode enum が railway.cli.new に存在しないこと。"""
        import railway.cli.new as new_module

        assert not hasattr(new_module, "NodeMode")


class TestLinearTemplateFunctionsRemoved:
    """linear テンプレート関数が存在しないこと。"""

    def test_get_linear_entry_template_not_exists(self) -> None:
        """_get_linear_entry_template が存在しないこと。"""
        import railway.cli.new as new_module

        assert not hasattr(new_module, "_get_linear_entry_template")

    def test_get_linear_node_template_not_exists(self) -> None:
        """_get_linear_node_template が存在しないこと。"""
        import railway.cli.new as new_module

        assert not hasattr(new_module, "_get_linear_node_template")

    def test_get_linear_node_standalone_template_not_exists(self) -> None:
        """_get_linear_node_standalone_template が存在しないこと。"""
        import railway.cli.new as new_module

        assert not hasattr(new_module, "_get_linear_node_standalone_template")

    def test_get_linear_node_input_template_not_exists(self) -> None:
        """_get_linear_node_input_template が存在しないこと。"""
        import railway.cli.new as new_module

        assert not hasattr(new_module, "_get_linear_node_input_template")

    def test_get_linear_node_output_template_not_exists(self) -> None:
        """_get_linear_node_output_template が存在しないこと。"""
        import railway.cli.new as new_module

        assert not hasattr(new_module, "_get_linear_node_output_template")

    def test_get_linear_node_test_standalone_template_not_exists(self) -> None:
        """_get_linear_node_test_standalone_template が存在しないこと。"""
        import railway.cli.new as new_module

        assert not hasattr(new_module, "_get_linear_node_test_standalone_template")


class TestCreateLinearEntryRemoved:
    """_create_linear_entry が存在しないこと。"""

    def test_create_linear_entry_not_exists(self) -> None:
        """_create_linear_entry が存在しないこと。"""
        import railway.cli.new as new_module

        assert not hasattr(new_module, "_create_linear_entry")


class TestModeOptionRemoved:
    """new コマンドに --mode オプションが存在しないこと。"""

    def test_mode_option_not_accepted_for_entry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """railway new entry に --mode オプションを渡すとエラーになること。"""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        (tmp_path / "src" / "nodes").mkdir(parents=True)
        (tmp_path / "transition_graphs").mkdir()
        (tmp_path / "_railway" / "generated").mkdir(parents=True)
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"')

        result = runner.invoke(app, ["new", "entry", "my_workflow", "--mode", "dag"])
        # --mode オプションが存在しないのでエラーになるべき
        assert result.exit_code != 0

    def test_mode_option_not_accepted_for_node(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """railway new node に --mode オプションを渡すとエラーになること。"""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        (tmp_path / "src" / "nodes").mkdir(parents=True)
        (tmp_path / "tests" / "nodes").mkdir(parents=True)

        result = runner.invoke(app, ["new", "node", "my_node", "--mode", "dag"])
        # --mode オプションが存在しないのでエラーになるべき
        assert result.exit_code != 0


class TestTutorialLinearRemoved:
    """init で TUTORIAL_linear.md が生成されないこと。"""

    def test_tutorial_linear_not_created(self) -> None:
        """TUTORIAL_linear.md が生成されないこと。"""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)
            assert not (project_path / "TUTORIAL_linear.md").exists()

    def test_create_tutorial_linear_md_not_exists(self) -> None:
        """_create_tutorial_linear_md 関数が存在しないこと。"""
        import railway.cli.init as init_module

        assert not hasattr(init_module, "_create_tutorial_linear_md")


class TestTutorialLinearReferencesRemoved:
    """TUTORIAL テンプレートから linear 関連の参照が削除されていること。"""

    def test_tutorial_no_linear_reference(self) -> None:
        """TUTORIAL テンプレートに linear への参照がないこと。"""
        from railway.cli.init import _get_tutorial_content

        content = _get_tutorial_content("test_project")
        assert "TUTORIAL_linear" not in content
        assert "--mode linear" not in content

    def test_tutorial_no_step5_4_linear(self) -> None:
        """Step 5.4 の linear モード参考セクションが削除されていること。"""
        from railway.cli.init import _get_tutorial_content

        content = _get_tutorial_content("test_project")
        # Step 5.4 に linear の言及がないこと
        assert "linear モード（参考）" not in content


class TestDefaultBehaviorUnchanged:
    """デフォルト動作（dag モード）が変わらないこと。"""

    def test_entry_still_creates_dag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """railway new entry がデフォルトで dag モードを生成すること。"""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        (tmp_path / "src" / "nodes").mkdir(parents=True)
        (tmp_path / "transition_graphs").mkdir()
        (tmp_path / "_railway" / "generated").mkdir(parents=True)
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"')

        result = runner.invoke(app, ["new", "entry", "my_workflow"])
        assert result.exit_code == 0

        entry_file = tmp_path / "src" / "my_workflow.py"
        assert entry_file.exists()
        content = entry_file.read_text()
        assert "from _railway.generated.my_workflow_transitions import run" in content

    def test_node_still_creates_dag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """railway new node がデフォルトで dag モードを生成すること。"""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        (tmp_path / "src" / "nodes").mkdir(parents=True)
        (tmp_path / "tests" / "nodes").mkdir(parents=True)

        result = runner.invoke(app, ["new", "node", "my_node"])
        assert result.exit_code == 0

        node_file = tmp_path / "src" / "nodes" / "my_node.py"
        assert node_file.exists()
        content = node_file.read_text()
        assert "def my_node(board)" in content
        assert "Outcome" in content
