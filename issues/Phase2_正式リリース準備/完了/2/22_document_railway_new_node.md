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

## このドキュメント追加がユーザーにもたらす恩恵

### 1. 発見可能性の向上
- コマンドの存在を知ることで、手動作成の手間を省ける
- 「こんな便利なコマンドがあったのか」という驚きから喜びへ

### 2. 正しいパターンの習得
- 推奨されるdag形式とlinear形式の使い分けを理解できる
- 最初から正しい設計パターンで実装を始められる

### 3. TDDワークフローの促進
- テストファイルが自動生成されることを知り、TDDを実践しやすくなる
- 「テストを書かなきゃ」から「テストがあるから書こう」へ

### 4. 学習曲線の緩和
- TUTORIALで実際に手を動かして学べる
- シンプルな体験から実践的な活用へ段階的に習得

---

## 解決策

1. **README.md**: 「ノードの作成」セクションを追加し、`railway new node` の使い方を詳しく説明
2. **TUTORIAL.md**: Step で `railway new node` を使ったノード作成方法を追加
3. **モード選択の説明**: dag/linear モードの違いと選び方を説明

### ドキュメント設計方針

| ドキュメント | 目的 | スタイル |
|-------------|------|----------|
| README.md | リファレンス | 網羅的、詳細 |
| TUTORIAL.md | 学習体験 | シンプル、段階的 |

---

## 成果物

### README.md への追加内容

追加位置: 「CLI Commands」セクション内「Node（処理単位）」の後、または「ノードの実装」セクションの前

```markdown
### ノードの作成

`railway new node` コマンドは、**型安全なノードをすぐに開発開始できる状態で生成**します。

**なぜこのコマンドを使うのか？**

| 手動作成 | `railway new node` |
|----------|-------------------|
| ノード、Contract、テストを個別に作成 | **3ファイル同時生成** |
| import文を自分で書く | **正しいimport済み** |
| テスト構造を考える | **TDDテンプレート付き** |
| Outcomeの使い方を調べる | **動作するサンプル付き** |

```bash
# dag 形式（デフォルト）: 条件分岐ワークフロー向け
railway new node check_status
# → src/nodes/check_status.py        ← ノード本体（動作するサンプル付き）
# → src/contracts/check_status_context.py  ← Contract（型安全）
# → tests/nodes/test_check_status.py       ← TDDテンプレート

# linear 形式: 線形パイプライン向け
railway new node transform --mode linear
# → Input/Output の2つのContractが生成される
```

**dag 形式（デフォルト）** - 条件分岐が可能:

```python
from railway import node
from railway.core.dag.outcome import Outcome

from contracts.check_status_context import CheckStatusContext


@node
def check_status(ctx: CheckStatusContext) -> tuple[CheckStatusContext, Outcome]:
    """ステータスをチェックする。"""
    if ctx.is_valid:
        return ctx, Outcome.success("valid")   # → valid 遷移
    return ctx, Outcome.failure("invalid")     # → invalid 遷移
```

**linear 形式** - シンプルなデータ変換向け:

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

#### どちらを使う？

| 用途 | 形式 | 理由 |
|------|------|------|
| 運用自動化、条件分岐あり | **dag（デフォルト）** | Outcomeで遷移を制御 |
| ETL、データ変換 | linear | シンプルな入出力 |
| 迷ったら | **dag** | より汎用的 |

#### 使い分けガイド

| 場面 | 推奨方法 |
|------|----------|
| 既存ワークフローにノード追加 | `railway new node` |
| 単体の処理を作成 | `railway new node` |
| 新規ワークフロー作成 | `railway new entry`（ノードも同時生成） |
```

### TUTORIAL.md への追加内容

**注意**: TUTORIAL.mdは `railway/cli/init.py` の `_create_tutorial_md` 関数で生成されるため、そちらを修正する

**現在のTUTORIAL.md Step構成:**
```
Step 1: Hello World（2分）
Step 2: Contract - データの「契約」を定義する（3分）
Step 3: TDD - テストを先に書く（3分）
Step 4: Node実装（3分）
Step 5: IDE補完を体験する（2分）
Step 6: typed_pipeline - 依存関係の自動解決（3分）
Step 7: 安全なリファクタリング（2分）
Step 8: エラーハンドリング（実践）（5分）
Step 9: バージョン管理 - 安全なアップグレード体験（5分）
```

**追加方針**: Step 4（Node実装）の後、Step 5（IDE補完）の前に新しいStepを挿入し、以降のStep番号を+1する

**変更後のStep構成:**
```
Step 1-4: (変更なし)
Step 5: railway new node でノードを素早く追加（3分）← 新規追加
Step 6: IDE補完を体験する（2分）← 旧Step 5
Step 7: typed_pipeline - 依存関係の自動解決（3分）← 旧Step 6
...以降+1
Step 10: バージョン管理 - 安全なアップグレード体験（5分）← 旧Step 9
```

```markdown
## Step 5: railway new node でノードを素早く追加（3分）

既存のワークフローに新しいノードを追加する方法を学びます。
ここで体験するのは「**3つのファイルを1コマンドで生成し、即座にTDDを開始できる**」という恩恵です。

### 5.1 1コマンドで3ファイル生成

```bash
railway new node log_result
```

🎉 **たった1コマンドで以下が生成されます:**

| ファイル | 役割 | 恩恵 |
|----------|------|------|
| `src/nodes/log_result.py` | ノード本体 | 動作するサンプル付き |
| `src/contracts/log_result_context.py` | Contract | IDE補完が効く |
| `tests/nodes/test_log_result.py` | テスト | すぐにTDD開始可能 |

### 5.2 生成されたコードを確認

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

**ポイント:**
- `Outcome` を返すことで、次にどのノードに遷移するかを制御できる
- `model_copy()` でデータを安全に更新（元のデータは変更されない）

### 5.3 TDDワークフローを体験

生成されたテストファイルを使って、TDD（テスト駆動開発）を体験しましょう。

**Step 1: テストを編集（期待する動作を定義）**

`tests/nodes/test_log_result.py` を開き、具体的なテストを追加:

```python
def test_log_result_marks_as_logged(self):
    """処理後にログ済みフラグが立つこと"""
    ctx = LogResultContext(message="test", logged=False)
    result_ctx, outcome = log_result(ctx)

    assert outcome.is_success
    assert result_ctx.logged == True  # まだ実装していないのでFail
```

**Step 2: テスト実行（失敗を確認 = Red）**

```bash
uv run pytest tests/nodes/test_log_result.py -v
```

🔴 失敗することを確認。これがTDDの「Red」フェーズです。

**Step 3: 実装（テストを通す = Green）**

`src/nodes/log_result.py` と `src/contracts/log_result_context.py` を実装。

**Step 4: テスト再実行（成功を確認）**

```bash
uv run pytest tests/nodes/test_log_result.py -v
```

🟢 成功！これがTDDの「Green」フェーズです。

### 5.4 ワークフローに組み込む

遷移グラフ（YAML）に新ノードを追加:

```yaml
nodes:
  log_result:
    module: nodes.log_result
    function: log_result
    description: "結果をログに記録"

transitions:
  some_node:
    success::done: log_result
  log_result:
    success::done: exit::success
```

コード再生成:

```bash
railway sync transition --entry <your_entry>
```

---

### 💡 Tip: linear モード

線形パイプライン（ETL、データ変換）向けのノードを作成する場合:

```bash
railway new node format_output --mode linear
```

**違い:**
- Outcome を使用しない（シンプル）
- Input/Output の2つの Contract が生成される
```

---

## TDD実装手順

### Step 1: Red（テストを書く）

ドキュメントが「利点を伝えている」ことを検証するテスト。

```python
# tests/unit/docs/test_readme_new_node_section.py
"""Tests for railway new node documentation in README.

このテストスイートは以下を保証する：
1. コマンドの存在がドキュメント化されている
2. 利点（恩恵）が明示されている
3. 使い分けガイダンスがある
4. コード例が正確
"""

import pytest


class TestReadmeNewNodeSection:
    """Test that README has railway new node documentation."""

    @pytest.fixture
    def readme_content(self):
        """Read README.md content."""
        from pathlib import Path
        readme_path = Path(__file__).parents[3] / "readme.md"
        return readme_path.read_text()

    def test_readme_has_node_creation_section(self, readme_content):
        """README should have a node creation section.

        重要性: ユーザーがコマンドを発見できる。
        """
        assert "ノードの作成" in readme_content or "Node Creation" in readme_content

    def test_readme_shows_benefit_comparison(self, readme_content):
        """README should show benefit comparison table.

        重要性: 手動作成との違いが明確になる。
        """
        # 表形式で比較されていること
        has_comparison = (
            "手動" in readme_content
            or "3ファイル" in readme_content
            or "同時生成" in readme_content
        )
        assert has_comparison, "Should show benefits compared to manual creation"

    def test_readme_shows_railway_new_node_dag(self, readme_content):
        """README should show railway new node command for dag mode."""
        assert "railway new node" in readme_content
        assert "dag" in readme_content.lower()

    def test_readme_shows_railway_new_node_linear(self, readme_content):
        """README should show --mode linear option."""
        assert "--mode linear" in readme_content

    def test_readme_shows_generated_files(self, readme_content):
        """README should explain what files are generated.

        重要性: 何が生成されるか事前に知れる。
        """
        assert "_context.py" in readme_content or "context" in readme_content.lower()

    def test_readme_shows_dag_code_example(self, readme_content):
        """README should show dag node code example."""
        assert "tuple[" in readme_content
        assert "Outcome" in readme_content

    def test_readme_shows_mode_selection_guide(self, readme_content):
        """README should explain when to use which mode.

        重要性: ユーザーが適切なモードを選べる。
        """
        has_guidance = (
            "どちら" in readme_content
            or "用途" in readme_content
            or "場面" in readme_content
        )
        assert has_guidance, "Should have mode selection guidance"

    def test_readme_shows_linear_code_example(self, readme_content):
        """README should show linear node code example."""
        assert "Optional[" in readme_content
        assert "Output:" in readme_content or "Output]" in readme_content

    def test_readme_shows_typing_import(self, readme_content):
        """README should show typing import for Optional."""
        assert "from typing import Optional" in readme_content
```

```python
# tests/unit/docs/test_tutorial_new_node_section.py
"""Tests for railway new node documentation in TUTORIAL.

このテストスイートは以下を保証する：
1. railway new node がTUTORIALで紹介されている
2. シンプルながらも実践的な体験ができる
3. TDDワークフローを体験できる
"""

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
        """TUTORIAL should mention railway new node command.

        重要性: コマンドの発見可能性。
        """
        assert "railway new node" in tutorial_content

    def test_tutorial_shows_3_files_benefit(self, tutorial_content):
        """TUTORIAL should emphasize 3 files generated benefit.

        重要性: 恩恵を明示することでコマンドの価値が伝わる。
        """
        has_benefit = (
            "3" in tutorial_content
            or "ファイル" in tutorial_content
            or "files" in tutorial_content.lower()
        )
        assert has_benefit

    def test_tutorial_shows_tdd_red_green(self, tutorial_content):
        """TUTORIAL should show TDD Red-Green cycle.

        重要性: TDDを体験させることで、テスト文化を促進。
        """
        has_tdd_cycle = (
            ("Red" in tutorial_content or "失敗" in tutorial_content)
            and ("Green" in tutorial_content or "成功" in tutorial_content)
        )
        assert has_tdd_cycle, "Should show TDD Red-Green cycle"

    def test_tutorial_shows_pytest_command(self, tutorial_content):
        """TUTORIAL should show how to run tests."""
        assert "pytest" in tutorial_content.lower()
        assert "uv run" in tutorial_content

    def test_tutorial_shows_mode_option(self, tutorial_content):
        """TUTORIAL should mention --mode option.

        重要性: linear モードの存在を知らせる。
        """
        assert "--mode" in tutorial_content or "linear" in tutorial_content

    def test_tutorial_shows_yaml_integration(self, tutorial_content):
        """TUTORIAL should show how to add node to YAML.

        重要性: 生成したノードを実際に使う方法を示す。
        """
        has_yaml = (
            "yaml" in tutorial_content.lower()
            or "transition" in tutorial_content.lower()
        )
        assert has_yaml
```

### Step 2: Green（実装）

**README.md の更新箇所:**

追加位置: 「ノードの実装」セクションの直後

（上記「README.md への追加内容」セクションの内容をそのまま追加）

**railway/cli/init.py の `_create_tutorial_md` 関数更新:**

実装方針:
1. Step 4 の後に新しい Step 5 を挿入
2. 既存の Step 5 以降は番号を +1 してリネーム
3. 純粋関数の原則を維持

```python
# railway/cli/init.py

def _create_tutorial_md(project_name: str) -> str:
    """Generate TUTORIAL.md content.

    純粋関数: project_name -> tutorial content string
    副作用なし
    """
    # 既存の Step 1-4 は変更なし

    # === 新規追加: Step 5 ===
    step5_new_node = '''
## Step 5: railway new node でノードを素早く追加（3分）

既存のワークフローに新しいノードを追加する方法を学びます。
ここで体験するのは「**3つのファイルを1コマンドで生成し、即座にTDDを開始できる**」という恩恵です。

### 5.1 1コマンドで3ファイル生成

```bash
railway new node log_result
```

🎉 **たった1コマンドで以下が生成されます:**

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

🔴 失敗することを確認。これがTDDの「Red」フェーズです。

**Step 3: 実装（テストを通す = Green）**

`src/nodes/log_result.py` と `src/contracts/log_result_context.py` を実装。

**Step 4: テスト再実行（成功を確認）**

🟢 成功！これがTDDの「Green」フェーズです。

### 5.3 linear モード（参考）

線形パイプライン向けのノードを作成する場合:

```bash
railway new node format_output --mode linear
```

'''

    # 既存の Step 5 → Step 6 にリネーム
    # 既存の Step 6 → Step 7 にリネーム
    # ... 以降同様

    return (
        header
        + step1 + step2 + step3 + step4
        + step5_new_node  # 新規追加
        + step6_ide_completion  # 旧 Step 5
        + step7_typed_pipeline  # 旧 Step 6
        + step8_refactoring  # 旧 Step 7
        + step9_error_handling  # 旧 Step 8
        + step10_version_management  # 旧 Step 9
        + faq + next_steps + troubleshooting
    )
```

**変更の要点:**
1. 新しい Step 5 を Step 4 の後に挿入
2. 既存の Step 5 以降の番号を +1
3. TDD Red-Green サイクルを体験できる内容
4. 純粋関数の原則を維持

### Step 3: Refactor

**一貫性チェック:**
- [ ] README と TUTORIAL で説明が一貫している
- [ ] コード例が Issue #21 のテンプレートと一致している
- [ ] dag/linear の使い分け説明が両方で同じ

**品質チェック:**
- [ ] README: 利点が明確に伝わる表現になっている
- [ ] TUTORIAL: シンプルな体験で価値が伝わる
- [ ] 専門用語には説明が付いている

**動作確認:**
```bash
# README の内容確認
cat readme.md | grep -A 30 "ノードの作成"

# TUTORIAL 生成テスト
cd /tmp && railway init test_doc && cat test_doc/TUTORIAL.md | grep -A 50 "railway new node"
```

---

## 完了条件

### README.md
- [ ] 「ノードの作成」セクションが追加されている
- [ ] コマンドを使う**理由（恩恵）**が明確に記載されている
- [ ] dag/linear モードの**使い分け**が表形式で説明されている
- [ ] コード例が生成されるテンプレートと一致している

### TUTORIAL.md
- [ ] `railway new node` を使う Step が追加されている
- [ ] **1コマンドで3ファイル生成**の恩恵が明示されている
- [ ] **実際にTDDサイクル（Red → Green）を体験**できる手順がある
- [ ] YAML への組み込み方法がある

### 品質要件
- [ ] 全テストが通過
- [ ] README と TUTORIAL で説明が一貫している
- [ ] Issue #21 のテンプレートと、ドキュメントのコード例が一致している

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

### コンテンツ設計方針
- Issue #21 で実装されるテンプレートと、ドキュメントのコード例が一致するようにする
- README はリファレンス的な説明、TUTORIAL は段階的な学習体験として構成する
- `railway new entry` との使い分けを明確にする（entry はノードも同時生成、node は単独作成）

### 実装者向けチェックリスト

**README.md 更新時:**
- [ ] 追加位置が正しいか確認（「ノードの実装」セクションの直後）
- [ ] コード例が Issue #21 のテンプレートと一致しているか
- [ ] 表のフォーマットが崩れていないか

**TUTORIAL.md 更新時:**
- [ ] Step 番号が連続しているか（5, 6, 7, 8, 9, 10）
- [ ] 旧 Step への参照が更新されているか
- [ ] 新 Step が実際に動作するか手動確認

**テスト時:**
- [ ] `railway init` で新しい TUTORIAL.md が生成されることを確認
- [ ] 生成された TUTORIAL.md に新しい Step が含まれることを確認
