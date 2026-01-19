"""Tests for railway new contract command."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestRailwayNewContract:
    """Test railway new contract command."""

    def test_new_contract_creates_file(self):
        """Should create contract file in src/contracts/."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create project structure
            (Path(tmpdir) / "src").mkdir()
            (Path(tmpdir) / "src" / "__init__.py").touch()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "contract", "UsersFetchResult"])
                assert result.exit_code == 0
                contract_file = Path(tmpdir) / "src" / "contracts" / "users_fetch_result.py"
                assert contract_file.exists()
            finally:
                os.chdir(original_cwd)

    def test_new_contract_contains_contract_import(self):
        """Should contain Contract import."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src").mkdir()
            (Path(tmpdir) / "src" / "__init__.py").touch()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "contract", "MyContract"])
                content = (Path(tmpdir) / "src" / "contracts" / "my_contract.py").read_text()
                assert "from railway import Contract" in content
                assert "class MyContract(Contract):" in content
            finally:
                os.chdir(original_cwd)

    def test_new_contract_creates_contracts_dir(self):
        """Should create contracts directory if not exists."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src").mkdir()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "contract", "TestContract"])
                assert result.exit_code == 0
                contracts_dir = Path(tmpdir) / "src" / "contracts"
                assert contracts_dir.exists()
                assert (contracts_dir / "__init__.py").exists()
            finally:
                os.chdir(original_cwd)


class TestRailwayNewContractEntity:
    """Test railway new contract --entity command."""

    def test_new_contract_entity_has_id_field(self):
        """Should create entity with id field."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src").mkdir()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "contract", "User", "--entity"])
                assert result.exit_code == 0
                content = (Path(tmpdir) / "src" / "contracts" / "user.py").read_text()
                assert "id: int" in content
                assert "class User(Contract):" in content
            finally:
                os.chdir(original_cwd)

    def test_new_contract_entity_docstring(self):
        """Should have entity-specific docstring."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src").mkdir()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "contract", "Order", "--entity"])
                content = (Path(tmpdir) / "src" / "contracts" / "order.py").read_text()
                assert "Entity" in content or "entity" in content
            finally:
                os.chdir(original_cwd)


class TestRailwayNewContractParams:
    """Test railway new contract --params command."""

    def test_new_contract_params_inherits_params(self):
        """Should inherit from Params class."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src").mkdir()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "contract", "ReportParams", "--params"])
                assert result.exit_code == 0
                content = (Path(tmpdir) / "src" / "contracts" / "report_params.py").read_text()
                assert "from railway import Params" in content
                assert "class ReportParams(Params):" in content
            finally:
                os.chdir(original_cwd)

    def test_new_contract_params_docstring(self):
        """Should have params-specific docstring."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src").mkdir()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "contract", "FetchParams", "--params"])
                content = (Path(tmpdir) / "src" / "contracts" / "fetch_params.py").read_text()
                assert "Parameters" in content or "parameters" in content
            finally:
                os.chdir(original_cwd)


class TestRailwayNewContractMutualExclusion:
    """Test --entity and --params are mutually exclusive."""

    def test_entity_and_params_are_mutually_exclusive(self):
        """Should fail if both --entity and --params are specified."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src").mkdir()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(
                    app, ["new", "contract", "BadContract", "--entity", "--params"]
                )
                assert result.exit_code != 0
            finally:
                os.chdir(original_cwd)


class TestRailwayNewContractOptions:
    """Test railway new contract command options."""

    def test_new_contract_force_overwrites(self):
        """Should overwrite with --force."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "contracts").mkdir(parents=True)
            existing_file = Path(tmpdir) / "src" / "contracts" / "existing.py"
            existing_file.write_text("# Old content")
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["new", "contract", "Existing", "--force"])
                content = existing_file.read_text()
                assert "# Old content" not in content
                assert "class Existing(Contract)" in content
            finally:
                os.chdir(original_cwd)

    def test_new_contract_without_force_fails_on_existing(self):
        """Should fail without --force if file exists."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src" / "contracts").mkdir(parents=True)
            (Path(tmpdir) / "src" / "contracts" / "existing.py").write_text("# Old")
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "contract", "Existing"])
                assert result.exit_code != 0
                output = result.output.lower() if result.output else ""
                assert "exists" in output
            finally:
                os.chdir(original_cwd)


class TestRailwayNewContractOutput:
    """Test railway new contract command output."""

    def test_new_contract_shows_success_message(self):
        """Should show success message."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src").mkdir()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "contract", "SuccessContract"])
                output = result.stdout.lower()
                assert "created" in output or "✓" in result.stdout
            finally:
                os.chdir(original_cwd)

    def test_new_contract_shows_file_path(self):
        """Should show created file path."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "src").mkdir()
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["new", "contract", "PathContract"])
                assert "contracts" in result.stdout.lower()
            finally:
                os.chdir(original_cwd)
