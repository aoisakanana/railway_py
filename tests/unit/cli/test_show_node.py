"""Tests for railway show node command."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestRailwayShowNode:
    """Test railway show node command."""

    def test_show_node_displays_info(self):
        """Should display node information."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            nodes_dir = Path(tmpdir) / "src" / "nodes"
            nodes_dir.mkdir(parents=True)

            # Create a typed node
            (nodes_dir / "fetch_users.py").write_text('''
"""Fetch users node."""
from railway import node
from contracts.users_fetch_result import UsersFetchResult

@node(output=UsersFetchResult)
def fetch_users() -> UsersFetchResult:
    """Fetch all users."""
    return UsersFetchResult(users=[], total=0)
''')

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["show", "node", "fetch_users"])
                assert result.exit_code == 0
                assert "fetch_users" in result.stdout
            finally:
                os.chdir(original_cwd)

    def test_show_node_displays_output_type(self):
        """Should display output type."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            nodes_dir = Path(tmpdir) / "src" / "nodes"
            nodes_dir.mkdir(parents=True)

            (nodes_dir / "process_data.py").write_text('''
from railway import node
from contracts.result import ProcessResult

@node(output=ProcessResult)
def process_data() -> ProcessResult:
    return ProcessResult()
''')

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["show", "node", "process_data"])
                assert "ProcessResult" in result.stdout or "Output" in result.stdout
            finally:
                os.chdir(original_cwd)

    def test_show_node_displays_input_types(self):
        """Should display input types."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            nodes_dir = Path(tmpdir) / "src" / "nodes"
            nodes_dir.mkdir(parents=True)

            (nodes_dir / "generate_report.py").write_text('''
from railway import node
from contracts.users import UsersResult
from contracts.orders import OrdersResult
from contracts.report import ReportResult

@node(
    inputs={"users": UsersResult, "orders": OrdersResult},
    output=ReportResult,
)
def generate_report(users: UsersResult, orders: OrdersResult) -> ReportResult:
    return ReportResult()
''')

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["show", "node", "generate_report"])
                # Should show input types
                output = result.stdout
                assert "UsersResult" in output or "users" in output
                assert "OrdersResult" in output or "orders" in output
            finally:
                os.chdir(original_cwd)

    def test_show_node_not_found(self):
        """Should show error for non-existent node."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["show", "node", "nonexistent"])
                assert result.exit_code != 0 or "not found" in result.stdout.lower()
            finally:
                os.chdir(original_cwd)

    def test_show_node_untyped(self):
        """Should handle untyped nodes gracefully."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            nodes_dir = Path(tmpdir) / "src" / "nodes"
            nodes_dir.mkdir(parents=True)

            (nodes_dir / "simple_node.py").write_text('''
from railway import node

@node
def simple_node(data):
    return data
''')

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["show", "node", "simple_node"])
                assert result.exit_code == 0
                assert "simple_node" in result.stdout
            finally:
                os.chdir(original_cwd)


class TestRailwayShowNodeDependencies:
    """Test dependency visualization in show node."""

    def test_show_node_displays_dependencies(self):
        """Should display dependency tree."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            nodes_dir = Path(tmpdir) / "src" / "nodes"
            nodes_dir.mkdir(parents=True)

            # Create interdependent nodes
            (nodes_dir / "fetch_users.py").write_text('''
from railway import node
from contracts.users import UsersFetchResult

@node(output=UsersFetchResult)
def fetch_users() -> UsersFetchResult:
    return UsersFetchResult()
''')

            (nodes_dir / "process_users.py").write_text('''
from railway import node
from contracts.users import UsersFetchResult
from contracts.processed import ProcessedResult

@node(inputs={"users": UsersFetchResult}, output=ProcessedResult)
def process_users(users: UsersFetchResult) -> ProcessedResult:
    return ProcessedResult()
''')

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["show", "node", "process_users"])
                # Should show dependency on UsersFetchResult
                assert result.exit_code == 0
                output = result.stdout
                assert "UsersFetchResult" in output or "users" in output
            finally:
                os.chdir(original_cwd)


class TestRailwayShowNodeFormatting:
    """Test formatting of show node output."""

    def test_show_node_section_headers(self):
        """Should have clear section headers."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            nodes_dir = Path(tmpdir) / "src" / "nodes"
            nodes_dir.mkdir(parents=True)

            (nodes_dir / "formatted_node.py").write_text('''
from railway import node
from contracts.input import InputContract
from contracts.output import OutputContract

@node(inputs={"data": InputContract}, output=OutputContract)
def formatted_node(data: InputContract) -> OutputContract:
    return OutputContract()
''')

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["show", "node", "formatted_node"])
                output = result.stdout
                # Should have some structure (Node:, Input:, Output:, etc.)
                assert "Node" in output or "formatted_node" in output
            finally:
                os.chdir(original_cwd)
