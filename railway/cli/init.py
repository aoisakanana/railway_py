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

[tool.hatch.build.targets.wheel]
packages = ["src"]
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

Welcome to your Railway Framework project! This tutorial will guide you from zero to hero.

## Prerequisites

- Python 3.10+
- uv installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

---

## Step 1: Hello World (5 minutes)

### 1.1 Create a simple entry point

```bash
railway new entry hello
```

This creates `src/hello.py`. Edit it to create a simple Hello World:

```python
"""hello entry point."""

from railway import entry_point, node
from loguru import logger


@node
def greet(name: str) -> str:
    """Greet someone."""
    logger.info(f"Greeting {{name}}")
    return f"Hello, {{name}}!"


@entry_point
def main(name: str = "World"):
    """Simple hello world entry point."""
    message = greet(name)
    print(message)
    return message


if __name__ == "__main__":
    main()
```

### 1.2 Run it

```bash
uv run railway run hello
# Output: Hello, World!

uv run railway run hello -- --name Alice
# Output: Hello, Alice!
```

---

## Step 2: Error Handling (10 minutes)

Railway handles errors automatically with the @node decorator.

### 2.1 Create a node that can fail

```bash
railway new node divide
```

Edit `src/nodes/divide.py`:

```python
from railway import node

@node
def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
```

### 2.2 Errors are caught and logged

When an error occurs:
- The error is logged with type and message
- A hint may be provided for common errors
- The log file location is shown

---

## Step 3: Pipeline Processing (10 minutes)

### 3.1 Create nodes

```bash
railway new node fetch_data --example
railway new node process_data --example
```

### 3.2 Create a pipeline entry point

```python
from railway import entry_point, pipeline
from src.nodes.fetch_data import fetch_data
from src.nodes.process_data import process_data

@entry_point
def main(source: str):
    result = pipeline(
        fetch_data(source),  # Initial value
        process_data,        # Step 1
    )
    return result
```

**Key concept:** The first argument to `pipeline()` is the initial value.
Subsequent arguments are functions that receive the previous result.

---

## Step 4: Configuration (15 minutes)

### 4.1 Edit config file

Edit `config/development.yaml`:

```yaml
api:
  base_url: "https://api.example.com"
  timeout: 30

retry:
  default:
    max_attempts: 3
  nodes:
    fetch_data:
      max_attempts: 5
```

### 4.2 Use settings in your code

```python
from railway import node
from src.settings import settings

@node
def fetch_data() -> dict:
    url = settings.api.base_url + "/data"
    timeout = settings.api.timeout
    # Use url and timeout...
```

---

## Step 5: Testing (20 minutes)

### 5.1 Run existing tests

```bash
uv run pytest tests/
```

### 5.2 Write your own test

When you create nodes with `railway new node`, test files are created automatically.

```python
# tests/nodes/test_divide.py
import pytest
from src.nodes.divide import divide

def test_divide_success():
    result = divide(10, 2)
    assert result == 5.0

def test_divide_by_zero():
    with pytest.raises(ValueError):
        divide(10, 0)
```

---

## Step 6: Troubleshooting

### Common Errors

#### Error: "Module not found"
```
ModuleNotFoundError: No module named 'src.nodes.fetch_data'
```

**Solution:**
- Make sure you're running from the project root
- Check that the file exists at the correct path
- Use `uv run railway run` instead of `python -m`

#### Error: "Configuration error"
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for APISettings
base_url
  Field required [type=missing, input_value={{}}, input_type=dict]
```

**Solution:**
- Check `config/development.yaml` has the required field
- Make sure `.env` has `RAILWAY_ENV=development`
- Verify the config file is valid YAML

---

## Next Steps

1. **Add retry handling**: Use `@node(retry=True)`
2. **Configure logging**: Edit `config/development.yaml`
3. **Add type hints**: Use Pydantic models for type-safe data

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
