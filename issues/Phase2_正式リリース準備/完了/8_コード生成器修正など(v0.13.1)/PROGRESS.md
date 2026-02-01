# v0.13.1 コード生成器修正 進捗管理

## 全体進捗

| Issue | タイトル | 状態 | 担当 |
|-------|----------|------|------|
| #60 | YAMLテンプレート新形式化 | ✅ 完了 | Claude |
| #61 | エントリポイントテンプレート更新 | ✅ 完了 | Claude |
| #62 | 終端ノード自動生成 + バグ修正 | ✅ 完了 | Claude |
| #64 | sync デフォルト化（UX改善） | ✅ 完了 | Claude |
| #65 | ドキュメント更新（readme, TUTORIAL） | ✅ 完了 | Claude |
| #63 | オフラインドキュメント | **スコープ外** | - |

## 依存関係

```
#60 (YAML新形式)
 │
 ├─→ #61 (エントリポイントテンプレート) ─┐
 │                                       │
 └─→ #62 (終端ノード生成) ───────────────┼─→ #64 (sync デフォルト化) ─→ #65 (ドキュメント更新)
                                         │
#63 (オフラインdocs) ────────────────────┘ → v0.13.2 へ移動
```

**実装順序**:
1. **#60** (YAML テンプレート) ← 最優先、他のすべてがこれに依存
2. **#61, #62** (並行実装可能)
3. **#64** (#60, #61, #62 完了後) ← UX 改善のキー
4. **#65** (#64 完了後) ← ドキュメント反映

## 完了条件

### 機能
- [x] `railway new entry greeting && railway run greeting` が正常動作
- [x] 生成されたコードが mypy を通過
- [x] 生成されたコードが ruff を通過

### TDD・関数型
- [x] 全 Issue で Red → Green → Refactor フェーズに従う
- [x] 純粋関数と副作用関数の分離が明確
- [x] 全テスト通過（55 テスト）

### リリース
- [ ] v0.13.1 リリース

---

## Issue 責務分担

| Issue | 責務 | 成果物 |
|-------|------|--------|
| #60 | YAML テンプレートの修正 | `_get_dag_yaml_template()` 更新 |
| #61 | エントリポイントテンプレートの純粋関数 | `_get_dag_entry_template()` 更新、`_get_dag_entry_template_pending_sync()` 新規 |
| #62 | 終端ノードスケルトンの生成 + バグ修正 | `_generate_exit_nodes_from_yaml()` 新規、`_sync_entry()` 修正 |
| #64 | 統合と E2E テスト | `--no-sync` オプション、E2E テスト |
| #65 | ドキュメント更新 | `readme.md` 更新、`_create_tutorial_md()` 更新 |

---

## 詳細ログ

### 2026-02-01 実装サイクル

**Issue #60-#64 実装完了**:

1. **Issue #60: YAML テンプレート新形式化** ✅
   - `_get_dag_yaml_template()` を v0.13.0+ 新形式に更新
   - 11 ユニットテスト作成・通過（`tests/unit/cli/test_dag_yaml_template.py`）
   - 新形式: `nodes.exit`, `exit.success.done` 形式

2. **Issue #61: エントリポイントテンプレート更新** ✅
   - `_get_dag_entry_template()` を `run()` ヘルパー使用形式に更新
   - `_get_dag_entry_template_pending_sync()` を新規追加
   - 13 ユニットテスト作成・通過（`tests/unit/cli/test_dag_entry_template.py`）

3. **Issue #62: 終端ノードスケルトン自動生成** ✅
   - `_generate_exit_nodes_from_yaml()` を新規追加
   - **バグ修正**: `_sync_entry()` で `sync_exit_nodes()` を呼び出すように修正
   - 4 ユニットテスト作成・通過（`tests/unit/cli/test_new_entry_exit_nodes.py`）
   - 4 追加テスト（`tests/unit/cli/test_sync_exit_nodes.py`）

4. **Issue #64: sync デフォルト化（UX改善）** ✅
   - `--no-sync` オプション追加
   - デフォルトで sync が実行される
   - 6 ユニットテスト作成・通過（`tests/unit/cli/test_new_entry_sync.py`）
   - 8 E2E テスト作成・通過（`tests/e2e/test_new_entry_workflow.py`）

5. **Issue #65: ドキュメント更新** ✅
   - `readme.md` クイックスタート更新（1-command ワークフロー）
   - `TUTORIAL.md` テンプレート更新（新形式 YAML）
   - リリースノート作成（`.claude_output/RELEASE_NOTES_v0.13.1.md`）
   - ナレッジ追加（`.claude_output/knowledge/06_code_generator_patterns.md`）

**テスト結果**:
- ユニットテスト: 34 通過（v0.13.1 関連）
- E2E テスト: 8 通過
- 合計: 42 新規テスト通過

---

### 2026-02-01 レビュー

**レビュー サイクル 1**:
- Issue #60-#64 作成
- 依存関係の誤り修正（#62 は #60 のみに依存）
- UX 改善のため #64 を新規追加
- E2E テストを受け入れ条件に追加

**レビュー サイクル 2**:
- #61 の責務を明確化（純粋関数の提供に集中）
- `_get_dag_entry_template_pending_sync()` を追加
- テストの重複を整理（#61: 単体、#64: 統合）
- #63 を v0.13.1 スコープ外に移動

**レビュー サイクル 3（完了）**:

改善内容:
1. **既存コードとの整合性確保**
   - `_get_dag_yaml_template()` を更新（新関数 `generate_entry_yaml()` ではなく）
   - `_get_dag_entry_template()` を更新
   - 既存の `sync_exit_nodes()` を再利用

2. **テストのimportパス修正**
   - `railway.cli.new` から直接関数をimport
   - 存在しないモジュールパスを修正

3. **デフォルト動作の変更**
   - `--sync` をデフォルトに
   - `--no-sync` をオプトアウトに
   - 理由: 新規プロジェクトなので後方互換性の考慮は不要

4. **E2E テストの並列安全性確保**
   - `os.chdir()` の代わりに `subprocess.run(cwd=...)` を使用

5. **関数型パラダイムの強化**
   - `_get_package_directories()` を純粋関数として分離
   - 純粋関数と副作用関数の明確な分離を文書化

6. **#63 をスコープ外に**
   - コード生成と無関係のため v0.13.2 へ移動

7. **バグ修正: `railway sync transition` での終端ノード生成**
   - `sync_exit_nodes()` は存在するが `_sync_entry()` 内で呼び出されていなかった
   - Issue #62 に修正内容を追記
   - sync と new entry の両方で終端ノード生成が動作するように

---

## 変更サマリー

### v0.13.1 で変更されるファイル

| ファイル | 変更内容 |
|----------|----------|
| `railway/cli/new.py` | YAML/エントリポイントテンプレート更新、終端ノード生成、`--no-sync` オプション |
| `railway/cli/sync.py` | `_sync_entry()` で `sync_exit_nodes()` を呼び出す（**バグ修正**） |
| `railway/cli/init.py` | `_create_tutorial_md()` 更新 |
| `readme.md` | クイックスタート更新、YAML サンプル更新 |
| `tests/unit/cli/test_dag_yaml_template.py` | 新規 |
| `tests/unit/cli/test_dag_entry_template.py` | 新規 |
| `tests/unit/cli/test_new_entry_exit_nodes.py` | 新規 |
| `tests/unit/cli/test_sync_exit_nodes.py` | 新規（sync時の終端ノード生成テスト） |
| `tests/unit/cli/test_new_entry_sync.py` | 新規 |
| `tests/unit/cli/test_tutorial_template.py` | 新規 |
| `tests/e2e/test_new_entry_workflow.py` | 新規 |

### ユーザー影響

| 変更 | 影響 |
|------|------|
| YAML テンプレート新形式 | 新規プロジェクトのみ、既存プロジェクトに影響なし |
| sync デフォルト化 | `railway new entry` 後すぐに `railway run` 可能 |
| `--no-sync` オプション | 上級者向けにカスタマイズの余地を残す |
