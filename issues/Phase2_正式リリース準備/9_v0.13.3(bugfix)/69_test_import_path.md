# Issue #69: テスト自動生成のインポートパス修正

## 優先度

**High**

## 問題

`railway new entry` で生成されるテストファイルが、`src/` を `sys.path` に含めていないため、インポートに失敗する。

### 現状

```python
# 生成される tests/conftest.py（問題あり）
@pytest.fixture
def sample_user_data() -> dict:
    ...
# sys.path の設定がない！

# 生成されるテストファイル (tests/test_greeting.py)
from greeting import main  # ModuleNotFoundError
```

### 根本原因

`railway init` で生成される `conftest.py` が `src/` を `sys.path` に追加していない。

### 期待される動作

```python
# tests/conftest.py に追加すべき設定
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

これにより、テストファイルは以下のようにインポートできる:

```python
# src/ 配下のモジュールを直接インポート
from greeting import main
from nodes.greeting.start import start
```

## 解決策

### 設計判断

| 選択肢 | メリット | デメリット |
|--------|----------|------------|
| A) conftest.py で sys.path 設定 | 標準的、一箇所で管理 | なし |
| B) pyproject.toml の設定で対応 | 設定ファイルで完結 | ツール依存 |
| C) テストで `src.` プレフィックス使用 | 明示的 | 冗長、一貫性なし |

**採用: A) conftest.py で sys.path 設定**

理由:
- pytest の標準的なパターン
- railway 本体のテストでも同様の手法を使用
- 純粋関数でテンプレート生成可能

## 実装タスク

### 1. テスト作成（Red）

```python
# tests/unit/cli/test_conftest_template.py

from typer.testing import CliRunner
from railway.cli.main import app

runner = CliRunner()


class TestConftestTemplate:
    """conftest.py テンプレートのテスト。"""

    def test_conftest_adds_src_to_path(self, tmp_path, monkeypatch):
        """conftest.py が src/ を sys.path に追加する。"""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "myproject"])

        conftest = tmp_path / "myproject" / "tests" / "conftest.py"
        content = conftest.read_text()

        assert "sys.path.insert" in content
        assert "src" in content

    def test_generated_test_can_import_entry(self, tmp_path, monkeypatch):
        """生成されたテストがエントリをインポートできる。"""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "myproject"])
        monkeypatch.chdir(tmp_path / "myproject")

        runner.invoke(app, ["new", "entry", "greeting"])

        # テストファイルが存在し、インポートエラーがないことを確認
        test_file = tmp_path / "myproject" / "tests" / "test_greeting.py"
        assert test_file.exists()

        content = test_file.read_text()
        # src. プレフィックスなしでインポート
        assert "from greeting import" in content
```

### 2. conftest.py テンプレート修正

```python
# railway/cli/init.py

def _create_conftest_py(project_path: Path) -> None:
    """Create tests/conftest.py file with proper path setup."""
    content = '''"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path

# src/ を sys.path に追加（テストからのインポートを可能に）
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


import pytest


@pytest.fixture
def sample_user_data() -> dict:
    """サンプルユーザーデータを提供するフィクスチャ"""
    return {
        "user_id": 1,
        "name": "Test User",
        "email": "test@example.com",
    }


@pytest.fixture
def empty_data() -> dict:
    """空のデータを提供するフィクスチャ"""
    return {}
'''
    _write_file(project_path / "tests" / "conftest.py", content)
```

### 3. テストテンプレート修正

```python
# railway/cli/new.py

def _get_entry_test_template(name: str) -> str:
    """エントリポイントのテストテンプレートを生成（純粋関数）。

    Note:
        conftest.py で src/ が sys.path に追加されているため、
        src. プレフィックスなしでインポート可能。
    """
    pascal_name = _to_pascal_case(name)
    return f'''"""Tests for {name} entry point."""

import pytest
from {name} import main


class Test{pascal_name}:
    """Test {name} workflow."""

    def test_main_returns_exit_contract(self):
        """main() は ExitContract を返す。"""
        result = main()
        assert hasattr(result, "exit_code")
        assert hasattr(result, "exit_state")

    def test_main_success_path(self):
        """正常系のテスト。"""
        result = main()
        assert result.is_success

    def test_main_with_custom_context(self):
        """カスタムコンテキストでのテスト。"""
        # TODO: 実際のコンテキストに合わせて実装
        pass
'''
```

## 影響範囲

| ファイル | 変更内容 |
|----------|----------|
| `railway/cli/init.py` | `_create_conftest_py()` に sys.path 設定追加 |
| `railway/cli/new.py` | `_get_entry_test_template()` のインポートパス修正 |
| `tests/unit/cli/test_conftest_template.py` | 新規テスト |

## 既存プロジェクトへの影響

既存プロジェクトは `railway update` の対象外（v0.13.3 はバグ修正リリース）。
ユーザーは手動で `conftest.py` に以下を追加:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

## 完了条件

- [ ] conftest.py に sys.path 設定が含まれる
- [ ] 生成されたテストが src. プレフィックスなしでインポート
- [ ] pytest で実行できる
- [ ] テストが全てパス
