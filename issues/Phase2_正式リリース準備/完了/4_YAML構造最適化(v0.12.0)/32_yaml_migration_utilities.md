# Issue #32: YAML 構造変換ユーティリティ

**Phase:** 2
**優先度:** 高
**依存関係:** Issue #25（パーサーのネスト構造対応）
**見積もり:** 0.5日

---

## 概要

v0.11.x から v0.12.0 への YAML 構造変換を行う純粋関数群を実装する。
`railway update` コマンドで使用される。

---

## 変換対象

### 1. `exits` セクション → `nodes.exit` 配下

**Before (v0.11.x):**
```yaml
nodes:
  process:
    module: nodes.process
    function: process
    description: "処理"

exits:
  green_success:
    code: 0
    description: "正常終了"
  red_timeout:
    code: 1
    description: "タイムアウト"
```

**After (v0.12.0):**
```yaml
nodes:
  process:
    module: nodes.process
    function: process
    description: "処理"

  exit:
    success:
      done:
        description: "正常終了"
    failure:
      timeout:
        description: "タイムアウト"
```

### 2. 遷移先の形式変換

**Before (v0.11.x):**
```yaml
transitions:
  process:
    success::done: exit::green_success
    failure::timeout: exit::red_timeout
```

**After (v0.12.0):**
```yaml
transitions:
  process:
    success::done: exit.success.done
    failure::timeout: exit.failure.timeout
```

---

## 設計原則

- **純粋関数:** 全ての変換関数は副作用なし
- **イミュータブル:** 入力を変更せず、新しい dict を返す
- **エラーハンドリング:** Result 型パターンを使用
- **テスタブル:** 小さな関数に分割

---

## 実装（純粋関数）

### データ型定義

```python
# railway/migrations/yaml_converter.py
"""YAML structure conversion utilities for v0.11 to v0.12 migration."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ConversionResult:
    """変換結果（イミュータブル）。"""
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    warnings: tuple[str, ...] = ()

    @classmethod
    def ok(cls, data: dict[str, Any], warnings: tuple[str, ...] = ()) -> "ConversionResult":
        return cls(success=True, data=data, warnings=warnings)

    @classmethod
    def fail(cls, error: str) -> "ConversionResult":
        return cls(success=False, error=error)


@dataclass(frozen=True)
class ExitMapping:
    """旧形式 exit 名から新形式へのマッピング。"""
    old_name: str       # green_success
    new_path: str       # exit.success.done
    exit_code: int      # 0
    description: str    # "正常終了"
```

### 変換関数

```python
def convert_yaml_structure(data: dict[str, Any]) -> ConversionResult:
    """YAML 構造を v0.11 から v0.12 形式に変換（純粋関数）。

    Args:
        data: 旧形式の YAML データ

    Returns:
        ConversionResult: 変換結果
    """
    warnings: list[str] = []

    # exits セクションがなければ変換不要
    if "exits" not in data:
        return ConversionResult.ok(data)

    # exits を nodes.exit に変換
    exit_mappings = _extract_exit_mappings(data.get("exits", {}))
    new_nodes = _convert_nodes_section(data.get("nodes", {}), exit_mappings)

    # transitions の遷移先を変換
    new_transitions = _convert_transitions(
        data.get("transitions", {}),
        exit_mappings,
    )

    # 変換できなかった exit があれば警告
    unconverted = _find_unconverted_exits(exit_mappings)
    if unconverted:
        warnings.append(
            f"以下の exit は自動変換できませんでした: {', '.join(unconverted)}"
        )

    # 新しい構造を構築
    result = {
        **data,
        "nodes": new_nodes,
        "transitions": new_transitions,
    }
    # exits セクションを削除
    del result["exits"]

    return ConversionResult.ok(result, tuple(warnings))


def _extract_exit_mappings(
    exits: dict[str, Any],
) -> tuple[ExitMapping, ...]:
    """旧 exits セクションからマッピング情報を抽出（純粋関数）。

    exit 名のパターンから新形式を推論:
    - green_* → exit.success.*
    - red_* → exit.failure.*
    - yellow_* → exit.warning.*
    - その他 → exit.other.*
    """
    mappings: list[ExitMapping] = []

    for name, config in exits.items():
        code = config.get("code", 1)
        description = config.get("description", "")

        # 新しいパスを推論
        new_path = _infer_new_exit_path(name, code)

        mappings.append(ExitMapping(
            old_name=name,
            new_path=new_path,
            exit_code=code,
            description=description,
        ))

    return tuple(mappings)


def _infer_new_exit_path(old_name: str, exit_code: int) -> str:
    """旧 exit 名から新形式のパスを推論（純粋関数）。

    推論ルール:
    1. 名前に "green" or "success" → exit.success.*
    2. 名前に "red" or "error" or "fail" → exit.failure.*
    3. 名前に "yellow" or "warn" → exit.warning.*
    4. exit_code == 0 → exit.success.*
    5. それ以外 → exit.failure.*

    末尾の詳細名は元の名前からプレフィックスを除去:
    - green_success → done
    - red_timeout → timeout
    """
    name_lower = old_name.lower()

    # カテゴリを推論
    if "green" in name_lower or "success" in name_lower:
        category = "success"
    elif "red" in name_lower or "error" in name_lower or "fail" in name_lower:
        category = "failure"
    elif "yellow" in name_lower or "warn" in name_lower:
        category = "warning"
    elif exit_code == 0:
        category = "success"
    else:
        category = "failure"

    # 詳細名を抽出
    detail = _extract_detail_name(old_name, category)

    return f"exit.{category}.{detail}"


def _extract_detail_name(old_name: str, category: str) -> str:
    """旧 exit 名から詳細名を抽出（純粋関数）。

    プレフィックスを除去:
    - green_success → success → done (success は冗長)
    - green_resolved → resolved
    - red_timeout → timeout
    """
    # アンダースコアで分割
    parts = old_name.lower().split("_")

    # プレフィックス（green, red, yellow）を除去
    prefixes = {"green", "red", "yellow"}
    filtered = [p for p in parts if p not in prefixes]

    if not filtered:
        return "done"

    # カテゴリと同じ名前は "done" に置換
    if filtered == [category]:
        return "done"

    return "_".join(filtered)


def _convert_nodes_section(
    nodes: dict[str, Any],
    exit_mappings: tuple[ExitMapping, ...],
) -> dict[str, Any]:
    """nodes セクションに exit ノードを追加（純粋関数）。

    既存の nodes はそのまま維持し、exit 階層を追加。
    """
    # exit 階層を構築
    exit_tree = _build_exit_tree(exit_mappings)

    return {
        **nodes,
        "exit": exit_tree,
    }


def _build_exit_tree(
    mappings: tuple[ExitMapping, ...],
) -> dict[str, Any]:
    """ExitMapping から exit ノード階層を構築（純粋関数）。

    例:
    - exit.success.done → {"success": {"done": {...}}}
    - exit.failure.timeout → {"failure": {"timeout": {...}}}
    """
    tree: dict[str, Any] = {}

    for mapping in mappings:
        # "exit.success.done" → ["success", "done"]
        parts = mapping.new_path.removeprefix("exit.").split(".")

        # ツリーを走査して挿入
        current = tree
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # 葉ノードを設定
        leaf_name = parts[-1]
        current[leaf_name] = {
            "description": mapping.description,
        }
        # カスタム exit_code（success 以外で 0、または failure 以外で 1 以外）
        if mapping.new_path.startswith("exit.success.") and mapping.exit_code != 0:
            current[leaf_name]["exit_code"] = mapping.exit_code
        elif not mapping.new_path.startswith("exit.success.") and mapping.exit_code not in (1, None):
            current[leaf_name]["exit_code"] = mapping.exit_code

    return tree


def _convert_transitions(
    transitions: dict[str, Any],
    exit_mappings: tuple[ExitMapping, ...],
) -> dict[str, Any]:
    """transitions セクションの遷移先を変換（純粋関数）。

    exit::green_success → exit.success.done
    """
    # 旧名 → 新パス のマッピングを作成
    name_to_path = {m.old_name: m.new_path for m in exit_mappings}

    new_transitions: dict[str, Any] = {}

    for node_name, node_transitions in transitions.items():
        new_node_transitions: dict[str, str] = {}

        for state, target in node_transitions.items():
            new_target = _convert_transition_target(target, name_to_path)
            new_node_transitions[state] = new_target

        new_transitions[node_name] = new_node_transitions

    return new_transitions


def _convert_transition_target(
    target: str,
    name_to_path: dict[str, str],
) -> str:
    """単一の遷移先を変換（純粋関数）。

    - exit::green_success → exit.success.done
    - process → process（変更なし）
    """
    if not target.startswith("exit::"):
        return target

    # exit::green_success → green_success
    old_name = target.removeprefix("exit::")

    # マッピングから新パスを取得
    return name_to_path.get(old_name, target)


def _find_unconverted_exits(
    mappings: tuple[ExitMapping, ...],
) -> tuple[str, ...]:
    """変換できなかった exit を検出（純粋関数）。

    現在の実装では全て変換されるため、空タプルを返す。
    将来の拡張用。
    """
    return ()
```

---

## TDD 実装手順

### Step 1: テスト作成（Red）

```python
# tests/unit/migrations/test_yaml_converter.py
"""Tests for YAML structure conversion utilities."""

import pytest
from railway.migrations.yaml_converter import (
    convert_yaml_structure,
    _extract_exit_mappings,
    _infer_new_exit_path,
    _extract_detail_name,
    _convert_transition_target,
    _build_exit_tree,
    ConversionResult,
    ExitMapping,
)


class TestInferNewExitPath:
    """exit パス推論テスト。"""

    @pytest.mark.parametrize(
        ("old_name", "exit_code", "expected"),
        [
            ("green_success", 0, "exit.success.done"),
            ("green_resolved", 0, "exit.success.resolved"),
            ("green_done", 0, "exit.success.done"),
            ("red_timeout", 1, "exit.failure.timeout"),
            ("red_error", 1, "exit.failure.error"),
            ("yellow_warning", 2, "exit.warning.warning"),
            ("unknown", 0, "exit.success.unknown"),
            ("unknown", 1, "exit.failure.unknown"),
        ],
    )
    def test_infers_correct_path(
        self,
        old_name: str,
        exit_code: int,
        expected: str,
    ) -> None:
        """旧 exit 名から正しいパスを推論。"""
        result = _infer_new_exit_path(old_name, exit_code)
        assert result == expected


class TestExtractDetailName:
    """詳細名抽出テスト。"""

    @pytest.mark.parametrize(
        ("old_name", "category", "expected"),
        [
            ("green_success", "success", "done"),  # success は冗長
            ("green_resolved", "success", "resolved"),
            ("red_timeout", "failure", "timeout"),
            ("red_ssh_error", "failure", "ssh_error"),
            ("yellow_low_disk", "warning", "low_disk"),
        ],
    )
    def test_extracts_detail_name(
        self,
        old_name: str,
        category: str,
        expected: str,
    ) -> None:
        """詳細名を正しく抽出。"""
        result = _extract_detail_name(old_name, category)
        assert result == expected


class TestExtractExitMappings:
    """exit マッピング抽出テスト。"""

    def test_extracts_mappings_from_exits(self) -> None:
        """exits セクションからマッピングを抽出。"""
        exits = {
            "green_success": {"code": 0, "description": "正常終了"},
            "red_timeout": {"code": 1, "description": "タイムアウト"},
        }

        result = _extract_exit_mappings(exits)

        assert len(result) == 2
        assert any(m.old_name == "green_success" for m in result)
        assert any(m.new_path == "exit.success.done" for m in result)


class TestConvertTransitionTarget:
    """遷移先変換テスト。"""

    def test_converts_exit_target(self) -> None:
        """exit:: プレフィックスを新形式に変換。"""
        name_to_path = {"green_success": "exit.success.done"}

        result = _convert_transition_target("exit::green_success", name_to_path)

        assert result == "exit.success.done"

    def test_keeps_node_target_unchanged(self) -> None:
        """ノードへの遷移はそのまま。"""
        result = _convert_transition_target("process", {})

        assert result == "process"


class TestBuildExitTree:
    """exit ツリー構築テスト。"""

    def test_builds_nested_structure(self) -> None:
        """ネストした構造を構築。"""
        mappings = (
            ExitMapping("green_success", "exit.success.done", 0, "正常終了"),
            ExitMapping("red_timeout", "exit.failure.timeout", 1, "タイムアウト"),
        )

        result = _build_exit_tree(mappings)

        assert "success" in result
        assert "done" in result["success"]
        assert result["success"]["done"]["description"] == "正常終了"
        assert "failure" in result
        assert "timeout" in result["failure"]


class TestConvertYamlStructure:
    """YAML 構造変換の統合テスト。"""

    def test_converts_complete_structure(self) -> None:
        """完全な構造を変換。"""
        old_yaml = {
            "version": "1.0",
            "entrypoint": "test",
            "nodes": {
                "process": {
                    "module": "nodes.process",
                    "function": "process",
                    "description": "処理",
                },
            },
            "exits": {
                "green_success": {"code": 0, "description": "正常終了"},
                "red_timeout": {"code": 1, "description": "タイムアウト"},
            },
            "start": "process",
            "transitions": {
                "process": {
                    "success::done": "exit::green_success",
                    "failure::timeout": "exit::red_timeout",
                },
            },
        }

        result = convert_yaml_structure(old_yaml)

        assert result.success
        assert "exits" not in result.data
        assert "exit" in result.data["nodes"]
        assert result.data["transitions"]["process"]["success::done"] == "exit.success.done"

    def test_no_exits_section_returns_unchanged(self) -> None:
        """exits セクションがなければ変更なし。"""
        yaml_data = {
            "version": "1.0",
            "nodes": {"start": {"description": "開始"}},
        }

        result = convert_yaml_structure(yaml_data)

        assert result.success
        assert result.data == yaml_data

    def test_result_is_immutable(self) -> None:
        """結果はイミュータブル。"""
        result = ConversionResult.ok({"test": 1})

        with pytest.raises(AttributeError):
            result.success = False


class TestConversionResultFactory:
    """ConversionResult ファクトリテスト。"""

    def test_ok_creates_success_result(self) -> None:
        """ok() は成功結果を作成。"""
        result = ConversionResult.ok({"key": "value"})

        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None

    def test_fail_creates_failure_result(self) -> None:
        """fail() は失敗結果を作成。"""
        result = ConversionResult.fail("エラーメッセージ")

        assert result.success is False
        assert result.data is None
        assert result.error == "エラーメッセージ"

    def test_ok_with_warnings(self) -> None:
        """ok() は警告付きで作成可能。"""
        result = ConversionResult.ok(
            {"key": "value"},
            warnings=("警告1", "警告2"),
        )

        assert result.success is True
        assert len(result.warnings) == 2
```

### Step 2: 実装（Green）

上記の実装コードを `railway/migrations/yaml_converter.py` に実装。

### Step 3: リファクタリング

テストが通ったら、コードの改善を行う。

---

## 完了条件

- [ ] `ConversionResult` データクラス（イミュータブル）
- [ ] `ExitMapping` データクラス（イミュータブル）
- [ ] `convert_yaml_structure` メイン変換関数
- [ ] `_extract_exit_mappings` マッピング抽出
- [ ] `_infer_new_exit_path` パス推論
- [ ] `_extract_detail_name` 詳細名抽出
- [ ] `_convert_nodes_section` nodes セクション変換
- [ ] `_build_exit_tree` exit ツリー構築
- [ ] `_convert_transitions` transitions 変換
- [ ] `_convert_transition_target` 単一遷移先変換
- [ ] 全ての関数が純粋関数
- [ ] 全てのデータクラスがイミュータブル
- [ ] テストカバレッジ 90% 以上

---

## 関連 Issue

- Issue #25: パーサーのネスト構造対応（前提）
- Issue #33: v0.11.3 → v0.12.0 マイグレーション定義（後続）
