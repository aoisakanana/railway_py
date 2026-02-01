# Issue #68: 終端ノードファイル名の制約

## 優先度

**Critical**

## 問題

終端ノードのファイル名に数字のみ（`1.py`, `2.py`）を使用すると、Python の構文エラーが発生する。

### 現状

```yaml
nodes:
  exit:
    green:
      1:
        description: "ケース1"
      2:
        description: "ケース2"
```

生成されるコード:
```python
from nodes.exit.green.1 import done  # SyntaxError: invalid syntax
```

### エラー

```
SyntaxError: invalid syntax
```

## 解決策

### 設計判断

| 選択肢 | メリット | デメリット |
|--------|----------|------------|
| A) 検証してエラー表示 | 明確なフィードバック | ユーザー修正が必要 |
| B) 自動的にプレフィックス付加 | ユーザー負担なし | 暗黙の変換で混乱の可能性 |
| C) **両方: 検証 + 警告 + 提案** | バランス良い | 実装が少し複雑 |

**採用: C) 検証 + 警告 + 提案**

### 動作仕様

1. **パース時に検証**: 数字のみの識別子を検出
2. **警告メッセージ表示**: 問題と解決策を提示
3. **sync を中断**: 修正を促す

```
Error: 無効な識別子が検出されました
  - exit.green.1 → Python の識別子として使用できません

Hint: 以下のように修正してください:
  - exit.green.case_1
  - exit.green.exit_1

YAML を修正後、再度 sync を実行してください。
```

## 実装タスク

### 1. 純粋関数: 識別子検証

```python
# railway/core/dag/validator.py

import re
from typing import NamedTuple


class IdentifierValidation(NamedTuple):
    """識別子検証結果（イミュータブル）。"""
    is_valid: bool
    invalid_identifiers: tuple[str, ...]
    suggestions: tuple[str, ...]


def validate_python_identifiers(node_names: tuple[str, ...]) -> IdentifierValidation:
    """ノード名が Python の識別子として有効か検証（純粋関数）。

    Args:
        node_names: 検証するノード名のタプル

    Returns:
        IdentifierValidation: 検証結果

    Examples:
        >>> validate_python_identifiers(("start", "exit.success.done"))
        IdentifierValidation(is_valid=True, invalid_identifiers=(), suggestions=())

        >>> validate_python_identifiers(("exit.green.1", "exit.red.2"))
        IdentifierValidation(
            is_valid=False,
            invalid_identifiers=("1", "2"),
            suggestions=("exit_1", "exit_2")
        )
    """
    invalid = []
    suggestions = []

    for name in node_names:
        parts = name.split(".")
        for part in parts:
            if not _is_valid_identifier(part):
                invalid.append(part)
                suggestions.append(_suggest_valid_name(part))

    return IdentifierValidation(
        is_valid=len(invalid) == 0,
        invalid_identifiers=tuple(invalid),
        suggestions=tuple(suggestions),
    )


import keyword  # モジュールレベルでインポート


def _is_valid_identifier(name: str) -> bool:
    """Python の識別子として有効か（純粋関数）。"""
    # 数字のみ、または数字で始まる
    if name.isdigit() or (name and name[0].isdigit()):
        return False
    # Python キーワード
    if keyword.iskeyword(name):
        return False
    # 識別子パターン
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name))


def _suggest_valid_name(invalid_name: str) -> str:
    """有効な識別子を提案（純粋関数）。"""
    if invalid_name.isdigit():
        return f"exit_{invalid_name}"
    if invalid_name[0].isdigit():
        return f"n_{invalid_name}"
    return f"{invalid_name}_"
```

### 2. テスト作成（Red）

```python
# tests/unit/core/dag/test_identifier_validation.py

class TestIdentifierValidation:
    """識別子検証のテスト。"""

    def test_valid_identifiers(self):
        """有効な識別子は検証をパス。"""
        result = validate_python_identifiers(
            ("start", "exit.success.done", "check_time")
        )
        assert result.is_valid is True
        assert result.invalid_identifiers == ()

    def test_numeric_only_identifier_is_invalid(self):
        """数字のみの識別子は無効。"""
        result = validate_python_identifiers(("exit.green.1",))
        assert result.is_valid is False
        assert "1" in result.invalid_identifiers

    def test_suggests_prefixed_name(self):
        """無効な識別子に対して修正提案を返す。"""
        result = validate_python_identifiers(("exit.green.1",))
        assert "exit_1" in result.suggestions

    def test_numeric_start_is_invalid(self):
        """数字で始まる識別子は無効。"""
        result = validate_python_identifiers(("1st_node",))
        assert result.is_valid is False

    def test_keyword_is_invalid(self):
        """Python キーワードは無効。"""
        result = validate_python_identifiers(("class", "def"))
        assert result.is_valid is False
```

### 3. sync コマンドへの統合

```python
# railway/cli/sync.py

def _sync_entry(...) -> None:
    ...
    # Parse YAML
    graph = load_transition_graph(yaml_path)

    # 識別子検証
    node_names = tuple(n.name for n in graph.nodes)
    validation = validate_python_identifiers(node_names)

    if not validation.is_valid:
        _print_identifier_error(validation)
        raise SyncError("無効な識別子が含まれています")

    ...


def _print_identifier_error(validation: IdentifierValidation) -> None:
    """識別子エラーを表示（副作用あり）。"""
    typer.echo("Error: 無効な識別子が検出されました", err=True)
    for invalid, suggestion in zip(
        validation.invalid_identifiers,
        validation.suggestions
    ):
        typer.echo(f"  - {invalid} → {suggestion} に変更してください", err=True)
    typer.echo("\nYAML を修正後、再度 sync を実行してください。", err=True)
```

## 影響範囲

| ファイル | 変更内容 |
|----------|----------|
| `railway/core/dag/validator.py` | `validate_python_identifiers()` 追加 |
| `railway/cli/sync.py` | 識別子検証を呼び出し |
| `tests/unit/core/dag/test_identifier_validation.py` | 新規テスト |

## 完了条件

- [ ] 数字のみの識別子でエラーメッセージ表示
- [ ] 修正提案が表示される
- [ ] sync が中断される
- [ ] テストが全てパス
