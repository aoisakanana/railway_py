# Issue #33: inputs 自動推論

## 優先度: 中

## 概要

`@node(inputs={"x": SomeContract})` の手動指定は冗長。型ヒントから自動推論できるようにする。

## 現状の問題

```python
# 現状: 冗長な指定が必要
@node(output=ProcessedData, inputs={"users": UsersFetchResult})
def process_users(users: UsersFetchResult) -> ProcessedData:
    ...
```

引数の型ヒント `users: UsersFetchResult` と `inputs={"users": UsersFetchResult}` が重複している。

## 提案されたアプローチ

### 型ヒントからの自動推論

```python
# 提案: inputs を省略可能に
@node(output=ProcessedData)
def process_users(users: UsersFetchResult) -> ProcessedData:
    ...
    # inputs は型ヒントから自動推論される
```

### 実装方針（関数型パラダイム準拠）

```python
import inspect
from typing import get_type_hints

def _infer_inputs_from_hints(func: Callable) -> dict[str, type]:
    """型ヒントから inputs を推論する純粋関数"""
    hints = get_type_hints(func)
    sig = inspect.signature(func)
    return {
        param_name: _extract_contract_type(hints[param_name])
        for param_name in sig.parameters
        if param_name in hints and _is_contract_type(hints[param_name])
    }


def node(func=None, *, output=None, inputs=None):
    def decorator(f):
        # 明示的指定がなければ自動推論（副作用なし）
        resolved_inputs = inputs if inputs is not None else _infer_inputs_from_hints(f)
        # ... 残りの処理（resolved_inputs を使用）
    return decorator
```

## 考慮事項

### 明示的指定の優先

```python
# 明示的に指定された場合はそちらを優先
@node(output=ProcessedData, inputs={"users": UsersFetchResult})
def process_users(users: UsersFetchResult) -> ProcessedData:
    ...
```

### 非 Contract 型の扱い

```python
@node(output=Result)
def process(data: str, count: int) -> Result:
    # str, int は Contract ではないので inputs には含まれない
    ...
```

### Union 型の扱い

```python
@node(output=Result)
def process(data: UsersFetchResult | None) -> Result:
    # Union 内の Contract 型を抽出
    ...
```

## テスト（TDD準拠）

```python
# tests/unit/core/test_inputs_inference.py
from railway import node, Contract
from dataclasses import dataclass

@dataclass
class UsersFetchResult(Contract):
    users: list[str]

@dataclass
class ProcessedData(Contract):
    count: int


class TestInputsAutoInference:
    def test_infers_inputs_from_type_hints(self):
        """inputs は型ヒントから自動推論される"""
        @node(output=ProcessedData)
        def process_users(users: UsersFetchResult) -> ProcessedData:
            return ProcessedData(count=len(users.users))

        assert process_users._node_metadata.inputs == {"users": UsersFetchResult}

    def test_explicit_inputs_takes_precedence(self):
        """明示的な inputs 指定は自動推論より優先される"""
        @dataclass
        class AltContract(Contract):
            data: str

        @node(output=ProcessedData, inputs={"data": AltContract})
        def process(data: UsersFetchResult) -> ProcessedData:
            return ProcessedData(count=0)

        assert process._node_metadata.inputs == {"data": AltContract}

    def test_non_contract_types_ignored(self):
        """非 Contract 型は inputs に含まれない"""
        @node(output=ProcessedData)
        def process(name: str, count: int) -> ProcessedData:
            return ProcessedData(count=count)

        assert process._node_metadata.inputs == {}

    def test_mixed_contract_and_primitive_types(self):
        """Contract と プリミティブ型が混在する場合"""
        @node(output=ProcessedData)
        def process(users: UsersFetchResult, limit: int) -> ProcessedData:
            return ProcessedData(count=min(len(users.users), limit))

        # Contract 型のみが inputs に含まれる
        assert process._node_metadata.inputs == {"users": UsersFetchResult}

    def test_optional_contract_type(self):
        """Optional[Contract] も推論される"""
        @node(output=ProcessedData)
        def process(users: UsersFetchResult | None) -> ProcessedData:
            return ProcessedData(count=0 if users is None else len(users.users))

        assert process._node_metadata.inputs == {"users": UsersFetchResult}
```

## 実装計画（TDD）

### Phase 1: Red
上記テストを作成し、失敗することを確認

### Phase 2: Green
```python
# railway/core/decorators.py
def _infer_inputs_from_hints(func: Callable) -> dict[str, type]:
    """型ヒントから inputs を推論する純粋関数"""
    hints = get_type_hints(func)
    sig = inspect.signature(func)
    return {
        param_name: _extract_contract_type(hints[param_name])
        for param_name in sig.parameters
        if param_name in hints and _is_contract_type(hints[param_name])
    }

def _extract_contract_type(hint: type) -> type:
    """Union 型から Contract 型を抽出"""
    origin = get_origin(hint)
    if origin is Union:
        for arg in get_args(hint):
            if arg is not type(None) and _is_contract_type(arg):
                return arg
    return hint

def _is_contract_type(hint: type) -> bool:
    """Contract のサブクラスか判定"""
    try:
        return isinstance(hint, type) and issubclass(hint, Contract)
    except TypeError:
        return False
```

### Phase 3: Refactor
ドキュメント更新

## 受け入れ条件

- [ ] 型ヒントからの inputs 自動推論
- [ ] 明示的指定が優先される
- [ ] 非 Contract 型は無視される
- [ ] 既存コードへの影響なし（後方互換性）
- [ ] テスト追加
- [ ] ドキュメント更新

## 関連

- 外部監査（2026-01-22）: 優先度 中
- Issue #26: @node デコレータ型定義改善
- PEP 484: Type Hints
