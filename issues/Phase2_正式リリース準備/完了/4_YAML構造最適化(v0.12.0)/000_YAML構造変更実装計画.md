# YAML 構造変更実装計画

**作成日:** 2026-01-28
**更新日:** 2026-01-28 (レビュー後改訂)
**関連 ADR:** ADR-004: Exit ノードの設計と例外処理

---

## 背景

### 現状の問題

1. **`exits` セクションが特殊な構造**
   - `nodes` と異なる構造であり、一貫性がない
   - `module`, `function` を持たず、関数を実行できない

2. **終了の詳細を区別できない**
   - `exit::success::done` と `exit::success::skipped` を別の終端として定義できない
   - 終了コードは success/failure の2種類のみ

3. **冗長な記述**
   - `module` と `function` が YAML パスと同じ値になることが多い
   - 記述量が多く、タイプミスのリスクがある

---

## 設計思想

### 1. 一貫性の原則

**「すべてのノードは同じ構造を持つ」**

終端ノードも通常のノードと同じ構造・同じ動作をする。
特殊なケースを減らすことで、学習コストと実装の複雑さを削減する。

### 2. 慣例による設定（Convention over Configuration）

**「明示的な指定がなければ、規約から推論する」**

- `module` 省略時 → YAML パスから自動解決
- `function` 省略時 → キー名から自動解決
- `exit_code` 省略時 → `success` = 0, `failure` = 1

### 3. 表現力の確保

**「終了状態を詳細に区別できる」**

深いネストにより、終了の種類を細かく分類できる。

### 4. 終端ノードの簡潔さ

**「終端ノードは Context のみを返す」**

終端ノードに Outcome は不要。遷移先がないため。

```python
# 終端ノードの返り値
@node
def done(ctx: WorkflowContext) -> FinalSummary:
    return FinalSummary(status="completed", count=ctx.count)
```

---

## 新しい YAML 構造

```yaml
nodes:
  # 通常ノード（module/function 省略可能）
  start_process:
    description: "開始ノード"
    # 自動解決: module=nodes.start_process, function=start_process

  # 終端ノード（nodes.exit 配下）
  exit:
    success:
      done:
        description: "正常終了（Slack通知）"
        # 自動解決: module=nodes.exit.success.done, function=done
        # 自動判定: exit_code=0
      skipped:
        description: "スキップして終了"

    failure:
      timeout:
        description: "タイムアウト"
        # 自動判定: exit_code=1

      # 深いネストも可能
      ssh:
        handshake:
          description: "SSHハンドシェイク失敗"

    # カスタム終了コード
    warning:
      low_disk:
        description: "ディスク容量警告"
        exit_code: 2

transitions:
  start_process:
    success::done: main1

  main1:
    success::done: exit.success.done
    success::skipped: exit.success.skipped
    failure::timeout: exit.failure.timeout
```

---

## 実装計画

### Issue 一覧（実装順）

| 順序 | # | タイトル | 見積もり | 依存 |
|------|---|----------|----------|------|
| 1 | **23** | **テスト用 YAML フィクスチャ** | **0.25日** | なし |
| 2 | 24 | NodeDefinition の終端ノード対応 | 0.25日 | #23 |
| 3 | 25 | パーサーのネスト構造対応（自動解決含む） | 0.5日 | #23, #24 |
| 4a | **26** | **バリデーション更新** | **0.25日** | #24, #25 |
| 4b | 27 | codegen の終端ノード対応 | 0.5日 | #24, #25 |
| 4c | **32** | **YAML 構造変換ユーティリティ** | **0.5日** | #25 |
| 5 | 28 | dag_runner の終端ノード実行 | 0.5日 | #27 |
| 6a | **31** | **codegen に run() ヘルパー追加** | **0.25日** | #27, #28 |
| 6b | **33** | **v0.11.3 → v0.12.0 マイグレーション定義** | **0.5日** | #32 |
| 7 | **30** | **E2E 統合テスト** | **0.25日** | #26, #27, #28, #31, #33 |
| 8 | 29 | 終端ノードドキュメント追加 | 0.25日 | #30 |

**合計見積もり:** 4.0日

**Note:** 4a/4b/4c および 6a/6b は並列実行可能

---

### 依存関係

```
┌─────────────────────────────────────────────────────────────────┐
│                        実装フェーズ                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Phase 0: テストデータ準備                                      │
│  ┌──────────────────────┐                                      │
│  │ #23 YAML フィクスチャ │◄── TDD の前提、最初に着手            │
│  └──────────┬───────────┘                                      │
│             │                                                   │
│  Phase 1: 基盤整備                                              │
│             ▼                                                   │
│  ┌──────────────────┐                                          │
│  │ #24 NodeDefinition │◄── すべての実装 Issue の基盤           │
│  └────────┬─────────┘                                          │
│           │                                                     │
│  Phase 2: パーサー（自動解決統合）                               │
│           ▼                                                     │
│  ┌────────────────────────────┐                                │
│  │ #25 パーサー＋自動解決     │◄── ネスト構造の再帰的パース    │
│  └────────┬───────────────────┘                                │
│           │                                                     │
│  Phase 3: 検証 & コード生成                                     │
│           ├──────────────────┐                                 │
│           ▼                  ▼                                 │
│  ┌────────────────┐  ┌────────────────┐                        │
│  │ #26 Validator  │  │ #27 codegen    │◄── 並列実行可能        │
│  └───────┬────────┘  └───────┬────────┘                        │
│          │                    │                                 │
│  Phase 4: ランタイム          │                                 │
│          └──────────┬─────────┘                                │
│                     ▼                                           │
│          ┌─────────────────────┐                               │
│          │ #28 dag_runner      │                               │
│          └──────────┬──────────┘                               │
│                     │                                           │
│  Phase 5: ヘルパー  │                                           │
│                     ▼                                           │
│          ┌─────────────────────┐                               │
│          │ #31 run() ヘルパー  │                               │
│          └──────────┬──────────┘                               │
│                     │                                           │
│  Phase 6: 統合 & ドキュメント                                   │
│                     ▼                                           │
│          ┌─────────────────────┐                               │
│          │ #30 E2E 統合テスト  │                               │
│          └──────────┬──────────┘                               │
│                     ▼                                           │
│          ┌────────────────┐                                    │
│          │ #29 ドキュメント│                                    │
│          └────────────────┘                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**重要:**
- #27 と #28 は並列実行**不可**（#28 は #27 が生成する EXIT_CODES に依存）
- #26 は #28 と独立（dag_runner はバリデーション結果を直接使用しない）

---

### 推奨実装順序

#### クリティカルパス（最短経路）

```
#23 → #24 → #25 → #27 → #28 → #31 ─┬─→ #30 → #29
                ↘     ↗            │
                 #26               │
                ↘                  │
                 #32 → #33 ────────┘
```

#### 並列実行可能な Issue

Phase 2（パーサー）完了後、以下は並列実行可能：

- #26（Validator）、#27（codegen）、#32（YAML変換）

Phase 5 で並列実行可能：

- #31（run helper）と #33（migration）

**注意:** #27 と #28 は並列実行**不可**です。
#28 は #27 が生成する `EXIT_CODES` を使用するため。

---

## TDD 戦略

### テストピラミッド

```
        ┌───────────────┐
        │  E2E テスト   │ ← Issue #30
        │   (少数)      │
        ├───────────────┤
        │ 統合テスト    │ ← 各 Issue のフィクスチャ使用テスト
        │   (適度)      │
        ├───────────────┤
        │ 単体テスト    │ ← 各 Issue の純粋関数テスト
        │   (多数)      │
        └───────────────┘
```

### 各 Issue のテスト配置

| Issue | テストファイル | テストタイプ |
|-------|--------------|-------------|
| #23 | - | YAML 構文のみ検証 |
| #24 | `tests/unit/dag/test_node_definition.py` | 単体テスト |
| #25 | `tests/unit/dag/test_parser_exit_nodes.py` | 単体＋統合テスト |
| #26 | `tests/unit/dag/test_validator_exit_nodes.py` | 単体テスト |
| #27 | `tests/unit/dag/test_codegen_exit.py` | 単体テスト |
| #28 | `tests/unit/dag/test_runner_exit.py` | 単体＋統合テスト |
| #29 | - | 手動検証 |
| #30 | `tests/e2e/test_exit_node_workflow.py` | E2E テスト |
| #31 | `tests/unit/dag/test_codegen_run_helper.py` | 単体テスト |
| #32 | `tests/unit/migrations/test_yaml_converter.py` | 単体テスト |
| #33 | `tests/unit/migrations/test_v0_11_to_v0_12_migration.py` | 単体＋統合テスト |

---

## 成功基準

1. **機能要件**
   - 新 YAML 構造がパースできる
   - 終端ノードが実行される
   - 終端ノードの返り値がエントリーポイントの返り値になる

2. **非機能要件**
   - パース性能が劣化しない
   - エラーメッセージが明確

3. **品質要件**
   - テストカバレッジ 90% 以上
   - すべての TDD テストが通過
   - ドキュメントが更新されている

---

## 参考資料

- [ADR-004: Exit ノードの設計と例外処理](../../docs/adr/004_exit_node_design.md)
- [Railway Oriented Programming](https://fsharpforfunandprofit.com/rop/)
- [Convention over Configuration](https://en.wikipedia.org/wiki/Convention_over_configuration)
