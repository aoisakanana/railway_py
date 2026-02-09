"""Tests for railway init command."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestRailwayInit:
    """Test railway init command."""

    def test_init_creates_project_directory(self):
        """Should create project directory."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["init", "my_project"])
                assert result.exit_code == 0
                assert (Path(tmpdir) / "my_project").exists()
            finally:
                os.chdir(original_cwd)

    def test_init_creates_src_directory(self):
        """Should create src directory."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project"])
                assert (Path(tmpdir) / "my_project" / "src").exists()
                assert (Path(tmpdir) / "my_project" / "src" / "__init__.py").exists()
            finally:
                os.chdir(original_cwd)

    def test_init_creates_tests_directory(self):
        """Should create tests directory."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project"])
                assert (Path(tmpdir) / "my_project" / "tests").exists()
                assert (Path(tmpdir) / "my_project" / "tests" / "conftest.py").exists()
            finally:
                os.chdir(original_cwd)

    def test_init_creates_config_directory(self):
        """Should create config directory with YAML files."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project"])
                config_dir = Path(tmpdir) / "my_project" / "config"
                assert config_dir.exists()
                assert (config_dir / "development.yaml").exists()
            finally:
                os.chdir(original_cwd)

    def test_init_creates_logs_directory(self):
        """Should create logs directory."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project"])
                assert (Path(tmpdir) / "my_project" / "logs").exists()
            finally:
                os.chdir(original_cwd)

    def test_init_creates_pyproject_toml(self):
        """Should create pyproject.toml."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project"])
                pyproject = Path(tmpdir) / "my_project" / "pyproject.toml"
                assert pyproject.exists()
                content = pyproject.read_text()
                assert "my_project" in content
                assert "railway" in content.lower()
            finally:
                os.chdir(original_cwd)

    def test_init_creates_env_example(self):
        """Should create .env.example."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project"])
                env_example = Path(tmpdir) / "my_project" / ".env.example"
                assert env_example.exists()
                content = env_example.read_text()
                assert "RAILWAY_ENV" in content
            finally:
                os.chdir(original_cwd)

    def test_init_creates_settings_py(self):
        """Should create settings.py."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project"])
                settings = Path(tmpdir) / "my_project" / "src" / "settings.py"
                assert settings.exists()
                content = settings.read_text()
                assert "Settings" in content
            finally:
                os.chdir(original_cwd)

    def test_init_creates_tutorial_md(self):
        """Should create TUTORIAL.md."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project"])
                tutorial = Path(tmpdir) / "my_project" / "TUTORIAL.md"
                assert tutorial.exists()
            finally:
                os.chdir(original_cwd)

    def test_init_creates_gitignore(self):
        """Should create .gitignore."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project"])
                gitignore = Path(tmpdir) / "my_project" / ".gitignore"
                assert gitignore.exists()
                content = gitignore.read_text()
                assert ".env" in content
                assert "__pycache__" in content
            finally:
                os.chdir(original_cwd)


class TestRailwayInitOptions:
    """Test railway init command options."""

    def test_init_with_python_version(self):
        """Should use specified Python version."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project", "--python-version", "3.11"])
                pyproject = Path(tmpdir) / "my_project" / "pyproject.toml"
                content = pyproject.read_text()
                assert "3.11" in content
            finally:
                os.chdir(original_cwd)

    def test_init_with_examples(self):
        """Should create example entry point with --with-examples."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "my_project", "--with-examples"])
                # Should have example entry point
                hello = Path(tmpdir) / "my_project" / "src" / "hello.py"
                assert hello.exists()
            finally:
                os.chdir(original_cwd)


class TestRailwayInitErrors:
    """Test railway init error handling."""

    def test_init_existing_directory_fails(self):
        """Should fail if directory already exists."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                (Path(tmpdir) / "existing_project").mkdir()
                result = runner.invoke(app, ["init", "existing_project"])
                assert result.exit_code != 0
                # Error message is written to stderr, check output (stdout + stderr combined)
                output = result.output.lower() if result.output else ""
                assert "already exists" in output
            finally:
                os.chdir(original_cwd)

    def test_init_invalid_project_name(self):
        """Should normalize project names with dashes."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["init", "my-project"])
                # Should normalize to my_project
                assert result.exit_code == 0
                assert (Path(tmpdir) / "my_project").exists()
            finally:
                os.chdir(original_cwd)


class TestRailwayInitOutput:
    """Test railway init output messages."""

    def test_init_shows_success_message(self):
        """Should show success message."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["init", "my_project"])
                assert "Created" in result.stdout or "created" in result.stdout.lower()
            finally:
                os.chdir(original_cwd)

    def test_init_shows_next_steps(self):
        """Should show next steps."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["init", "my_project"])
                assert "cd my_project" in result.stdout or "Next" in result.stdout
            finally:
                os.chdir(original_cwd)


# =============================================================================
# Issue 15-01: pyproject.toml に mypy 設定追加
# =============================================================================


class TestPyprojectMypyConfig:
    """Test that generated pyproject.toml includes [tool.mypy] section."""

    def test_pyproject_has_mypy_section(self, tmp_path: Path) -> None:
        from railway.cli.init import _create_pyproject_toml

        _create_pyproject_toml(tmp_path, "test_project", "3.10")
        content = (tmp_path / "pyproject.toml").read_text()
        assert "[tool.mypy]" in content
        assert 'mypy_path = "src"' in content
        assert "explicit_package_bases = true" in content

    def test_pyproject_mypy_ignore_missing_imports(self, tmp_path: Path) -> None:
        from railway.cli.init import _create_pyproject_toml

        _create_pyproject_toml(tmp_path, "test_project", "3.10")
        content = (tmp_path / "pyproject.toml").read_text()
        assert "ignore_missing_imports = true" in content


# =============================================================================
# Issue 15-02: バージョン固定
# =============================================================================


class TestComputeVersionConstraint:
    """Test _compute_version_constraint pure function."""

    def test_stable_version(self) -> None:
        from railway.cli.init import _compute_version_constraint

        assert _compute_version_constraint("0.13.11") == ">=0.13.11,<0.14.0"

    def test_rc_version(self) -> None:
        from railway.cli.init import _compute_version_constraint

        assert _compute_version_constraint("0.13.10rc2") == ">=0.13.10rc2,<0.14.0"

    def test_major_zero(self) -> None:
        from railway.cli.init import _compute_version_constraint

        assert _compute_version_constraint("0.2.5") == ">=0.2.5,<0.3.0"

    def test_major_one(self) -> None:
        from railway.cli.init import _compute_version_constraint

        assert _compute_version_constraint("1.0.0") == ">=1.0.0,<1.1.0"

    def test_version_constraint_used_in_pyproject(self, tmp_path: Path) -> None:
        """Generated pyproject.toml should use version constraint, not >=0.1.0."""
        from railway.cli.init import _create_pyproject_toml

        _create_pyproject_toml(tmp_path, "test_project", "3.10")
        content = (tmp_path / "pyproject.toml").read_text()
        assert "railway-framework>=0.1.0" not in content
        assert "railway-framework>=" in content


# =============================================================================
# Issue 15-03: テストディレクトリ構造
# =============================================================================


class TestInitTestStructure:
    """Test that tests/nodes/__init__.py is created."""

    def test_tests_nodes_init_py_created(self, tmp_path: Path) -> None:
        from railway.cli.init import _create_init_files

        # Create required directories
        (tmp_path / "tests" / "nodes").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "nodes").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "common").mkdir(parents=True, exist_ok=True)
        _create_init_files(tmp_path)
        assert (tmp_path / "tests" / "nodes" / "__init__.py").exists()

    def test_tests_init_py_still_created(self, tmp_path: Path) -> None:
        from railway.cli.init import _create_init_files

        (tmp_path / "tests" / "nodes").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "nodes").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "common").mkdir(parents=True, exist_ok=True)
        _create_init_files(tmp_path)
        assert (tmp_path / "tests" / "__init__.py").exists()


class TestCreateEntryTestPath:
    """Test that _create_entry uses correct test path."""

    def test_entry_test_created_in_tests_dir(self, tmp_path: Path) -> None:
        """Entry test should be in tests/test_<name>.py, not tests/nodes/test_<name>.py."""
        import os

        from railway.cli.new import _create_entry_test

        tests_dir = tmp_path / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            _create_entry_test("my_entry")
            assert (tests_dir / "test_my_entry.py").exists()
        finally:
            os.chdir(original_cwd)


# =============================================================================
# Issue 15-04: TUTORIAL sync 整合性
# =============================================================================


class TestTutorialSyncConsistency:
    """Test that TUTORIAL.md uses separate files for each greeting node."""

    def test_tutorial_uses_separate_files(self, tmp_path: Path) -> None:
        from railway.cli.init import _create_tutorial_md

        _create_tutorial_md(tmp_path, "greeting")
        content = (tmp_path / "TUTORIAL.md").read_text()
        assert "greet_morning.py" in content

    def test_tutorial_has_advanced_module_section(self, tmp_path: Path) -> None:
        from railway.cli.init import _create_tutorial_md

        _create_tutorial_md(tmp_path, "greeting")
        content = (tmp_path / "TUTORIAL.md").read_text()
        # Should have an advanced section about module specification
        assert "module" in content.lower()

    def test_tutorial_separate_files_not_combined(self, tmp_path: Path) -> None:
        """Main body should use separate files, not combined greet.py."""
        from railway.cli.init import _create_tutorial_md

        _create_tutorial_md(tmp_path, "greeting")
        content = (tmp_path / "TUTORIAL.md").read_text()
        # The step 4.2 section should reference separate files
        assert "greet_morning.py" in content
        assert "greet_afternoon.py" in content
        assert "greet_evening.py" in content


# =============================================================================
# Issue 15-05: サンプル YAML 新形式
# =============================================================================


class TestSampleYamlFormat:
    """Test that sample YAML uses new exit format."""

    def test_no_exits_section(self) -> None:
        from railway.cli.init import _get_sample_transition_yaml

        yaml_content = _get_sample_transition_yaml()
        assert "exits:" not in yaml_content

    def test_uses_new_exit_format(self) -> None:
        from railway.cli.init import _get_sample_transition_yaml

        yaml_content = _get_sample_transition_yaml()
        assert "exit::" not in yaml_content
        assert "exit.success" in yaml_content

    def test_has_nodes_exit_section(self) -> None:
        import yaml

        from railway.cli.init import _get_sample_transition_yaml

        yaml_content = _get_sample_transition_yaml()
        data = yaml.safe_load(yaml_content)
        assert "exit" in data.get("nodes", {})

    def test_has_start_field(self) -> None:
        import yaml

        from railway.cli.init import _get_sample_transition_yaml

        yaml_content = _get_sample_transition_yaml()
        data = yaml.safe_load(yaml_content)
        assert "start" in data

    def test_has_transitions_with_dot_format(self) -> None:
        import yaml

        from railway.cli.init import _get_sample_transition_yaml

        yaml_content = _get_sample_transition_yaml()
        data = yaml.safe_load(yaml_content)
        transitions = data.get("transitions", {})
        greet_transitions = transitions.get("greet", {})
        # All transition targets for exits should use dot notation
        for value in greet_transitions.values():
            if "exit" in str(value):
                assert "exit." in str(value)
                assert "exit::" not in str(value)
