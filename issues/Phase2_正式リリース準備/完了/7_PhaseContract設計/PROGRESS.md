# フィールドベース依存関係設計 - 進捗管理

## 設計変更履歴

### レビュー 1: 型ベース → フィールドベースへ変更

**問題:** 型ベース依存関係（Phase Contract）では、型の継承階層がノードの実行順序を固定し、
「YAML のみでワークフロー変更」という目標を達成できない。

**解決:** フィールドベース依存関係を採用。`requires`/`optional`/`provides` でノードの依存を宣言。

### レビュー 2: YAML 依存情報 → ノードコードのみへ変更

**問題:** YAML に依存情報を書くと、YAML 記述者がノードの実装詳細を知る必要がある。

**解決:** 依存情報は **ノードコードのみ** に記述。フレームワークが自動抽出して検証。

## 最終設計

### 関心の分離

| 役割 | 責務 | 知る必要があること |
|------|------|------------------|
| **ノード実装者** | `@node` で依存を宣言 | ノードが必要とするフィールド |
| **YAML 記述者** | 遷移を定義 | **ノード名と Outcome のみ** |
| **フレームワーク** | 依存の自動検証 | 両方を読み取って検証 |

### 実装パターン

```python
# ノードコードで依存を宣言（YAML には書かない）
@node(
    requires=["incident_id"],           # 必須フィールド
    optional=["hostname"],              # オプションフィールド
    provides=["escalated", "notified"], # 追加するフィールド
)
def escalate(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
    if ctx.hostname:  # optional なので存在チェック
        notify_with_host(ctx.hostname)
    return ctx.model_copy(update={"escalated": True}), Outcome.success("done")
```

```yaml
# YAML には遷移のみ（依存情報なし）
nodes:
  check_severity:
    description: "重要度チェック"
  escalate:
    description: "エスカレーション"

transitions:
  check_severity:
    success::critical: escalate  # ← フレームワークが自動検証
```

## ステータス

| # | タイトル | ステータス | 備考 |
|---|----------|-----------|------|
| 50 | ADR-006: フィールドベース依存関係 | ⬜ 未着手 | |
| 51 | FieldDependency 型システム | ⬜ 未着手 | #50 完了後 |
| 52 | Node 依存宣言拡張 | ⬜ 未着手 | #51 完了後 |
| 53 | 依存情報の自動抽出 | ⬜ 未着手 | #52 完了後 |
| 54 | 遷移グラフ依存バリデータ | ⬜ 未着手 | #51, #53 完了後 |
| 55 | Codegen 依存対応 | ⬜ 未着手 | #53 完了後 |
| 56 | Runner 依存チェック | ⬜ 未着手 | #53 完了後 |
| 57 | ドキュメント更新 | ⬜ 未着手 | #50-56 完了後 |
| 58 | マイグレーションツール | ⬜ 未着手 | #50-57 完了後 |

## 依存関係グラフ

```
50 (ADR)
   │
   ▼
51 (FieldDependency 型システム)
   │
   ▼
52 (Node 依存宣言拡張)
   │
   ▼
53 (依存情報の自動抽出)
   │
   ├───────────────┬───────────────┐
   ▼               ▼               ▼
54 (Validator)   55 (Codegen)    56 (Runner)
   │
   ▼
57 (ドキュメント)
   │
   ▼
58 (マイグレーション)
```

## TDD チェックリスト

各 Issue は以下のフローで実装:

1. ⬜ Red: 失敗するテストを作成
2. ⬜ Green: テストを通す最小限の実装
3. ⬜ Refactor: コードを整理

## 関数型パラダイム チェックリスト

- [ ] すべての新規関数が純粋関数
- [ ] すべての新規クラスが `frozen=True` または `@dataclass(frozen=True)`
- [ ] 副作用は最小限の関数に分離
- [ ] `frozenset` / `tuple` を優先（`set` / `list` より）

## 目標達成の検証

### 目標
> 遷移グラフ（YAML）を変更して sync すれば、ノードのコードを変更せずにワークフローを変更できる

### 追加目標
> YAML 記述者がノードの実装詳細を知る必要がない

### 検証シナリオ

| シナリオ | 期待動作 | 検証方法 |
|----------|----------|----------|
| ノード削除（依存あり） | sync でエラー | ユニットテスト |
| ノード削除（依存なし） | YAML 変更のみで OK | E2E テスト |
| ノード順序変更 | 依存が満たされれば OK | E2E テスト |
| optional のみ依存 | 警告のみで sync 成功 | ユニットテスト |

### 検証コード例

```python
# シナリオ: ノード削除
# Before: check_host → escalate
# After: (check_host 削除) → escalate

# escalate は hostname を optional で宣言しているので、
# check_host がなくても sync 成功（警告は出る）
@node(requires=["incident_id"], optional=["hostname"], provides=["escalated"])
def escalate(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
    if ctx.hostname:  # optional なので存在チェック
        notify_with_host(ctx.hostname)
    else:
        notify_without_host()
    return ctx.model_copy(update={"escalated": True}), Outcome.success("done")

# 検証
# 1. YAML から check_host を削除
# 2. `railway sync transition --entry workflow`
# 3. 警告: "escalate の optional フィールド hostname が利用不可"
# 4. sync 成功（requires は満たされている）
```

## 完了条件

- [ ] すべての Issue が完了
- [ ] 全テスト通過
- [ ] **YAML 記述者がノードの依存を知らなくてもワークフロー変更可能**
- [ ] sync 時に依存エラーが分かりやすく報告される
- [ ] ドキュメント更新完了
- [ ] `railway update` でレガシープロジェクトが自動変換される

## 作業ログ

### 2026-01-29
- Issue 作成
- 型ベースから フィールドベースへ設計変更（レビュー 1）
- YAML 依存情報からノードコードのみへ設計変更（レビュー 2）
- Issue #50-58 を改訂版に更新完了

### 2026-01-29（レビュー 3: 初期フィールド自動導出）

**問題:** 初期フィールドの定義方法が曖昧だった

**検討した案:**
- 案A: YAML に `initial_context` セクションを追加 → **却下**（設計原則違反）
- 案B: 開始ノードの Contract から自動導出 → **採用**

**理由:** YAML には遷移のみを記述する設計原則を維持するため

**変更内容:**
- Issue #53: `extract_initial_fields_from_start_node()` を追加
  - 開始ノードの Contract の必須フィールドを初期フィールドとして導出
  - Optional フィールドは初期フィールドに含まれない
- Issue #54: 初期フィールド自動導出を sync コマンドに統合
  - `validate_requires_against_contract()` を追加（requires と Contract の整合性チェック）
- Issue #56: `warn_on_provides_violation` オプションを追加
  - provides 宣言したのに設定しない場合の実行時警告

**設計原則の確認:**

| 原則 | 状態 |
|------|------|
| YAML は遷移のみを記述 | ✅ 維持（initial_context を YAML に書かない） |
| ノードの詳細は YAML に書かない | ✅ 維持 |
| 依存情報はノードコードのみ | ✅ 維持 |
| フレームワークが自動抽出・検証 | ✅ 拡張（初期フィールドも自動導出）|
