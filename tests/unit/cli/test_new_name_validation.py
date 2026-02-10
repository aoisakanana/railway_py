"""Tests for CLI input name validation in railway new command.

パターン A: スラッシュ入りノード名 → 拒否
パターン B: ハイフン入りエントリーポイント名 → 拒否
パターン C: Python予約語エントリーポイント名 → 拒否
パターン D: Python予約語ノード名 → 拒否
ドット区切り: 階層ノード名 → 許容
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
    (p / "src" / "nodes" / "__init__.py").write_text('"""Node modules."""\n')
    (p / "src" / "contracts").mkdir()
    (p / "src" / "contracts" / "__init__.py").write_text('"""Contract modules."""\n')
    (p / "tests").mkdir()
    (p / "tests" / "nodes").mkdir(parents=True)
    (p / "transition_graphs").mkdir()
    (p / "_railway" / "generated").mkdir(parents=True)


class TestEntryNameValidation:
    """railway new entry の入力バリデーションテスト."""

    def test_hyphen_entry_rejected(self) -> None:
        """パターン B: ハイフン入りエントリーポイント名は拒否."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "entry", "my-workflow"])
                assert result.exit_code != 0
                assert "my_workflow" in result.output
            finally:
                os.chdir(original_cwd)

    def test_keyword_entry_rejected(self) -> None:
        """パターン C: Python予約語エントリーポイント名は拒否."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "entry", "import"])
                assert result.exit_code != 0
                assert "予約語" in result.output
            finally:
                os.chdir(original_cwd)

    def test_class_keyword_entry_rejected(self) -> None:
        """パターン C: class も予約語として拒否."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "entry", "class"])
                assert result.exit_code != 0
            finally:
                os.chdir(original_cwd)

    def test_valid_entry_accepted(self) -> None:
        """正常なエントリーポイント名は受理."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "entry", "my_workflow"])
                assert result.exit_code == 0
            finally:
                os.chdir(original_cwd)


class TestNodeNameValidation:
    """railway new node の入力バリデーションテスト."""

    def test_slash_node_rejected(self) -> None:
        """パターン A: スラッシュ入りノード名は拒否."""
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

    def test_keyword_node_rejected(self) -> None:
        """パターン D: Python予約語ノード名は拒否."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "node", "class"])
                assert result.exit_code != 0
                assert "予約語" in result.output
            finally:
                os.chdir(original_cwd)

    def test_hyphen_node_rejected(self) -> None:
        """ハイフン入りノード名は拒否."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "node", "my-node"])
                assert result.exit_code != 0
                assert "my_node" in result.output
            finally:
                os.chdir(original_cwd)

    def test_dotted_node_accepted(self) -> None:
        """ドット区切りノード名は受理."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "node", "processing.validate"])
                assert result.exit_code == 0
            finally:
                os.chdir(original_cwd)

    def test_valid_simple_node_accepted(self) -> None:
        """正常な単一ノード名は受理."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "node", "farewell"])
                assert result.exit_code == 0
            finally:
                os.chdir(original_cwd)

    def test_keyword_in_dotted_segment_rejected(self) -> None:
        """ドット区切りの一部が予約語でも拒否."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            _setup_project_dir(tmpdir)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "node", "processing.import"])
                assert result.exit_code != 0
            finally:
                os.chdir(original_cwd)
