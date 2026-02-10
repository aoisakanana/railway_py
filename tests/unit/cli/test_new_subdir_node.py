"""Tests for railway new node with hierarchical (dotted) paths.

ドット区切り階層ノード:
- `railway new node processing.validate` → src/nodes/processing/validate.py
- スラッシュはCLIレベルで拒否される（test_new_name_validation.pyで検証）
- 中間ディレクトリは自動作成される
- 関数名は最終セグメント（validate）
"""

import os
import tempfile
from pathlib import Path

from typer.testing import CliRunner

runner = CliRunner()


def _setup_project_dir(tmpdir: str) -> None:
    """Set up minimal project structure for tests."""
    p = Path(tmpdir)
    (p / "src").mkdir()
    (p / "src" / "__init__.py").touch()
    (p / "src" / "nodes").mkdir()
    (p / "src" / "contracts").mkdir()
    (p / "src" / "contracts" / "__init__.py").write_text('"""Contract modules."""\n')
    (p / "tests").mkdir()
    (p / "tests" / "nodes").mkdir(parents=True)


class TestNewNodeDottedPath:
    """railway new node processing.validate のドット区切り対応テスト."""

    def test_dotted_node_creates_subdirectory(self) -> None:
        """ドット区切りノードで中間ディレクトリが作成されること."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "node", "processing.validate"])
                assert result.exit_code == 0, f"Failed with: {result.output}"

                node_path = (
                    Path(tmpdir) / "src" / "nodes" / "processing" / "validate.py"
                )
                assert node_path.exists(), f"Node file not found: {node_path}"
            finally:
                os.chdir(original_cwd)

    def test_dotted_node_function_name_is_leaf(self) -> None:
        """生成コード内の関数名が最終セグメントであること."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "node", "processing.validate"])

                node_path = (
                    Path(tmpdir) / "src" / "nodes" / "processing" / "validate.py"
                )
                content = node_path.read_text()
                assert "def validate(" in content
                assert "def processing" not in content
            finally:
                os.chdir(original_cwd)

    def test_dotted_node_import_path_uses_dots(self) -> None:
        """生成コード内の import パスがドット区切りであること."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "node", "processing.validate"])

                node_path = (
                    Path(tmpdir) / "src" / "nodes" / "processing" / "validate.py"
                )
                content = node_path.read_text()
                assert "from contracts.processing.validate_context import" in content
            finally:
                os.chdir(original_cwd)

    def test_dotted_node_contract_in_subdirectory(self) -> None:
        """Contract ファイルがサブディレクトリに作成されること."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "node", "processing.validate"])

                contract_path = (
                    Path(tmpdir)
                    / "src"
                    / "contracts"
                    / "processing"
                    / "validate_context.py"
                )
                assert contract_path.exists(), f"Contract not found: {contract_path}"
            finally:
                os.chdir(original_cwd)

    def test_dotted_node_test_in_subdirectory(self) -> None:
        """テストファイルがサブディレクトリに作成されること."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "node", "processing.validate"])

                test_path = (
                    Path(tmpdir) / "tests" / "nodes" / "processing" / "test_validate.py"
                )
                assert test_path.exists(), f"Test file not found: {test_path}"
            finally:
                os.chdir(original_cwd)

    def test_dotted_node_cli_output_shows_correct_test_path(self) -> None:
        """CLI出力のテストファイルパスが実際の配置と一致すること."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "node", "processing.validate"])
                assert result.exit_code == 0

                # CLI出力が正しいパスを表示すること
                assert "Created tests/nodes/processing/test_validate.py" in result.output
                # 誤ったパスが表示されないこと
                assert "Created tests/nodes/test_validate.py\n" not in result.output
            finally:
                os.chdir(original_cwd)

    def test_deep_dotted_node_cli_output_shows_correct_test_path(self) -> None:
        """深い階層ノードのCLI出力テストファイルパスが正しいこと."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "node", "sub.deep.process"])
                assert result.exit_code == 0

                assert "Created tests/nodes/sub/deep/test_process.py" in result.output
                assert "Created tests/nodes/test_process.py\n" not in result.output
            finally:
                os.chdir(original_cwd)

    def test_flat_node_cli_output_unchanged(self) -> None:
        """フラットノードのCLI出力は従来通り."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "node", "check_status"])
                assert result.exit_code == 0

                assert "Created tests/nodes/test_check_status.py" in result.output
            finally:
                os.chdir(original_cwd)

    def test_slash_node_rejected_at_cli(self) -> None:
        """CLI 経由でスラッシュノード名が拒否されること."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "node", "greeting/farewell"])
                assert result.exit_code != 0
                assert "greeting.farewell" in result.output
            finally:
                os.chdir(original_cwd)

    def test_deep_dotted_node(self) -> None:
        """深いドット区切り（3段以上）でもファイルが作成されること."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "node", "sub.deep.process"])
                assert result.exit_code == 0, f"Failed with: {result.output}"

                node_path = (
                    Path(tmpdir)
                    / "src"
                    / "nodes"
                    / "sub"
                    / "deep"
                    / "process.py"
                )
                assert node_path.exists()
                content = node_path.read_text()
                assert "def process(" in content
                assert "from contracts.sub.deep.process_context import" in content
            finally:
                os.chdir(original_cwd)
