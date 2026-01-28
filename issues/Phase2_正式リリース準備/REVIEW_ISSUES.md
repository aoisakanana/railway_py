# ExitContract 実装 自己レビュー Issue一覧

**レビュー日**: 2026-01-28
**対象バージョン**: v0.12.2

---

## Issue #39: async_dag_runner のエラーメッセージ不整合

**重要度**: HIGH
**カテゴリ**: バグ / 一貫性

### 問題

`dag_runner` と `async_dag_runner` で未定義状態エラーのメッセージが異なる。

**dag_runner (runner.py:170)**:
```python
raise UndefinedStateError(
    f"未定義の状態です: {state_string} (ノード: {node_name})"
)
```

**async_dag_runner (runner.py:308)**:
```python
raise UndefinedStateError(f"未定義の状態です: {state_string}")
# ← node_name が欠落
```

### 影響

- 非同期ワークフローのデバッグ時、どのノードでエラーが発生したか分からない
- sync/async 間で一貫性のないエラーメッセージ

### 修正方針

```python
# runner.py:308 を修正
raise UndefinedStateError(
    f"未定義の状態です: {state_string} (ノード: {node_name})"
)
```

### テスト

- 既存テスト `test_strict_mode_raises_error_async` を確認
- エラーメッセージに `node_name` が含まれることを検証

---

## Issue #40: 終端ノード例外伝播のテスト不足

**重要度**: MEDIUM
**カテゴリ**: テストカバレッジ

### 問題

ADR-004 で「終端ノードで発生した例外はそのまま伝播する」と明記されているが、これを検証するテストがない。

**ドキュメント (ADR-004)**:
> 終端ノードで発生した例外はそのまま伝播する。特別な処理は行わない。

### 影響

- 重要な動作仕様がテストで検証されていない
- 将来の変更で意図せず動作が変わる可能性

### 修正方針

`tests/unit/core/dag/test_runner_exit_contract.py` にテスト追加:

```python
def test_exit_node_exception_propagates():
    """終端ノードの例外は呼び出し元に伝播する。"""
    @node(name="exit.success.done")
    def exit_raises(ctx):
        raise RuntimeError("Exit node error")

    @node(name="start")
    def start():
        return {"data": 1}, Outcome.success("done")

    transitions = {
        "start::success::done": exit_raises,
    }

    with pytest.raises(RuntimeError, match="Exit node error"):
        dag_runner(start=start, transitions=transitions)


@pytest.mark.asyncio
async def test_exit_node_exception_propagates_async():
    """非同期終端ノードの例外は呼び出し元に伝播する。"""
    @async_node(name="exit.success.done")
    async def exit_raises(ctx):
        raise RuntimeError("Async exit node error")

    # ... 同様のテスト
```

---

## Issue #41: ADR-005 ステータス更新

**重要度**: LOW
**カテゴリ**: ドキュメント

### 問題

ADR-005 のステータスが「提案中」のままだが、実装は完了している。

**現在 (docs/adr/005_exit_contract_simplification.md:4)**:
```markdown
## ステータス
提案中 (2026-01-28)
```

**あるべき状態**:
```markdown
## ステータス
承認済み (2026-01-28)
```

### 修正方針

ステータスを「承認済み」に変更。

---

## Issue #42: DefaultExitContract.context のドキュメント不足

**重要度**: LOW
**カテゴリ**: ドキュメント

### 問題

`DefaultExitContract.context` フィールドの用途が文書化されていない。

**現在 (exit_contract.py:81)**:
```python
context: Any = None
```

### 影響

- `context` が何を保持するか不明確
- 型が `Any` のため IDE 補完が効かない

### 修正方針

docstring を追加:

```python
class DefaultExitContract(ExitContract):
    """終端ノードが ExitContract を返さない場合のフォールバック。

    Attributes:
        context: 終端ノードの返り値をそのまま保持。
                 ExitContract サブクラスを返さない既存コードとの後方互換のため。
    """
    context: Any = None
```

---

## 優先度サマリー

| Issue | 重要度 | カテゴリ | 工数 |
|-------|--------|----------|------|
| #39 | HIGH | バグ | 小 |
| #40 | MEDIUM | テスト | 中 |
| #41 | LOW | ドキュメント | 小 |
| #42 | LOW | ドキュメント | 小 |

---

## 保留事項（修正不要と判断）

### codegen の `_node_name` アクセス

**理由**: 生成コードでは `generate_node_name_assignments()` により全ノードに `_node_name` が設定される。`run()` ヘルパーは生成コードの `START_NODE` のみを使用するため問題なし。

### transitions 型アノテーション

**理由**: `dict[str, Callable | str]` は正確。string はレガシー exit 形式 (`"exit::green::done"`) のみサポートされ、これは意図通り。

### on_step コールバック検証

**理由**: Python の動的型付けでは呼び出し時エラーで十分。事前検証は過剰。
