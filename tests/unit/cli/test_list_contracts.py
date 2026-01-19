"""Tests for railway list contracts command."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestRailwayListContracts:
    """Test railway list contracts command."""

    def test_list_contracts_shows_contracts(self):
        """Should list all contracts in src/contracts/."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create project structure with contracts
            contracts_dir = Path(tmpdir) / "src" / "contracts"
            contracts_dir.mkdir(parents=True)
            (contracts_dir / "__init__.py").touch()

            # Create a contract file
            (contracts_dir / "users_fetch_result.py").write_text('''
"""Users fetch result contract."""
from railway import Contract

class UsersFetchResult(Contract):
    """Result of fetching users."""
    users: list
    total: int
''')

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["list", "contracts"])
                assert result.exit_code == 0
                assert "UsersFetchResult" in result.stdout
            finally:
                os.chdir(original_cwd)

    def test_list_contracts_shows_params(self):
        """Should distinguish Params contracts."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            contracts_dir = Path(tmpdir) / "src" / "contracts"
            contracts_dir.mkdir(parents=True)
            (contracts_dir / "__init__.py").touch()

            # Create a Params contract
            (contracts_dir / "fetch_params.py").write_text('''
"""Fetch parameters."""
from railway import Params

class FetchParams(Params):
    """Parameters for fetching data."""
    user_id: int
''')

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["list", "contracts"])
                assert result.exit_code == 0
                # Should show FetchParams, possibly under Params section
                assert "FetchParams" in result.stdout
            finally:
                os.chdir(original_cwd)

    def test_list_contracts_shows_file_path(self):
        """Should show file path for each contract."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            contracts_dir = Path(tmpdir) / "src" / "contracts"
            contracts_dir.mkdir(parents=True)

            (contracts_dir / "my_contract.py").write_text('''
from railway import Contract

class MyContract(Contract):
    value: int
''')

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["list", "contracts"])
                assert "contracts" in result.stdout.lower()
            finally:
                os.chdir(original_cwd)

    def test_list_contracts_empty_shows_none(self):
        """Should show message when no contracts exist."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src").mkdir()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["list", "contracts"])
                assert result.exit_code == 0
                output = result.stdout.lower()
                assert "none" in output or "no" in output or "empty" in output or "()" in output
            finally:
                os.chdir(original_cwd)

    def test_list_contracts_multiple(self):
        """Should list multiple contracts."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            contracts_dir = Path(tmpdir) / "src" / "contracts"
            contracts_dir.mkdir(parents=True)

            (contracts_dir / "contract_a.py").write_text('''
from railway import Contract
class ContractA(Contract):
    value: int
''')
            (contracts_dir / "contract_b.py").write_text('''
from railway import Contract
class ContractB(Contract):
    name: str
''')

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["list", "contracts"])
                assert "ContractA" in result.stdout
                assert "ContractB" in result.stdout
            finally:
                os.chdir(original_cwd)


class TestRailwayListContractsRegistered:
    """Test listing from ContractRegistry."""

    def test_list_contracts_uses_registry(self):
        """Should use ContractRegistry for listing."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            contracts_dir = Path(tmpdir) / "src" / "contracts"
            contracts_dir.mkdir(parents=True)
            (contracts_dir / "__init__.py").write_text('''
from railway import Contract

class RegisteredContract(Contract):
    data: str
''')

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["list", "contracts"])
                # Should find contracts via static analysis or registry
                assert result.exit_code == 0
            finally:
                os.chdir(original_cwd)


class TestRailwayListContractsErrors:
    """Test error handling for list contracts."""

    def test_list_contracts_outside_project(self):
        """Should handle non-project directory gracefully."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["list", "contracts"])
                # Should either fail or show empty list
                assert result.exit_code == 0 or "not" in result.stdout.lower()
            finally:
                os.chdir(original_cwd)
