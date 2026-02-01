# Issue #66: 開始ノードの引数整合性問題

## 優先度

**Critical**

## 問題

`railway new entry` で生成される開始ノードは引数を取らない関数として生成されるが、`run()` 関数は `START_NODE(initial_context)` を呼び出す。

### 現状

```python
# 生成されるノード (src/nodes/greeting/start.py)
@node
def start() -> tuple[GreetingContext, Outcome]:
    """開始ノード"""
    return GreetingContext(message="Hello"), Outcome.success("done")

# 生成される run() 関数 (_railway/generated/greeting_transitions.py)
def run(initial_context: Any, ...) -> ExitContract:
    def start_wrapper():
        return START_NODE(initial_context)  # ← 引数を渡している
    ...
```

### エラー

```
TypeError: start() takes 0 positional arguments but 1 was given
```

## 解決策

開始ノードは `initial_context` を受け取る形式で生成する。

### 新しいノードテンプレート

```python
@node
def start(ctx: GreetingContext | None = None) -> tuple[GreetingContext, Outcome]:
    """開始ノード

    Args:
        ctx: 初期コンテキスト（省略時はデフォルト値を使用）
    """
    if ctx is None:
        ctx = GreetingContext(message="Hello")
    return ctx, Outcome.success("done")
```

### 設計判断

| 選択肢 | メリット | デメリット |
|--------|----------|------------|
| A) ノードが引数を受け取る | `run()` と整合性あり | 既存コードとの違い |
| B) `run()` が引数を渡さない | 既存ノードと互換 | 外部からコンテキスト注入不可 |

**採用: A) ノードが引数を受け取る**

理由:
- 外部からコンテキストを注入できる（テスト容易性）
- DAG ワークフローの本来の設計意図に沿う
- `None` デフォルトで後方互換も維持

## 実装タスク

### 1. テスト作成（Red）

```python
# tests/unit/cli/test_start_node_template.py

from typer.testing import CliRunner
from railway.cli.main import app

runner = CliRunner()


def _init_project(path: Path) -> None:
    """テスト用プロジェクト初期化ヘルパー。"""
    runner.invoke(app, ["init", path.name], catch_exceptions=False)


class TestStartNodeTemplate:
    """開始ノードテンプレートのテスト。"""

    def test_start_node_accepts_optional_context(self, tmp_path, monkeypatch):
        """開始ノードは optional な context を受け取る。"""
        project_path = tmp_path / "myproject"
        project_path.mkdir()
        monkeypatch.chdir(tmp_path)
        _init_project(project_path)
        monkeypatch.chdir(project_path)

        runner.invoke(app, ["new", "entry", "greeting"])

        content = (project_path / "src" / "nodes" / "greeting" / "start.py").read_text()
        assert "ctx:" in content or "context:" in content
        assert "None" in content  # デフォルト値

    def test_run_can_pass_initial_context(self, tmp_path, monkeypatch):
        """run() は初期コンテキストを渡せる。"""
        project_path = tmp_path / "myproject"
        project_path.mkdir()
        monkeypatch.chdir(tmp_path)
        _init_project(project_path)
        monkeypatch.chdir(project_path)

        runner.invoke(app, ["new", "entry", "greeting"])

        # 生成された run() 関数をインポートして実行
        import sys
        sys.path.insert(0, str(project_path / "src"))
        sys.path.insert(0, str(project_path / "_railway" / "generated"))

        from greeting_transitions import run
        from nodes.greeting.start import GreetingContext

        # カスタムコンテキストを渡して実行
        result = run(GreetingContext(message="Custom"))
        assert result.is_success

    def test_start_node_works_without_argument(self, tmp_path, monkeypatch):
        """開始ノードは引数なしでも動作する（None がデフォルト）。"""
        project_path = tmp_path / "myproject"
        project_path.mkdir()
        monkeypatch.chdir(tmp_path)
        _init_project(project_path)
        monkeypatch.chdir(project_path)

        runner.invoke(app, ["new", "entry", "greeting"])

        import sys
        sys.path.insert(0, str(project_path / "src"))
        sys.path.insert(0, str(project_path / "_railway" / "generated"))

        from greeting_transitions import run

        # None を渡して実行（デフォルト値を使用）
        result = run(None)
        assert result.is_success
```

### 2. 実装（Green）

#### 2.1 ノードテンプレート修正

```python
# railway/cli/new.py

def _get_dag_node_template(name: str) -> str:
    """開始ノードのテンプレートを生成（純粋関数）。"""
    class_name = _to_pascal_case(name)
    return f'''"""開始ノード for {name}."""

from railway import Contract, node
from railway.core.dag import Outcome


class {class_name}Context(Contract):
    """ワークフローコンテキスト"""
    message: str = ""


@node
def start(ctx: {class_name}Context | None = None) -> tuple[{class_name}Context, Outcome]:
    """開始ノード

    Args:
        ctx: 初期コンテキスト（省略時はデフォルト値を使用）
    """
    if ctx is None:
        ctx = {class_name}Context(message="Hello")
    return ctx, Outcome.success("done")
'''
```

### 3. リファクタリング

- テンプレートの共通化
- Context 型のインポート整理

## 影響範囲

| ファイル | 変更内容 |
|----------|----------|
| `railway/cli/new.py` | `_get_dag_node_template()` 修正 |
| `tests/unit/cli/test_start_node_template.py` | 新規テスト |

## 完了条件

- [ ] テストが全てパス
- [ ] 生成されたノードが `run()` から正常に呼び出せる
- [ ] 引数なしでも動作する
