"""Tests for py.typed marker in project generation."""

import tempfile
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from railway.cli.main import app

runner = CliRunner()


class TestInitPyTyped:
    """py.typed マーカーのテスト"""

    def test_creates_py_typed_in_src(self):
        """railway init で src/py.typed が作成される"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["init", "test_project"], catch_exceptions=False)

            py_typed = Path(tmpdir) / "test_project" / "src" / "py.typed"
            # 現在のディレクトリが変わっているかもしれないので、カレントディレクトリからも確認
            current_py_typed = Path("test_project") / "src" / "py.typed"

            # tmpdir に移動してからテスト
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["init", "test_project"], catch_exceptions=False)
                py_typed = Path(tmpdir) / "test_project" / "src" / "py.typed"
                assert py_typed.exists(), f"py.typed should exist in src/. Result: {result.output}"
            finally:
                os.chdir(original_cwd)

    def test_py_typed_is_empty_file(self):
        """py.typed は空ファイル（PEP 561 準拠）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"], catch_exceptions=False)

                py_typed = Path(tmpdir) / "test_project" / "src" / "py.typed"
                content = py_typed.read_text()
                # PEP 561: py.typed は空ファイルで良い
                assert content == "", "py.typed should be empty (PEP 561 compliant)"
            finally:
                os.chdir(original_cwd)

    def test_py_typed_created_with_examples_flag(self):
        """--with-examples フラグでも py.typed が作成される"""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(
                    app, ["init", "test_project", "--with-examples"], catch_exceptions=False
                )

                py_typed = Path(tmpdir) / "test_project" / "src" / "py.typed"
                assert py_typed.exists(), "py.typed should exist with --with-examples"
            finally:
                os.chdir(original_cwd)

    def test_creates_py_typed_in_nodes(self):
        """railway init で src/nodes/py.typed が作成される（mypy 対応）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"], catch_exceptions=False)

                py_typed = Path(tmpdir) / "test_project" / "src" / "nodes" / "py.typed"
                assert py_typed.exists(), "py.typed should exist in src/nodes/"
            finally:
                os.chdir(original_cwd)

    def test_creates_py_typed_in_contracts(self):
        """railway init で src/contracts/py.typed が作成される（mypy 対応）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"], catch_exceptions=False)

                py_typed = Path(tmpdir) / "test_project" / "src" / "contracts" / "py.typed"
                assert py_typed.exists(), "py.typed should exist in src/contracts/"
            finally:
                os.chdir(original_cwd)


class TestGetPyTypedPaths:
    """_get_py_typed_paths() 純粋関数のテスト"""

    def test_returns_tuple_of_paths(self, tmp_path: Path) -> None:
        """タプルでパスを返す"""
        from railway.cli.init import _get_py_typed_paths

        paths = _get_py_typed_paths(tmp_path / "myproject")

        assert isinstance(paths, tuple)
        assert len(paths) >= 3  # src, nodes, contracts

    def test_paths_are_correct(self, tmp_path: Path) -> None:
        """正しいパスを返す"""
        from railway.cli.init import _get_py_typed_paths

        project_path = tmp_path / "myproject"
        paths = _get_py_typed_paths(project_path)

        expected = (
            project_path / "src" / "py.typed",
            project_path / "src" / "nodes" / "py.typed",
            project_path / "src" / "contracts" / "py.typed",
        )
        assert paths == expected

    def test_is_pure_function(self, tmp_path: Path) -> None:
        """純粋関数: 同じ入力に同じ出力"""
        from railway.cli.init import _get_py_typed_paths

        project_path = tmp_path / "myproject"
        result1 = _get_py_typed_paths(project_path)
        result2 = _get_py_typed_paths(project_path)

        assert result1 == result2
