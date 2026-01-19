# Issue #02: Contextクラス実装

## 概要
コンテキスト変数を管理するContextクラスを実装する。

## 依存関係
- Issue #01: コンテキスト変数基本設計（先行）

## 実装要件

### 基本インターフェース
```python
from railway import Context

# 初期化
ctx = Context(entry_point="my_entry")

# context.yamlからの初期化
ctx = Context.from_entry("my_entry")

# 初期パラメータの設定・取得
ctx.set_param("user_id", 1)
user_id = ctx.get_param("user_id")
user_id = ctx.get_param("missing", default=0)  # デフォルト値

# node結果の読み書き
ctx["fetch_data"] = {"user": user_data}
user = ctx["fetch_data"]["user"]      # KeyError if not exists
user = ctx.get("fetch_data", {})      # デフォルト値付き

# 存在確認
if "fetch_data" in ctx:
    ...

# メタデータアクセス
nodes = ctx.meta.nodes
started_at = ctx.meta.started_at
```

### Contextクラスの実装
```python
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
import yaml

@dataclass
class ContextMeta:
    entry_point: str
    started_at: datetime = field(default_factory=datetime.now)
    nodes: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)


class Context:
    def __init__(self, entry_point: str):
        self._meta = ContextMeta(entry_point=entry_point)
        self._data: dict[str, dict[str, Any]] = {}

    @classmethod
    def from_entry(cls, entry_name: str, base_path: Path | None = None) -> "Context":
        """context.yamlからContextを生成"""
        if base_path is None:
            base_path = Path("src")

        context_file = base_path / entry_name / "context.yaml"
        if not context_file.exists():
            raise FileNotFoundError(f"Context file not found: {context_file}")

        with open(context_file) as f:
            definition = yaml.safe_load(f)

        ctx = cls(entry_point=entry_name)
        for node_name in definition.get("nodes", []):
            ctx.register_node(node_name)

        return ctx

    @property
    def meta(self) -> ContextMeta:
        return self._meta

    # パラメータ操作
    def set_param(self, key: str, value: Any) -> None:
        """初期パラメータを設定"""
        self._meta.params[key] = value

    def get_param(self, key: str, default: Any = None) -> Any:
        """初期パラメータを取得"""
        return self._meta.params.get(key, default)

    # node登録
    def register_node(self, node_name: str) -> None:
        """nodeを登録"""
        if node_name not in self._meta.nodes:
            self._meta.nodes.append(node_name)

    def unregister_node(self, node_name: str) -> None:
        """nodeを登録解除"""
        if node_name in self._meta.nodes:
            self._meta.nodes.remove(node_name)
        if node_name in self._data:
            del self._data[node_name]

    # データアクセス
    def __getitem__(self, key: str) -> dict[str, Any]:
        """node結果の取得（存在しない場合はKeyError）"""
        if key == "_meta":
            raise KeyError("Use .meta property to access metadata")
        if key not in self._data:
            raise KeyError(f"Node '{key}' has no result yet")
        return self._data[key]

    def get(self, key: str, default: Any = None) -> dict[str, Any] | Any:
        """node結果の取得（デフォルト値付き）"""
        if key == "_meta":
            raise KeyError("Use .meta property to access metadata")
        return self._data.get(key, default)

    def __setitem__(self, key: str, value: dict[str, Any]) -> None:
        """node結果の設定"""
        if key == "_meta":
            raise KeyError("Cannot set metadata directly")
        if key not in self._meta.nodes:
            raise KeyError(f"Node '{key}' is not registered. Use register_node() first.")
        self._data[key] = value

    def __contains__(self, key: str) -> bool:
        """node結果の存在確認"""
        return key in self._data

    # シリアライズ
    def to_dict(self) -> dict[str, Any]:
        """全データを辞書として取得"""
        return {
            "_meta": {
                "entry_point": self._meta.entry_point,
                "started_at": self._meta.started_at.isoformat(),
                "nodes": self._meta.nodes,
                "params": self._meta.params,
            },
            **self._data,
        }
```

### エラーハンドリング
| 操作 | エラー条件 | 例外 |
|------|-----------|------|
| `ctx[key]` | 結果が未設定 | `KeyError` |
| `ctx[key] = value` | nodeが未登録 | `KeyError` |
| `ctx["_meta"]` | メタデータへの直接アクセス | `KeyError` |
| `Context.from_entry()` | context.yamlが存在しない | `FileNotFoundError` |

## テスト要件
- Context初期化
- `from_entry()`によるYAMLからの初期化
- パラメータ設定・取得
- node登録・解除
- データ読み書き（`[]`と`get()`）
- 存在確認（`in`）
- エラーケース（未登録node、存在しないkey等）

## 関連ファイル
- 新規: `railway/core/context.py`
- 新規: `tests/unit/core/test_context.py`

## 優先度
最高
