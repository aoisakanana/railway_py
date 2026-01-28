# ExitContract 設計 - 進捗

## 完了

### Issue #34: executor の YamlTransform 適用 ✅
- **完了日**: 2026-01-28
- **変更内容**:
  - `apply_yaml_transform()` 関数を追加
  - `apply_migration()` が `yaml_transforms` を適用するよう修正
- **テスト**: 5 テストケース追加（すべてパス）

### Issue #35: ExitContract 基底クラス追加 ✅
- **完了日**: 2026-01-28
- **変更内容**:
  - `railway/core/exit_contract.py` 作成
  - `ExitContract` 基底クラス（exit_code 自動導出）
  - `DefaultExitContract` フォールバッククラス
  - `railway` パッケージからエクスポート
- **テスト**: 16 テストケース追加（すべてパス）

### Issue #36: dag_runner・codegen の ExitContract 対応 ✅
- **完了日**: 2026-01-28
- **変更内容**:
  - `dag_runner()` が `ExitContract` を返すよう変更
  - `Exit` クラスと `DagRunnerResult` クラス削除
  - `exit_codes` パラメータ削除
  - レガシー `exit::...` 形式の後方互換対応
  - `_is_exit_node()` / `_derive_exit_state()` 純粋関数追加
  - テスト更新（runner, callbacks, E2E）
- **テスト**: 237 テストケース全てパス

### Issue #37: 不要コード削除 ✅
- **完了日**: 2026-01-28
- **変更内容**:
  - `state.py`: `ExitOutcome`, `make_state`, `make_exit`, `parse_state`, `parse_exit` 削除
  - `outcome.py`: `map_to_state`, `is_outcome` 削除
  - `codegen.py`: `DagRunnerResult`, `Exit` 依存を除去、`ExitContract` 対応
  - `__init__.py`: 削除した関数のエクスポートを除去
  - テスト更新: 削除対象のテストを削除
- **テスト**: 983 テストケース全てパス

### Issue #38: リリース準備 ✅
- **完了日**: 2026-01-28
- **変更内容**:
  - `readme.md`: ExitContract API の使用例を追加
  - `railway/cli/init.py`: TUTORIAL テンプレートを ExitContract 対応に更新
  - `railway/migrations/definitions/v0_12_1_to_v0_12_2.py`: マイグレーション定義作成
  - `railway/migrations/definitions/__init__.py`: 新マイグレーションをエクスポート
  - `docs/adr/005_exit_contract_simplification.md`: ADR-005 確認済み
- **テスト**: 983 テストケース全てパス

## 進行中

（なし）

## 未着手

（なし）
