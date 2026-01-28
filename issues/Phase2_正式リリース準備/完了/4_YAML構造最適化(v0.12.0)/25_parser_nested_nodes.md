# Issue #25: パーサーのネスト構造対応（自動解決含む）

**Phase:** 2
**優先度:** 高
**依存関係:** Issue #23（フィクスチャ）, Issue #24（NodeDefinition）
**見積もり:** 0.5日

---

## 概要

YAML パーサーを更新し、`nodes` セクションのネスト構造を再帰的にパースする。
同時に `module` と `function` の自動解決も実装する（密結合のため分離不可）。

**設計原則:**
- 各関数は純粋関数（副作用なし、同じ入力に同じ出力）
- エラーは例外ではなく Result 型で表現（可能な限り）
- イミュータブルなデータ構造を使用

---

## 機能要件

### 1. ネスト構造の再帰的パース

```yaml
nodes:
  exit:
    success:
      done:
        description: "正常終了"
```

↓ パース結果

```python
NodeDefinition(
    name="exit.success.done",
    module="nodes.exit.success.done",  # 自動解決
    function="done",                    # 自動解決
    is_exit=True,
    exit_code=0,
)
```

### 2. 葉ノードの判定（明確なルール）

葉ノードは以下のいずれかの条件を満たす：

| 優先度 | 条件 | 判定 |
|--------|------|------|
| 1 | 値が `None` または空 dict `{}` | 葉ノード |
| 2 | 値が dict でない | 葉ノード |
| 3 | 予約キーのみを含む | 葉ノード |

**予約キー:** `description`, `module`, `function`, `exit_code`

**重要:** 予約キー以外のキーがあれば、それは子ノードとみなす。

```yaml
# ケース1: 葉ノード（予約キーのみ）
done:
  description: "正常終了"
  module: custom.module

# ケース2: 中間ノード（子ノードあり）
success:
  done:       # ← 予約キーではない = 子ノード
    description: "正常終了"
  skipped:    # ← 予約キーではない = 子ノード
    description: "スキップ"
```

### 3. module/function 自動解決

| YAML パス | module（自動） | function（自動） |
|----------|----------------|------------------|
| `nodes.start` | `nodes.start` | `start` |
| `nodes.exit.success.done` | `nodes.exit.success.done` | `done` |

**明示的な指定は常に優先される。**

### 4. 終端ノードの判定と終了コード

- `nodes.exit.` で始まるパス = 終端ノード
- `exit.success.*` → exit_code=0
- `exit.failure.*` → exit_code=1
- その他（exit.warning.* など）→ exit_code=1（デフォルト）
- カスタム指定は `exit_code` フィールドで上書き

---

## 実装（純粋関数）

```python
"""Parser functions for nested nodes structure."""

from collections.abc import Iterator, Sequence
from typing import Any

from railway.core.dag.types import NodeDefinition

# 葉ノードを示す予約キー
_LEAF_KEYS: frozenset[str] = frozenset({
    "description",
    "module",
    "function",
    "exit_code",
})


def parse_nodes(data: dict[str, Any]) -> Sequence[NodeDefinition]:
    """nodes セクションをパースする（純粋関数）。

    Args:
        data: YAML の nodes セクション

    Returns:
        パースされた NodeDefinition のシーケンス（不変）

    Example:
        >>> nodes_data = {"start": {"description": "開始"}}
        >>> result = parse_nodes(nodes_data)
        >>> result[0].name
        'start'
    """
    return tuple(_parse_nodes_recursive(data, "nodes"))


def _parse_nodes_recursive(
    data: dict[str, Any],
    path_prefix: str,
) -> Iterator[NodeDefinition]:
    """ノード定義を再帰的にパースする（ジェネレータ）。

    遅延評価により、メモリ効率が良い。
    tuple() で収集することで不変シーケンスになる。
    """
    for key, value in data.items():
        current_path = f"{path_prefix}.{key}"

        if _is_leaf_node(value):
            yield _parse_leaf_node(key, value, current_path)
        else:
            # 中間ノード（再帰）
            yield from _parse_nodes_recursive(value, current_path)


def _is_leaf_node(value: dict[str, Any] | None) -> bool:
    """葉ノードかどうか判定する（純粋関数）。

    葉ノードの条件:
    1. None または空 dict
    2. dict でない
    3. 予約キーのみを含む（子ノードがない）

    Args:
        value: ノードの値

    Returns:
        葉ノードなら True
    """
    if value is None:
        return True
    if not isinstance(value, dict):
        return True
    if len(value) == 0:
        return True

    # 予約キー以外のキーがあれば中間ノード
    non_reserved_keys = set(value.keys()) - _LEAF_KEYS
    return len(non_reserved_keys) == 0


def _parse_leaf_node(
    key: str,
    data: dict[str, Any] | None,
    yaml_path: str,
) -> NodeDefinition:
    """葉ノードをパースする（純粋関数）。

    自動解決:
    - module: 明示指定 or yaml_path
    - function: 明示指定 or key
    """
    data = data or {}

    # 自動解決（明示指定があればそれを優先）
    module = data.get("module") or yaml_path
    function = data.get("function") or key

    # 終端判定（nodes.exit. で始まるパス）
    is_exit = yaml_path.startswith("nodes.exit.")

    # 終了コード
    exit_code = _resolve_exit_code(yaml_path, data) if is_exit else None

    return NodeDefinition(
        name=yaml_path.removeprefix("nodes."),
        module=module,
        function=function,
        description=data.get("description", ""),
        is_exit=is_exit,
        exit_code=exit_code,
    )


def _resolve_exit_code(yaml_path: str, data: dict[str, Any]) -> int:
    """終了コードを解決する（純粋関数）。

    優先順位:
    1. 明示的な exit_code 指定
    2. exit.success.* → 0
    3. それ以外 → 1
    """
    if "exit_code" in data:
        return data["exit_code"]
    if ".success." in yaml_path:
        return 0
    return 1  # failure, warning, その他はデフォルト 1
```

---

## TDD 実装手順

### テストファイル構成

```
tests/unit/dag/
└── test_parser_exit_nodes.py    # すべての exit node パーサーテスト
```

**Note:** ファイルを分散させず、1ファイルにまとめて凝集度を高める。

### Step 1: パブリック API 経由でテスト（Red）

```python
# tests/unit/dag/test_parser_exit_nodes.py
"""Tests for exit node parsing (pure functions).

Note:
    TDD のベストプラクティスに従い、パブリック API (parse_nodes) 経由でテスト。
    内部関数 (_is_leaf_node, _parse_leaf_node) は実装詳細として隠蔽。
"""

import pytest
from railway.core.dag.parser import parse_nodes
from railway.core.dag.types import NodeDefinition


class TestAutoResolve:
    """自動解決のテスト（parse_nodes 経由）。"""

    def test_auto_resolve_from_path(self) -> None:
        """パスから module/function を自動解決。"""
        nodes_data = {"start": {"description": "開始"}}
        result = parse_nodes(nodes_data)

        assert len(result) == 1
        assert result[0].module == "nodes.start"
        assert result[0].function == "start"
        assert result[0].name == "start"

    def test_explicit_module_override(self) -> None:
        """明示的な module 指定は自動解決より優先。"""
        nodes_data = {
            "check": {"module": "custom.module", "description": "カスタム"}
        }
        result = parse_nodes(nodes_data)

        assert result[0].module == "custom.module"
        assert result[0].function == "check"  # 自動解決

    def test_explicit_function_override(self) -> None:
        """明示的な function 指定は自動解決より優先。"""
        nodes_data = {
            "check": {"function": "custom_func", "description": "カスタム"}
        }
        result = parse_nodes(nodes_data)

        assert result[0].module == "nodes.check"  # 自動解決
        assert result[0].function == "custom_func"

    def test_both_explicit(self) -> None:
        """module と function 両方明示。"""
        nodes_data = {
            "check": {
                "module": "custom.module",
                "function": "custom_func",
                "description": "カスタム",
            }
        }
        result = parse_nodes(nodes_data)

        assert result[0].module == "custom.module"
        assert result[0].function == "custom_func"


class TestExitCodeResolve:
    """終了コード解決のテスト（parse_nodes 経由）。"""

    def test_success_exit_code_zero(self) -> None:
        """exit.success.* は exit_code=0。"""
        nodes_data = {
            "exit": {"success": {"done": {"description": "正常終了"}}}
        }
        result = parse_nodes(nodes_data)

        exit_done = result[0]
        assert exit_done.name == "exit.success.done"
        assert exit_done.is_exit is True
        assert exit_done.exit_code == 0

    def test_failure_exit_code_one(self) -> None:
        """exit.failure.* は exit_code=1。"""
        nodes_data = {
            "exit": {"failure": {"error": {"description": "異常終了"}}}
        }
        result = parse_nodes(nodes_data)

        exit_error = result[0]
        assert exit_error.is_exit is True
        assert exit_error.exit_code == 1

    def test_warning_exit_code_default_one(self) -> None:
        """exit.warning.* は exit_code=1（デフォルト）。"""
        nodes_data = {
            "exit": {"warning": {"low_disk": {"description": "警告"}}}
        }
        result = parse_nodes(nodes_data)

        assert result[0].is_exit is True
        assert result[0].exit_code == 1

    def test_explicit_exit_code_override(self) -> None:
        """明示的な exit_code は自動解決より優先。"""
        nodes_data = {
            "exit": {"warning": {"low_disk": {"description": "警告", "exit_code": 2}}}
        }
        result = parse_nodes(nodes_data)

        assert result[0].exit_code == 2

    def test_non_exit_node_no_exit_code(self) -> None:
        """通常ノードは exit_code=None。"""
        nodes_data = {"start": {"description": "開始"}}
        result = parse_nodes(nodes_data)

        assert result[0].is_exit is False
        assert result[0].exit_code is None


class TestLeafNodeDetection:
    """葉ノード判定のテスト（parse_nodes の振る舞いで検証）。"""

    def test_empty_value_is_leaf(self) -> None:
        """None または空 dict は葉ノード。"""
        nodes_data = {"exit": {"success": {"done": None}}}
        result = parse_nodes(nodes_data)

        assert len(result) == 1
        assert result[0].name == "exit.success.done"

    def test_reserved_keys_only_is_leaf(self) -> None:
        """予約キーのみを含む dict は葉ノード。"""
        nodes_data = {
            "check": {
                "description": "説明",
                "module": "m",
                "function": "f",
                "exit_code": 0,
            }
        }
        result = parse_nodes(nodes_data)

        assert len(result) == 1
        assert result[0].name == "check"

    def test_non_reserved_key_is_intermediate(self) -> None:
        """予約キー以外があれば中間ノード。"""
        nodes_data = {
            "exit": {
                "success": {"done": {"description": "終了"}},
                "failure": {"error": {"description": "失敗"}},
            }
        }
        result = parse_nodes(nodes_data)

        # exit は中間ノード、done と error が葉ノード
        assert len(result) == 2
        names = {n.name for n in result}
        assert "exit.success.done" in names
        assert "exit.failure.error" in names


class TestNestedNodesParsing:
    """ネスト構造パーステスト。"""

    def test_parse_flat_nodes(self) -> None:
        """フラットなノード構造。"""
        nodes_data = {
            "start": {"description": "開始"},
            "process": {"description": "処理"},
        }

        result = parse_nodes(nodes_data)

        assert len(result) == 2
        assert result[0].name == "start"
        assert result[1].name == "process"

    def test_parse_nested_exit_nodes(self) -> None:
        """ネストした終端ノード構造。"""
        nodes_data = {
            "exit": {
                "success": {
                    "done": {"description": "正常終了"},
                },
                "failure": {
                    "error": {"description": "異常終了"},
                },
            },
        }

        result = parse_nodes(nodes_data)

        assert len(result) == 2
        names = {n.name for n in result}
        assert "exit.success.done" in names
        assert "exit.failure.error" in names

    def test_parse_deep_nested_exit_nodes(self) -> None:
        """深いネストの終端ノード。"""
        nodes_data = {
            "exit": {
                "failure": {
                    "ssh": {
                        "handshake": {"description": "ハンドシェイク失敗"},
                    },
                },
            },
        }

        result = parse_nodes(nodes_data)

        assert len(result) == 1
        assert result[0].name == "exit.failure.ssh.handshake"
        assert result[0].module == "nodes.exit.failure.ssh.handshake"
        assert result[0].function == "handshake"

    def test_parse_mixed_flat_and_nested(self) -> None:
        """フラットとネストの混在。"""
        nodes_data = {
            "start": {"description": "開始"},
            "exit": {
                "success": {
                    "done": {"description": "正常終了"},
                },
            },
        }

        result = parse_nodes(nodes_data)

        assert len(result) == 2
        names = {n.name for n in result}
        assert "start" in names
        assert "exit.success.done" in names

    def test_empty_leaf_node(self) -> None:
        """空の葉ノード（description なし）。"""
        nodes_data = {
            "exit": {
                "success": {
                    "done": None,  # 空
                },
            },
        }

        result = parse_nodes(nodes_data)

        assert len(result) == 1
        assert result[0].name == "exit.success.done"
        assert result[0].description == ""


class TestParserWithFixtures:
    """フィクスチャを使用した統合テスト。"""

    def test_parse_basic_exit_fixture(self, exit_node_fixtures) -> None:
        """basic_exit.yml をパース。"""
        from railway.core.dag.parser import load_transition_graph

        yaml_path = exit_node_fixtures / "basic_exit.yml"
        graph = load_transition_graph(yaml_path)

        exit_done = next(
            (n for n in graph.nodes if n.name == "exit.success.done"),
            None,
        )
        assert exit_done is not None
        assert exit_done.is_exit is True
        assert exit_done.exit_code == 0

    def test_parse_auto_resolve_fixture(self, exit_node_fixtures) -> None:
        """auto_resolve.yml をパース。"""
        from railway.core.dag.parser import load_transition_graph

        yaml_path = exit_node_fixtures / "auto_resolve.yml"
        graph = load_transition_graph(yaml_path)

        start = next(
            (n for n in graph.nodes if n.name == "start_process"),
            None,
        )
        assert start is not None
        assert start.module == "nodes.start_process"
        assert start.function == "start_process"
```

---

## 完了条件

- [ ] 葉ノード判定関数 `_is_leaf_node`（純粋関数）
- [ ] ネスト構造の再帰的パース `_parse_nodes_recursive`
- [ ] module/function 自動解決
- [ ] 終端ノード判定（`nodes.exit.` プレフィックス）
- [ ] 終了コード自動判定（success=0, その他=1）
- [ ] カスタム終了コード対応
- [ ] フィクスチャを使用したテスト
- [ ] すべてのテスト通過

---

## 関連 Issue

- Issue #23: テスト用 YAML フィクスチャ（前提）
- Issue #24: NodeDefinition の終端ノード対応（前提）
- Issue #27: codegen の終端ノード対応
- Issue #28: dag_runner の終端ノード実行
