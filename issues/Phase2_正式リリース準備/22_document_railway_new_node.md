# Issue #22: railway new node コマンドのドキュメント追加

**Phase:** 2e
**優先度:** 中
**依存関係:** #21
**見積もり:** 0.25日

---

## 概要

`railway new node` コマンドの使い方が README.md と TUTORIAL.md に十分に記載されていない。

### 現状

| ドキュメント | 状態 |
|-------------|------|
| README.md | CLIリファレンスに3行のみ（詳細説明なし） |
| TUTORIAL.md | **記載なし** - ノードを手動で作成する方法のみ |

ユーザーは `railway new node` コマンドの存在を知らない可能性があり、TDDワークフローでの活用方法も示されていない。

---

## 解決策

1. **README.md**: 「ノードの作成」セクションを追加し、`railway new node` の使い方を詳しく説明
2. **TUTORIAL.md**: Step で `railway new node` を使ったノード作成方法を追加
3. **モード選択の説明**: dag/linear モードの違いと選び方を説明

---

## 成果物

### README.md への追加内容

```markdown
### ノードの作成

単独のノードを作成するには `railway new node` を使用します:

```bash
# dag 形式（デフォルト）: 条件分岐ワークフロー向け
railway new node check_status
# → src/nodes/check_status.py
# → src/contracts/check_status_context.py
# → tests/nodes/test_check_status.py

# linear 形式: 線形パイプライン向け
railway new node transform --mode linear
# → src/nodes/transform.py
# → src/contracts/transform_input.py
# → src/contracts/transform_output.py
# → tests/nodes/test_transform.py
```

**dag 形式（デフォルト）** - `tuple[Contract, Outcome]` を返す:

```python
from railway import node
from railway.core.dag.outcome import Outcome

from contracts.check_status_context import CheckStatusContext


@node
def check_status(ctx: CheckStatusContext) -> tuple[CheckStatusContext, Outcome]:
    """ステータスをチェックする。"""
    if ctx.is_valid:
        return ctx, Outcome.success("valid")
    return ctx, Outcome.failure("invalid")
```

**linear 形式** - `Contract` を返す:

```python
from typing import Optional

from railway import node

from contracts.transform_input import TransformInput
from contracts.transform_output import TransformOutput


@node
def transform(input_data: Optional[TransformInput] = None) -> TransformOutput:
    """データを変換する。"""
    return TransformOutput(result="transformed")
```

#### いつ `railway new node` を使うか？

| 場面 | 推奨方法 |
|------|----------|
| 既存エントリーポイントに新ノードを追加 | `railway new node` |
| スタンドアロンの処理を作成 | `railway new node` |
| 新規エントリーポイント作成時 | `railway new entry`（ノードも同時生成） |
```

### TUTORIAL.md への追加内容（Step 5 として追加）

```markdown
## Step 5: railway new node でノードを追加（3分）

既存のワークフローに新しいノードを追加する方法を学びます。

### 5.1 ノードの作成

```bash
railway new node log_result
```

以下のファイルが生成されます:
- `src/nodes/log_result.py` - ノード本体
- `src/contracts/log_result_context.py` - Context Contract
- `tests/nodes/test_log_result.py` - テストファイル

### 5.2 生成されたファイルを確認

`src/nodes/log_result.py`:

```python
from railway import node
from railway.core.dag.outcome import Outcome

from contracts.log_result_context import LogResultContext


@node
def log_result(ctx: LogResultContext) -> tuple[LogResultContext, Outcome]:
    """log_result の処理を実行する。"""
    # イミュータブル更新の例:
    # updated_ctx = ctx.model_copy(update={"processed": True})
    # return updated_ctx, Outcome.success("done")
    return ctx, Outcome.success("done")
```

### 5.3 TDDワークフロー

`railway new node` は TDD を促進するためにテストファイルも生成します:

1. `tests/nodes/test_log_result.py` を編集してテストを定義
2. テスト実行（失敗を確認）: `uv run pytest tests/nodes/test_log_result.py -v`
3. `src/nodes/log_result.py` を実装
4. テスト再実行（成功を確認）

### 5.4 ワークフローに組み込む

遷移グラフ（YAML）に新ノードを追加:

```yaml
nodes:
  # ... 既存ノード ...
  log_result:
    module: nodes.log_result
    function: log_result
    description: "結果をログに記録"

transitions:
  # ... 既存遷移 ...
  some_node:
    success::done: log_result  # 新ノードへの遷移を追加
  log_result:
    success::done: exit::success
```

コード再生成:

```bash
railway sync transition --entry greeting
```

---

### linear モードでのノード作成

線形パイプライン向けのノードを作成する場合:

```bash
railway new node format_output --mode linear
```

生成されるコード:

```python
from typing import Optional

from railway import node

from contracts.format_output_input import FormatOutputInput
from contracts.format_output_output import FormatOutputOutput


@node
def format_output(input_data: Optional[FormatOutputInput] = None) -> FormatOutputOutput:
    """format_output の処理を実行する。"""
    return FormatOutputOutput()
```

**dag モードとの違い:**
- Outcome を使用しない
- Input/Output の2つの Contract が生成される
- typed_pipeline での使用に適している
```

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/docs/test_readme_new_node_section.py
"""Tests for railway new node documentation in README."""

import pytest


class TestReadmeNewNodeSection:
    """Test that README has railway new node documentation."""

    @pytest.fixture
    def readme_content(self):
        """Read README.md content."""
        from pathlib import Path
        # tests/unit/docs/ -> tests/unit/ -> tests/ -> project root
        readme_path = Path(__file__).parents[3] / "readme.md"
        return readme_path.read_text()

    def test_readme_has_node_creation_section(self, readme_content):
        """README should have a node creation section."""
        assert "ノードの作成" in readme_content or "Node Creation" in readme_content

    def test_readme_shows_railway_new_node_dag(self, readme_content):
        """README should show railway new node command for dag mode."""
        assert "railway new node" in readme_content
        # Should show dag mode is default
        assert "dag" in readme_content.lower()

    def test_readme_shows_railway_new_node_linear(self, readme_content):
        """README should show --mode linear option."""
        assert "--mode linear" in readme_content

    def test_readme_shows_generated_files(self, readme_content):
        """README should explain what files are generated."""
        # Should mention contract generation
        assert "_context.py" in readme_content or "context" in readme_content.lower()

    def test_readme_shows_dag_code_example(self, readme_content):
        """README should show dag node code example."""
        assert "tuple[" in readme_content
        assert "Outcome" in readme_content

    def test_readme_shows_when_to_use(self, readme_content):
        """README should explain when to use railway new node."""
        # Should have guidance on when to use
        has_guidance = (
            "いつ" in readme_content
            or "When" in readme_content
            or "場面" in readme_content
        )
        assert has_guidance, "Should explain when to use railway new node"

    def test_readme_shows_linear_code_example(self, readme_content):
        """README should show linear node code example."""
        # Linear mode should show Optional input and Contract output
        assert "Optional[" in readme_content
        # Should NOT have Outcome in linear example context
        assert "-> TransformOutput:" in readme_content or "Output:" in readme_content

    def test_readme_shows_typing_import(self, readme_content):
        """README should show typing import for Optional."""
        assert "from typing import Optional" in readme_content
```

```python
# tests/unit/docs/test_tutorial_new_node_section.py
"""Tests for railway new node documentation in TUTORIAL."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestTutorialNewNodeSection:
    """Test that generated TUTORIAL has railway new node section."""

    @pytest.fixture
    def tutorial_content(self):
        """Generate and read TUTORIAL.md content."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])
                tutorial_path = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                return tutorial_path.read_text()
            finally:
                os.chdir(original_cwd)

    def test_tutorial_mentions_railway_new_node(self, tutorial_content):
        """TUTORIAL should mention railway new node command."""
        assert "railway new node" in tutorial_content

    def test_tutorial_shows_node_generation(self, tutorial_content):
        """TUTORIAL should show what files are generated."""
        # Should explain file generation
        has_generation = (
            "生成" in tutorial_content
            or "created" in tutorial_content.lower()
            or "generates" in tutorial_content.lower()
        )
        assert has_generation

    def test_tutorial_shows_tdd_workflow(self, tutorial_content):
        """TUTORIAL should show TDD workflow with generated tests."""
        # Should mention testing the generated node
        assert "test" in tutorial_content.lower()
        assert "pytest" in tutorial_content.lower()

    def test_tutorial_shows_mode_option(self, tutorial_content):
        """TUTORIAL should explain --mode option."""
        assert "--mode" in tutorial_content or "linear" in tutorial_content

    def test_tutorial_shows_yaml_integration(self, tutorial_content):
        """TUTORIAL should show how to add node to YAML."""
        # Should explain adding to transition graph
        has_yaml = (
            "yaml" in tutorial_content.lower()
            or "transition" in tutorial_content.lower()
        )
        assert has_yaml
```

### Step 2: Green（実装）

**README.md の更新箇所:**

「CLIリファレンス」セクションの後に「ノードの作成」セクションを追加。
（上記「README.md への追加内容」セクションの内容をそのまま追加）

**railway/cli/init.py の `_create_tutorial_md` 関数更新:**

```python
def _create_tutorial_md(project_name: str) -> str:
    """Generate TUTORIAL.md content.

    Pure function: project_name -> tutorial content string
    """
    # ... 既存の Step 1-4 ...

    # Step 5 を追加（既存の Step 4 の後）
    step5_content = '''
## Step 5: railway new node でノードを追加（3分）

既存のワークフローに新しいノードを追加する方法を学びます。

### 5.1 ノードの作成

```bash
railway new node log_result
```

以下のファイルが生成されます:
- `src/nodes/log_result.py` - ノード本体
- `src/contracts/log_result_context.py` - Context Contract
- `tests/nodes/test_log_result.py` - テストファイル

### 5.2 TDDワークフロー

`railway new node` は TDD を促進するためにテストファイルも生成します:

1. `tests/nodes/test_log_result.py` を編集してテストを定義
2. テスト実行（失敗を確認）: `uv run pytest tests/nodes/test_log_result.py -v`
3. `src/nodes/log_result.py` を実装
4. テスト再実行（成功を確認）

### 5.3 ワークフローに組み込む

遷移グラフ（YAML）に新ノードを追加し、`railway sync transition` でコード再生成。

### 5.4 linear モード

線形パイプライン向けのノードを作成する場合:

```bash
railway new node format_output --mode linear
```

**dag モードとの違い:**
- Outcome を使用しない
- Input/Output の2つの Contract が生成される
- typed_pipeline での使用に適している
'''

    return base_content + step5_content
```

**変更の要点:**
1. 既存の `_create_tutorial_md` 関数内で、Step 4 の後に Step 5 を追加
2. 純粋関数の原則を維持（引数 → 文字列を返す）
3. Step 番号が後続の Step（Step 6 等）と衝突しないよう確認

### Step 3: Refactor

- README と TUTORIAL で説明が一貫していることを確認
- コード例が Issue #21 のテンプレートと一致していることを確認

---

## 完了条件

- [ ] README.md に「ノードの作成」セクションが追加されている
- [ ] README.md に dag/linear モードの説明がある
- [ ] README.md に「いつ使うか」のガイダンスがある
- [ ] TUTORIAL.md に `railway new node` を使う Step が追加されている
- [ ] TUTORIAL.md に TDD ワークフローの説明がある
- [ ] TUTORIAL.md に YAML への組み込み方法がある
- [ ] 全テストが通過

---

## 関連ファイル

- `readme.md` - プロジェクト README
- `railway/cli/init.py` - TUTORIAL.md 生成（`_create_tutorial_md` 関数）
- `tests/unit/docs/test_readme_new_node_section.py` - 新規テスト
- `tests/unit/docs/test_tutorial_new_node_section.py` - 新規テスト

---

## 依存関係

- **Issue #21**: `railway new node` のテンプレート更新が先に完了している必要がある
  - dag/linear モードの実装
  - Contract 自動生成
  - テストテンプレート生成

---

## 備考

- Issue #21 で実装されるテンプレートと、ドキュメントのコード例が一致するようにする
- README はリファレンス的な説明、TUTORIAL は段階的な学習体験として構成する
- `railway new entry` との使い分けを明確にする（entry はノードも同時生成、node は単独作成）
