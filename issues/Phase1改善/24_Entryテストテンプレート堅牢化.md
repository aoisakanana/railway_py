# Issue #24: Entry テストテンプレートが書き換え後に壊れる

## 優先度: 中

## 概要

`railway new entry` で生成されるテストテンプレートが `app` をインポートするが、ユーザーがエントリポイントを書き換えると `app` が存在しなくなりテストが壊れる。

## 現状確認（2026-01-19）

### 現在のテストテンプレート（railway/cli/new.py:443）
```python
from {name} import app  # ← 問題箇所
```

### 現在のエントリテンプレート
```python
@entry_point
def main(...):
    ...

# Export Typer app for testing with CliRunner
app = main._typer_app  # ← これが存在する前提
```

## 問題シナリオ

1. ユーザーが `railway new entry user_report` を実行
2. `src/user_report.py` と `tests/test_user_report.py` が生成される
3. ユーザーがチュートリアルを参考にエントリポイントを書き換える
4. `app = main._typer_app` の行を削除してしまう（または存在を知らない）
5. テストが `ImportError: cannot import name 'app'` で失敗

## 原因

Issue #20 で `app` エクスポートを追加したが、テストテンプレートが `app` に依存している。
ユーザーがエントリポイントをカスタマイズする際、`app` エクスポートを維持する必要性が明確でない。

## 解決策

### Option A: `main._typer_app` を直接参照（推奨）

テストテンプレートを変更し、`app` ではなく `main._typer_app` を直接参照:

```python
from typer.testing import CliRunner
from {name} import main  # app ではなく main をインポート

runner = CliRunner()

def test_{name}_runs_successfully():
    result = runner.invoke(main._typer_app, [])  # 直接参照
    assert result.exit_code == 0
```

**メリット:**
- エントリポイントの書き換えに影響されない
- `app` エクスポートの有無に依存しない
- `@entry_point` デコレータの内部構造を学べる

### Option B: エントリテンプレートから `app` エクスポートを削除

生成されるエントリポイントから `app = main._typer_app` を削除し、
テストテンプレートも `main._typer_app` を使用するように統一。

**メリット:**
- 生成コードがシンプルになる
- ユーザーが不要な行を気にする必要がない

## 推奨: Option A + B の組み合わせ

1. テストテンプレートを `main._typer_app` 参照に変更
2. エントリテンプレートから `app` エクスポートを削除（オプション）

## 実装

### railway/cli/new.py の変更

```python
def _get_entry_test_template(name: str) -> str:
    """Get test template for an entry point."""
    class_name = "".join(word.title() for word in name.split("_"))
    return f'''"""Tests for {name} entry point."""

import pytest
from typer.testing import CliRunner

from {name} import main

runner = CliRunner()


class Test{class_name}:
    """Test suite for {name} entry point.

    Uses CliRunner with main._typer_app to isolate from pytest's sys.argv.
    """

    def test_{name}_runs_successfully(self):
        """Entry point should complete without error."""
        result = runner.invoke(main._typer_app, [])
        assert result.exit_code == 0, f"Failed with: {{result.stdout}}"

    def test_{name}_with_help(self):
        """Entry point should show help."""
        result = runner.invoke(main._typer_app, ["--help"])
        assert result.exit_code == 0
'''
```

## テスト

```python
def test_entry_test_template_uses_main_typer_app():
    """Entry test template should use main._typer_app, not app."""
    from railway.cli.new import _get_entry_test_template

    template = _get_entry_test_template("user_report")

    # Should import main, not app
    assert "from user_report import main" in template
    assert "from user_report import app" not in template

    # Should use main._typer_app
    assert "main._typer_app" in template
```

## 影響を受ける既存テスト

以下のテストファイルを更新する必要がある可能性:

1. `tests/unit/cli/test_entry_test_template.py` - `app` インポートのテスト
2. 生成されたプロジェクトのテスト

## 受け入れ条件

- [ ] テストテンプレートが `main._typer_app` を使用
- [ ] `from {name} import app` が `from {name} import main` に変更
- [ ] ユーザーがエントリポイントを書き換えてもテストが壊れない
- [ ] 既存の `test_entry_test_template.py` を更新
- [ ] テストで動作を検証

## 関連

- Issue #20: エントリポイントテスト修正（完了）
- レビュー4（v0.8.1）: コード生成 7/10
