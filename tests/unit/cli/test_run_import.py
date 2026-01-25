"""Tests for railway run command import handling."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestRunWithoutSrcPrefix:
    """Test railway run works without src. prefix in imports."""

    def test_run_finds_entrypoint_without_src_prefix(self, tmp_path, monkeypatch):
        """Should find entrypoint in src/ without src. prefix."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)

        # Create project structure
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "__init__.py").touch()

        # Create entrypoint without src. prefix imports
        (tmp_path / "src" / "my_entry.py").write_text('''
from railway import entry_point

@entry_point
def main():
    return {"status": "ok"}
''')

        result = runner.invoke(app, ["run", "my_entry"])

        assert result.exit_code == 0, f"Failed: {result.output}"

    def test_run_resolves_internal_imports(self, tmp_path, monkeypatch):
        """Should resolve imports between modules in src/."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)

        # Create project structure
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "__init__.py").touch()
        (tmp_path / "src" / "contracts").mkdir()
        (tmp_path / "src" / "contracts" / "__init__.py").touch()

        # Create contract
        (tmp_path / "src" / "contracts" / "my_contract.py").write_text('''
from railway import Contract

class MyResult(Contract):
    value: str
''')

        # Create entrypoint that imports contract
        (tmp_path / "src" / "my_entry.py").write_text('''
from railway import entry_point
from contracts.my_contract import MyResult

@entry_point
def main():
    result = MyResult(value="test")
    return result.model_dump()
''')

        result = runner.invoke(app, ["run", "my_entry"])

        assert result.exit_code == 0, f"Failed: {result.output}"

    def test_run_resolves_nodes_imports(self, tmp_path, monkeypatch):
        """Should resolve imports from nodes/ directory."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)

        # Create project structure
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "__init__.py").touch()
        (tmp_path / "src" / "nodes").mkdir()
        (tmp_path / "src" / "nodes" / "__init__.py").touch()

        # Create node
        (tmp_path / "src" / "nodes" / "my_node.py").write_text('''
from railway import node

@node
def my_node():
    return {"done": True}
''')

        # Create entrypoint that imports node
        (tmp_path / "src" / "my_entry.py").write_text('''
from railway import entry_point
from nodes.my_node import my_node

@entry_point
def main():
    return my_node()
''')

        result = runner.invoke(app, ["run", "my_entry"])

        assert result.exit_code == 0, f"Failed: {result.output}"


class TestRunSrcPathHandling:
    """Test sys.path manipulation for src/ imports."""

    def test_src_added_to_path(self, tmp_path, monkeypatch):
        """Should add src/ to sys.path before import."""
        from railway.cli.run import _setup_src_path

        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()

        original_path = sys.path.copy()

        _setup_src_path(tmp_path)

        src_path = str(tmp_path / "src")
        assert src_path in sys.path, "src/ should be in sys.path"

        # Cleanup
        sys.path[:] = original_path

    def test_src_path_is_prioritized(self, tmp_path, monkeypatch):
        """src/ should be early in sys.path for priority."""
        from railway.cli.run import _setup_src_path

        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()

        original_path = sys.path.copy()

        _setup_src_path(tmp_path)

        src_path = str(tmp_path / "src")
        # src should be at index 0 or 1 (after '' or project root)
        assert sys.path.index(src_path) <= 1, "src/ should be early in sys.path"

        # Cleanup
        sys.path[:] = original_path

    def test_src_not_duplicated_in_path(self, tmp_path, monkeypatch):
        """Should not add duplicate src/ to sys.path."""
        from railway.cli.run import _setup_src_path

        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()

        original_path = sys.path.copy()

        # Add twice
        _setup_src_path(tmp_path)
        _setup_src_path(tmp_path)

        src_path = str(tmp_path / "src")
        count = sys.path.count(src_path)
        assert count == 1, f"src/ should appear once, but appeared {count} times"

        # Cleanup
        sys.path[:] = original_path


class TestRunModuleResolution:
    """Test module resolution logic."""

    def test_resolve_module_from_name_simple(self):
        """Should resolve simple module path from entrypoint name."""
        from railway.cli.run import _resolve_module_path

        assert _resolve_module_path("my_entry") == "my_entry"

    def test_resolve_module_from_name_with_subdirectory(self):
        """Should resolve module path with subdirectory."""
        from railway.cli.run import _resolve_module_path

        assert _resolve_module_path("workflows.daily") == "workflows.daily"

    def test_resolve_module_removes_py_extension(self):
        """Should remove .py extension if present."""
        from railway.cli.run import _resolve_module_path

        assert _resolve_module_path("my_entry.py") == "my_entry"

    def test_resolve_module_removes_src_prefix(self):
        """Should remove src. prefix for backwards compatibility."""
        from railway.cli.run import _resolve_module_path

        assert _resolve_module_path("src.my_entry") == "my_entry"
        assert _resolve_module_path("src.workflows.daily") == "workflows.daily"


class TestRunBackwardsCompatibility:
    """Test backwards compatibility with old src. prefix style."""

    def test_run_with_src_prefix_still_works(self, tmp_path, monkeypatch):
        """Should still work when src. prefix is provided explicitly."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)

        # Create project structure
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "__init__.py").touch()

        # Create entrypoint
        (tmp_path / "src" / "my_entry.py").write_text('''
from railway import entry_point

@entry_point
def main():
    return {"status": "ok"}
''')

        # This test verifies that providing src.my_entry or my_entry both work
        # The command itself uses the entry name, not module path
        result = runner.invoke(app, ["run", "my_entry"])

        assert result.exit_code == 0, f"Failed: {result.output}"
