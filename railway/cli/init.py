"""railway init command implementation."""

from pathlib import Path
from typing import Callable

import typer


def _validate_project_name(name: str) -> str:
    """
    Validate and normalize project name.

    Replaces dashes with underscores for Python compatibility.
    """
    normalized = name.replace("-", "_")
    if not normalized.isidentifier():
        raise typer.BadParameter(f"'{name}' is not a valid Python identifier")
    return normalized


def _create_directory(path: Path) -> None:
    """Create a directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)


def _write_file(path: Path, content: str) -> None:
    """Write content to a file."""
    path.write_text(content)


def _create_pyproject_toml(project_path: Path, project_name: str, python_version: str) -> None:
    """Create pyproject.toml file."""
    content = f'''[project]
name = "{project_name}"
version = "0.1.0"
description = "Railway framework automation project"
requires-python = ">={python_version}"
dependencies = [
    "railway-framework>=0.1.0",
    "loguru>=0.7.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "typer>=0.9.0",
    "pyyaml>=6.0.0",
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
'''
    _write_file(project_path / "pyproject.toml", content)


def _create_env_example(project_path: Path, project_name: str) -> None:
    """Create .env.example file."""
    content = f'''# Environment (development/staging/production)
RAILWAY_ENV=development

# Application
APP_NAME={project_name}

# Log Level Override (optional)
LOG_LEVEL=DEBUG
'''
    _write_file(project_path / ".env.example", content)


def _create_development_yaml(project_path: Path, project_name: str) -> None:
    """Create config/development.yaml file."""
    content = f'''# Railway Framework Configuration - Development

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
'''
    _write_file(project_path / "config" / "development.yaml", content)


def _create_settings_py(project_path: Path) -> None:
    """Create src/settings.py file."""
    content = '''"""Application settings."""

from railway.core.settings import Settings, get_settings, reset_settings

# Re-export for convenience
__all__ = ["Settings", "get_settings", "reset_settings", "settings"]

# Lazy settings proxy
settings = get_settings()
'''
    _write_file(project_path / "src" / "settings.py", content)


def _create_tutorial_md(project_path: Path, project_name: str) -> None:
    """Create TUTORIAL.md file."""
    content = f'''# {project_name} Tutorial

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
'''
    _write_file(project_path / "TUTORIAL.md", content)


def _create_gitignore(project_path: Path) -> None:
    """Create .gitignore file."""
    content = '''# Python
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
'''
    _write_file(project_path / ".gitignore", content)


def _create_init_files(project_path: Path) -> None:
    """Create __init__.py files."""
    init_files = [
        (project_path / "src" / "__init__.py", '"""Source package."""\n'),
        (project_path / "src" / "nodes" / "__init__.py", '"""Node modules."""\n'),
        (project_path / "src" / "common" / "__init__.py", '"""Common utilities."""\n'),
        (project_path / "tests" / "__init__.py", ""),
    ]
    for path, content in init_files:
        _write_file(path, content)


def _create_conftest_py(project_path: Path) -> None:
    """Create tests/conftest.py file."""
    content = '''"""Pytest configuration."""

import pytest
'''
    _write_file(project_path / "tests" / "conftest.py", content)


def _create_example_entry(project_path: Path) -> None:
    """Create example entry point."""
    content = '''"""Hello World entry point."""

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
'''
    _write_file(project_path / "src" / "hello.py", content)


def _create_project_structure(
    project_path: Path,
    project_name: str,
    python_version: str,
    with_examples: bool,
) -> None:
    """Create all project directories and files."""
    # Create directories (functional approach with map)
    directories = [
        project_path / "src" / "nodes",
        project_path / "src" / "common",
        project_path / "tests" / "nodes",
        project_path / "config",
        project_path / "logs",
    ]
    list(map(_create_directory, directories))

    # Create files (using pure functions)
    _create_pyproject_toml(project_path, project_name, python_version)
    _create_env_example(project_path, project_name)
    _create_development_yaml(project_path, project_name)
    _create_settings_py(project_path)
    _create_tutorial_md(project_path, project_name)
    _create_gitignore(project_path)
    _create_init_files(project_path)
    _create_conftest_py(project_path)

    # Create example if requested
    if with_examples:
        _create_example_entry(project_path)


def _show_success_output(project_name: str) -> None:
    """Display success message and next steps."""
    typer.echo(f"\nCreated project: {project_name}\n")
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


def init(
    project_name: str = typer.Argument(..., help="Name of the project to create"),
    python_version: str = typer.Option("3.10", help="Minimum Python version"),
    with_examples: bool = typer.Option(False, help="Include example entry points"),
) -> None:
    """
    Create a new Railway Framework project.

    Creates the project directory structure with all necessary files
    for a Railway-based automation project.
    """
    # Validate project name
    normalized_name = _validate_project_name(project_name)

    # Check if directory exists
    project_path = Path.cwd() / normalized_name
    if project_path.exists():
        typer.echo(f"Error: Directory '{normalized_name}' already exists", err=True)
        raise typer.Exit(1)

    # Create directory structure
    _create_project_structure(project_path, normalized_name, python_version, with_examples)

    # Show success message
    _show_success_output(normalized_name)
