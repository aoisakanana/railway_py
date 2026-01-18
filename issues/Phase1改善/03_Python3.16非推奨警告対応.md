# Issue 03: Python 3.16 非推奨警告対応

## 概要

Python 3.14 環境で `asyncio.iscoroutinefunction` の非推奨警告が表示される。Python 3.16 で削除予定。

## 問題の詳細

### 警告メッセージ
```
DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and
slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
```

### 発生条件
- Python 3.14 以降の環境で発生
- 非同期ノードの検出処理で使用されている

## 改善案

### 修正方法

```python
# Before
import asyncio
asyncio.iscoroutinefunction(func)

# After
import inspect
inspect.iscoroutinefunction(func)
```

### 後方互換性の考慮

Python 3.13 以前でも `inspect.iscoroutinefunction()` は利用可能なため、単純に置き換えて問題ない。

## 実装

1. コードベース内の `asyncio.iscoroutinefunction` を検索
2. すべて `inspect.iscoroutinefunction` に置き換え
3. 必要に応じて `import inspect` を追加

## 関連ファイル

検索対象：
- `src/railway/core/decorators.py`
- `src/railway/core/pipeline.py`
- その他 `asyncio.iscoroutinefunction` を使用している箇所

## 優先度

Medium - 現時点では警告のみだが、Python 3.16 リリース前に対応が必要
