# Issue #40: 終端ノード例外伝播テスト追加

**優先度**: P1
**依存**: なし
**ブロック**: なし
**カテゴリ**: テストカバレッジ

---

## 概要

ADR-004 で明記された「終端ノードで発生した例外はそのまま伝播する」動作を検証するテストを追加する。

## 背景

**ADR-004 より**:
> 終端ノードで発生した例外はそのまま伝播する。特別な処理は行わない。

この重要な動作仕様がテストで検証されていない。

## TDD 実装フロー

### Phase 1: Red（失敗するテストを先に作成）

```python
# tests/unit/core/dag/test_runner_exit_contract.py

import pytest
from railway import ExitContract, node
from railway.core.dag import dag_runner, async_dag_runner, Outcome


class ExitNodeExceptionTest(ExitContract):
    """テスト用 ExitContract。"""
    exit_state: str = "success.done"


class TestExitNodeExceptionPropagation:
    """終端ノード例外伝播のテスト。"""

    def test_exit_node_exception_propagates(self) -> None:
        """終端ノードの例外は呼び出し元に伝播する。"""
        @node(name="exit.success.done")
        def exit_raises(ctx) -> ExitNodeExceptionTest:
            raise RuntimeError("Exit node error")

        @node(name="start")
        def start():
            return {"data": 1}, Outcome.success("done")

        transitions = {
            "start::success::done": exit_raises,
        }

        with pytest.raises(RuntimeError, match="Exit node error"):
            dag_runner(start=start, transitions=transitions)

    def test_exit_node_value_error_propagates(self) -> None:
        """終端ノードの ValueError も伝播する。"""
        @node(name="exit.failure.error")
        def exit_raises_value_error(ctx) -> ExitNodeExceptionTest:
            raise ValueError("Invalid value in exit node")

        @node(name="start")
        def start():
            return {}, Outcome.failure("error")

        transitions = {
            "start::failure::error": exit_raises_value_error,
        }

        with pytest.raises(ValueError, match="Invalid value in exit node"):
            dag_runner(start=start, transitions=transitions)


@pytest.mark.asyncio
class TestExitNodeExceptionPropagationAsync:
    """非同期終端ノード例外伝播のテスト。"""

    async def test_async_exit_node_exception_propagates(self) -> None:
        """非同期終端ノードの例外は呼び出し元に伝播する。"""
        @node(name="exit.success.done")
        async def exit_raises(ctx) -> ExitNodeExceptionTest:
            raise RuntimeError("Async exit node error")

        @node(name="start")
        async def start():
            return {"data": 1}, Outcome.success("done")

        transitions = {
            "start::success::done": exit_raises,
        }

        with pytest.raises(RuntimeError, match="Async exit node error"):
            await async_dag_runner(start=start, transitions=transitions)
```

### Phase 2: Green

テストが既存の実装で通過することを確認。

（現在の実装では例外は伝播するはずなので、テストは Green になる想定）

### Phase 3: Refactor

- テストの構造化
- より多くの例外タイプのカバー（オプション）

---

## 修正ファイル

| ファイル | 変更内容 |
|----------|----------|
| `tests/unit/core/dag/test_runner_exit_contract.py` | テスト追加 |

---

## 受け入れ条件

- [ ] sync 版のテスト追加
- [ ] async 版のテスト追加
- [ ] テストが ADR-004 の仕様を検証している
- [ ] 全テスト通過

---

*仕様のテストによる保護*
