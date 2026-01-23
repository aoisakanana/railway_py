# Issue #26: @node デコレータの型定義改善

## 優先度: 中

## 概要

`@node` デコレータを使用すると、mypy で型推論エラーが発生する。デコレータの型定義を `@overload` を用いて改善し、戻り値の型が正しく推論されるようにする。

## 調査結果（2026-01-23 実施）

### 現在の実装

```python
# railway/core/decorators.py:49-58
def node(
    func: Callable[P, T] | None = None,
    *,
    inputs: dict[str, Type[Contract]] | None = None,
    output: Type[Contract] | None = None,
    retry: bool | Retry = False,
    log_input: bool = False,
    log_output: bool = False,
    name: str | None = None,
) -> Callable[P, T] | Callable[[Callable[P, T]], Callable[P, T]]:
```

### 問題の確認

```bash
$ echo 'from railway import node

@node
def fetch_users() -> list[str]:
    return ["Alice", "Bob"]

result: list[str] = fetch_users()
' > /tmp/test_node_typing.py && uv run mypy --strict /tmp/test_node_typing.py
```

**結果:**
```
/tmp/test_node_typing.py:7: error: Too few arguments  [call-arg]
/tmp/test_node_typing.py:7: error: Incompatible types in assignment (expression has type "list[str] | Callable[[], list[str]]", variable has type "list[str]")  [assignment]
Found 2 errors in 1 file (checked 1 source file)
```

### 原因

戻り値型が `Callable[P, T] | Callable[[Callable[P, T]], Callable[P, T]]` の Union 型のため、mypy が以下の2パターンを区別できない：

1. `@node` - 直接デコレート → `Callable[P, T]` を返す
2. `@node(...)` - パラメータ付き → `Callable[[Callable[P, T]], Callable[P, T]]` を返す

mypy は Union の両方の可能性を考慮するため、`fetch_users()` の戻り値が `list[str] | Callable[[], list[str]]` と推論されてしまう。

## 解決策: @overload の使用

### 実装方針

```python
from typing import overload, Callable, ParamSpec, TypeVar, Type
from railway.core.contract import Contract

P = ParamSpec("P")
T = TypeVar("T")

@overload
def node(func: Callable[P, T]) -> Callable[P, T]: ...

@overload
def node(
    func: None = None,
    *,
    inputs: dict[str, Type[Contract]] | None = None,
    output: Type[Contract] | None = None,
    retry: bool | Retry = False,
    log_input: bool = False,
    log_output: bool = False,
    name: str | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]: ...

def node(
    func: Callable[P, T] | None = None,
    *,
    inputs: dict[str, Type[Contract]] | None = None,
    output: Type[Contract] | None = None,
    retry: bool | Retry = False,
    log_input: bool = False,
    log_output: bool = False,
    name: str | None = None,
) -> Callable[P, T] | Callable[[Callable[P, T]], Callable[P, T]]:
    # 既存の実装はそのまま
    ...
```

### overload の役割

| 呼び出しパターン | マッチする overload | 戻り値型 |
|------------------|---------------------|----------|
| `@node` | 1番目（func: Callable） | `Callable[P, T]` |
| `@node()` | 2番目（func: None） | `Callable[[Callable[P, T]], Callable[P, T]]` |
| `@node(retry=True)` | 2番目（func: None） | `Callable[[Callable[P, T]], Callable[P, T]]` |

## テスト（TDD準拠）

### Phase 1: Red（現状）

```python
# tests/unit/core/test_node_typing.py
from railway import node

class TestNodeTypePreservation:
    def test_preserves_return_type(self):
        """@node デコレータが戻り値型を保持する"""
        @node
        def fetch_users() -> list[str]:
            return ["Alice", "Bob"]

        result: list[str] = fetch_users()
        assert result == ["Alice", "Bob"]

    def test_preserves_argument_types(self):
        """@node デコレータが引数型を保持する"""
        @node
        def greet(name: str, count: int) -> str:
            return f"Hello, {name}!" * count

        result: str = greet("World", 2)
        assert result == "Hello, World!Hello, World!"

    def test_with_retry_parameter(self):
        """retry パラメータ指定時も型を保持する"""
        @node(retry=True)
        def fetch_data() -> dict[str, int]:
            return {"count": 42}

        result: dict[str, int] = fetch_data()
        assert result == {"count": 42}

    def test_with_output_parameter(self):
        """output パラメータ指定時も型を保持する"""
        from dataclasses import dataclass

        @dataclass
        class User:
            name: str

        @node(output=User)
        def create_user(name: str) -> User:
            return User(name=name)

        result: User = create_user("Alice")
        assert result.name == "Alice"
```

### mypy 検証スクリプト

```bash
# mypy での検証（型チェックのテスト）
uv run mypy --strict tests/unit/core/test_node_typing.py
```

### Phase 2: Green

`railway/core/decorators.py` に `@overload` を追加。

### Phase 3: Refactor

mypy --strict でエラーが出ないことを確認。

## 実装計画

1. **テストファイル作成**: `tests/unit/core/test_node_typing.py`
2. **Red 確認**: mypy でエラーが出ることを確認（現状）
3. **overload 追加**: `railway/core/decorators.py` に2つの overload を追加
4. **Green 確認**: mypy でエラーが消えることを確認
5. **既存テスト**: 既存の機能テストが通ることを確認

## 受け入れ条件

- [x] **調査完了**: 問題の原因を特定（Union型による型推論の曖昧さ）
- [ ] `@node` デコレータが戻り値型を正しく保持
- [ ] `@node(...)` 形式でも型を保持
- [ ] mypy --strict で警告が出ない
- [ ] IDE での型推論が正常に動作
- [ ] 既存の機能に影響なし

## 関連

- Issue #27: プロジェクトテンプレートpy.typed追加（依存）
- PEP 612: Parameter Specification Variables
- mypy ドキュメント: Decorator factories
- `railway/core/decorators.py:49-116`: 対象コード
