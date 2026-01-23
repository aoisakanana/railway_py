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

    def test_py_typed_contains_pep561_marker(self):
        """py.typed に PEP 561 マーカーコメントが含まれる"""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"], catch_exceptions=False)

                py_typed = Path(tmpdir) / "test_project" / "src" / "py.typed"
                content = py_typed.read_text()
                assert "PEP 561" in content, "py.typed should mention PEP 561"
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
