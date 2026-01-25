# Phase 2 正式リリース準備 - 進捗管理

## 概要

Phase 2 の正式リリース準備タスクの進捗を記録します。

---

## 完了したIssue

### Issue #21: railway new node テンプレートの最新化 ✅

**完了日:** 2026-01-26

**実装内容:**
- `NodeMode` Enum 追加（dag/linear）
- dag形式ノードテンプレート（`tuple[Contract, Outcome]` を返す）
- linear形式ノードテンプレート（Input/Output Contract）
- Context Contract 自動生成
- テストテンプレート（TDDワークフロー対応）
- イミュータブル更新パターン（`model_copy()`）の例示
- `--mode` オプションのバリデーション追加
- 後方互換性維持（`--output` / `--input` オプション）

**テスト結果:**
- `tests/unit/cli/test_new_node_template.py`: 21テスト全て通過

**修正ファイル:**
- `railway/cli/new.py`
- `tests/unit/cli/test_new_node_template.py` (新規)

---

### Issue #22: railway new node コマンドのドキュメント追加 ✅

**完了日:** 2026-01-26

**実装内容:**

#### README.md
- 「ノードの作成」セクション追加
- 手動作成との比較表（恩恵の明示）
- dag/linear モードの使い分けガイド
- 両モードのコード例
- 使い分けガイド表

#### TUTORIAL.md (railway/cli/init.py)
- Step 5「railway new node でノードを素早く追加」追加
- 3ファイル同時生成の恩恵説明
- TDD Red-Green サイクルの体験手順
- linear モードの参照情報
- Step番号の再調整（Step 5-8）

**テスト結果:**
- `tests/unit/docs/test_readme_new_node_section.py`: 10テスト全て通過
- `tests/unit/docs/test_tutorial_new_node_section.py`: 6テスト全て通過

**修正ファイル:**
- `readme.md`
- `railway/cli/init.py`
- `tests/unit/docs/test_readme_new_node_section.py` (新規)
- `tests/unit/docs/test_tutorial_new_node_section.py` (新規)

---

## 全体テスト結果

```
============================= 822 passed in 20.78s =============================
```

全822テストが通過。リグレッションなし。

---

## 次のアクション

- [ ] バージョン番号の更新検討
- [ ] 変更内容のgit commit
- [ ] PyPIへのリリース準備

---

## 技術的な決定事項

### 関数型パラダイム適用

| 原則 | 適用箇所 |
|------|----------|
| 純粋関数 | テンプレート生成関数（引数 → 文字列） |
| 副作用の局所化 | `_write_file`, `_create_single_contract` に集約 |
| イミュータブル | 生成されるノードで `model_copy()` 推奨 |

### TDD実践

1. **Red**: テストを先に作成（期待動作を定義）
2. **Green**: 最小限の実装でテストを通す
3. **Refactor**: コードの整理・最適化

---

## 変更履歴

| 日付 | Issue | 内容 |
|------|-------|------|
| 2026-01-26 | #21 | railway new node テンプレート最新化 |
| 2026-01-26 | #22 | ドキュメント追加（README.md, TUTORIAL.md） |
