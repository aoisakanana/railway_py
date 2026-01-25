# Issue #19: TUTORIAL.md 更新（dag_runner 型デフォルト）

**Phase:** 2d
**優先度:** 中
**依存関係:** #10, #12, #15, #16, #17
**見積もり:** 1日

---

## 概要

TUTORIAL.md を dag_runner 型（条件分岐対応）をデフォルトとして全面改訂する。
旧来の typed_pipeline 型のチュートリアルは `TUTORIAL_linear.md` に移動する。

---

## 変更内容

### 1. TUTORIAL.md 全面改訂

- **デフォルト**: dag_runner 型のハンズオンチュートリアル
- **Outcome クラス**: 状態返却の簡潔な記法を使用
- **typed_pipeline**: 「線形パイプライン」セクションで簡潔に説明
- **参照**: TUTORIAL_linear.md への誘導

### 2. TUTORIAL_linear.md 新規作成

- 旧来の typed_pipeline 型の詳細チュートリアル
- 線形パイプライン専用の学習リソース

---

## 成果物

### TUTORIAL.md（改訂後）

```markdown
# Railway Framework チュートリアル

このチュートリアルでは、Railway Frameworkを使ったワークフロー開発を学びます。

## 前提条件

- Python 3.11以上
- Railway Frameworkがインストール済み

```bash
pip install railway-framework
```

## 1. プロジェクト初期化

```bash
railway init my_project
cd my_project
```

生成される構造：

```
my_project/
├── src/
│   ├── __init__.py
│   └── nodes/
├── transition_graphs/
├── _railway/
│   └── generated/
├── config/
└── pyproject.toml
```

## 2. はじめてのワークフロー

### 2.1 エントリーポイント作成

```bash
railway new entry greeting
```

以下のファイルが生成されます：

- `src/greeting.py` - エントリーポイント
- `src/nodes/greeting/start.py` - 開始ノード
- `transition_graphs/greeting_*.yml` - 遷移グラフ定義

### 2.2 遷移グラフを確認

`transition_graphs/greeting_*.yml`:

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

options:
  max_iterations: 100
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

## 3. ノードの実装

### 3.1 ノードの基本形

ノードは `Contract` と `Outcome` を返す純粋関数です：

```python
from railway import Contract, node
from railway.core.dag.outcome import Outcome


class GreetingContext(Contract):
    """ワークフローコンテキスト"""
    message: str = ""


@node
def start() -> tuple[GreetingContext, Outcome]:
    """開始ノード"""
    ctx = GreetingContext(message="Hello, Railway!")
    return ctx, Outcome.success("done")
```

### 3.2 Outcome クラス

`Outcome` は状態を簡潔に表現するクラスです：

```python
# 成功状態
Outcome.success("done")      # → success::done
Outcome.success("validated") # → success::validated

# 失敗状態
Outcome.failure("error")     # → failure::error
Outcome.failure("timeout")   # → failure::timeout
```

### 3.3 型安全なコンテキスト

Contract を使うことで型安全なコンテキストを実現できます：

```python
from railway import Contract


class UserContext(Contract):
    """ユーザーコンテキスト"""
    user_id: str
    name: str | None = None
    is_verified: bool = False
```

**Contract を使う理由:**
- 型安全: mypyでエラーを早期発見
- IDE補完: 開発効率が向上
- 不変性: `frozen=True` でバグを防止

## 4. 条件分岐ワークフロー

### 4.1 分岐を含むワークフロー

時間帯に応じて挨拶を変えるワークフローを作成します。

`transition_graphs/greeting_*.yml` を編集：

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

### 4.2 ノードの実装

`src/nodes/greeting/check_time.py`:

```python
from datetime import datetime
from railway import Contract, node
from railway.core.dag.outcome import Outcome


class TimeContext(Contract):
    """時間帯コンテキスト"""
    period: str


@node
def check_time() -> tuple[TimeContext, Outcome]:
    """時間帯を判定して状態を返す"""
    hour = datetime.now().hour

    if 5 <= hour < 12:
        ctx = TimeContext(period="morning")
        return ctx, Outcome.success("morning")
    elif 12 <= hour < 18:
        ctx = TimeContext(period="afternoon")
        return ctx, Outcome.success("afternoon")
    else:
        ctx = TimeContext(period="evening")
        return ctx, Outcome.success("evening")
```

`src/nodes/greeting/greet.py`:

```python
from railway import node
from railway.core.dag.outcome import Outcome
from nodes.greeting.check_time import TimeContext


@node
def greet_morning(ctx: TimeContext) -> tuple[TimeContext, Outcome]:
    """朝の挨拶"""
    print("おはようございます！")
    return ctx, Outcome.success("done")


@node
def greet_afternoon(ctx: TimeContext) -> tuple[TimeContext, Outcome]:
    """午後の挨拶"""
    print("こんにちは！")
    return ctx, Outcome.success("done")


@node
def greet_evening(ctx: TimeContext) -> tuple[TimeContext, Outcome]:
    """夜の挨拶"""
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

出力例：

```
[check_time] 開始...
[check_time] ✓ 完了 (success::morning)
[greet_morning] 開始...
おはようございます！
[greet_morning] ✓ 完了 (success::done)
ワークフロー完了: 2 ステップ
```

## 5. エラーハンドリング

### 5.1 失敗パスの追加

遷移グラフに失敗パスを追加：

```yaml
transitions:
  check_time:
    success::morning: greet_morning
    success::afternoon: greet_afternoon
    success::evening: greet_evening
    failure::error: exit::error
```

### 5.2 ノードでのエラーハンドリング

```python
@node
def check_time() -> tuple[TimeContext, Outcome]:
    """時間帯を判定"""
    try:
        hour = datetime.now().hour
        # ... 処理
        return ctx, Outcome.success("morning")
    except Exception:
        return TimeContext(period="unknown"), Outcome.failure("error")
```

## 6. ポイント

1. **ノードは状態を返すだけ** - 遷移先はYAMLで定義
2. **Outcome を使う** - `Outcome.success("done")` で簡潔に
3. **Contract を使う** - 型安全なコンテキスト
4. **YAMLを変更したら再sync** - `railway sync transition --entry <name>`

## 7. 次のステップ

- [readme_linear.md](readme_linear.md) - 線形パイプラインの学習
- [TUTORIAL_linear.md](TUTORIAL_linear.md) - 線形パイプライン詳細チュートリアル
- [docs/adr/](docs/adr/) - 設計決定記録

## 8. チャレンジ

1. 週末と平日で挨拶を変える分岐を追加
2. 複数の終了コード（success::green, success::yellow）を使い分け
3. コールバック `StepRecorder` を使って実行ログを記録
```

### TUTORIAL_linear.md（新規作成）

```markdown
# Railway Framework チュートリアル - 線形パイプライン

このチュートリアルでは、`typed_pipeline` を使用した線形パイプラインの開発を学びます。

条件分岐が必要な場合は [TUTORIAL.md](TUTORIAL.md) の dag_runner を使用してください。

## 線形パイプラインとは

処理が必ず順番に実行されるパイプラインです：

```
A → B → C → D
```

条件分岐はありません。ETL、データ変換に適しています。

## 1. プロジェクト初期化

```bash
railway init my_project
cd my_project
```

## 2. エントリーポイント作成

```bash
railway new entry my_pipeline --mode linear
```

以下のファイルが生成されます：

- `src/my_pipeline.py` - エントリーポイント（typed_pipeline 使用）
- `src/nodes/my_pipeline/step1.py` - ステップ1
- `src/nodes/my_pipeline/step2.py` - ステップ2

## 3. 生成されるコード

### エントリーポイント

`src/my_pipeline.py`:

```python
from railway import entry_point, typed_pipeline
from nodes.my_pipeline.step1 import step1
from nodes.my_pipeline.step2 import step2


@entry_point
def main():
    """パイプラインを実行"""
    result = typed_pipeline([
        step1,
        step2,
    ])
    print(f"完了: {result}")
    return result
```

### ノード

`src/nodes/my_pipeline/step1.py`:

```python
from railway import Contract, node


class Step1Output(Contract):
    """ステップ1の出力"""
    data: str


@node
def step1() -> Step1Output:
    """ステップ1の処理"""
    return Step1Output(data="processed")
```

## 4. 実行

```bash
railway run my_pipeline
```

## 5. typed_pipeline の特徴

- **Contract 自動解決**: 次のノードに必要な Contract を自動で渡す
- **シンプル**: 状態管理不要
- **線形処理専用**: 条件分岐不可

## 6. dag_runner との比較

| 項目 | typed_pipeline | dag_runner |
|------|----------------|------------|
| 分岐 | 不可 | 可能 |
| 遷移定義 | コード内 | YAML |
| 戻り値 | Contract | tuple[Contract, Outcome] |
| 用途 | ETL | 運用自動化 |

条件分岐が必要になったら `dag_runner` への移行を検討してください。

## 7. 次のステップ

- [TUTORIAL.md](TUTORIAL.md) - DAGワークフローチュートリアル
- [docs/adr/002_execution_models.md](docs/adr/002_execution_models.md) - 実行モデルの詳細
```

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/docs/test_tutorial.py
"""Tests for TUTORIAL documentation."""
import pytest
from pathlib import Path


class TestTutorialDefault:
    """Test TUTORIAL uses dag_runner as default."""

    @pytest.fixture
    def tutorial_content(self):
        tutorial_path = Path(__file__).parent.parent.parent.parent / "TUTORIAL.md"
        return tutorial_path.read_text()

    def test_dag_runner_is_primary(self, tutorial_content):
        """dag_runner should appear before typed_pipeline."""
        dag_pos = tutorial_content.find("dag_runner")
        pipeline_pos = tutorial_content.find("typed_pipeline")
        # typed_pipeline は参照としてのみ登場するか、dag_runnerより後
        if pipeline_pos != -1:
            assert dag_pos < pipeline_pos, "dag_runner should appear first"

    def test_uses_outcome_class(self, tutorial_content):
        """Should use Outcome class."""
        assert "Outcome" in tutorial_content
        assert "Outcome.success" in tutorial_content

    def test_has_branching_example(self, tutorial_content):
        """Should have conditional branching example."""
        assert "条件分岐" in tutorial_content or "branching" in tutorial_content.lower()

    def test_references_linear_tutorial(self, tutorial_content):
        """Should reference TUTORIAL_linear.md."""
        assert "TUTORIAL_linear" in tutorial_content


class TestTutorialLinearExists:
    """Test TUTORIAL_linear.md exists."""

    def test_file_exists(self):
        tutorial_linear = Path(__file__).parent.parent.parent.parent / "TUTORIAL_linear.md"
        assert tutorial_linear.exists()

    def test_mentions_typed_pipeline(self):
        tutorial_linear = Path(__file__).parent.parent.parent.parent / "TUTORIAL_linear.md"
        content = tutorial_linear.read_text()
        assert "typed_pipeline" in content
        assert "--mode linear" in content

    def test_mentions_etl(self):
        tutorial_linear = Path(__file__).parent.parent.parent.parent / "TUTORIAL_linear.md"
        content = tutorial_linear.read_text()
        assert "ETL" in content
```

### Step 2: Green

TUTORIAL.md と TUTORIAL_linear.md を上記の内容で作成/更新する。

---

## 完了条件

- [ ] TUTORIAL.md が dag_runner 型をデフォルトとして説明
- [ ] Outcome クラスの使用例を含む
- [ ] 条件分岐ワークフローのハンズオン
- [ ] TUTORIAL_linear.md への参照
- [ ] TUTORIAL_linear.md 新規作成
- [ ] typed_pipeline の詳細は TUTORIAL_linear.md に移動
- [ ] テストが通過

---

## 次のIssue

- Phase 2 完了後: 事例１ワークフローを新APIで再実装して動作確認
