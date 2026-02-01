# Issue #67: モジュールパス自動解決の改善

## 優先度

**Critical**

## 問題

YAML で `module/function` を省略すると、フレームワークはノード名から自動解決を試みるが、ネストされたディレクトリ構造に対応していない。

### 現状

```yaml
# transition_graphs/greeting_*.yml
nodes:
  check_time:
    description: "時刻チェック"
    # module/function 省略
```

```
実際のファイル構造:
  src/nodes/greeting/check_time.py

フレームワークの解決:
  nodes.check_time  # 存在しない

期待される解決:
  nodes.greeting.check_time
```

### エラー

```
ModuleNotFoundError: No module named 'nodes.check_time'
```

## 解決策

YAML 生成時に `module` を明示的に記載する。ファイルシステムの走査は複雑になるため、生成時に確定させる方式を採用。

### 設計判断

| 選択肢 | メリット | デメリット |
|--------|----------|------------|
| A) 実行時にファイルシステム走査 | 柔軟 | パフォーマンス低下、複雑 |
| B) **生成時に module を確定** | シンプル、高速 | YAML が冗長 |
| C) entrypoint からパス推論 | 中間的 | 規約依存 |

**採用: B) 生成時に module を確定**

理由:
- 純粋関数で実装可能（副作用なし）
- 実行時のオーバーヘッドなし
- YAML を見れば依存関係が明確

### 新しい YAML テンプレート

```yaml
version: "1.0"
entrypoint: greeting

nodes:
  start:
    module: nodes.greeting.start  # 明示的に記載
    function: start
    description: "開始ノード"

  exit:
    success:
      done:
        module: nodes.exit.success.done
        function: done
        description: "正常終了"
```

## 実装タスク

### 1. テスト作成（Red）

```python
# tests/unit/cli/test_yaml_module_path.py

class TestYamlModulePath:
    """YAML のモジュールパス生成テスト。"""

    def test_yaml_includes_explicit_module_path(self, tmp_path, monkeypatch):
        """生成される YAML に明示的な module パスが含まれる。"""
        from railway.cli.main import app

        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        runner.invoke(app, ["new", "entry", "greeting"])

        yaml_files = list((tmp_path / "transition_graphs").glob("greeting_*.yml"))
        content = yaml_files[0].read_text()

        assert "module: nodes.greeting.start" in content

    def test_exit_node_has_full_module_path(self, tmp_path, monkeypatch):
        """終端ノードにもフルパスが含まれる。"""
        ...

    def test_nested_entry_has_correct_path(self, tmp_path, monkeypatch):
        """ネストされたエントリでも正しいパス。"""
        runner.invoke(app, ["new", "entry", "workflows/daily"])
        # module: nodes.workflows.daily.start
        ...
```

### 2. 純粋関数の実装

```python
# railway/cli/new.py

def _resolve_module_path(entry_name: str, node_name: str) -> str:
    """ノードのモジュールパスを解決（純粋関数）。

    Args:
        entry_name: エントリポイント名（例: "greeting", "workflows/daily"）
        node_name: ノード名（例: "start", "check_time"）

    Returns:
        モジュールパス（例: "nodes.greeting.start"）

    Examples:
        >>> _resolve_module_path("greeting", "start")
        "nodes.greeting.start"

        >>> _resolve_module_path("workflows/daily", "check")
        "nodes.workflows.daily.check"
    """
    # "/" を "." に変換
    entry_path = entry_name.replace("/", ".")
    return f"nodes.{entry_path}.{node_name}"


def _resolve_exit_module_path(exit_path: str) -> str:
    """終端ノードのモジュールパスを解決（純粋関数）。

    Args:
        exit_path: 終端ノードパス（例: "success.done", "failure.timeout"）

    Returns:
        モジュールパス（例: "nodes.exit.success.done"）

    Examples:
        >>> _resolve_exit_module_path("success.done")
        "nodes.exit.success.done"
    """
    return f"nodes.exit.{exit_path}"
```

### 3. YAML テンプレート修正

```python
def _get_dag_yaml_template(name: str) -> str:
    """DAG モードの YAML テンプレートを生成（純粋関数）。"""
    start_module = _resolve_module_path(name, "start")
    exit_done_module = _resolve_exit_module_path("success.done")
    exit_error_module = _resolve_exit_module_path("failure.error")

    return f'''version: "1.0"
entrypoint: {name}
description: "{name} ワークフロー"

nodes:
  start:
    module: {start_module}
    function: start
    description: "開始ノード"

  exit:
    success:
      done:
        module: {exit_done_module}
        function: done
        description: "正常終了"
    failure:
      error:
        module: {exit_error_module}
        function: error
        description: "エラー終了"

start: start

transitions:
  start:
    success::done: exit.success.done
    failure::error: exit.failure.error
'''
```

## 影響範囲

| ファイル | 変更内容 |
|----------|----------|
| `railway/cli/new.py` | `_resolve_module_path()` 追加、テンプレート修正 |
| `tests/unit/cli/test_yaml_module_path.py` | 新規テスト |

## 終端ノードの配置

終端ノードは**グローバル共有**として設計されている:

```
src/
  nodes/
    greeting/          # エントリポイント固有
      start.py
    exit/              # 全エントリポイントで共有
      success/
        done.py
      failure/
        error.py
```

**理由:**
- 終端ノード（Slack 通知、ログ出力など）は複数のワークフローで再利用可能
- エントリポイントごとに終端ノードを作成するのは冗長

**生成タイミング:**
- `railway new entry` は終端ノードのスケルトンも生成
- 既存の終端ノードは上書きしない

## 完了条件

- [ ] 生成される YAML に明示的な module パスが含まれる
- [ ] 終端ノードのスケルトンファイルが生成される
- [ ] 既存の終端ノードは上書きされない
- [ ] `railway sync transition` でエラーなく動作
- [ ] テストが全てパス
