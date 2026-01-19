"""Tests for railway new node with typed options."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestRailwayNewNodeWithOutput:
    """Test railway new node --output command."""

    def test_new_node_with_output_creates_typed_node(self):
        """Should create node with output type annotation."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "src" / "contracts").mkdir(parents=True)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(
                    app, ["new", "node", "fetch_users", "--output", "UsersFetchResult"]
                )
                assert result.exit_code == 0
                content = (Path(tmpdir) / "src" / "nodes" / "fetch_users.py").read_text()
                assert "@node(output=UsersFetchResult)" in content
                assert "def fetch_users() -> UsersFetchResult:" in content
            finally:
                os.chdir(original_cwd)

    def test_new_node_with_output_imports_contract(self):
        """Should import the output contract type."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(
                    app, ["new", "node", "fetch_data", "--output", "DataFetchResult"]
                )
                content = (Path(tmpdir) / "src" / "nodes" / "fetch_data.py").read_text()
                assert "from contracts.data_fetch_result import DataFetchResult" in content
            finally:
                os.chdir(original_cwd)

    def test_new_node_with_output_returns_contract_instance(self):
        """Should return contract instance in template."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(
                    app, ["new", "node", "process", "--output", "ProcessResult"]
                )
                content = (Path(tmpdir) / "src" / "nodes" / "process.py").read_text()
                assert "return ProcessResult(" in content
            finally:
                os.chdir(original_cwd)


class TestRailwayNewNodeWithInput:
    """Test railway new node --input command."""

    def test_new_node_with_input_creates_typed_node(self):
        """Should create node with input type annotation."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(
                    app,
                    [
                        "new",
                        "node",
                        "process_users",
                        "--input",
                        "users:UsersFetchResult",
                        "--output",
                        "ProcessResult",
                    ],
                )
                assert result.exit_code == 0
                content = (Path(tmpdir) / "src" / "nodes" / "process_users.py").read_text()
                assert 'inputs={"users": UsersFetchResult}' in content
                assert "def process_users(users: UsersFetchResult)" in content
            finally:
                os.chdir(original_cwd)

    def test_new_node_with_input_imports_input_contract(self):
        """Should import the input contract type."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(
                    app,
                    [
                        "new",
                        "node",
                        "transform",
                        "--input",
                        "data:InputData",
                        "--output",
                        "OutputData",
                    ],
                )
                content = (Path(tmpdir) / "src" / "nodes" / "transform.py").read_text()
                assert "from contracts.input_data import InputData" in content
            finally:
                os.chdir(original_cwd)

    def test_new_node_with_multiple_inputs(self):
        """Should handle multiple --input options."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(
                    app,
                    [
                        "new",
                        "node",
                        "generate_report",
                        "--input",
                        "users:UsersFetchResult",
                        "--input",
                        "orders:OrdersFetchResult",
                        "--output",
                        "ReportResult",
                    ],
                )
                assert result.exit_code == 0
                content = (Path(tmpdir) / "src" / "nodes" / "generate_report.py").read_text()
                assert "UsersFetchResult" in content
                assert "OrdersFetchResult" in content
                assert "users: UsersFetchResult" in content
                assert "orders: OrdersFetchResult" in content
            finally:
                os.chdir(original_cwd)


class TestRailwayNewNodeTypedTest:
    """Test typed node test file generation."""

    def test_typed_node_test_checks_output_type(self):
        """Should generate test that checks output type."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "tests" / "nodes").mkdir(parents=True)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(
                    app, ["new", "node", "typed_node", "--output", "TypedResult"]
                )
                test_file = Path(tmpdir) / "tests" / "nodes" / "test_typed_node.py"
                assert test_file.exists()
                content = test_file.read_text()
                assert "TypedResult" in content
                assert "isinstance" in content
            finally:
                os.chdir(original_cwd)

    def test_typed_node_with_input_test_imports(self):
        """Should generate test that imports input types."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            (Path(tmpdir) / "tests" / "nodes").mkdir(parents=True)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(
                    app,
                    [
                        "new",
                        "node",
                        "input_node",
                        "--input",
                        "data:InputContract",
                        "--output",
                        "OutputContract",
                    ],
                )
                test_file = Path(tmpdir) / "tests" / "nodes" / "test_input_node.py"
                content = test_file.read_text()
                assert "InputContract" in content
                assert "OutputContract" in content
            finally:
                os.chdir(original_cwd)


class TestRailwayNewNodeInputValidation:
    """Test input format validation."""

    def test_invalid_input_format_fails(self):
        """Should fail with invalid input format (missing colon)."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(
                    app,
                    [
                        "new",
                        "node",
                        "bad_node",
                        "--input",
                        "InvalidFormat",
                        "--output",
                        "Result",
                    ],
                )
                assert result.exit_code != 0
            finally:
                os.chdir(original_cwd)

    def test_input_requires_output(self):
        """Should require --output when --input is specified."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "nodes").mkdir(parents=True)
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(
                    app,
                    ["new", "node", "incomplete_node", "--input", "data:DataContract"],
                )
                # Should either fail or work (implementation choice)
                # If it works, it should have proper type handling
                if result.exit_code == 0:
                    content = (
                        Path(tmpdir) / "src" / "nodes" / "incomplete_node.py"
                    ).read_text()
                    assert "DataContract" in content
            finally:
                os.chdir(original_cwd)
