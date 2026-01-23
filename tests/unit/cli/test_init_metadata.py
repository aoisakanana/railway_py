"""Tests for railway init command's metadata generation.

TDD Red Phase: まずテストを書き、失敗を確認する。
"""
import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from railway import __version__
from railway.core.project_metadata import load_metadata


runner = CliRunner()


class TestInitCommandMetadata:
    """initコマンドがメタデータを生成することを検証。"""

    def test_init_creates_railway_directory(self):
        """initコマンドが.railwayディレクトリを作成する。"""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["init", "test_project"])

                assert result.exit_code == 0
                assert (Path(tmpdir) / "test_project" / ".railway").is_dir()
            finally:
                os.chdir(original_cwd)

    def test_init_creates_project_yaml(self):
        """initコマンドがproject.yamlを作成する。"""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["init", "test_project"])

                assert result.exit_code == 0
                project_yaml = Path(tmpdir) / "test_project" / ".railway" / "project.yaml"
                assert project_yaml.exists()
            finally:
                os.chdir(original_cwd)

    def test_init_records_current_version(self):
        """initコマンドが現在のrailway-frameworkバージョンを記録する。"""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                project_path = Path(tmpdir) / "test_project"
                metadata = load_metadata(project_path)

                assert metadata is not None
                assert metadata.railway.version == __version__
            finally:
                os.chdir(original_cwd)

    def test_init_records_project_name(self):
        """initコマンドがプロジェクト名を記録する。"""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_awesome_project"])

                project_path = Path(tmpdir) / "my_awesome_project"
                metadata = load_metadata(project_path)

                assert metadata is not None
                assert metadata.project.name == "my_awesome_project"
            finally:
                os.chdir(original_cwd)

    def test_init_sets_min_version(self):
        """initコマンドがmin_versionを設定する。"""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                project_path = Path(tmpdir) / "test_project"
                metadata = load_metadata(project_path)

                assert metadata is not None
                assert metadata.compatibility.min_version == __version__
            finally:
                os.chdir(original_cwd)

    def test_init_output_shows_railway_directory(self):
        """initコマンドの出力に.railwayディレクトリが表示される。"""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["init", "test_project"])

                assert ".railway/" in result.output
                assert "project.yaml" in result.output
            finally:
                os.chdir(original_cwd)
