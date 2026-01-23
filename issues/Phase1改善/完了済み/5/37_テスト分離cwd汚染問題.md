# Issue #37: テスト分離問題 - cwdの汚染による120テスト失敗

## 概要

全テストを一括実行すると120件のCLIテストが`FileNotFoundError`で失敗するが、個別実行では成功する。

## 症状

```bash
# 全テスト実行 → 120件失敗
uv run pytest tests/
# 結果: 120 failed, 298 passed

# 個別実行 → 全て成功
uv run pytest tests/unit/cli/test_tutorial_error_handling.py -v
# 結果: 8 passed
```

エラーメッセージ:
```
FileNotFoundError: [Errno 2] No such file or directory
```

## 根本原因

`tests/integration/test_full_workflow.py`の以下のテストが、`tempfile.TemporaryDirectory()`内で`os.chdir()`を使用し、cwdを復元せずに終了している:

1. `TestProjectCreationWorkflow::test_init_new_node_run` (line 20, 27)
2. `TestGeneratedProjectStructure::test_generated_project_has_all_files` (line 293)
3. `TestGeneratedProjectStructure::test_generated_node_has_test` (line 319, 323)

**問題のパターン:**
```python
with tempfile.TemporaryDirectory() as tmpdir:
    os.chdir(tmpdir)  # ← 一時ディレクトリに移動
    # ... テスト実行 ...
# ← ここでtmpdirが削除されるが、
#     cwdはまだ削除されたディレクトリを指している
```

結果として、後続のテストが`os.getcwd()`を呼ぶと、存在しないディレクトリを参照して`FileNotFoundError`が発生する。

## 影響範囲

- `tests/unit/cli/` 配下の全テスト（120件）
- `os.getcwd()`を使用する全てのテスト

## 解決方針

### 方針1: conftest.pyに自動cwd保護fixtureを追加（推奨）

```python
# tests/conftest.py
import os
import pytest

@pytest.fixture(autouse=True)
def preserve_cwd():
    """各テストの前後でcwdを保護する。"""
    original_cwd = os.getcwd()
    try:
        yield
    finally:
        try:
            os.chdir(original_cwd)
        except FileNotFoundError:
            # テストがcwdを削除した場合はプロジェクトルートに戻る
            os.chdir(Path(__file__).parent.parent)
```

**利点:**
- 全テストに自動適用
- 個別テストの修正不要
- 将来のテストも自動保護
- TDDのベストプラクティス（テストは独立・分離）

### 方針2: 問題のあるテストを個別修正

```python
# 修正前
with tempfile.TemporaryDirectory() as tmpdir:
    os.chdir(tmpdir)
    # ...

# 修正後
with tempfile.TemporaryDirectory() as tmpdir:
    original_cwd = os.getcwd()
    try:
        os.chdir(tmpdir)
        # ...
    finally:
        os.chdir(original_cwd)
```

**欠点:**
- 全ての問題箇所を見つけて修正する必要がある
- 将来のテストで同じ問題が再発する可能性

## 推奨対応

**方針1（conftest.py fixture）** を採用する。

理由:
1. 問題の根本的な防止策
2. 将来のテストも自動保護
3. テストの独立性・分離性の保証
4. 修正漏れのリスク排除

## 実装手順

1. `tests/conftest.py`に`preserve_cwd` fixtureを追加
2. 全テスト実行で418件全てがpassすることを確認
3. 既存の問題テストはそのままでも動作するが、コードレビュー時に個別修正を推奨

## テストコマンド

```bash
# 修正前: 120 failed
uv run pytest tests/

# 修正後: 418 passed
uv run pytest tests/
```

## 関連Issue

なし（新規発見）

## 優先度

**高** - 全テスト実行が不可能な状態

## 見積もり

- 修正: 10分
- テスト確認: 5分
