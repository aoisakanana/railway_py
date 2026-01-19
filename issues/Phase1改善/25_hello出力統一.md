# Issue #25: hello entry の出力がチュートリアルと不一致

## 優先度: 低

## 概要

`railway init` で生成される `hello.py` の出力と、TUTORIAL.md の期待出力が一致していない。

## 現状確認（2026-01-19）

### TUTORIAL.md（Step 1）
```markdown
**期待される出力:**
```
Hello, World!
```
```

### hello.py（実際の出力）
```python
@entry_point
def hello():
    """最小限のHello World"""
    print("Hello from Railway!")  # ← 実際の出力
    return {"message": "Hello from Railway!"}
```

**→ 不一致が確認された ✅**

## 影響

- 初心者がチュートリアルを見ながら実行すると、出力が異なり戸惑う
- 「正しく動作しているのか？」という不安を与える
- ドキュメントの信頼性が低下

## 解決策

### Option A: hello.py を「Hello, World!」に統一（推奨）

```python
@entry_point
def hello():
    """最小限のHello World"""
    print("Hello, World!")
    return {"message": "Hello, World!"}
```

**メリット:**
- 業界標準の "Hello, World!" に準拠
- チュートリアルとの一貫性
- 初心者に馴染みやすい

### Option B: TUTORIAL.md を「Hello from Railway!」に統一

```markdown
**期待される出力:**
```
Hello from Railway!
```
```

**メリット:**
- Railway フレームワークであることを明示
- 既存の hello.py を変更不要

## 推奨: Option A

理由:
1. "Hello, World!" はプログラミング入門の普遍的な慣習
2. 初心者がまず確認したいのは「正しく動くこと」
3. Railway 特有の機能は後のステップで示すべき

## 実装

### railway/cli/init.py の変更

```python
def _create_simple_hello_entry(project_path: Path) -> None:
    """Create minimal hello.py for immediate verification."""
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
'''
    _write_file(project_path / "src" / "hello.py", content)
```

## テスト

```python
import os
import tempfile
from pathlib import Path

from typer.testing import CliRunner


def test_hello_output_matches_tutorial():
    """hello.py output should match TUTORIAL expectation."""
    from railway.cli.main import app

    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            runner.invoke(app, ["init", "test_project"])

            hello_py = Path(tmpdir) / "test_project" / "src" / "hello.py"
            content = hello_py.read_text()

            # Should contain "Hello, World!" (standard greeting)
            assert 'print("Hello, World!")' in content
            assert '"Hello, World!"' in content  # return value も確認
        finally:
            os.chdir(original_cwd)
```

## 影響を受ける既存テスト

`tests/unit/cli/test_init_hello.py` の以下のテストを更新:
- `test_hello_py_contains_hello_message` - 「Hello」「Railway」の確認を「Hello, World!」に変更

## 受け入れ条件

- [ ] hello.py の出力が「Hello, World!」に変更
- [ ] TUTORIAL.md の期待出力と一致
- [ ] 関連テストが更新される

## 関連

- Issue #18: チュートリアル整合性修正（完了）
- レビュー4（v0.8.1）: セットアップ体験 8/10
