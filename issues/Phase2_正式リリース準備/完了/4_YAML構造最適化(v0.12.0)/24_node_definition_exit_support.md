# Issue #24: NodeDefinition の終端ノード対応

**Phase:** 2
**優先度:** 高
**依存関係:** Issue #23（テスト用フィクスチャ）
**見積もり:** 0.25日

---

## 概要

`NodeDefinition` データクラスに終端ノード用のフィールドを追加する。
これは後続の Issue（パーサー、codegen、dag_runner）の基盤となる。

---

## 現状

```python
@dataclass(frozen=True)
class NodeDefinition:
    """ノード定義。"""
    name: str
    module: str
    function: str
    description: str
```

---

## 変更後

```python
@dataclass(frozen=True)
class NodeDefinition:
    """ノード定義（終端ノード対応）。

    Attributes:
        name: ノード識別子（例: "start", "exit.success.done"）
        module: Python モジュールパス（例: "nodes.start"）
        function: 関数名（例: "start"）
        description: 説明文
        is_exit: 終端ノードか否か
        exit_code: 終了コード（終端ノードのみ、None は未設定）
    """

    name: str
    module: str
    function: str
    description: str
    is_exit: bool = False
    exit_code: int | None = None

    # Note: __post_init__ でのデフォルト設定は行わない
    # exit_code はパーサー（Issue #25）で正しく設定される:
    # - exit.success.* → 0
    # - exit.failure.* → 1
    # - カスタム指定 → その値

    @property
    def has_handler(self) -> bool:
        """実行可能なハンドラ関数を持つか。

        module と function の両方が設定されていれば True。
        終端ノードでもハンドラを持てる（終了時処理を実行）。
        """
        return bool(self.module and self.function)
```

---

## TDD 実装手順

### Step 1: テスト作成（Red）

```python
# tests/unit/dag/test_node_definition.py
"""Tests for NodeDefinition exit node support."""

import pytest
from railway.core.dag.types import NodeDefinition


class TestNodeDefinitionExitSupport:
    """NodeDefinition の終端ノード対応テスト。"""

    def test_default_is_not_exit(self) -> None:
        """デフォルトは終端ノードではない。"""
        node = NodeDefinition(
            name="start",
            module="nodes.start",
            function="start",
            description="開始",
        )
        assert node.is_exit is False
        assert node.exit_code is None

    def test_exit_node_with_explicit_code(self) -> None:
        """終端ノードは明示的な exit_code を持てる。"""
        node = NodeDefinition(
            name="exit.success.done",
            module="nodes.exit.success.done",
            function="done",
            description="正常終了",
            is_exit=True,
            exit_code=0,
        )
        assert node.is_exit is True
        assert node.exit_code == 0

    def test_exit_node_code_from_parser(self) -> None:
        """終端ノードの exit_code はパーサーで設定される。

        Note:
            NodeDefinition 単体では exit_code のデフォルト設定を行わない。
            パーサー（Issue #25）が exit.success.* → 0, exit.failure.* → 1 を設定する。
        """
        # パーサーが設定した値がそのまま保持される
        node = NodeDefinition(
            name="exit.failure.error",
            module="nodes.exit.failure.error",
            function="error",
            description="異常終了",
            is_exit=True,
            exit_code=1,  # パーサーが設定
        )
        assert node.is_exit is True
        assert node.exit_code == 1

    def test_has_handler_with_module_and_function(self) -> None:
        """module と function があればハンドラを持つ。"""
        node = NodeDefinition(
            name="start",
            module="nodes.start",
            function="start",
            description="開始",
        )
        assert node.has_handler is True

    def test_has_handler_without_module(self) -> None:
        """module が空ならハンドラを持たない。"""
        node = NodeDefinition(
            name="exit.success.done",
            module="",
            function="done",
            description="終端",
            is_exit=True,
            exit_code=0,
        )
        assert node.has_handler is False

    def test_has_handler_without_function(self) -> None:
        """function が空ならハンドラを持たない。"""
        node = NodeDefinition(
            name="exit.success.done",
            module="nodes.exit.success.done",
            function="",
            description="終端",
            is_exit=True,
            exit_code=0,
        )
        assert node.has_handler is False

    def test_exit_node_can_have_handler(self) -> None:
        """終端ノードもハンドラを持てる。"""
        node = NodeDefinition(
            name="exit.success.done",
            module="nodes.exit.success.done",
            function="done",
            description="正常終了（Slack通知）",
            is_exit=True,
            exit_code=0,
        )
        assert node.is_exit is True
        assert node.has_handler is True

    def test_immutable(self) -> None:
        """frozen=True で不変。"""
        node = NodeDefinition(
            name="start",
            module="nodes.start",
            function="start",
            description="開始",
        )
        with pytest.raises(AttributeError):
            node.name = "changed"  # type: ignore

    def test_hashable(self) -> None:
        """frozen=True で hashable。"""
        node1 = NodeDefinition(
            name="start",
            module="nodes.start",
            function="start",
            description="開始",
        )
        node2 = NodeDefinition(
            name="start",
            module="nodes.start",
            function="start",
            description="開始",
        )
        # 同じ内容なら同じハッシュ
        assert hash(node1) == hash(node2)
        # set に追加可能
        nodes = {node1, node2}
        assert len(nodes) == 1
```

### Step 2: 実装（Green）

`railway/core/dag/types.py` を更新。

### Step 3: リファクタリング

既存コードへの影響を確認し、必要に応じて調整。

---

## 完了条件

- [ ] `is_exit` フィールド追加
- [ ] `exit_code` フィールド追加（パーサーで設定、デフォルト設定不要）
- [ ] `has_handler` プロパティ追加
- [ ] frozen=True 維持（イミュータブル）
- [ ] 既存テスト通過
- [ ] 新規テスト通過（TDD: Red → Green → Refactor）

---

## 関連 Issue

- Issue #23: テスト用 YAML フィクスチャ（前提）
- Issue #25: パーサーのネスト構造対応（自動解決含む）
- Issue #27: codegen の終端ノード対応
- ADR-004: Exit ノードの設計と例外処理
