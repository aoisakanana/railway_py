# Phase2: DAGワークフロー実装計画

**作成日:** 2025-01-25
**対象:** v0.10.2
**開発手法:** TDD（テスト駆動開発）+ 関数型パラダイム

---

## 1. 設計原則

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
| #08 | コード生成器（純粋関数） | #04, #05, #07 | 1.5日 |
| #09 | CLIコマンド `railway sync transition` | #05, #06, #08 | 1日 |

### Phase 2c: ランタイム（Issue 10-11）

| Issue | タイトル | 依存関係 | 見積もり |
|-------|---------|----------|----------|
| #10 | DAGランナー実装 | #04, #07 | 1.5日 |
| #11 | ステップコールバック（監査用） | #10 | 0.5日 |

### Phase 2d: テンプレート・ドキュメント（Issue 12-14）

| Issue | タイトル | 依存関係 | 見積もり |
|-------|---------|----------|----------|
| #12 | プロジェクトテンプレート更新 | #09 | 0.5日 |
| #13 | README.md 更新 | #10 | 0.5日 |
| #14 | TUTORIAL.md 更新 | #10, #12 | 1日 |

---

## 4. 依存関係グラフ

```
Phase 2a (基盤)
===============

#04 TransitionGraph データ型
 ├── #05 YAMLパーサー
 ├── #06 グラフバリデータ
 └── #07 状態Enum基底クラス

Phase 2b (コード生成)
====================

#05 + #07 ──→ #08 コード生成器
#05 + #06 + #08 ──→ #09 CLIコマンド

Phase 2c (ランタイム)
====================

#04 + #07 ──→ #10 DAGランナー
#10 ──→ #11 ステップコールバック

Phase 2d (ドキュメント)
=====================

#09 ──→ #12 テンプレート更新
#10 ──→ #13 README更新
#10 + #12 ──→ #14 TUTORIAL更新
```

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

| # | タイトル | Phase | ファイル |
|---|---------|-------|---------|
| 00 | DAG実装計画（本ドキュメント） | - | `00_DAG実装計画.md` |
| 01 | DAG/グラフワークフローの必要性 | 背景 | `001_dag_pipeline_native_support.md` |
| 02 | 状態命名規則の検討 | 背景 | `002_dag_state_naming_convention.md` |
| 03 | YAML駆動の遷移グラフ設計 | 背景 | `003_yaml_driven_transition_graph.md` |
| 04 | TransitionGraph データ型定義 | 2a | `04_transition_graph_types.md` |
| 05 | YAMLパーサー実装 | 2a | `05_yaml_parser.md` |
| 06 | グラフバリデータ実装 | 2a | `06_graph_validator.md` |
| 07 | 状態Enum基底クラス | 2a | `07_node_outcome.md` |
| 08 | コード生成器実装 | 2b | `08_codegen.md` |
| 09 | CLI `railway sync transition` | 2b | `09_cli_sync.md` |
| 10 | DAGランナー実装 | 2c | `10_dag_runner.md` |
| 11 | ステップコールバック | 2c | `11_step_callback.md` |
| 12 | プロジェクトテンプレート更新 | 2d | `12_template_update.md` |
| 13 | README.md 更新 | 2d | `13_readme_update.md` |
| 14 | TUTORIAL.md 更新 | 2d | `14_tutorial_update.md` |

---

## 8. 関連ドキュメント

- 背景Issue: `001_dag_pipeline_native_support.md`
- 命名規則検討: `002_dag_state_naming_convention.md`
- YAML設計: `003_yaml_driven_transition_graph.md`
- 事例１仕様: `.運用高度化事例/事例１.md`
- 事例１実装: `/examples/review/src/top2.py`

---

**次のステップ:** Issue #04 から順に実装を開始
