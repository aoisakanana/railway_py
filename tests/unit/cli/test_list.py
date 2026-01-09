"""Tests for railway list command."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestRailwayList:
    """Test railway list command."""

    def test_list_shows_entries(self):
        """Should list entry points."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "__init__.py").touch()
            (src_dir / "daily_report.py").write_text('''
"""Daily report entry."""
from railway import entry_point

@entry_point
def main():
    """Generate daily report."""
    pass
''')
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["list"])
                assert result.exit_code == 0
                assert "daily_report" in result.stdout
            finally:
                os.chdir(original_cwd)

    def test_list_shows_nodes(self):
        """Should list nodes."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            nodes_dir = src_dir / "nodes"
            nodes_dir.mkdir(parents=True)
            (src_dir / "__init__.py").touch()
            (nodes_dir / "__init__.py").touch()
            (nodes_dir / "fetch_data.py").write_text('''
"""Fetch data node."""
from railway import node

@node
def fetch_data():
    """Fetch data from API."""
    pass
''')
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["list"])
                assert result.exit_code == 0
                assert "fetch_data" in result.stdout
            finally:
                os.chdir(original_cwd)

    def test_list_entries_only(self):
        """Should list only entries with 'entries' subcommand."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            nodes_dir = src_dir / "nodes"
            nodes_dir.mkdir(parents=True)
            (src_dir / "__init__.py").touch()
            (nodes_dir / "__init__.py").touch()
            (src_dir / "my_entry.py").write_text('@entry_point\ndef main(): pass')
            (nodes_dir / "my_node.py").write_text('@node\ndef my_node(): pass')
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["list", "entries"])
                assert "my_entry" in result.stdout
            finally:
                os.chdir(original_cwd)

    def test_list_nodes_only(self):
        """Should list only nodes with 'nodes' subcommand."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            nodes_dir = src_dir / "nodes"
            nodes_dir.mkdir(parents=True)
            (src_dir / "__init__.py").touch()
            (nodes_dir / "__init__.py").touch()
            (src_dir / "my_entry.py").write_text('@entry_point\ndef main(): pass')
            (nodes_dir / "my_node.py").write_text('@node\ndef my_node(): pass')
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["list", "nodes"])
                assert "my_node" in result.stdout
            finally:
                os.chdir(original_cwd)

    def test_list_shows_statistics(self):
        """Should show statistics."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            nodes_dir = src_dir / "nodes"
            tests_dir = Path(tmpdir) / "tests" / "nodes"
            nodes_dir.mkdir(parents=True)
            tests_dir.mkdir(parents=True)
            (src_dir / "__init__.py").touch()
            (nodes_dir / "__init__.py").touch()
            (src_dir / "entry1.py").write_text('@entry_point\ndef main(): pass')
            (src_dir / "entry2.py").write_text('@entry_point\ndef main(): pass')
            (nodes_dir / "node1.py").write_text('@node\ndef node1(): pass')
            (tests_dir / "test_node1.py").touch()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["list"])
                # Should show counts
                assert "2" in result.stdout  # 2 entries
                assert "1" in result.stdout  # 1 node
            finally:
                os.chdir(original_cwd)


class TestRailwayListOutput:
    """Test railway list output formatting."""

    def test_list_shows_docstrings(self):
        """Should show docstrings as descriptions."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "__init__.py").touch()
            (src_dir / "documented.py").write_text('''
"""Documented entry point."""
from railway import entry_point

@entry_point
def main():
    """This is the main function."""
    pass
''')
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["list"])
                # Should show module or function docstring
                assert "documented" in result.stdout.lower()
            finally:
                os.chdir(original_cwd)


class TestRailwayListErrors:
    """Test railway list error handling."""

    def test_list_outside_project_fails(self):
        """Should fail when not in a Railway project."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                # No src/ directory
                result = runner.invoke(app, ["list"])
                assert result.exit_code != 0
            finally:
                os.chdir(original_cwd)

    def test_list_empty_project(self):
        """Should handle empty project gracefully."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "__init__.py").touch()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["list"])
                assert result.exit_code == 0
                # Should indicate no entries/nodes found
            finally:
                os.chdir(original_cwd)
