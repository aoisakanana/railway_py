# Issue #37: 不要コード削除

**優先度**: P1
**依存**: #36
**ブロック**: #38

---

## 概要

ExitContract 対応後に不要となったクラス・関数・属性を削除する。

## 削除対象

> **Note**: `Exit` クラス、`DagRunnerResult` クラスは #36 で削除済み。

### 1. state.py

| 対象 | 理由 |
|------|------|
| `ExitOutcome` クラス | 未使用 |
| `make_state()` | `Outcome.to_state_string()` で代替 |
| `make_exit()` | 未使用 |
| `parse_state()` | テストでのみ使用 |
| `parse_exit()` | テストでのみ使用 |

### 2. outcome.py

| 対象 | 理由 |
|------|------|
| `map_to_state()` | テストでのみ使用 |
| `is_outcome()` | 未使用 |

### 3. types.py

| 対象 | 理由 |
|------|------|
| `NodeDefinition.exit_code` 属性 | `ExitContract` で定義 |

### 4. parser.py

| 対象 | 理由 |
|------|------|
| `exit_code` パース処理 | 不要 |

### 5. type_check.py

| 対象 | 理由 |
|------|------|
| `get_function_output_type()` | 未使用 |

### 6. __init__.py エクスポート

| 対象 | 変更 | ファイル |
|------|------|----------|
| `validate_contract` | 削除（internal に） | `railway/__init__.py` |
| `make_state`, `make_exit`, `parse_state`, `parse_exit` | 削除 | `railway/core/dag/__init__.py` |
| `map_to_state`, `is_outcome` | 削除 | `railway/core/dag/__init__.py` |
| `ExitOutcome` | 削除 | `railway/core/dag/__init__.py` |

> **Note**: `Exit`, `DagRunnerResult` のエクスポート削除は #36 で実施済み。

## 実装手順

> **Note**: 削除タスクは TDD の「Red」フェーズがない。代わりに以下の手順で安全に削除する。

### Phase 1: 影響調査（Green を維持）

各削除対象について `grep` で使用箇所を確認:

```bash
# 例: make_state の使用箇所を確認
grep -r "make_state" railway/ tests/
```

### Phase 2: テスト削除/更新

削除対象をテストしているテストを特定し削除:

```python
# 削除するテストの例
class TestMakeState:  # 削除
    ...

class TestParseState:  # 削除
    ...
```

### Phase 3: コード削除

使用箇所がないことを確認後、対象コードを削除:

```python
# state.py から削除
def make_state(...): ...  # 削除
def make_exit(...): ...   # 削除
```

### Phase 4: エクスポート更新

`__init__.py` からエクスポートを削除。

### Phase 5: 回帰テスト

```bash
pytest tests/ -v
```

全テストがパスすることを確認。

## 受け入れ条件

> **Note**: `Exit`, `DagRunnerResult` は #36 で削除済み。

### state.py
- [ ] `ExitOutcome` が削除されている
- [ ] `make_state`, `make_exit`, `parse_state`, `parse_exit` が削除されている

### outcome.py
- [ ] `map_to_state`, `is_outcome` が削除されている

### type_check.py
- [ ] `get_function_output_type` が削除されている

### types.py / parser.py
- [ ] `NodeDefinition.exit_code` が削除されている
- [ ] parser の `exit_code` パース処理が削除されている

### エクスポート
- [ ] `validate_contract` が `railway/__init__.py` から削除
- [ ] 上記の削除対象が `__init__.py` から削除

### テスト
- [ ] 全テストがパス

---

*クリーンアップ・不要コードの除去*
