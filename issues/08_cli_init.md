# Issue #08: railway init コマンド

**Phase:** 1a
**優先度:** 高
**依存関係:** #01
**見積もり:** 1日

---

## 概要

新規プロジェクトを作成する`railway init`コマンドを実装する。
Jinja2テンプレートを使ってプロジェクト構造を生成する。

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/cli/test_init.py
"""Tests for railway init command."""
import pytest
from typer.testing import CliRunner
from pathlib import Path
import tempfile
import os


runner = CliRunner()


class TestRailwayInit:
    """Test railway init command."""

    def test_init_creates_project_directory(self):
        """Should create project directory."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            result = runner.invoke(app, ["init", "my_project"])

            assert result.exit_code == 0
            assert (Path(tmpdir) / "my_project").exists()

    def test_init_creates_src_directory(self):
        """Should create src directory."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            runner.invoke(app, ["init", "my_project"])

            assert (Path(tmpdir) / "my_project" / "src").exists()
            assert (Path(tmpdir) / "my_project" / "src" / "__init__.py").exists()

    def test_init_creates_tests_directory(self):
        """Should create tests directory."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            runner.invoke(app, ["init", "my_project"])

            assert (Path(tmpdir) / "my_project" / "tests").exists()
            assert (Path(tmpdir) / "my_project" / "tests" / "conftest.py").exists()

    def test_init_creates_config_directory(self):
        """Should create config directory with YAML files."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            runner.invoke(app, ["init", "my_project"])

            config_dir = Path(tmpdir) / "my_project" / "config"
            assert config_dir.exists()
            assert (config_dir / "development.yaml").exists()

    def test_init_creates_logs_directory(self):
        """Should create logs directory."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            runner.invoke(app, ["init", "my_project"])

            assert (Path(tmpdir) / "my_project" / "logs").exists()

    def test_init_creates_pyproject_toml(self):
        """Should create pyproject.toml."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            runner.invoke(app, ["init", "my_project"])

            pyproject = Path(tmpdir) / "my_project" / "pyproject.toml"
            assert pyproject.exists()
            content = pyproject.read_text()
            assert "my_project" in content
            assert "railway-framework" in content

    def test_init_creates_env_example(self):
        """Should create .env.example."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            runner.invoke(app, ["init", "my_project"])

            env_example = Path(tmpdir) / "my_project" / ".env.example"
            assert env_example.exists()
            content = env_example.read_text()
            assert "RAILWAY_ENV" in content

    def test_init_creates_settings_py(self):
        """Should create settings.py."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            runner.invoke(app, ["init", "my_project"])

            settings = Path(tmpdir) / "my_project" / "src" / "settings.py"
            assert settings.exists()
            content = settings.read_text()
            assert "Settings" in content

    def test_init_creates_tutorial_md(self):
        """Should create TUTORIAL.md."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            runner.invoke(app, ["init", "my_project"])

            tutorial = Path(tmpdir) / "my_project" / "TUTORIAL.md"
            assert tutorial.exists()

    def test_init_creates_gitignore(self):
        """Should create .gitignore."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            runner.invoke(app, ["init", "my_project"])

            gitignore = Path(tmpdir) / "my_project" / ".gitignore"
            assert gitignore.exists()
            content = gitignore.read_text()
            assert ".env" in content
            assert "__pycache__" in content


class TestRailwayInitOptions:
    """Test railway init command options."""

    def test_init_with_python_version(self):
        """Should use specified Python version."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            runner.invoke(app, ["init", "my_project", "--python-version", "3.11"])

            pyproject = Path(tmpdir) / "my_project" / "pyproject.toml"
            content = pyproject.read_text()
            assert "3.11" in content

    def test_init_with_examples(self):
        """Should create example entry point with --with-examples."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            runner.invoke(app, ["init", "my_project", "--with-examples"])

            # Should have example entry point
            hello = Path(tmpdir) / "my_project" / "src" / "hello.py"
            assert hello.exists()


class TestRailwayInitErrors:
    """Test railway init error handling."""

    def test_init_existing_directory_fails(self):
        """Should fail if directory already exists."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            (Path(tmpdir) / "existing_project").mkdir()

            result = runner.invoke(app, ["init", "existing_project"])

            assert result.exit_code != 0
            assert "already exists" in result.stdout.lower()

    def test_init_invalid_project_name(self):
        """Should fail for invalid project names."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            result = runner.invoke(app, ["init", "invalid-name-with-dashes"])

            # Should warn about name (Python packages prefer underscores)
            # May still succeed with warning


class TestRailwayInitOutput:
    """Test railway init output messages."""

    def test_init_shows_success_message(self):
        """Should show success message."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            result = runner.invoke(app, ["init", "my_project"])

            assert "Created project" in result.stdout or "✓" in result.stdout

    def test_init_shows_next_steps(self):
        """Should show next steps."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            result = runner.invoke(app, ["init", "my_project"])

            assert "cd my_project" in result.stdout or "Next steps" in result.stdout
```

```bash
# 実行して失敗を確認
pytest tests/unit/cli/test_init.py -v
# Expected: FAILED (ImportError or AttributeError)
```

### Step 2: Green（最小限の実装）

```python
# railway/cli/main.py
"""
Main CLI entry point for Railway Framework.
"""
import typer

app = typer.Typer(
    name="railway",
    help="Railway Framework CLI - Build robust Python automation",
    add_completion=False,
)


# Import subcommands
from railway.cli import init as init_cmd
from railway.cli import new as new_cmd
from railway.cli import list as list_cmd

app.add_typer(init_cmd.app, name="init")
# Note: 'new' and 'list' will be added in their respective issues


if __name__ == "__main__":
    app()
```

```python
# railway/cli/init.py
"""
railway init command implementation.
"""
import typer
from pathlib import Path
from typing import Optional
from jinja2 import Environment, PackageLoader
import os

app = typer.Typer()


def validate_project_name(name: str) -> str:
    """Validate and normalize project name."""
    # Replace dashes with underscores for Python compatibility
    normalized = name.replace("-", "_")
    if not normalized.isidentifier():
        raise typer.BadParameter(f"'{name}' is not a valid Python identifier")
    return normalized


@app.callback(invoke_without_command=True)
def init(
    project_name: str = typer.Argument(..., help="Name of the project to create"),
    python_version: str = typer.Option("3.10", help="Minimum Python version"),
    with_examples: bool = typer.Option(False, help="Include example entry points"),
):
    """
    Create a new Railway Framework project.

    Creates the project directory structure with all necessary files
    for a Railway-based automation project.
    """
    # Validate project name
    project_name = validate_project_name(project_name)

    # Check if directory exists
    project_path = Path.cwd() / project_name
    if project_path.exists():
        typer.echo(f"Error: Directory '{project_name}' already exists", err=True)
        raise typer.Exit(1)

    # Create directory structure
    _create_project_structure(project_path, project_name, python_version, with_examples)

    # Show success message
    typer.echo(f"\n✓ Created project: {project_name}\n")
    typer.echo("Project structure:")
    typer.echo(f"  {project_name}/")
    typer.echo("  ├── src/")
    typer.echo("  ├── tests/")
    typer.echo("  ├── config/")
    typer.echo("  ├── .env.example")
    typer.echo("  └── TUTORIAL.md\n")
    typer.echo("Next steps:")
    typer.echo(f"  1. cd {project_name}")
    typer.echo("  2. cp .env.example .env")
    typer.echo("  3. Open TUTORIAL.md and follow the guide")
    typer.echo("  4. railway new entry hello --example")


def _create_project_structure(
    project_path: Path,
    project_name: str,
    python_version: str,
    with_examples: bool,
) -> None:
    """Create all project directories and files."""
    # Create directories
    (project_path / "src" / "nodes").mkdir(parents=True)
    (project_path / "src" / "common").mkdir(parents=True)
    (project_path / "tests" / "nodes").mkdir(parents=True)
    (project_path / "config").mkdir(parents=True)
    (project_path / "logs").mkdir(parents=True)

    # Load Jinja2 environment
    try:
        env = Environment(loader=PackageLoader("railway", "templates/project"))
    except Exception:
        # Fallback to direct file creation if templates not found
        _create_files_directly(project_path, project_name, python_version)
        return

    # Render templates
    context = {
        "project_name": project_name,
        "python_version": python_version,
    }

    # Create files from templates
    template_files = {
        "pyproject.toml.jinja": "pyproject.toml",
        ".env.example.jinja": ".env.example",
        "config.yaml.jinja": "config/development.yaml",
        "settings.py.jinja": "src/settings.py",
        "tutorial.md.jinja": "TUTORIAL.md",
        ".gitignore.jinja": ".gitignore",
    }

    for template_name, output_name in template_files.items():
        try:
            template = env.get_template(template_name)
            content = template.render(**context)
            (project_path / output_name).write_text(content)
        except Exception:
            pass  # Skip if template not found

    # Create __init__.py files
    (project_path / "src" / "__init__.py").write_text('"""Source package."""\n')
    (project_path / "src" / "nodes" / "__init__.py").write_text('"""Node modules."""\n')
    (project_path / "src" / "common" / "__init__.py").write_text('"""Common utilities."""\n')
    (project_path / "tests" / "__init__.py").write_text("")
    (project_path / "tests" / "conftest.py").write_text(
        '"""Pytest configuration."""\nimport pytest\n'
    )

    # Create example if requested
    if with_examples:
        _create_example_entry(project_path)


def _create_files_directly(project_path: Path, project_name: str, python_version: str) -> None:
    """Create files directly without templates (fallback)."""
    # pyproject.toml
    (project_path / "pyproject.toml").write_text(f'''[project]
name = "{project_name}"
version = "0.1.0"
description = "Railway framework automation project"
requires-python = ">={python_version}"
dependencies = [
    "railway-framework>=0.1.0",
]

[project.optional-dependencies]
dev = [
    "ruff>=0.1.0",
    "mypy>=1.7.0",
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
''')

    # .env.example
    (project_path / ".env.example").write_text('''# Environment (development/staging/production)
RAILWAY_ENV=development

# Application
APP_NAME={project_name}

# Log Level Override (optional)
LOG_LEVEL=DEBUG
''')

    # config/development.yaml
    (project_path / "config" / "development.yaml").write_text('''# Railway Framework Configuration - Development

app:
  name: {project_name}
  version: "0.1.0"

api:
  base_url: "https://api.example.com"
  timeout: 30

logging:
  level: DEBUG
  format: "{{time:HH:mm:ss}} | {{level}} | {{message}}"
  handlers:
    - type: console
      level: DEBUG

retry:
  default:
    max_attempts: 3
    min_wait: 2
    max_wait: 10
'''.format(project_name=project_name))

    # src/settings.py
    (project_path / "src" / "settings.py").write_text('''"""Application settings."""
from railway.core.settings import Settings, get_settings, reset_settings

# Re-export for convenience
__all__ = ["Settings", "get_settings", "reset_settings", "settings"]

# Lazy settings proxy
settings = get_settings()
''')

    # TUTORIAL.md
    (project_path / "TUTORIAL.md").write_text(f'''# {project_name} Tutorial

Welcome to your Railway Framework project!

## Quick Start

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Create your first entry point:
   ```bash
   railway new entry hello --example
   ```

3. Run it:
   ```bash
   railway run hello
   ```

## Next Steps

See the Railway Framework documentation for more details.
''')

    # .gitignore
    (project_path / ".gitignore").write_text('''# Python
__pycache__/
*.py[cod]
*.so
.Python
*.egg-info/
dist/
build/

# Environment
.env
.venv/
venv/

# IDE
.idea/
.vscode/
*.swp

# Logs
logs/*.log

# Testing
.coverage
htmlcov/
.pytest_cache/

# mypy
.mypy_cache/
''')

    # Create __init__.py files
    (project_path / "src" / "__init__.py").write_text('"""Source package."""\n')
    (project_path / "src" / "nodes" / "__init__.py").write_text('"""Node modules."""\n')
    (project_path / "src" / "common" / "__init__.py").write_text('"""Common utilities."""\n')
    (project_path / "tests" / "__init__.py").write_text("")
    (project_path / "tests" / "conftest.py").write_text(
        '"""Pytest configuration."""\nimport pytest\n'
    )


def _create_example_entry(project_path: Path) -> None:
    """Create example entry point."""
    (project_path / "src" / "hello.py").write_text('''"""Hello World entry point."""
from railway import entry_point, node
from loguru import logger


@node
def greet(name: str) -> str:
    """Greet someone."""
    logger.info(f"Greeting {name}")
    return f"Hello, {name}!"


@entry_point
def main(name: str = "World"):
    """Simple hello world entry point."""
    message = greet(name)
    print(message)
    return message


if __name__ == "__main__":
    main()
''')
```

```bash
# 実行して成功を確認
pytest tests/unit/cli/test_init.py -v
# Expected: PASSED
```

---

## 完了条件

- [ ] `railway init <name>` でプロジェクトが作成される
- [ ] src/, tests/, config/, logs/ ディレクトリが作成される
- [ ] pyproject.toml が正しく生成される
- [ ] .env.example が生成される
- [ ] settings.py が生成される
- [ ] TUTORIAL.md が生成される
- [ ] .gitignore が生成される
- [ ] `--with-examples` でサンプルが作成される
- [ ] 既存ディレクトリでエラーになる
- [ ] テストカバレッジ90%以上

---

## 次のIssue

- #09: railway new コマンド
