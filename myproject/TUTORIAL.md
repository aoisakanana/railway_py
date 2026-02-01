# myproject チュートリアル

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

### 2.2 すぐに実行可能！

**v0.13.1+**: `railway new entry` は自動的にコード生成も行います。

```bash
railway run greeting
```

**期待される出力:**
```
[start] 開始...
[start] ✓ 完了 (success::done)
ワークフロー完了: exit.success.done
```

🎉 **1コマンドで動くワークフローが完成！**

### 2.3 遷移グラフを確認

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

  # 終端ノードは nodes.exit 配下に定義（v0.13.0+）
  exit:
    success:
      done:
        description: "正常終了"
    failure:
      error:
        description: "エラー終了"

start: start

transitions:
  start:
    success::done: exit.success.done
    failure::error: exit.failure.error
```

編集後は再同期：

```bash
railway sync transition --entry greeting
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
    """ワークフローコンテキスト"""
    message: str = ""


@node
def start() -> tuple[GreetingContext, Outcome]:
    """開始ノード"""
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
    description: "時間帯を判定"
  greet_morning:
    description: "朝の挨拶"
  greet_afternoon:
    description: "午後の挨拶"
  greet_evening:
    description: "夜の挨拶"

  # 終端ノード（v0.13.0+ 形式）
  exit:
    success:
      done:
        description: "正常終了"

start: check_time

transitions:
  check_time:
    success::morning: greet_morning
    success::afternoon: greet_afternoon
    success::evening: greet_evening
  greet_morning:
    success::done: exit.success.done
  greet_afternoon:
    success::done: exit.success.done
  greet_evening:
    success::done: exit.success.done
```

**ポイント:**
- `module/function` は省略可能（ノード名から自動解決）
- 終端ノードは `nodes.exit` 配下に定義
- 遷移先は `exit.success.done` 形式で指定

### 4.2 ノードを実装

`src/nodes/greeting/check_time.py`:

```python
from datetime import datetime
from railway import Contract, node
from railway.core.dag import Outcome


class TimeContext(Contract):
    """時間帯コンテキスト"""
    period: str


@node
def check_time() -> tuple[TimeContext, Outcome]:
    """時間帯を判定して状態を返す"""
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
    """時間帯を判定"""
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
    print(f"[{step.node_name}] -> {step.state}")
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
2. 複数の終端ノード（exit.success.done, exit.failure.error）を使い分け
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
