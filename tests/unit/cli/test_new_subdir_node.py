"""Tests for railway new node with subdirectory paths.

Bug: `railway new node greeting/farewell` crashes with FileNotFoundError
because intermediate directories (src/contracts/greeting/) are not created.
"""

import os
import tempfile
from pathlib import Path

import pytest
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


class TestNewNodeSubdirectory:
    """railway new node greeting/farewell のサブディレクトリ対応テスト."""

    def test_contract_intermediate_dir_created(self) -> None:
        """Contract の中間ディレクトリが作成されること."""
        from railway.cli.new import NodeMode, _create_node_contract

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                _create_node_contract("greeting/farewell", NodeMode.dag)

                contract_path = Path(tmpdir) / "src" / "contracts" / "greeting" / "farewell_context.py"
                assert contract_path.exists(), f"Contract file not found: {contract_path}"
            finally:
                os.chdir(original_cwd)

    def test_node_file_intermediate_dir_created(self) -> None:
        """ノードファイルの中間ディレクトリが作成されること."""
        from railway.cli.new import _create_node

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                _create_node("greeting/farewell", example=False, force=False)

                node_path = Path(tmpdir) / "src" / "nodes" / "greeting" / "farewell.py"
                assert node_path.exists(), f"Node file not found: {node_path}"
            finally:
                os.chdir(original_cwd)

    def test_test_file_intermediate_dir_created(self) -> None:
        """テストファイルの中間ディレクトリが作成されること."""
        from railway.cli.new import _create_node

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                _create_node("greeting/farewell", example=False, force=False)

                test_path = Path(tmpdir) / "tests" / "nodes" / "greeting" / "test_farewell.py"
                assert test_path.exists(), f"Test file not found: {test_path}"
            finally:
                os.chdir(original_cwd)

    def test_cli_new_node_subdir_no_crash(self) -> None:
        """CLI 経由で subdir/name ノードがクラッシュしないこと."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "node", "greeting/farewell"])
                assert result.exit_code == 0, f"Failed with: {result.output}"
            finally:
                os.chdir(original_cwd)

    def test_linear_mode_contract_intermediate_dir_created(self) -> None:
        """linear モードでも Contract 中間ディレクトリが作成されること."""
        from railway.cli.new import NodeMode, _create_node_contract

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                _create_node_contract("greeting/farewell", NodeMode.linear)

                input_path = Path(tmpdir) / "src" / "contracts" / "greeting" / "farewell_input.py"
                output_path = Path(tmpdir) / "src" / "contracts" / "greeting" / "farewell_output.py"
                assert input_path.exists(), f"Input contract not found: {input_path}"
                assert output_path.exists(), f"Output contract not found: {output_path}"
            finally:
                os.chdir(original_cwd)
