"""railway init command implementation."""

from datetime import datetime
from pathlib import Path
from typing import Callable

import typer

from railway import __version__
from railway.core.project_metadata import create_metadata, save_metadata


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
    """Create TUTORIAL.md file with dag_runner as default."""
    content = f'''# {project_name} チュートリアル

Railway Framework の**DAGワークフロー**を体験しましょう！

## 学べること

- dag_runner による条件分岐ワークフロー
- Outcome クラスによる状態返却
- Contract（型契約）によるデータ定義
- 遷移グラフ（YAML）の定義
- コード生成（railway sync transition）
- バージョン管理と安全なアップグレード

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

🎉 **2分で動きました！** 次のStepでは、DAGワークフローの核心を学びます。

---

## Step 2: はじめてのDAGワークフロー（5分）

DAGワークフローでは、条件分岐を含むワークフローを定義できます。

### 2.1 エントリーポイント作成

```bash
railway new entry greeting
```

以下のファイルが生成されます：

- `src/greeting.py` - エントリーポイント（dag_runner使用）
- `src/nodes/greeting/start.py` - 開始ノード
- `transition_graphs/greeting_*.yml` - 遷移グラフ定義

### 2.2 遷移グラフを確認

`transition_graphs/greeting_*.yml` を開いて確認してください:

```yaml
version: "1.0"
entrypoint: greeting
description: "greeting ワークフロー"

nodes:
  start:
    module: nodes.greeting.start
    function: start
    description: "開始ノード"

exits:
  success:
    code: 0
    description: "正常終了"
  error:
    code: 1
    description: "異常終了"

start: start

transitions:
  start:
    success::done: exit::success
    failure::error: exit::error
```

### 2.3 コード生成

```bash
railway sync transition --entry greeting
```

`_railway/generated/greeting_transitions.py` が生成されます。

### 2.4 実行

```bash
railway run greeting
```

---

## Step 3: ノードの実装 - Outcome を使う（3分）

DAGワークフローのノードは `Contract` と `Outcome` を返す純粋関数です。

### 3.1 ノードの基本形

`src/nodes/greeting/start.py` を確認:

```python
from railway import Contract, node
from railway.core.dag import Outcome


class GreetingContext(Contract):
    \"\"\"ワークフローコンテキスト\"\"\"
    message: str = ""


@node
def start() -> tuple[GreetingContext, Outcome]:
    \"\"\"開始ノード\"\"\"
    ctx = GreetingContext(message="Hello, Railway!")
    return ctx, Outcome.success("done")
```

### 3.2 Outcome クラス

`Outcome` は状態を簡潔に表現します:

```python
# 成功状態
Outcome.success("done")      # → success::done
Outcome.success("validated") # → success::validated

# 失敗状態
Outcome.failure("error")     # → failure::error
Outcome.failure("timeout")   # → failure::timeout
```

**ポイント:**
- ノードは状態を返すだけ
- 次のノードへの遷移はYAMLで定義
- 純粋関数として実装

---

## Step 4: 条件分岐ワークフロー（5分）

時間帯に応じて挨拶を変えるワークフローを作成します。

### 4.1 遷移グラフを編集

`transition_graphs/greeting_*.yml` を以下のように編集:

```yaml
version: "1.0"
entrypoint: greeting
description: "挨拶ワークフロー"

nodes:
  check_time:
    module: nodes.greeting.check_time
    function: check_time
    description: "時間帯を判定"
  greet_morning:
    module: nodes.greeting.greet
    function: greet_morning
    description: "朝の挨拶"
  greet_afternoon:
    module: nodes.greeting.greet
    function: greet_afternoon
    description: "午後の挨拶"
  greet_evening:
    module: nodes.greeting.greet
    function: greet_evening
    description: "夜の挨拶"

exits:
  success:
    code: 0
    description: "正常終了"

start: check_time

transitions:
  check_time:
    success::morning: greet_morning
    success::afternoon: greet_afternoon
    success::evening: greet_evening
  greet_morning:
    success::done: exit::success
  greet_afternoon:
    success::done: exit::success
  greet_evening:
    success::done: exit::success
```

### 4.2 ノードを実装

`src/nodes/greeting/check_time.py`:

```python
from datetime import datetime
from railway import Contract, node
from railway.core.dag import Outcome


class TimeContext(Contract):
    \"\"\"時間帯コンテキスト\"\"\"
    period: str


@node
def check_time() -> tuple[TimeContext, Outcome]:
    \"\"\"時間帯を判定して状態を返す\"\"\"
    hour = datetime.now().hour

    if 5 <= hour < 12:
        return TimeContext(period="morning"), Outcome.success("morning")
    elif 12 <= hour < 18:
        return TimeContext(period="afternoon"), Outcome.success("afternoon")
    else:
        return TimeContext(period="evening"), Outcome.success("evening")
```

`src/nodes/greeting/greet.py`:

```python
from railway import node
from railway.core.dag import Outcome
from nodes.greeting.check_time import TimeContext


@node
def greet_morning(ctx: TimeContext) -> tuple[TimeContext, Outcome]:
    \"\"\"朝の挨拶\"\"\"
    print("おはようございます！")
    return ctx, Outcome.success("done")


@node
def greet_afternoon(ctx: TimeContext) -> tuple[TimeContext, Outcome]:
    \"\"\"午後の挨拶\"\"\"
    print("こんにちは！")
    return ctx, Outcome.success("done")


@node
def greet_evening(ctx: TimeContext) -> tuple[TimeContext, Outcome]:
    \"\"\"夜の挨拶\"\"\"
    print("こんばんは！")
    return ctx, Outcome.success("done")
```

### 4.3 コード生成と実行

```bash
# コード生成
railway sync transition --entry greeting

# 実行
railway run greeting
```

出力例:

```
[check_time] 開始...
[check_time] ✓ 完了 (success::morning)
[greet_morning] 開始...
おはようございます！
[greet_morning] ✓ 完了 (success::done)
ワークフロー完了: 2 ステップ
```

---

## Step 5: railway new node でノードを素早く追加（3分）

既存のワークフローに新しいノードを追加する方法を学びます。
ここで体験するのは「**3つのファイルを1コマンドで生成し、即座にTDDを開始できる**」という恩恵です。

### 5.1 1コマンドで3ファイル生成

```bash
railway new node log_result
```

**たった1コマンドで以下が生成されます:**

| ファイル | 役割 | 恩恵 |
|----------|------|------|
| `src/nodes/log_result.py` | ノード本体 | 動作するサンプル付き |
| `src/contracts/log_result_context.py` | Contract | IDE補完が効く |
| `tests/nodes/test_log_result.py` | テスト | すぐにTDD開始可能 |

### 5.2 TDDワークフローを体験

**Step 1: テストを編集（期待する動作を定義）**

`tests/nodes/test_log_result.py` を開き、具体的なテストを追加。

**Step 2: テスト実行（失敗を確認 = Red）**

```bash
uv run pytest tests/nodes/test_log_result.py -v
```

失敗することを確認。これがTDDの「Red」フェーズです。

**Step 3: 実装（テストを通す = Green）**

`src/nodes/log_result.py` と `src/contracts/log_result_context.py` を実装。

**Step 4: テスト再実行（成功を確認）**

成功！これがTDDの「Green」フェーズです。

### 5.3 linear モード（参考）

線形パイプライン向けのノードを作成する場合:

```bash
railway new node format_output --mode linear
```

---

## Step 6: エラーハンドリング（3分）

### 6.1 失敗パスの追加

遷移グラフに失敗パスを追加:

```yaml
transitions:
  check_time:
    success::morning: greet_morning
    success::afternoon: greet_afternoon
    success::evening: greet_evening
    failure::error: exit::error
```

### 6.2 ノードでのエラーハンドリング

```python
@node
def check_time() -> tuple[TimeContext, Outcome]:
    \"\"\"時間帯を判定\"\"\"
    try:
        hour = datetime.now().hour
        # ... 処理
        return ctx, Outcome.success("morning")
    except Exception:
        return TimeContext(period="unknown"), Outcome.failure("error")
```

---

## Step 7: ステップコールバック（3分）

### 7.1 StepRecorder で実行履歴を記録

```python
from railway.core.dag import dag_runner, StepRecorder

recorder = StepRecorder()

result = dag_runner(
    start=check_time,
    transitions=TRANSITIONS,
    on_step=recorder,
)

# 実行履歴を確認
for step in recorder.get_history():
    print(f"[{{step.node_name}}] -> {{step.state}}")
```

### 7.2 AuditLogger で監査ログ

```python
from railway.core.dag import AuditLogger

audit = AuditLogger(workflow_id="incident-123")

result = dag_runner(
    start=check_time,
    transitions=TRANSITIONS,
    on_step=audit,
)
```

---

## Step 8: バージョン管理（3分）

### 8.1 現状を確認

```bash
cat .railway/project.yaml
```

### 8.2 更新

```bash
# プレビュー
railway update --dry-run

# 実行
railway update
```

### 8.3 バックアップから復元

```bash
railway backup list
railway backup restore
```

---

## Step 9: 既存プロジェクトのアップグレード（3分）

v0.10.x 以前のプロジェクトを最新形式にアップグレードする方法を学びます。

### 9.1 変更内容をプレビュー

```bash
railway update --dry-run
```

**出力例:**
```
マイグレーション: 0.10.0 → 0.12.0

ファイル追加:
  - transition_graphs/.gitkeep
  - _railway/generated/.gitkeep

コードガイダンス:
  src/nodes/process.py:5
    現在: def process(data: dict) -> dict:
    推奨: def process(ctx: ProcessContext) -> tuple[ProcessContext, Outcome]:
```

### 9.2 アップグレード実行

```bash
railway update
```

### 9.3 コードを修正

ガイダンスに従って、旧形式のノードを新形式に変更します。

**Before:**
```python
@node
def process(data: dict) -> dict:
    return data
```

**After:**
```python
@node
def process(ctx: ProcessContext) -> tuple[ProcessContext, Outcome]:
    return ctx, Outcome.success("done")
```

**恩恵:**
- Outcome で次の遷移先を制御できる
- Contract で型安全にデータを扱える
- YAML で遷移ロジックを可視化できる

---

## ポイントまとめ

1. **ノードは状態を返すだけ** - 遷移先はYAMLで定義
2. **Outcome を使う** - `Outcome.success("done")` で簡潔に
3. **Contract を使う** - 型安全なコンテキスト
4. **YAMLを変更したら再sync** - `railway sync transition --entry <name>`

---

## 次のステップ

### 学んだこと

- dag_runner による条件分岐ワークフロー
- Outcome クラスによる状態返却
- 遷移グラフ（YAML）の定義
- コード生成
- ステップコールバック
- バージョン管理とアップグレード

### さらに学ぶ

- [TUTORIAL_linear.md](TUTORIAL_linear.md) - 線形パイプライン詳細チュートリアル
- [docs/adr/002_execution_models.md](docs/adr/002_execution_models.md) - 実行モデルの詳細
- `railway docs` で詳細を確認

---

## チャレンジ

1. 週末と平日で挨拶を変える分岐を追加
2. 複数の終了コード（Exit.GREEN, Exit.YELLOW）を使い分け
3. CompositeCallback を使って複数のコールバックを組み合わせ

---

## トラブルシューティング

### mypy で型チェックが効かない場合

```bash
uv sync --reinstall-package railway-framework
rm -rf .mypy_cache/
uv run mypy src/
```

### テストが失敗する場合

```bash
rm -rf .pytest_cache/ __pycache__/
uv sync
```
'''
    _write_file(project_path / "TUTORIAL.md", content)


def _create_tutorial_linear_md(project_path: Path, project_name: str) -> None:
    """Create TUTORIAL_linear.md file for typed_pipeline."""
    content = f'''# {project_name} チュートリアル - 線形パイプライン

このチュートリアルでは、`typed_pipeline` を使用した線形パイプラインの開発を学びます。

条件分岐が必要な場合は [TUTORIAL.md](TUTORIAL.md) の dag_runner を使用してください。

## 線形パイプラインとは

処理が必ず順番に実行されるパイプラインです：

```
A → B → C → D
```

条件分岐はありません。ETL、データ変換に適しています。

## 所要時間

約10分

## 前提条件

- Python 3.10以上
- uv インストール済み
- VSCode推奨（IDE補完を体験するため）

---

## Step 1: プロジェクト初期化（1分）

```bash
railway init my_pipeline
cd my_pipeline
uv sync
```

---

## Step 2: エントリーポイント作成（1分）

```bash
railway new entry my_pipeline --mode linear
```

以下のファイルが生成されます：

- `src/my_pipeline.py` - エントリーポイント（typed_pipeline 使用）
- `src/nodes/my_pipeline/step1.py` - ステップ1
- `src/nodes/my_pipeline/step2.py` - ステップ2

---

## Step 3: 生成されるコード

### エントリーポイント

`src/my_pipeline.py`:

```python
from railway import entry_point, typed_pipeline
from nodes.my_pipeline.step1 import step1
from nodes.my_pipeline.step2 import step2


@entry_point
def main():
    """パイプラインを実行"""
    result = typed_pipeline(
        step1,
        step2,
    )
    print(f"完了: {{result}}")
    return result
```

### ノード

`src/nodes/my_pipeline/step1.py`:

```python
from railway import Contract, node


class Step1Output(Contract):
    """ステップ1の出力"""
    data: str


@node(output=Step1Output)
def step1() -> Step1Output:
    """ステップ1の処理"""
    return Step1Output(data="processed")
```

---

## Step 4: 実行（1分）

```bash
railway run my_pipeline
```

---

## Step 5: Contract - データの「契約」を定義（3分）

### 5.1 Contractを作成

```bash
railway new contract UsersFetchResult
```

### 5.2 ファイルを編集

`src/contracts/users_fetch_result.py`:

```python
from railway import Contract


class User(Contract):
    id: int
    name: str


class UsersFetchResult(Contract):
    users: list[User]
    total: int
```

---

## Step 6: typed_pipeline - 依存関係の自動解決（3分）

### 6.1 複数のノードを組み合わせ

```python
from railway import entry_point, typed_pipeline

from nodes.fetch_users import fetch_users
from nodes.generate_report import generate_report


@entry_point
def main():
    result = typed_pipeline(
        fetch_users,      # UsersFetchResult を出力
        generate_report,  # UsersFetchResult を入力 → ReportResult を出力
    )

    print(result.content)  # IDE補完が効く！
    return result
```

### 6.2 依存関係の自動解決

```
fetch_users ──────────────> generate_report
  output: UsersFetchResult    input: UsersFetchResult
                              output: ReportResult
```

フレームワークが**型を見て自動的に依存関係を解決**します。

---

## typed_pipeline の特徴

- **Contract 自動解決**: 次のノードに必要な Contract を自動で渡す
- **シンプル**: 状態管理不要
- **線形処理専用**: 条件分岐不可
- **IDE補完**: Contract の型情報でIDE補完が効く

---

## dag_runner との比較

| 項目 | typed_pipeline | dag_runner |
|------|----------------|------------|
| 分岐 | 不可 | 可能 |
| 遷移定義 | コード内（順番で定義） | YAML |
| 戻り値 | Contract | tuple[Contract, Outcome] |
| 用途 | ETL、データ変換 | 運用自動化 |
| 複雑度 | シンプル | やや複雑 |
| 柔軟性 | 低い | 高い |

---

## いつ dag_runner に移行すべきか

以下の場合は dag_runner への移行を検討してください：

- **条件分岐が必要**: 処理結果に応じて次のステップが変わる
- **エラーパスが複数**: エラー種別に応じて異なる対応が必要
- **複雑なワークフロー**: 複数の終了パスがある

```
# typed_pipeline: 線形フロー
A → B → C → D

# dag_runner: 条件分岐フロー
    ┌→ B → D
A → │
    └→ C → E
```

---

## 次のステップ

- [TUTORIAL.md](TUTORIAL.md) - DAGワークフローチュートリアル
- [docs/adr/002_execution_models.md](docs/adr/002_execution_models.md) - 実行モデルの詳細
'''
    _write_file(project_path / "TUTORIAL_linear.md", content)


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

# Railway generated code
_railway/generated/*.py
!_railway/generated/.gitkeep
'''
    _write_file(project_path / ".gitignore", content)


def _get_sample_transition_yaml() -> str:
    """Get sample transition graph YAML content."""
    return '''version: "1.0"
entrypoint: hello
description: "サンプルワークフロー"

nodes:
  greet:
    module: nodes.greet
    function: greet
    description: "挨拶を出力"

exits:
  success:
    code: 0
    description: "正常終了"
  error:
    code: 1
    description: "異常終了"

start: greet

transitions:
  greet:
    success::done: exit::success
    failure::error: exit::error

options:
  max_iterations: 10
'''


def _create_dag_directories(project_path: Path) -> None:
    """Create DAG workflow directories and files."""
    # Create transition_graphs directory
    graphs_dir = project_path / "transition_graphs"
    graphs_dir.mkdir(parents=True, exist_ok=True)
    (graphs_dir / ".gitkeep").write_text(
        "# Transition graph YAML files\n"
        "# File naming: {entrypoint}_{YYYYMMDDHHmmss}.yml\n"
    )

    # Create _railway/generated directory
    generated_dir = project_path / "_railway" / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    (generated_dir / ".gitkeep").write_text(
        "# Auto-generated transition code\n"
        "# Do not edit manually - use `railway sync transition`\n"
    )

    # Create sample YAML with timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    sample_yaml = _get_sample_transition_yaml()
    (graphs_dir / f"hello_{timestamp}.yml").write_text(sample_yaml)


def _create_py_typed(project_path: Path) -> None:
    """Create py.typed marker for PEP 561 compliance.

    This enables type checking tools (mypy, pyright) to recognize
    the user's project as a typed package.
    """
    content = "# PEP 561 marker - this package supports type checking\n"
    _write_file(project_path / "src" / "py.typed", content)


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
    _create_tutorial_linear_md(project_path, project_name)
    _create_gitignore(project_path)
    _create_init_files(project_path)
    _create_conftest_py(project_path)
    _create_py_typed(project_path)

    # Create hello entry point
    # Default: simple hello.py for immediate verification
    # --with-examples: complex pipeline example
    if with_examples:
        _create_example_entry(project_path)
    else:
        _create_simple_hello_entry(project_path)

    # Create DAG workflow directories
    _create_dag_directories(project_path)

    # Create .railway/project.yaml with version metadata
    metadata = create_metadata(project_name, __version__)
    save_metadata(project_path, metadata)


def _show_success_output(project_name: str) -> None:
    """Display success message and next steps."""
    typer.echo(f"\nCreated project: {project_name}\n")
    typer.echo("Project structure:")
    typer.echo(f"  {project_name}/")
    typer.echo("  ├── .railway/")
    typer.echo("  │   └── project.yaml")
    typer.echo("  ├── _railway/")
    typer.echo("  │   └── generated/")
    typer.echo("  ├── transition_graphs/")
    typer.echo("  │   └── hello_*.yml")
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
