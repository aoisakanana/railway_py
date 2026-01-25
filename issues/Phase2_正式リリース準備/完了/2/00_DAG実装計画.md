# Phase2: DAGワークフロー実装計画

**作成日:** 2025-01-25
**対象:** v0.10.2
**開発手法:** TDD（テスト駆動開発）+ 関数型パラダイム

---

## 1. 設計原則

### 1.0 用語定義

| 用語 | 英語 | 説明 | 例 |
|------|------|------|-----|
| 状態文字列 | State String | ノード実行結果を表す文字列 | `"fetch_alert::success::done"` |
| Outcome | - | ノードが返す結果オブジェクト（ユーザーAPI） | `Outcome.success("done")` |
| State Enum | - | 生成コード内の状態定数（内部用） | `Top2State.FETCH_ALERT_SUCCESS_DONE` |
| NodeOutcome | - | State Enum の基底クラス | `class MyState(NodeOutcome)` |
| Exit | - | 終了コード定数（ユーザーAPI） | `Exit.GREEN`, `Exit.RED` |
| ExitOutcome | - | 生成コード内の終了Enum基底（内部用） | `class MyExit(ExitOutcome)` |

### 1.1 TDD基本方針

Phase1と同様に、以下のサイクルを厳守：

```
1. Red    - まずテストを書く（失敗することを確認）
2. Green  - テストが通る最小限のコードを実装
3. Refactor - コードをリファクタリング（テストは通ったまま）
```

### 1.2 関数型パラダイムのベストプラクティス

| 原則 | 説明 | 適用箇所 |
|------|------|----------|
| **純粋関数** | 副作用なし、同じ入力→同じ出力 | パーサー、バリデータ、コード生成器 |
| **イミュータブル** | データは変更せず新規生成 | 遷移グラフ、状態オブジェクト |
| **関数合成** | 小さな関数を組み合わせる | パイプライン処理 |
| **型安全** | 静的型付けで安全性担保 | Contract、Protocol活用 |
| **副作用の分離** | IO操作は境界に押し出す | ファイル読み書き、コード生成 |

### 1.3 副作用の分離パターン

```
        純粋関数層（テスト容易）
        ┌─────────────────────────────────────┐
        │  parse_yaml_content(content: str)   │
        │  validate_graph(graph: TransitionGraph)│
        │  generate_code(graph: TransitionGraph) │
        └─────────────────────────────────────┘
                        ↑ ↓
        ──────────────────────────────────────────
        IO境界層（副作用あり、薄く保つ）
        ┌─────────────────────────────────────┐
        │  read_yaml_file(path: Path)         │
        │  write_generated_code(path: Path)   │
        └─────────────────────────────────────┘
```

### 1.4 テストカバレッジ目標

- **Unit Test:** 90%以上
- **Integration Test:** 主要フローをカバー
- **E2E Test:** CLIコマンドをカバー
- **総合:** 80%以上

---

## 2. アーキテクチャ概要

### 2.1 データフロー

```
[YAML定義]
    │
    ↓ parse
[TransitionGraph]  ←── 純粋なデータ構造（イミュータブル）
    │
    ├─→ validate ──→ [ValidationResult]
    │
    └─→ generate ──→ [GeneratedCode]
                          │
                          ↓ write (IO境界)
                     [_railway/generated/*.py]
```

### 2.2 コアデータ型

```python
# すべてイミュータブル（frozen=True）
@dataclass(frozen=True)
class NodeDefinition:
    name: str
    module: str
    function: str
    description: str

@dataclass(frozen=True)
class StateTransition:
    from_state: str
    to_node: str | ExitCode

@dataclass(frozen=True)
class TransitionGraph:
    version: str
    entrypoint: str
    nodes: tuple[NodeDefinition, ...]
    transitions: tuple[StateTransition, ...]
    exits: tuple[ExitDefinition, ...]
    start_node: str
    options: GraphOptions
```

---

## 3. 実装フェーズ

### Phase 2a: 基盤（Issue 04-07）

| Issue | タイトル | 依存関係 | 見積もり |
|-------|---------|----------|----------|
| #04 | TransitionGraph データ型定義 | - | 0.5日 |
| #05 | YAMLパーサー（純粋関数） | #04 | 1日 |
| #06 | グラフバリデータ（純粋関数） | #04 | 1日 |
| #07 | 状態Enum基底クラス | #04 | 0.5日 |

### Phase 2b: コード生成（Issue 08-09）

| Issue | タイトル | 依存関係 | 見積もり |
|-------|---------|----------|----------|
| #08 | コード生成器（純粋関数） | #04, #05, #06, #07 | 1.5日 |
| #09 | CLIコマンド `railway sync transition` | #05, #06, #08 | 1日 |

> **Note:** #08 は #06（バリデータ）にも依存。生成前に検証することで、不正なコード生成を防止。

### Phase 2c: ランタイム（Issue 15, 10, 11）

| Issue | タイトル | 依存関係 | 見積もり |
|-------|---------|----------|----------|
| #15 | Outcome クラス & @node デコレータ | #07 | 1日 |
| #10 | DAGランナー実装 | #04, #07, #15 | 1.5日 |
| #11 | ステップコールバック（監査用） | #10 | 0.5日 |

### Phase 2d: テンプレート・ドキュメント（Issue 12, 16-19）

| Issue | タイトル | 依存関係 | 見積もり |
|-------|---------|----------|----------|
| #12 | プロジェクトテンプレート更新 | #09 | 0.5日 |
| #16 | アーキテクチャガイド（ADR追加） | #10, #15 | 0.5日 |
| #17 | `railway new entry` コマンド変更 | #09, #12, #15 | 0.5日 |
| #18 | README.md 更新（dag_runner 型デフォルト） | #10, #15, #16, #17 | 0.5日 |
| #19 | TUTORIAL.md 更新（dag_runner 型デフォルト） | #10, #12, #15, #16, #17 | 1日 |

---

## 4. 依存関係グラフ

```
Phase 2a-0 (前提条件)
====================

#03.1 テストフィクスチャ準備 ← すべてのTDD Issueの前提

Phase 2a (基盤)
===============

#03.1 ──→ #04 TransitionGraph データ型
              ├── #05 YAMLパーサー (#03.1にも依存)
              ├── #06 グラフバリデータ (#03.1にも依存)
              └── #07 状態Enum基底クラス

Phase 2b (コード生成)
====================

#03.1 + #05 + #06 + #07 ──→ #08 コード生成器
                                 │
                                 │ ※ #06 依存: 生成前検証のため
                                 ↓
#03.1 + #05 + #06 + #08 ──→ #09 CLIコマンド

Phase 2c (ランタイム)
====================

#07 ──→ #15 Outcomeクラス & @nodeデコレータ
#03.1 + #04 + #07 + #15 ──→ #10 DAGランナー
#10 ──→ #11 ステップコールバック

Phase 2d (ドキュメント)
=====================

#09 ──→ #12 テンプレート更新
#10 + #15 ──→ #16 アーキテクチャガイド（ADR追加）
#09 + #12 + #15 ──→ #17 `railway new entry` コマンド変更
#10 + #15 + #16 + #17 ──→ #18 README更新（dag_runner デフォルト）
#10 + #12 + #15 + #16 + #17 ──→ #19 TUTORIAL更新（dag_runner デフォルト）
```

### 4.1 クリティカルパス

```
#04 → #05 → #06 → #08 → #09 → #12 → #17 → #19
      ↓
      #07 → #15 → #10 → #11
                   ↓
                  #16 → #18
```

最長パス: #04 → #05 → #06 → #08 → #09 → #12 → #17 → #19 (7日)

> **Note:** #15（Outcome）は #07 のみに依存し、#10（dag_runner）が #15 に依存する。
> これにより、Outcome クラスを先に実装してから dag_runner で使用する正しい順序になる。

---

## 5. ディレクトリ構造（実装後）

```
railway/
├── core/
│   ├── dag/                      # 新規追加
│   │   ├── __init__.py
│   │   ├── types.py              # TransitionGraph等のデータ型
│   │   ├── parser.py             # YAMLパーサー（純粋関数）
│   │   ├── validator.py          # グラフバリデータ（純粋関数）
│   │   ├── codegen.py            # コード生成器（純粋関数）
│   │   ├── runner.py             # DAGランナー
│   │   └── state.py              # NodeOutcome基底クラス
│   └── ...
├── cli/
│   ├── sync.py                   # 新規: railway sync コマンド
│   └── ...
└── templates/
    └── project/
        ├── transition_graphs/    # 新規: 遷移グラフテンプレート
        │   └── .gitkeep
        └── ...

tests/
├── unit/
│   └── core/
│       └── dag/                  # 新規追加
│           ├── test_types.py
│           ├── test_parser.py
│           ├── test_validator.py
│           ├── test_codegen.py
│           ├── test_runner.py
│           └── test_state.py
├── integration/
│   └── test_dag_workflow.py      # 新規
└── e2e/
    └── test_cli_sync.py          # 新規
```

---

## 6. 品質ゲート

### 6.1 各Issue完了の条件

- [ ] Red Phase: 失敗するテストが書かれている
- [ ] Green Phase: テストが全て通過
- [ ] Refactor Phase: コードが整理されている
- [ ] カバレッジが90%以上（Unit）
- [ ] mypyでエラーなし
- [ ] ruffでエラーなし
- [ ] 関数型原則に準拠（純粋関数、イミュータブル）

### 6.2 Phase完了の条件

- [ ] 全Issueが完了
- [ ] 統合テストが通過
- [ ] E2Eテストが通過
- [ ] カバレッジ80%以上
- [ ] README.md が最新
- [ ] TUTORIAL.md が最新
- [ ] 事例１ワークフローが新APIで動作

---

## 7. Issue一覧

### 7.1 Issue番号体系

| 範囲 | カテゴリ | 説明 |
|------|----------|------|
| 00 | 計画 | 本計画ドキュメント |
| 001-003 | 背景/設計 | 設計検討・ADR（実装対象外） |
| 03.1 | 前提条件 | テストフィクスチャ準備 |
| 04-12, 15-19 | 実装 | TDDで実装するIssue |

> **Note:** 001-003 は設計背景・決定事項を記録するドキュメントであり、
> 実装対象ではありません。実装は 04 から開始します。
> #17-#19 はドキュメント・CLI変更で、#18/#19 が最終Issue（README/TUTORIAL更新）。

### 7.2 背景/設計Issue（参照用）

| # | タイトル | 内容 |
|---|---------|------|
| 001 | DAG/グラフワークフローの必要性 | 機能要件の背景、API設計案 |
| 002 | 状態命名規則の検討 | 状態文字列のフォーマット決定 |
| 003 | YAML駆動の遷移グラフ設計 | YAMLスキーマ、コード生成設計 |

### 7.3 前提条件Issue（TDD開始前に完了必須）

| # | タイトル | 依存関係 | 見積もり |
|---|---------|----------|----------|
| 03.1 | テストフィクスチャ準備（conftest.py + YAML） | - | 0.25日 |

> **重要:** Issue 03.1 は TDD の Red Phase を開始する前に完了している必要があります。
> フィクスチャなしではテストが ImportError ではなく適切に失敗しません。

### 7.4 実装Issue（TDD対象）

| # | タイトル | Phase | 依存関係 | 見積もり |
|---|---------|-------|----------|----------|
| 04 | TransitionGraph データ型定義 | 2a | 03.1 | 0.5日 |
| 05 | YAMLパーサー実装 | 2a | #04 | 1日 |
| 06 | グラフバリデータ実装 | 2a | #04 | 1日 |
| 07 | 状態Enum基底クラス | 2a | #04 | 0.5日 |
| 08 | コード生成器実装 | 2b | #04,#05,#06,#07 | 1.5日 |
| 09 | CLI `railway sync transition` | 2b | #05,#06,#08 | 1日 |
| 15 | Outcomeクラス & @nodeデコレータ | 2c | #07 | 1日 |
| 10 | DAGランナー実装 | 2c | #04,#07,#15 | 1.5日 |
| 11 | ステップコールバック | 2c | #10 | 0.5日 |
| 12 | プロジェクトテンプレート更新 | 2d | #09 | 0.5日 |
| 16 | アーキテクチャガイド（ADR追加） | 2d | #10,#15 | 0.5日 |
| 17 | `railway new entry` コマンド変更 | 2d | #09,#12,#15 | 0.5日 |
| 18 | README.md 更新（dag_runner デフォルト） | 2d | #10,#15,#16,#17 | 0.5日 |
| 19 | TUTORIAL.md 更新（dag_runner デフォルト） | 2d | #10,#12,#15,#16,#17 | 1日 |

**合計見積もり: 12.25日**

---

## 8. テストYAMLの活用

### 8.1 テスト用YAMLファイル

`tests/fixtures/transition_graphs/` ディレクトリにテスト用YAMLが配置されています：

| ファイル | 用途 | 複雑度 |
|---------|------|--------|
| `simple_20250125000000.yml` | 最小構成（1ノード、2終了） | 低 |
| `branching_20250125000000.yml` | 分岐テスト（5ノード、3分岐→合流） | 中 |
| `top2_20250125000000.yml` | 事例1完全版（8ノード、4終了） | 高 |

### 8.2 conftest.py の実装（必須）

**重要:** Phase2実装の前提条件として、以下の `tests/conftest.py` を実装してください。

```python
# tests/conftest.py
"""
Pytest fixtures for DAG workflow tests.

このファイルはPhase2のすべてのテストで共有されるフィクスチャを定義します。
"""
import pytest
from pathlib import Path


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "transition_graphs"


@pytest.fixture
def simple_yaml() -> Path:
    """最小構成YAML（1ノード、2終了）

    用途:
    - パーサーの基本動作確認
    - バリデータの正常系テスト
    - コード生成器の最小構成テスト
    """
    return FIXTURES_DIR / "simple_20250125000000.yml"


@pytest.fixture
def branching_yaml() -> Path:
    """分岐テストYAML（5ノード、3分岐→合流）

    用途:
    - 条件分岐のパース・検証
    - 合流点の到達可能性テスト
    - 複数パスのコード生成テスト
    """
    return FIXTURES_DIR / "branching_20250125000000.yml"


@pytest.fixture
def top2_yaml() -> Path:
    """事例1完全版YAML（8ノード、4終了）

    用途:
    - 実運用レベルのワークフローテスト
    - 複雑な遷移パターンの検証
    - E2Eテストのベースライン
    """
    return FIXTURES_DIR / "top2_20250125000000.yml"


@pytest.fixture
def invalid_yaml_missing_start(tmp_path) -> Path:
    """開始ノードが未定義のYAML（バリデータエラーテスト用）"""
    content = """
version: "1.0"
entrypoint: invalid
description: ""
nodes:
  a:
    module: nodes.a
    function: func_a
    description: ""
exits: {}
start: nonexistent
transitions: {}
"""
    yaml_path = tmp_path / "invalid_start.yml"
    yaml_path.write_text(content)
    return yaml_path


@pytest.fixture
def invalid_yaml_orphan_node(tmp_path) -> Path:
    """到達不能ノードを含むYAML（バリデータ警告テスト用）"""
    content = """
version: "1.0"
entrypoint: orphan
description: ""
nodes:
  a:
    module: nodes.a
    function: func_a
    description: ""
  orphan:
    module: nodes.orphan
    function: orphan_func
    description: "到達不能ノード"
exits:
  done:
    code: 0
    description: ""
start: a
transitions:
  a:
    success::done: exit::done
"""
    yaml_path = tmp_path / "orphan.yml"
    yaml_path.write_text(content)
    return yaml_path


@pytest.fixture
def invalid_yaml_cycle(tmp_path) -> Path:
    """循環参照を含むYAML（バリデータエラーテスト用）"""
    content = """
version: "1.0"
entrypoint: cycle
description: ""
nodes:
  a:
    module: nodes.a
    function: func_a
    description: ""
  b:
    module: nodes.b
    function: func_b
    description: ""
exits:
  done:
    code: 0
    description: ""
start: a
transitions:
  a:
    success::done: b
  b:
    success::done: a  # 循環！終了への到達不能
"""
    yaml_path = tmp_path / "cycle.yml"
    yaml_path.write_text(content)
    return yaml_path
```

**ディレクトリ構造:**
```
tests/
├── conftest.py                 # ← 必ず実装
├── fixtures/
│   └── transition_graphs/
│       ├── simple_20250125000000.yml    ✓ 既存
│       ├── branching_20250125000000.yml ✓ 既存
│       └── top2_20250125000000.yml      ✓ 既存
└── unit/
    └── core/
        └── dag/
            ├── test_types.py
            ├── test_parser.py
            ├── test_validator.py
            ├── test_codegen.py
            ├── test_runner.py
            ├── test_state.py
            └── test_callbacks.py
```

### 8.3 各Issueでの活用

- **#05 YAMLパーサー**: 3種類すべてのYAMLをパースしてTransitionGraphに変換
- **#06 バリデータ**: 正常系YAMLの検証、`invalid_yaml_*` フィクスチャでエラー検出
- **#08 コード生成器**: 生成コードの構文チェック、import検証
- **#10 DAGランナー**: モックノードでのワークフロー実行テスト

### 8.4 前提条件チェックリスト

Phase2実装開始前に以下を確認：
- [ ] `tests/fixtures/transition_graphs/` に3つのYAMLが存在
- [ ] `tests/conftest.py` にフィクスチャが定義済み
- [ ] `pytest tests/conftest.py --collect-only` でフィクスチャが認識される

---

## 9. エラーコード一覧

### 9.1 バリデータエラーコード

| コード | 分類 | 説明 | 対処 |
|--------|------|------|------|
| E001 | エラー | 開始ノードが定義されていない | `start:` に指定したノード名が `nodes:` に存在するか確認 |
| E002 | エラー | 遷移先の終了コードが未定義 | `exits:` にターゲット名を追加 |
| E003 | エラー | 遷移先ノードが未定義 | `nodes:` にターゲットノードを追加 |
| E004 | エラー | ノードに遷移が定義されていない（行き止まり） | `transitions:` にそのノードの遷移を追加 |
| E005 | エラー | 同一ノードで状態が重複 | 重複した状態を削除または名前変更 |
| E006 | エラー | 終了に到達できない（無限ループ）| 循環パスに終了への遷移を追加 |
| W001 | 警告 | ノードが開始ノードから到達不能 | 到達パスを追加するか、不要なノードを削除 |

### 9.2 パーサーエラーコード

| コード | 分類 | 説明 | 対処 |
|--------|------|------|------|
| P001 | エラー | YAML構文エラー | YAMLの構文を確認（インデント、コロン等） |
| P002 | エラー | 必須フィールドが不足 | `version`, `entrypoint`, `nodes`, `start` を確認 |
| P003 | エラー | サポート外バージョン | `version: "1.0"` を指定 |

### 9.3 ランタイムエラーコード

| コード | 分類 | 説明 | 対処 |
|--------|------|------|------|
| R001 | エラー | 最大イテレーション数超過 | `max_iterations` を増やすか、ワークフローを見直す |
| R002 | エラー | 未定義の状態（strictモード）| 遷移テーブルに状態を追加 |

---

## 10. Phase1との統合

### 9.1 typed_pipeline と dag_runner の使い分け

| 用途 | 推奨API | 理由 |
|------|---------|------|
| 線形パイプライン | `typed_pipeline` | シンプル、Contract自動解決 |
| 条件分岐あり | `dag_runner` | 状態ベースの遷移制御 |
| 複雑なワークフロー | `dag_runner` | YAMLで可視化・管理可能 |

### 10.2 コンテキストの型安全性

DAGワークフローでも、Phase1のContract原則を尊重します：

```python
# Contract + Outcome（唯一のサポート形式）
from railway import Contract, node
from railway.core.dag.outcome import Outcome
from railway.core.dag.runner import dag_runner, Exit

class WorkflowContext(Contract):
    incident_id: str
    session_id: str | None = None

@node
def fetch_alert(params: AlertParams) -> tuple[WorkflowContext, Outcome]:
    ctx = WorkflowContext(incident_id=params.incident_id)
    return ctx, Outcome.success("done")

# 遷移テーブルは文字列キーのみ（シンプル！）
transitions = {
    "fetch_alert::success::done": process,
    "fetch_alert::failure::http": Exit.RED,
    "process::success::done": Exit.GREEN,
}
```

**重要:** `dict` はサポートされません。Contractの使用が必須です。

### 10.3 Outcome クラス

状態返却には `Outcome` クラスを使用します：

```python
from railway.core.dag.outcome import Outcome

# 成功状態
return ctx, Outcome.success("done")       # → {node_name}::success::done
return ctx, Outcome.success("validated")  # → {node_name}::success::validated

# 失敗状態
return ctx, Outcome.failure("error")      # → {node_name}::failure::error
return ctx, Outcome.failure("timeout")    # → {node_name}::failure::timeout
```

dag_runner が関数名から状態文字列を自動生成します。詳細は Issue #15 を参照。

### 10.4 Exit 定数クラス

終了コードには `Exit` クラスの定数を使用します：

```python
from railway.core.dag.runner import Exit

transitions = {
    "process::success::done": Exit.GREEN,      # 正常終了
    "process::failure::error": Exit.RED,       # 異常終了
    "validate::success::warning": Exit.YELLOW, # 警告終了
}

# カスタム終了コード
Exit.code("green", "resolved")  # → "exit::green::resolved"
```

詳細は Issue #10 を参照。

---

## 11. 関連ドキュメント

- 背景Issue: `001_dag_pipeline_native_support.md`
- 命名規則検討: `002_dag_state_naming_convention.md`
- YAML設計: `003_yaml_driven_transition_graph.md`
- 事例１仕様: `.運用高度化事例/事例１.md`
- 事例１実装: `/examples/review/src/top2.py`

---

**次のステップ:** Issue #03.1 を完了後、Issue #04 から順に実装を開始

---

## 12. レビューログ

### レビュー実施日: 2025-01-25

#### ラウンド1: 整合性チェック

**発見した問題:**
1. テストフィクスチャの前提条件がIssue化されていなかった
2. 各IssueのフィクスチャへのTDD依存が明示されていなかった
3. ok/failヘルパー関数の将来対応が不明確だった
4. READMEとTUTORIALの内容重複があった

**対応:**
- Issue #03.1（テストフィクスチャ準備）を新規作成
- Issue #04, #05, #06, #08, #09, #10 に #03.1 への依存を追加
- Issue #10 のヘルパー関数に将来対応のバージョン（v0.11.0以降）を明記
- Issue #13 のREADMEセクションを簡略化し、TUTORIALへの誘導を追加

#### ラウンド2: 依存関係グラフ整合性

**発見した問題:**
1. 依存関係グラフが #03.1 の追加を反映していなかった
2. Issue #04 の依存関係が「なし」のままだった
3. Issue #12 のタイムスタンプ生成ロジックが不明確だった

**対応:**
- セクション4の依存関係グラフを更新し、Phase 2a-0（前提条件）を追加
- Issue #04 の依存関係を #03.1 に更新
- Issue #12 にタイムスタンプ生成の実装詳細を追加

#### ラウンド3: TDD・関数型パラダイム準拠

**発見した問題:**
1. Issue #10 のテストコードでミュータブルな操作（`context["value"] = 1`）が使用されていた
2. Contract推奨の強調が一部のIssueで不足していた

**対応:**
- Issue #10 のテストコードをイミュータブルパターン（`{**ctx, "value": 2}`）に修正
- テストクラスのdocstringにContract推奨の注記を追加
- `TestDagRunnerWithContract` を模範例として明示

### 改善結果サマリー

| カテゴリ | 改善前 | 改善後 |
|---------|--------|--------|
| Issue数 | 14 | 15（#03.1追加） |
| フィクスチャ依存明示 | なし | 6 Issue に追加 |
| TDD Red Phase 明確性 | 曖昧 | 前提条件明示 |
| 関数型パラダイム準拠 | 一部違反 | イミュータブルパターン徹底 |
| ドキュメント重複 | あり | 役割分担明確化 |

---

### レビュー実施日: 2025-01-25（追加レビュー）

#### ラウンド4: 設計明確化・APIデフォルト変更

**ユーザーからのフィードバック:**
1. 後方互換性は不要、理想の実装を優先
2. Contract継続利用の是非
3. pipeline() vs dag_runner() の関係性明確化
4. `railway new entry` のデフォルトを dag_runner 型に変更
5. README/TUTORIALを dag_runner 型デフォルトに

**対応:**
- Issue #15（@node自動マッピング & Outcome）を新規作成
- Issue #16（アーキテクチャガイド ADR-002/003）を新規作成
- Issue #17（`railway new entry` コマンド変更）を新規作成
- Issue #13 → #18 に採番変更（README更新、dag_runner デフォルト）
- Issue #14 → #19 に採番変更（TUTORIAL更新、dag_runner デフォルト）
- Issue #10 から dict サポートを削除（Contract のみ）
- readme_linear.md / TUTORIAL_linear.md を新設（typed_pipeline 用）

**成果物:**
- `.claude_output/design_analysis_20250125.md` - Contract継続利用の分析
- `.claude_output/architecture_clarification_20250125.md` - アーキテクチャ明確化

### 最終改善結果サマリー

| カテゴリ | 改善前 | 改善後 |
|---------|--------|--------|
| Issue数 | 15 | 18（#15,#16,#17追加、#13→#18,#14→#19採番変更） |
| デフォルト実行モデル | typed_pipeline | dag_runner |
| コンテキスト型 | dict または Contract | Contract のみ |
| 状態返却 | 手動Enum | Outcome クラス |
| アーキテクチャドキュメント | なし | ADR-002, ADR-003 追加 |
| 線形パイプラインドキュメント | READMEに統合 | 分離（readme_linear.md, TUTORIAL_linear.md） |

---

### レビュー実施日: 2026-01-26（継続レビュー）

#### ラウンド5: Issue全体整合性レビュー

**発見した問題:**
1. Issue #11 が Contract-only ポリシーに違反（テストコードで dict 使用）
2. Issue #11 が Outcome クラス（Issue #15）との統合例を示していない
3. Issue #11 の依存関係に #15 が欠落
4. Issue #12 の「次のIssue」参照が古い（#13→#18）
5. dag_runner と Outcome の接続が不明確（TUTORIAL の使い方と実装の乖離）

**対応:**
- Issue #11 のテストコードを Contract + Outcome パターンに全面改訂
- Issue #11 の依存関係に #15 を追加
- Issue #12 の「次のIssue」を #17 に修正
- Issue #10 に Outcome サポートを追加（状態文字列キーでの遷移）
- Issue #10 の dag_runner 実装を拡張（Outcome 自動変換、文字列キー対応）
- Issue #10 に `TestDagRunnerWithOutcome` テストクラスを追加

#### ラウンド6: API シンプル化（旧: ユーザビリティ向上）

**設計改善（更新）:**
dag_runner は **Outcome + 文字列キー のみ** をサポート（シンプルに統一！）

- ノード: `Outcome.success("done")` を返す
- dag_runner: 関数名から状態文字列を自動生成
- 遷移テーブル: 文字列キー `"node_name::success::done"` のみ
- State Enum: 生成コード内部でのみ使用（ユーザーは触らない）

**Note:** State Enum を直接使用するパターンは削除。シンプルさを優先。

---

### レビュー実施日: 2026-01-26（大規模リファクタリング）

#### ラウンド7: シンプル化の徹底

**発見した問題:**
1. @node(state_enum=...) パラメータが冗長（DRY違反）
2. 遷移テーブルのキー形式が2種類（State Enum + 文字列）で混乱
3. Exit が Enum で複雑（定数クラスで十分）
4. コード生成が Enum キーを使用（文字列キーに統一すべき）
5. コールバック引数が NodeOutcome を使用（文字列に統一すべき）

**対応:**
- Issue #15: @node デコレータから state_enum パラメータを削除
- Issue #15: dag_runner が関数名から状態文字列を自動生成
- Issue #10: Exit を定数クラスに変更（Enum から）
- Issue #10: 遷移テーブルを文字列キーのみに統一
- Issue #10: dag_runner の型シグネチャを更新
- Issue #11: コールバック引数を state_string: str に変更
- Issue #08: 遷移テーブル生成を文字列キーに変更
- Issue #07: NodeOutcome/ExitOutcome を内部実装専用として位置づけ

### 最終改善結果サマリー（ラウンド7）

| カテゴリ | 改善前 | 改善後 |
|---------|--------|--------|
| @node パラメータ | state_enum 必要 | パラメータ不要 |
| 遷移テーブルキー | Enum + 文字列混在 | 文字列のみ |
| Exit 型 | Enum (ExitOutcome) | 定数クラス |
| コールバック引数 | NodeOutcome | str (状態文字列) |
| 状態文字列生成 | ユーザー手動 | dag_runner 自動 |
| 生成コードの役割 | ユーザー直接使用 | 内部検証/IDE補完用 |

**設計方針:**
- **ユーザー API**: Outcome + 文字列キー + Exit 定数（最もシンプル）
- **内部実装**: State Enum（型安全性維持）
- **コード生成**: 遷移テーブル + メタデータ（文字列キー）
   - 遷移テーブル: State Enum をキーに使用
   - 用途: 複雑なワークフロー、IDE補完を活用したい場合

**影響を受けたIssue:**
- #10: dag_runner 実装（Outcome/文字列キー対応）
- #11: ステップコールバック（Contract + Outcome パターン）
- #15: @node デコレータ（Outcome → State Enum 自動マッピングはオプション）

### 継続レビュー結果サマリー

| カテゴリ | 改善前 | 改善後 |
|---------|--------|--------|
| Issue #11 整合性 | Contract違反、Outcome未使用 | Contract + Outcome パターン |
| dag_runner 柔軟性 | State Enum のみ | Outcome + State Enum 両対応 |
| 遷移テーブルキー | Enum のみ | 文字列 + Enum 両対応 |
| Issue 間参照 | 一部古い | 全て最新化 |

---

### レビュー実施日: 2026-01-26（Issue全体整合性レビュー継続）

#### ラウンド8: 依存関係・API整合性

**発見した問題:**
1. Issue #15 が #10 に依存と記載されているが、実際は逆（#10 が #15 に依存）
   - dag_runner が `Outcome.to_state_string()` を呼び出す
   - #15 → #10 の順で実装すべき
2. Exit クラスが公開APIにエクスポートされていない
   - ユーザーは `railway.core.dag.runner` からインポートする必要があった
3. NodeOutcome/ExitOutcome と Outcome/Exit の関係性が不明確
4. 用語（状態文字列、State Enum、Outcome等）の定義が欠如

**対応:**
- Issue #15 の依存関係を `#07` のみに修正
- Issue #10 の依存関係に `#15` を追加
- Issue #11 の依存関係を `#10` のみに簡略化（推移的依存で十分）
- Phase 2c の実装順序を `#15 → #10 → #11` に変更
- Issue #15 の API エクスポートに `Exit` を追加
- Issue #07 に型の関係性テーブルを追加
- 計画書に用語定義セクション（1.0）を追加
- Issue #08 に生成コードの実行時依存（Exit）について注記を追加

### ラウンド8 改善結果サマリー

| カテゴリ | 改善前 | 改善後 |
|---------|--------|--------|
| #15 依存関係 | #07, #10（誤り） | #07 のみ |
| #10 依存関係 | #04, #07 | #04, #07, #15 |
| #11 依存関係 | #10, #15 | #10 のみ |
| Phase 2c 順序 | #10 → #11 (+ #15) | #15 → #10 → #11 |
| Exit 公開API | なし | `from railway import Exit` |
| 用語定義 | なし | セクション1.0に追加 |
| 型の関係性 | 不明確 | Issue #07 にテーブル追加 |

#### ラウンド9: YAML形式・クリティカルパス整合性

**発見した問題:**
1. conftest.py の invalid fixtures で短縮形式 `success:` を使用（正式形式は `success::done:`）
2. クリティカルパス図が依存関係変更を反映していない
3. 「次のIssue」参照が一部古い

**対応:**
- Issue #03.1 と #00 の invalid YAML fixtures を完全形式に修正
  - `success: exit::done` → `success::done: exit::done`
  - `success: b` → `success::done: b`
- クリティカルパス図を更新: `#07 → #15 → #10 → #11`
- Issue #07 の「次のIssue」に #15 を追加
- Issue #15 の「次のIssue」を #10 に修正

### 最終レビュー結果サマリー（ラウンド8-9）

| カテゴリ | 問題数 | 修正済 |
|---------|--------|--------|
| 依存関係の逆転 | 1 | ✓ |
| 公開APIの欠落 | 1 | ✓ |
| 用語定義の欠如 | 1 | ✓ |
| 型関係性の曖昧さ | 1 | ✓ |
| YAML形式の不整合 | 2 | ✓ |
| クリティカルパス図の誤り | 1 | ✓ |
| 「次のIssue」参照の誤り | 2 | ✓ |

**修正したIssue:**
- #00: 用語定義追加、クリティカルパス修正、YAML形式修正
- #03.1: YAML形式修正
- #07: 型関係性テーブル追加、「次のIssue」修正
- #08: 実行時依存の注記追加
- #10: 依存関係に #15 追加
- #11: 依存関係を #10 のみに簡略化
- #15: 依存関係修正、Exit公開API追加、「次のIssue」修正
