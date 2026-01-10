# Issue #14: TUTORIAL.md自動生成

**Phase:** 1b
**優先度:** 中
**依存関係:** #08
**見積もり:** 0.5日

---

## 概要

`railway init`でプロジェクト作成時に、段階的チュートリアル（TUTORIAL.md）を自動生成する。
仕様書9節で定義されたTUTORIAL.md仕様に基づく。

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/cli/test_tutorial_generation.py
"""Tests for TUTORIAL.md generation."""
import pytest
from pathlib import Path
import tempfile
import os


class TestTutorialGeneration:
    """Test TUTORIAL.md generation."""

    def test_init_creates_tutorial(self):
        """Should create TUTORIAL.md."""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)

            tutorial = project_path / "TUTORIAL.md"
            assert tutorial.exists()

    def test_tutorial_has_title(self):
        """Should have title with project name."""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "my_automation"
            _create_project_structure(project_path, "my_automation", "3.10", False)

            content = (project_path / "TUTORIAL.md").read_text()
            assert "my_automation" in content or "Tutorial" in content

    def test_tutorial_has_quick_start(self):
        """Should have quick start section."""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)

            content = (project_path / "TUTORIAL.md").read_text()
            assert "quick start" in content.lower() or "step 1" in content.lower()

    def test_tutorial_has_code_examples(self):
        """Should have code examples."""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)

            content = (project_path / "TUTORIAL.md").read_text()
            assert "```" in content  # Code blocks

    def test_tutorial_mentions_railway_commands(self):
        """Should mention railway CLI commands."""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)

            content = (project_path / "TUTORIAL.md").read_text()
            assert "railway" in content.lower()

    def test_tutorial_has_troubleshooting(self):
        """Should have troubleshooting section."""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)

            content = (project_path / "TUTORIAL.md").read_text()
            # May have troubleshooting or common errors section
            assert "error" in content.lower() or "troubleshoot" in content.lower()


class TestTutorialContent:
    """Test TUTORIAL.md content quality."""

    def test_tutorial_explains_node_decorator(self):
        """Should explain @node decorator."""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)

            content = (project_path / "TUTORIAL.md").read_text()
            assert "@node" in content

    def test_tutorial_explains_entry_point(self):
        """Should explain @entry_point decorator."""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)

            content = (project_path / "TUTORIAL.md").read_text()
            assert "@entry_point" in content or "entry_point" in content

    def test_tutorial_explains_pipeline(self):
        """Should explain pipeline function."""
        from railway.cli.init import _create_project_structure

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            _create_project_structure(project_path, "test_project", "3.10", False)

            content = (project_path / "TUTORIAL.md").read_text()
            assert "pipeline" in content.lower()
```

```bash
# 実行して失敗を確認
pytest tests/unit/cli/test_tutorial_generation.py -v
# Expected: PASSED or partial (depends on existing implementation)
```

### Step 2: Green（実装確認・更新）

TUTORIAL.mdテンプレートを作成（または更新）:

```python
# railway/templates/project/tutorial.md.jinja
"""TUTORIAL.md template based on spec section 9."""

TUTORIAL_TEMPLATE = '''# {{ project_name }} Tutorial

Welcome to your Railway Framework project! This tutorial will guide you from zero to hero.

## Prerequisites

- Python 3.10+
- uv installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

---

## Step 1: Hello World (5 minutes)

### 1.1 Create a simple entry point

```bash
railway new entry hello --example
```

This creates `src/hello.py`:

```python
from railway import entry_point, node

@node
def greet(name: str) -> str:
    return f"Hello, {name}!"

@entry_point
def main(name: str = "World"):
    message = greet(name)
    print(message)
    return message

if __name__ == "__main__":
    main()
```

### 1.2 Run it

```bash
railway run hello
# Output: Hello, World!

railway run hello --name Alice
# Output: Hello, Alice!
```

### 1.3 Choosing how to run

**Method 1: `railway run` command (Recommended)**
```bash
railway run hello --name Alice
```

**Method 2: Direct Python module execution**
```bash
uv run python -m src.hello --name Alice
```

Both produce the same results. Use `railway run` for daily development.

---

## Step 2: Error Handling (10 minutes)

Railway handles errors automatically with @node decorator.

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
pytest tests/
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
ModuleNotFoundError: No module named \'src.nodes.fetch_data\'
```

**Solution:**
- Make sure you\'re running from the project root
- Check that the file exists at the correct path
- Use `railway run` instead of `python -m`

#### Error: "Configuration error"
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for APISettings
base_url
  Field required [type=missing, input_value={}, input_type=dict]
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
```

---

## 完了条件

- [ ] TUTORIAL.mdがプロジェクト作成時に生成される
- [ ] プロジェクト名がTUTORIAL.mdに含まれる
- [ ] Hello Worldの例が含まれる
- [ ] @node, @entry_point, pipelineの説明が含まれる
- [ ] 設定管理の説明が含まれる
- [ ] テストの説明が含まれる
- [ ] トラブルシューティングが含まれる
- [ ] テストカバレッジ90%以上

---

## 次のIssue

- #15: テストテンプレート自動生成
