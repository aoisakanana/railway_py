# 終端ノード型安全化 - 進捗

## 完了

- [x] Issue #39: async_dag_runner エラーメッセージ修正 (2026-01-29)
  - `async_dag_runner` の UndefinedStateError に `node_name` を追加
  - `dag_runner` と同じフォーマットに統一
- [x] Issue #40: 終端ノード例外伝播テスト追加 (2026-01-29)
  - ADR-004 の仕様「終端ノードで発生した例外はそのまま伝播する」を検証
  - sync/async 両方のテストを追加（7テスト）
- [x] Issue #41: ADR-005 ステータス更新 (2026-01-29)
  - 「提案中」→「承認済み」に更新
- [x] Issue #46: DefaultExitContract 削除 (2026-01-29)
  - `ExitNodeTypeError` / `LegacyExitFormatError` エラークラス追加
  - `runner.py` を書き直し: ExitContract 返却を強制
  - `DefaultExitContract` クラス削除
  - 関連テスト更新（287 DAGテスト + 13 E2Eテスト）
- [x] Issue #47: TUTORIAL.md 更新 (2026-01-29)
  - `tests/docs/test_tutorial_examples.py` 追加（8テスト）
  - Step 10 を v0.13.0 ExitContract パターンに更新
  - v0.12.x からの移行手順を追加
  - dag_runner 返り値の説明を追加
  - 全1074テスト通過

## 進行中

なし

## 全Issue完了

## 完了（v0.12.3）

- [x] Issue #45: 終端ノード返り値型チェック (2026-01-29)
  - `TypeCheckResult` イミュータブル dataclass 追加
  - `parse_source()`, `find_function()`, `extract_return_type_name()` 純粋関数追加
  - `is_valid_exit_contract_type_name()`, `check_function_return_type()` 純粋関数追加
  - `check_exit_node_return_type()` エントリポイント（副作用あり）追加

- [x] Issue #44: 終端ノードスケルトン自動生成 (2026-01-29)
  - `_exit_path_to_contract_name()` 純粋関数追加
  - `_exit_path_to_exit_state()` 純粋関数追加
  - `generate_exit_node_skeleton()` 純粋関数追加
  - `SyncResult` イミュータブル dataclass 追加
  - `sync_exit_nodes()` 関数追加（副作用を分離）

## 未着手

### v0.12.3 (非破壊的変更)

- Issue #44: 終端ノードスケルトン自動生成
- Issue #45: 終端ノード返り値型チェック

### v0.13.0 (破壊的変更)

- Issue #46: DefaultExitContract 削除
- Issue #47: TUTORIAL.md 更新

## 実装順序

```
前提Issue (#39, #40, #41)
          ↓
#44 (スケルトン生成)
          ↓
#45 (型チェック警告)
          ↓
#46 (削除・強制) ← v0.13.0
          ↓
#47 (TUTORIAL.md 更新)
```

## 設計原則

### TDD フロー
1. **Red**: 失敗するテストを先に書く
2. **Green**: テストを通す最小限の実装
3. **Refactor**: コードを整理

### 関数型パラダイム
- **純粋関数**: 副作用なし、同じ入力に同じ出力
- **イミュータブル**: `frozen=True` の dataclass
- **副作用の分離**: ファイルI/Oは最小限の関数に分離

### 型安全性
- 終端ノードは `ExitContract` サブクラス（カスタムクラス含む）を返す
- 生成されるスケルトンは `ctx: ExitContract` 型ヒント
- 名前ベース判定は早期フィードバック用、最終チェックは実行時
