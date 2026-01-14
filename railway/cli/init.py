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
    content = f'''# {project_name} チュートリアル

Railway Framework プロジェクトへようこそ！このチュートリアルでは、手順通りに実行すれば動作するサンプルを作成します。

## 前提条件

- Python 3.10以上
- uv インストール済み（`curl -LsSf https://astral.sh/uv/install.sh | sh`）
- 依存関係インストール済み（`uv sync`）
- 環境設定済み（`cp .env.example .env`）

---

## Step 1: Hello World（5分）

### 1.1 エントリポイントを作成

```bash
railway new entry hello
```

### 1.2 ファイルを編集

`src/hello.py` を以下の内容で**上書き**してください:

```python
"""hello entry point."""

from railway import entry_point, node
from loguru import logger


@node
def greet(name: str) -> str:
    """挨拶する"""
    logger.info(f"Greeting {{name}}")
    return f"Hello, {{name}}!"


@entry_point
def main(name: str = "World"):
    """シンプルな Hello World エントリポイント"""
    message = greet(name)
    print(message)
    return message


if __name__ == "__main__":
    main()
```

### 1.3 実行

```bash
uv run railway run hello
```

**期待される出力:**
```
Running entry point: hello
... | INFO | [greet] Starting...
... | INFO | Greeting World
... | INFO | [greet] ✓ Completed
Hello, World!
... | INFO | [main] ✓ Completed successfully
```

### 1.4 引数を渡して実行

```bash
uv run railway run hello -- --name Alice
```

**期待される出力:**
```
Hello, Alice!
```

---

## Step 2: パイプライン処理（10分）

複数のノードを連結して処理を行います。

### 2.1 ノードを作成

```bash
railway new node fetch_data
railway new node process_data
```

### 2.2 fetch_data ノードを編集

`src/nodes/fetch_data.py` を以下の内容で**上書き**してください:

```python
"""fetch_data node."""

from railway import node
from loguru import logger


@node
def fetch_data(user_id: int) -> dict:
    """ユーザーデータを取得する（サンプル）"""
    logger.info(f"Fetching data for user {{user_id}}")
    # 実際のAPIコールの代わりにサンプルデータを返す
    return {{
        "user_id": user_id,
        "name": "Taro Yamada",
        "email": "taro@example.com",
    }}
```

### 2.3 process_data ノードを編集

`src/nodes/process_data.py` を以下の内容で**上書き**してください:

```python
"""process_data node."""

from railway import node
from loguru import logger


@node
def process_data(data: dict) -> dict:
    """データを加工する"""
    logger.info(f"Processing data for user {{data['user_id']}}")
    return {{
        **data,
        "processed": True,
        "display_name": data["name"].upper(),
    }}
```

### 2.4 パイプライン用エントリポイントを作成

```bash
railway new entry user_report
```

`src/user_report.py` を以下の内容で**上書き**してください:

```python
"""user_report entry point."""

from railway import entry_point, pipeline
from loguru import logger

from src.nodes.fetch_data import fetch_data
from src.nodes.process_data import process_data


@entry_point
def main(user_id: int = 1):
    """ユーザーレポートを生成する

    Args:
        user_id: ユーザーID（デフォルト: 1）
    """
    result = pipeline(
        fetch_data(user_id),  # 最初の値
        process_data,          # 次の処理
    )
    logger.info(f"Result: {{result}}")
    print(f"Display Name: {{result['display_name']}}")
    return result


if __name__ == "__main__":
    main()
```

### 2.5 実行

```bash
uv run railway run user_report
```

**期待される出力:**
```
Running entry point: user_report
... | INFO | [fetch_data] Starting...
... | INFO | Fetching data for user 1
... | INFO | [fetch_data] ✓ Completed
... | INFO | [process_data] Starting...
... | INFO | Processing data for user 1
... | INFO | [process_data] ✓ Completed
... | INFO | Result: {{'user_id': 1, 'name': 'Taro Yamada', ...}}
Display Name: TARO YAMADA
... | INFO | [main] ✓ Completed successfully
```

別のユーザーIDで実行:
```bash
uv run railway run user_report -- --user-id 42
```

---

## Step 3: エラーハンドリング（5分）

@node デコレータはエラーを自動的にキャッチしてログに出力します。

### 3.1 エラーが発生するノードを作成

```bash
railway new node divide
```

`src/nodes/divide.py` を以下の内容で**上書き**してください:

```python
"""divide node."""

from railway import node


@node
def divide(a: float, b: float) -> float:
    """割り算を行う"""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
```

### 3.2 テスト用エントリポイントを作成

```bash
railway new entry calc
```

`src/calc.py` を以下の内容で**上書き**してください:

```python
"""calc entry point."""

from railway import entry_point
from src.nodes.divide import divide


@entry_point
def main(a: float = 10, b: float = 2):
    """割り算を実行する

    Args:
        a: 被除数
        b: 除数
    """
    result = divide(a, b)
    print(f"{{a}} / {{b}} = {{result}}")
    return result


if __name__ == "__main__":
    main()
```

### 3.3 正常実行

```bash
uv run railway run calc
```

**期待される出力:**
```
10.0 / 2.0 = 5.0
```

### 3.4 エラー発生時

```bash
uv run railway run calc -- --b 0
```

**期待される出力:**
```
... | ERROR | [divide] ✗ Failed: ValueError: Cannot divide by zero
... | ERROR | 詳細は logs/app.log を確認してください
... | ERROR | ヒント: 入力データの形式や値を確認してください。
```

---

## Step 4: テストの実行（5分）

### 4.1 テストファイルを編集

`railway new node` で作成したノードには、テストファイルが自動生成されています。

`tests/nodes/test_divide.py` を以下の内容で**上書き**してください:

```python
"""Tests for divide node."""

import pytest
from src.nodes.divide import divide


class TestDivide:
    """divide ノードのテスト"""

    def test_divide_success(self):
        """正常系: 割り算が成功する"""
        result = divide(10, 2)
        assert result == 5.0

    def test_divide_by_zero(self):
        """異常系: ゼロ除算でエラー"""
        with pytest.raises(ValueError) as exc_info:
            divide(10, 0)
        assert "Cannot divide by zero" in str(exc_info.value)
```

### 4.2 テスト実行

```bash
uv run pytest tests/nodes/test_divide.py -v
```

**期待される出力:**
```
tests/nodes/test_divide.py::TestDivide::test_divide_success PASSED
tests/nodes/test_divide.py::TestDivide::test_divide_by_zero PASSED
```

---

## トラブルシューティング

### エラー: "Module not found"
```
ModuleNotFoundError: No module named 'src.nodes.fetch_data'
```

**解決方法:**
- プロジェクトルートから実行しているか確認
- ファイルが正しいパスに存在するか確認
- `uv run railway run` を使用する

### エラー: "Missing argument"
```
Missing argument 'SOURCE'.
```

**解決方法:**
- `--` の後に引数を渡す: `uv run railway run entry_name -- --arg value`
- または、関数の引数にデフォルト値を設定する

---

## 次のステップ

1. **リトライ機能**: `@node(retry=True)` でネットワークエラーなどに対応
2. **設定管理**: `config/development.yaml` で環境別設定
3. **型チェック**: `uv run mypy src/` で型安全性を確認

詳細は Railway Framework のドキュメントを参照してください。
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
