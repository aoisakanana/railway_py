# Issue #39: async_dag_runner エラーメッセージ修正

**優先度**: P0
**依存**: なし
**ブロック**: なし
**カテゴリ**: バグ修正

---

## 概要

`async_dag_runner` の未定義状態エラーメッセージに `node_name` が欠落している。`dag_runner` と一貫性を持たせる。

## 問題

**dag_runner (runner.py:170)** - 正しい:
```python
raise UndefinedStateError(
    f"未定義の状態です: {state_string} (ノード: {node_name})"
)
```

**async_dag_runner (runner.py:308)** - node_name が欠落:
```python
raise UndefinedStateError(f"未定義の状態です: {state_string}")
```

## 影響

- 非同期ワークフローのデバッグ時、どのノードでエラーが発生したか分からない
- sync/async 間で一貫性のないエラーメッセージ

## TDD 実装フロー

### Phase 1: Red（失敗するテストを先に作成）

```python
# tests/unit/core/dag/test_runner_async.py

@pytest.mark.asyncio
async def test_strict_mode_error_includes_node_name():
    """strict モードのエラーメッセージにノード名が含まれる。"""
    @async_node(name="start")
    async def start():
        return {}, Outcome.success("undefined_outcome")

    transitions = {}  # 空の遷移テーブル

    with pytest.raises(UndefinedStateError) as exc_info:
        await async_dag_runner(start=start, transitions=transitions)

    error_message = str(exc_info.value)
    assert "start" in error_message  # ノード名が含まれる
    assert "undefined_outcome" in error_message
```

### Phase 2: Green（最小実装）

```python
# railway/core/dag/runner.py:308

# Before:
raise UndefinedStateError(f"未定義の状態です: {state_string}")

# After:
raise UndefinedStateError(
    f"未定義の状態です: {state_string} (ノード: {node_name})"
)
```

### Phase 3: Refactor

既存テスト `test_strict_mode_raises_error_async` を確認し、エラーメッセージの検証を追加。

---

## 修正ファイル

| ファイル | 変更内容 |
|----------|----------|
| `railway/core/dag/runner.py` | 308行目のエラーメッセージ修正 |
| `tests/unit/core/dag/test_runner_async.py` | テスト追加 |

---

## 受け入れ条件

- [ ] エラーメッセージに `node_name` が含まれる
- [ ] `dag_runner` と同じフォーマット
- [ ] テスト追加
- [ ] 全テスト通過

---

*デバッグ体験の改善*
