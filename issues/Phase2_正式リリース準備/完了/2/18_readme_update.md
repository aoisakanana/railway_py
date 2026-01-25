# Issue #18: README.md 更新（dag_runner 型デフォルト）

**Phase:** 2d
**優先度:** 中
**依存関係:** #10, #15, #16, #17
**見積もり:** 0.5日

---

## 概要

README.md を dag_runner 型（条件分岐対応）をデフォルトとして全面改訂する。
旧来の typed_pipeline 型の説明は `readme_linear.md` に移動する。

---

## 変更内容

### 1. README.md 全面改訂

- **デフォルト**: dag_runner 型のクイックスタート
- **typed_pipeline**: 「線形パイプライン」セクションで簡潔に説明
- **使い分け**: ADR-002 を参照

### 2. readme_linear.md 新規作成

- 旧来の typed_pipeline 型の詳細ドキュメント
- 線形パイプライン専用の学習リソース

---

## 成果物

### README.md（改訂後）

```markdown
# Railway Framework

Python用の型安全なワークフローフレームワーク。
条件分岐を含む複雑なワークフローをYAMLで宣言的に定義できます。

## 特徴

- **DAGワークフロー**: 条件分岐を含むワークフローをYAMLで定義
- **型安全**: Contract + State Enum による静的型チェック
- **純粋関数**: ノードは副作用のない純粋関数
- **コード生成**: YAMLから遷移コードを自動生成

## クイックスタート

### 1. プロジェクト初期化

```bash
pip install railway-framework
railway init my_project
cd my_project
```

### 2. エントリーポイント作成

```bash
railway new entry my_workflow
```

これにより以下が生成されます：
- `src/my_workflow.py` - エントリーポイント
- `src/nodes/my_workflow/start.py` - 開始ノード
- `transition_graphs/my_workflow_*.yml` - 遷移グラフ

### 3. 遷移グラフを編集

`transition_graphs/my_workflow_*.yml`:

```yaml
version: "1.0"
entrypoint: my_workflow

nodes:
  start:
    module: nodes.my_workflow.start
    function: start
    description: "開始ノード"
  process:
    module: nodes.my_workflow.process
    function: process
    description: "処理ノード"

exits:
  success:
    code: 0
  error:
    code: 1

start: start

transitions:
  start:
    success::done: process
    failure::error: exit::error
  process:
    success::complete: exit::success
    failure::error: exit::error
```

### 4. コード生成

```bash
railway sync transition --entry my_workflow
```

### 5. 実行

```bash
railway run my_workflow
```

## ノードの実装

ノードは `Contract` と `Outcome` を返す純粋関数です：

```python
from railway import Contract, node
from railway.core.dag.outcome import Outcome


class MyContext(Contract):
    value: str


@node
def process(ctx: MyContext) -> tuple[MyContext, Outcome]:
    if ctx.value:
        return ctx, Outcome.success("done")
    else:
        return ctx, Outcome.failure("empty")
```

## 実行モデル

Railway Framework は2つの実行モデルを提供します：

| モデル | 用途 | コマンド |
|--------|------|----------|
| **dag_runner** | 条件分岐ワークフロー（推奨） | `railway new entry <name>` |
| typed_pipeline | 線形パイプライン | `railway new entry <name> --mode linear` |

詳細は [ADR-002](docs/adr/002_execution_models.md) を参照。

線形パイプラインの詳細は [readme_linear.md](readme_linear.md) を参照。

## CLI コマンド

```bash
# プロジェクト初期化
railway init <project_name>

# エントリーポイント作成
railway new entry <name>                 # dag_runner 型（デフォルト）
railway new entry <name> --mode linear   # typed_pipeline 型

# 遷移コード生成
railway sync transition --entry <name>
railway sync transition --all

# 実行
railway run <entrypoint>

# バージョン確認
railway --version
```

## ドキュメント

- [TUTORIAL.md](TUTORIAL.md) - ハンズオンチュートリアル
- [readme_linear.md](readme_linear.md) - 線形パイプライン詳細
- [docs/adr/](docs/adr/) - 設計決定記録
```

### readme_linear.md（新規作成）

```markdown
# Railway Framework - 線形パイプライン

このドキュメントは `typed_pipeline` を使用した線形パイプラインの詳細ガイドです。

条件分岐が必要な場合は [README.md](README.md) の dag_runner を使用してください。

## 線形パイプラインとは

処理が必ず順番に実行されるパイプラインです：

```
A → B → C → D
```

条件分岐はありません。ETL、データ変換に適しています。

## クイックスタート

### 1. エントリーポイント作成

```bash
railway new entry my_pipeline --mode linear
```

### 2. 生成されるファイル

```
src/
├── my_pipeline.py           # typed_pipeline 使用
└── nodes/
    └── my_pipeline/
        ├── step1.py         # Contract 返却
        └── step2.py
```

### 3. エントリーポイント

```python
from railway import entry_point, typed_pipeline
from nodes.my_pipeline.step1 import step1
from nodes.my_pipeline.step2 import step2


@entry_point
def main():
    result = typed_pipeline([
        step1,
        step2,
    ])
    return result
```

### 4. ノード実装

```python
from railway import Contract, node


class Step1Output(Contract):
    data: str


@node
def step1() -> Step1Output:
    return Step1Output(data="processed")
```

## typed_pipeline の特徴

- **Contract 自動解決**: 次のノードに必要な Contract を自動で渡す
- **シンプル**: 状態管理不要
- **線形処理専用**: 条件分岐不可

## dag_runner との比較

| 項目 | typed_pipeline | dag_runner |
|------|----------------|------------|
| 分岐 | 不可 | 可能 |
| 遷移定義 | コード内 | YAML |
| 戻り値 | Contract | tuple[Contract, Outcome] |
| 用途 | ETL | 運用自動化 |

条件分岐が必要になったら `dag_runner` への移行を検討してください。
```

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/docs/test_readme.py
"""Tests for README documentation."""
import pytest
from pathlib import Path


class TestReadmeDefault:
    """Test README uses dag_runner as default."""

    @pytest.fixture
    def readme_content(self):
        readme_path = Path(__file__).parent.parent.parent.parent / "readme.md"
        return readme_path.read_text()

    def test_dag_runner_is_primary(self, readme_content):
        """dag_runner should appear before typed_pipeline."""
        dag_pos = readme_content.find("dag_runner")
        pipeline_pos = readme_content.find("typed_pipeline")
        assert dag_pos < pipeline_pos, "dag_runner should appear first"

    def test_quick_start_uses_dag(self, readme_content):
        """Quick start should use dag_runner."""
        # Find the quick start section
        qs_start = readme_content.find("クイックスタート")
        qs_end = readme_content.find("##", qs_start + 1)
        quick_start = readme_content[qs_start:qs_end]

        assert "railway new entry" in quick_start
        assert "--mode linear" not in quick_start

    def test_mentions_outcome(self, readme_content):
        """Should mention Outcome class."""
        assert "Outcome" in readme_content

    def test_references_linear_readme(self, readme_content):
        """Should reference readme_linear.md."""
        assert "readme_linear" in readme_content.lower()


class TestReadmeLinearExists:
    """Test readme_linear.md exists."""

    def test_file_exists(self):
        readme_linear = Path(__file__).parent.parent.parent.parent / "readme_linear.md"
        assert readme_linear.exists()

    def test_mentions_typed_pipeline(self):
        readme_linear = Path(__file__).parent.parent.parent.parent / "readme_linear.md"
        content = readme_linear.read_text()
        assert "typed_pipeline" in content
        assert "--mode linear" in content
```

### Step 2: Green

README.md と readme_linear.md を上記の内容で作成/更新する。

---

## 完了条件

- [ ] README.md が dag_runner 型をデフォルトとして説明
- [ ] クイックスタートが dag_runner 型
- [ ] Outcome クラスの説明を含む
- [ ] readme_linear.md への参照
- [ ] readme_linear.md 新規作成
- [ ] typed_pipeline の詳細は readme_linear.md に移動
- [ ] テストが通過

---

## 次のIssue

- #19: TUTORIAL.md 更新
