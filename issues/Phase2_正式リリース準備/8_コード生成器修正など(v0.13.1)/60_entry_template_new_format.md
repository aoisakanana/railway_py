# Issue #60: YAML テンプレートを新形式に更新

**優先度**: P0
**依存**: なし
**ブロック**: #61, #62, #64

---

## 概要

`railway new entry` で生成される YAML テンプレートを v0.12.3+ の新形式に更新する。

## 背景

現在のテンプレートはレガシー形式 (`exit::success`) を使用しており、v0.12.3 で `LegacyExitFormatError` が発生する。

**現在の問題**:
```bash
railway new entry greeting
railway sync transition --entry greeting
railway run greeting
# → LegacyExitFormatError
```

---

## 既存コードの確認

修正対象は `railway/cli/new.py` の `_get_dag_yaml_template()` 関数:

```python
# 現在の実装（レガシー形式）
def _get_dag_yaml_template(name: str) -> str:
    return f'''...
exits:
  success:
    code: 0
...
transitions:
  start:
    success::done: exit::success
'''
```

---

## TDD 実装フロー

### Phase 1: Red（失敗するテストを先に作成）

```python
# tests/unit/cli/test_dag_yaml_template.py

import pytest
import yaml
from railway.cli.new import _get_dag_yaml_template


class TestGetDagYamlTemplate:
    """YAML テンプレート生成のテスト。"""

    def test_generates_nodes_exit_section(self) -> None:
        """nodes.exit セクションが生成される（exits セクションではなく）。"""
        yaml_content = _get_dag_yaml_template("greeting")
        parsed = yaml.safe_load(yaml_content)

        assert "nodes" in parsed
        assert "exit" in parsed["nodes"]
        assert "success" in parsed["nodes"]["exit"]
        assert "done" in parsed["nodes"]["exit"]["success"]

        # レガシー形式が含まれない
        assert "exits" not in parsed

    def test_uses_new_transition_format(self) -> None:
        """新形式 exit.success.done を使用する。"""
        yaml_content = _get_dag_yaml_template("greeting")

        assert "exit.success.done" in yaml_content
        assert "exit.failure.error" in yaml_content

        # レガシー形式が含まれない
        assert "exit::success" not in yaml_content
        assert "exit::error" not in yaml_content
        assert "exit::green" not in yaml_content

    def test_includes_failure_exit(self) -> None:
        """失敗終端ノードも含まれる。"""
        yaml_content = _get_dag_yaml_template("greeting")
        parsed = yaml.safe_load(yaml_content)

        assert "failure" in parsed["nodes"]["exit"]
        assert "error" in parsed["nodes"]["exit"]["failure"]

    def test_start_node_has_description(self) -> None:
        """開始ノードに description がある。"""
        yaml_content = _get_dag_yaml_template("greeting")
        parsed = yaml.safe_load(yaml_content)

        assert parsed["nodes"]["start"]["description"] is not None


class TestDagYamlTemplateIntegration:
    """YAML 構文の統合テスト。"""

    def test_generated_yaml_is_valid(self) -> None:
        """生成された YAML は構文的に正しい。"""
        yaml_content = _get_dag_yaml_template("greeting")
        parsed = yaml.safe_load(yaml_content)

        assert parsed is not None
        assert "nodes" in parsed
        assert "transitions" in parsed
        assert "start" in parsed

    def test_generated_yaml_passes_parser(self) -> None:
        """生成された YAML は parser を通過する。"""
        from railway.core.dag.parser import parse_transition_graph

        yaml_content = _get_dag_yaml_template("greeting")
        parsed = yaml.safe_load(yaml_content)

        graph = parse_transition_graph(parsed)

        assert graph is not None
        assert graph.entrypoint == "greeting"
        assert graph.start_node == "start"

    def test_generated_yaml_passes_validator(self) -> None:
        """生成された YAML は validator を通過する。"""
        from railway.core.dag.parser import parse_transition_graph
        from railway.core.dag.validator import validate_graph

        yaml_content = _get_dag_yaml_template("greeting")
        parsed = yaml.safe_load(yaml_content)

        graph = parse_transition_graph(parsed)
        result = validate_graph(graph)

        assert result.is_valid, f"Validation errors: {result.errors}"
```

### Phase 2: Green（最小実装）

```python
# railway/cli/new.py の _get_dag_yaml_template() を修正

def _get_dag_yaml_template(name: str) -> str:
    """Get transition graph YAML template (v0.13.0+ 新形式).

    純粋関数: name -> YAML テンプレート文字列

    Args:
        name: エントリーポイント名

    Returns:
        YAML テンプレート文字列
    """
    return f'''version: "1.0"
entrypoint: {name}
description: "{name} ワークフロー"

nodes:
  start:
    module: nodes.{name}.start
    function: start
    description: "開始ノード"

  exit:
    success:
      done:
        description: "正常終了"
    failure:
      error:
        description: "エラー終了"

start: start

transitions:
  start:
    success::done: exit.success.done
    failure::error: exit.failure.error

options:
  max_iterations: 100
'''
```

### Phase 3: Refactor

- 終端ノードのカスタマイズオプション追加（`exit_nodes` パラメータ）
- テンプレート定数を別ファイルに分離（必要に応じて）

---

## 修正ファイル

| ファイル | 変更内容 |
|----------|----------|
| `railway/cli/new.py` | `_get_dag_yaml_template()` を新形式に更新 |
| `tests/unit/cli/test_dag_yaml_template.py` | 新規テストファイル |

---

## 変更前後の比較

### Before（レガシー形式）

```yaml
version: "1.0"
entrypoint: greeting

nodes:
  start:
    module: nodes.greeting.start
    function: start

exits:
  success:
    code: 0
    description: "正常終了"
  error:
    code: 1
    description: "異常終了"

start: start

transitions:
  start:
    success::done: exit::success
    failure::error: exit::error
```

### After（新形式）

```yaml
version: "1.0"
entrypoint: greeting
description: "greeting ワークフロー"

nodes:
  start:
    module: nodes.greeting.start
    function: start
    description: "開始ノード"

  exit:
    success:
      done:
        description: "正常終了"
    failure:
      error:
        description: "エラー終了"

start: start

transitions:
  start:
    success::done: exit.success.done
    failure::error: exit.failure.error

options:
  max_iterations: 100
```

---

## 受け入れ条件

### 機能
- [ ] 生成される YAML が `nodes.exit` 形式を使用
- [ ] `exits` セクションが含まれない
- [ ] `exit::success` 形式が含まれない
- [ ] 生成された YAML が parser + validator を通過

### TDD・関数型
- [ ] Red → Green → Refactor フェーズに従って実装
- [ ] `_get_dag_yaml_template()` は純粋関数（副作用なし）
- [ ] 全テスト通過

---

*v0.13.0 対応の基本修正*
