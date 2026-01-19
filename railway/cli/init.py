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

[dependency-groups]
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

# src/ プレフィックスを取り除く設定
[tool.hatch.build.targets.wheel.sources]
"src" = ""
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

Railway Framework の**型安全なパイプライン**を体験しましょう！

## 学べること

- Contract（型契約）によるデータ定義
- Node（処理単位）の実装
- IDE補完の活用
- TDDワークフロー
- typed_pipeline による依存関係の自動解決

## 所要時間

約15分

## 前提条件

- Python 3.10以上
- uv インストール済み（`curl -LsSf https://astral.sh/uv/install.sh | sh`）
- VSCode推奨（IDE補完を体験するため）

## セットアップ

```bash
uv sync --group dev
cp .env.example .env
```

---

## Step 1: Hello World（2分）

まずは動作確認から。

### 1.1 実行

```bash
uv run railway run hello
```

**期待される出力:**
```
Hello, World!
```

🎉 **2分で動きました！** 次のStepでは、型安全の核心「Contract」を学びます。

---

## Step 2: Contract - データの「契約」を定義する（3分）

従来のパイプラインの問題点：

```python
# ❌ 従来: 何が入っているか分からない
def process(data):
    users = data["users"]  # KeyError? typo? IDE補完なし
```

Railwayでは**Contract**でデータ構造を定義します：

```python
# ✅ Railway: 型で明確に定義
class UsersFetchResult(Contract):
    users: list[User]
    total: int
```

### 2.1 Contractを作成

```bash
railway new contract UsersFetchResult
```

### 2.2 ファイルを編集

`src/contracts/users_fetch_result.py` を以下の内容で**上書き**してください:

```python
"""UsersFetchResult contract."""

from railway import Contract


class User(Contract):
    """ユーザーエンティティ"""
    id: int
    name: str
    email: str


class UsersFetchResult(Contract):
    """fetch_usersノードの出力契約"""
    users: list[User]
    total: int
```

**ポイント:**
- **Pydantic BaseModel** がベース（自動バリデーション）
- フィールドに型を指定 → **IDE補完が効く**

---

## Step 3: TDD - テストを先に書く（3分）

Railwayでは**テストファースト**を推奨。まず失敗するテストを書きます。

### 3.1 型付きノードを生成

```bash
railway new node fetch_users --output UsersFetchResult
```

`--output` オプションで出力型を指定すると、テストファイルも型付きで生成されます。

### 3.2 テストを編集（Red Phase）

`tests/nodes/test_fetch_users.py` を以下の内容で**上書き**してください:

```python
"""Tests for fetch_users node."""

from contracts.users_fetch_result import UsersFetchResult
from nodes.fetch_users import fetch_users


class TestFetchUsers:
    def test_returns_users_fetch_result(self):
        """正しい型を返すこと"""
        result = fetch_users()
        assert isinstance(result, UsersFetchResult)

    def test_returns_at_least_one_user(self):
        """少なくとも1人のユーザーを返すこと"""
        result = fetch_users()
        assert result.total >= 1  # IDE補完が効く！
        assert len(result.users) == result.total
```

**💡 ポイント: モックが不要！**

```python
# ❌ 従来: Contextのモックが必要
def test_fetch_users():
    ctx = MagicMock()
    fetch_users(ctx)
    ctx.__setitem__.assert_called_with(...)

# ✅ Railway: 引数を渡して戻り値を確認するだけ
def test_fetch_users():
    result = fetch_users()
    assert result.total >= 1
```

### 3.3 テスト実行（失敗を確認）

```bash
uv run pytest tests/nodes/test_fetch_users.py -v
```

🔴 **Red Phase!** テストが失敗することを確認しました。

---

## Step 4: Node実装（3分）

テストを通すための実装を書きます。

### 4.1 ノードを実装（Green Phase）

`src/nodes/fetch_users.py` を以下の内容で**上書き**してください:

```python
"""fetch_users node."""

from railway import node
from contracts.users_fetch_result import UsersFetchResult, User


@node(output=UsersFetchResult)
def fetch_users() -> UsersFetchResult:
    """ユーザー一覧を取得する"""
    users = [
        User(id=1, name="Alice", email="alice@example.com"),
        User(id=2, name="Bob", email="bob@example.com"),
    ]
    return UsersFetchResult(
        users=users,
        total=len(users),
    )
```

### 4.2 テスト実行（成功を確認）

```bash
uv run pytest tests/nodes/test_fetch_users.py -v
```

🟢 **Green Phase!** テストが通りました。

**ポイント:**
- `@node(output=UsersFetchResult)` で出力型を宣言
- 純粋関数：引数を受け取り、値を返すだけ
- 型が保証される

---

## Step 5: IDE補完を体験する（2分）

Output Modelパターンの最大の利点を体験しましょう。

### 5.1 別のノードを作成

```bash
railway new contract ReportResult
railway new node generate_report --input users:UsersFetchResult --output ReportResult
```

### 5.2 ContractとNodeを編集

`src/contracts/report_result.py`:

```python
"""ReportResult contract."""

from datetime import datetime
from railway import Contract


class ReportResult(Contract):
    """レポート生成結果"""
    content: str
    user_count: int
    generated_at: datetime
```

### 5.3 VSCodeで補完を試す

`src/nodes/generate_report.py` を開き、以下のように編集してみてください:

```python
"""generate_report node."""

from datetime import datetime
from railway import node
from contracts.users_fetch_result import UsersFetchResult
from contracts.report_result import ReportResult


@node(
    inputs={{"users": UsersFetchResult}},
    output=ReportResult,
)
def generate_report(users: UsersFetchResult) -> ReportResult:
    # ここで users. と入力して Ctrl+Space を押してください！
    names = ", ".join(u.name for u in users.users)  # IDE補完が効く！
    return ReportResult(
        content=f"Users: {{names}}",
        user_count=users.total,  # typo するとIDEが警告
        generated_at=datetime.now(),
    )
```

🎉 **IDE補完が効く！** `users.` と入力すると候補が表示されます。

---

## Step 6: typed_pipeline - 依存関係の自動解決（3分）

複数のNodeを組み合わせてパイプラインを構築します。

### 6.1 エントリポイントを作成

```bash
railway new entry user_report
```

`src/user_report.py` を以下の内容で**上書き**してください:

```python
"""user_report entry point."""

from railway import entry_point, typed_pipeline

from nodes.fetch_users import fetch_users
from nodes.generate_report import generate_report


@entry_point
def main():
    """ユーザーレポートを生成する"""
    result = typed_pipeline(
        fetch_users,      # UsersFetchResult を出力
        generate_report,  # UsersFetchResult を入力 → ReportResult を出力
    )

    print(result.content)      # IDE補完が効く！
    print(f"Count: {{result.user_count}}")
    return result


if __name__ == "__main__":
    main()
```

### 6.2 実行

```bash
uv run railway run user_report
```

**期待される出力:**
```
Users: Alice, Bob
Count: 2
```

**依存関係の自動解決:**

```
fetch_users ──────────────> generate_report
  output: UsersFetchResult    input: UsersFetchResult
                              output: ReportResult
```

フレームワークが**型を見て自動的に依存関係を解決**します。

### 6.3 Nodeはパイプライン構成に依存しない

これがOutput Modelパターンの核心的な利点です:

```python
# 構成1: シンプル
typed_pipeline(fetch_users, generate_report)

# 構成2: 間にフィルター処理を追加
typed_pipeline(fetch_users, filter_active_users, generate_report)

# 構成3: データ加工を追加
typed_pipeline(fetch_users, enrich_users, generate_report)

# ↑ どの構成でも generate_report の実装は同じ！
```

**なぜこれが重要か:**

| 従来 | Railway |
|------|---------|
| パイプライン変更時にNode修正が必要 | Node修正不要 |
| 前後のNode実装を意識 | 入出力Contractだけを意識 |
| 結合テストが必須 | 単体テストで十分 |

`generate_report` は**「UsersFetchResultを受け取りReportResultを返す」**という契約だけを守ればよく、パイプラインの全体構成には一切依存しません。

---

## Step 7: 安全なリファクタリング（2分）

Output Modelパターンのもう一つの利点を体験します。

### 7.1 フィールド名を変更したい

`UsersFetchResult.total` を `count` に変更したいとします。

### 7.2 従来の問題

```python
# ❌ 従来: 文字列なので grep で探すしかない
data["total"]  # どこで使われてる？ 変更漏れがあっても実行時まで気づかない
```

### 7.3 Railwayでの安全な変更

1. **Contract を変更:**
   `src/contracts/users_fetch_result.py` の `total` を `count` に変更

2. **IDEが全参照箇所をハイライト**

3. **一括リネーム (F2キー)**

4. **型チェックで確認:**
   ```bash
   uv run mypy src/
   ```

🎉 **変更漏れゼロ！** IDEと型チェッカーが守ってくれます。

---

## 次のステップ

おめでとうございます！🎉 Railwayの基本を習得しました。

### 学んだこと

- Contract で型契約を定義
- Node で純粋関数として処理を実装
- TDD でテストファーストに開発
- IDE補完の活用
- typed_pipeline で依存関係を自動解決
- 安全なリファクタリング

### さらに学ぶ

1. **リトライ機能**: `@node(retry=True)` でネットワークエラーに対応
2. **設定管理**: `config/development.yaml` で環境別設定
3. **非同期処理**: `typed_async_pipeline` で非同期対応
4. **ドキュメント**: `railway docs` で詳細を確認

---

## トラブルシューティング

### mypy で型チェックが効かない場合

mypyで「Skipping analyzing "railway"」と表示される場合:

```bash
# 1. パッケージを再インストール
uv sync --reinstall-package railway-framework

# 2. mypy キャッシュをクリア
rm -rf .mypy_cache/

# 3. 確認
uv run mypy src/
```

### テストが失敗する場合

```bash
# pytest キャッシュをクリア
rm -rf .pytest_cache/ __pycache__/

# 依存関係を再同期
uv sync
```
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
    content = '''"""Pytest configuration and shared fixtures."""

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


def _create_simple_hello_entry(project_path: Path) -> None:
    """Create minimal hello.py for immediate verification.

    This simple entry point allows users to verify their setup works
    immediately after `railway init` without any additional steps.
    """
    content = '''"""Hello World entry point - セットアップ確認用."""

from railway import entry_point


@entry_point
def hello():
    """最小限のHello World

    railway init 後すぐに動作確認できます:
        uv run railway run hello
    """
    print("Hello, World!")
    return {"message": "Hello, World!"}


if __name__ == "__main__":
    hello()
'''
    _write_file(project_path / "src" / "hello.py", content)


def _create_example_entry(project_path: Path) -> None:
    """Create complex example entry point with pipeline demonstration."""
    content = '''"""Hello World entry point with pipeline example."""

from railway import entry_point, node, pipeline


@node
def validate_name(name: str) -> str:
    """名前を検証して正規化する（純粋関数）"""
    if not name or not name.strip():
        raise ValueError("Name cannot be empty")
    return name.strip()


@node
def create_greeting(name: str) -> str:
    """挨拶メッセージを作成する（純粋関数）"""
    return f"Hello, {name}!"


@entry_point
def hello(name: str = "World"):
    """パイプラインを使った Hello World

    Args:
        name: 挨拶する相手の名前

    Usage:
        uv run railway run hello
        uv run railway run hello --name Alice
    """
    message = pipeline(
        name,
        validate_name,
        create_greeting,
    )
    print(message)
    return message


if __name__ == "__main__":
    hello()
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

    # Create hello entry point
    # Default: simple hello.py for immediate verification
    # --with-examples: complex pipeline example
    if with_examples:
        _create_example_entry(project_path)
    else:
        _create_simple_hello_entry(project_path)


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
    typer.echo("  2. uv sync --group dev")
    typer.echo("  3. cp .env.example .env")
    typer.echo("  4. uv run railway run hello  # 動作確認")
    typer.echo("  5. Open TUTORIAL.md and follow the guide")


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
