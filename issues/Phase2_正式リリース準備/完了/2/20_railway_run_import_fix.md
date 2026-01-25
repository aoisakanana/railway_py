# Issue #20: railway run コマンドの import パス対応

**Phase:** 2d
**優先度:** 高
**依存関係:** #17
**見積もり:** 0.5日

---

## 概要

`railway run <entrypoint>` コマンドが、`src` を省略した import 文に対応できていない。

`uv run python -m` で `src` ディレクトリをモジュールルートとして扱うようにした結果、生成されるコードの import 文から `src.` プレフィックスが除外されるようになった。しかし、`railway run` コマンドが古い `src.` プレフィックス付きのパスを想定しているため、エントリーポイントの実行に失敗する。

---

## 現状の問題

### 生成される import 文（新形式）

```python
# src/my_workflow.py
from nodes.my_workflow.start import start  # src. なし
from contracts.my_context import MyContext  # src. なし
```

### railway run の期待（旧形式）

```python
# railway run が内部で想定しているパス
import src.my_workflow  # src. プレフィックス付き
```

### エラー例

```bash
$ railway run my_workflow
ModuleNotFoundError: No module named 'src.my_workflow'
```

---

## 解決策

`railway run` コマンドを修正し、以下の動作を実現する：

1. **src ディレクトリをモジュールルートとして扱う**
2. **sys.path に src を追加** してから import を実行
3. **エントリーポイント名から直接モジュールを解決**

---

## 成果物

### 修正後の動作

```bash
$ railway run my_workflow
# 内部で以下を実行:
# 1. sys.path に src/ を追加
# 2. import my_workflow
# 3. my_workflow.main() を実行
```

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/cli/test_run_import.py
"""Tests for railway run command import handling."""
import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestRunWithoutSrcPrefix:
    """Test railway run works without src. prefix in imports."""

    def test_run_finds_entrypoint_without_src_prefix(self, tmp_path, monkeypatch):
        """Should find entrypoint in src/ without src. prefix."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)

        # Create project structure
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "__init__.py").touch()

        # Create entrypoint without src. prefix imports
        (tmp_path / "src" / "my_entry.py").write_text('''
from railway import entry_point

@entry_point
def main():
    return {"status": "ok"}
''')

        result = runner.invoke(app, ["run", "my_entry"])

        assert result.exit_code == 0, f"Failed: {result.output}"

    def test_run_resolves_internal_imports(self, tmp_path, monkeypatch):
        """Should resolve imports between modules in src/."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)

        # Create project structure
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "__init__.py").touch()
        (tmp_path / "src" / "contracts").mkdir()
        (tmp_path / "src" / "contracts" / "__init__.py").touch()

        # Create contract
        (tmp_path / "src" / "contracts" / "my_contract.py").write_text('''
from railway import Contract

class MyResult(Contract):
    value: str
''')

        # Create entrypoint that imports contract
        (tmp_path / "src" / "my_entry.py").write_text('''
from railway import entry_point
from contracts.my_contract import MyResult

@entry_point
def main():
    return MyResult(value="test")
''')

        result = runner.invoke(app, ["run", "my_entry"])

        assert result.exit_code == 0, f"Failed: {result.output}"

    def test_run_resolves_nodes_imports(self, tmp_path, monkeypatch):
        """Should resolve imports from nodes/ directory."""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)

        # Create project structure
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "__init__.py").touch()
        (tmp_path / "src" / "nodes").mkdir()
        (tmp_path / "src" / "nodes" / "__init__.py").touch()

        # Create node
        (tmp_path / "src" / "nodes" / "my_node.py").write_text('''
from railway import node

@node
def my_node():
    return {"done": True}
''')

        # Create entrypoint that imports node
        (tmp_path / "src" / "my_entry.py").write_text('''
from railway import entry_point, pipeline
from nodes.my_node import my_node

@entry_point
def main():
    return pipeline(my_node())
''')

        result = runner.invoke(app, ["run", "my_entry"])

        assert result.exit_code == 0, f"Failed: {result.output}"


class TestRunSrcPathHandling:
    """Test sys.path manipulation for src/ imports."""

    def test_src_added_to_path(self, tmp_path, monkeypatch):
        """Should add src/ to sys.path before import."""
        from railway.cli.run import _setup_src_path
        import sys

        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()

        original_path = sys.path.copy()

        _setup_src_path()

        src_path = str(tmp_path / "src")
        assert src_path in sys.path, "src/ should be in sys.path"

        # Cleanup
        sys.path[:] = original_path

    def test_src_path_is_first(self, tmp_path, monkeypatch):
        """src/ should be first in sys.path for priority."""
        from railway.cli.run import _setup_src_path
        import sys

        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()

        original_path = sys.path.copy()

        _setup_src_path()

        src_path = str(tmp_path / "src")
        # src should be at index 0 or 1 (after '')
        assert sys.path.index(src_path) <= 1, "src/ should be early in sys.path"

        # Cleanup
        sys.path[:] = original_path


class TestRunModuleResolution:
    """Test module resolution logic."""

    def test_resolve_module_from_name(self):
        """Should resolve module path from entrypoint name."""
        from railway.cli.run import _resolve_module_path

        # Simple name
        assert _resolve_module_path("my_entry") == "my_entry"

        # With subdirectory
        assert _resolve_module_path("workflows.daily") == "workflows.daily"

    def test_import_entrypoint_module(self, tmp_path, monkeypatch):
        """Should import entrypoint module dynamically."""
        from railway.cli.run import _import_entrypoint
        import sys

        monkeypatch.chdir(tmp_path)

        # Create module
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "__init__.py").touch()
        (tmp_path / "src" / "test_entry.py").write_text('''
def main():
    return "success"
''')

        # Add to path
        sys.path.insert(0, str(tmp_path / "src"))

        try:
            module = _import_entrypoint("test_entry")
            assert hasattr(module, "main")
            assert module.main() == "success"
        finally:
            sys.path.remove(str(tmp_path / "src"))
```

### Step 2: Green（実装）

`railway/cli/run.py` を修正：

```python
"""Run command implementation."""
import importlib
import sys
from pathlib import Path
from typing import Any

import typer


def _setup_src_path() -> None:
    """Add src/ directory to sys.path for imports.

    Pure function side effect: modifies sys.path
    This is necessary for Python's import system.
    """
    cwd = Path.cwd()
    src_path = cwd / "src"

    if src_path.exists() and src_path.is_dir():
        src_str = str(src_path.resolve())
        if src_str not in sys.path:
            sys.path.insert(0, src_str)


def _resolve_module_path(entrypoint: str) -> str:
    """Resolve module path from entrypoint name.

    Args:
        entrypoint: Entrypoint name (e.g., "my_workflow" or "workflows.daily")

    Returns:
        Module path for import
    """
    # Remove .py extension if present
    if entrypoint.endswith(".py"):
        entrypoint = entrypoint[:-3]

    # Remove src. prefix if present (for backwards compatibility)
    if entrypoint.startswith("src."):
        entrypoint = entrypoint[4:]

    return entrypoint


def _import_entrypoint(module_path: str) -> Any:
    """Import entrypoint module dynamically.

    Args:
        module_path: Module path to import

    Returns:
        Imported module

    Raises:
        ModuleNotFoundError: If module cannot be found
    """
    return importlib.import_module(module_path)


def _get_main_function(module: Any) -> callable:
    """Get main function from module.

    Args:
        module: Imported module

    Returns:
        Main function

    Raises:
        AttributeError: If main function not found
    """
    if not hasattr(module, "main"):
        raise AttributeError(f"Module {module.__name__} has no 'main' function")
    return module.main


def run_entrypoint(entrypoint: str) -> Any:
    """Run an entrypoint by name.

    Args:
        entrypoint: Name of the entrypoint to run

    Returns:
        Result from the entrypoint's main function
    """
    # Setup import path
    _setup_src_path()

    # Resolve module path
    module_path = _resolve_module_path(entrypoint)

    # Import and run
    module = _import_entrypoint(module_path)
    main_fn = _get_main_function(module)

    return main_fn()
```

### Step 3: Refactor

1. **純粋関数の分離**: `_resolve_module_path` は純粋関数として維持
2. **副作用の局所化**: `_setup_src_path` のみが `sys.path` を変更
3. **テスト容易性**: 各関数を個別にテスト可能に

---

## 完了条件

- [x] `railway run <entrypoint>` が `src/` 配下のエントリーポイントを実行できる
- [x] `src.` プレフィックスなしの import 文が解決される
- [x] `nodes/`, `contracts/` 間の相互 import が動作する
- [x] 既存の `src.` プレフィックス付きコードとの後方互換性
- [x] 全テストが通過（786テスト）

---

## 関連ファイル

- `railway/cli/run.py` - run コマンド実装
- `railway/cli/main.py` - CLI エントリーポイント
- `tests/unit/cli/test_run_import.py` - テスト（新規）

---

## 備考

- `uv run python -m <module>` での実行時は、`pyproject.toml` の設定により `src/` がモジュールルートになる
- `railway run` は内部で同等の動作を再現する必要がある
- `sys.path` の操作は副作用だが、Python の import システム上避けられない
