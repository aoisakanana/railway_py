# Issue #29: pipeline/typed_pipeline 使い分けドキュメント

## 優先度: 中

## 概要

`pipeline` と `typed_pipeline` の違い・使い分けがドキュメントで明確に説明されていない。ユーザーが適切な関数を選択できるよう、ドキュメントを改善する。

## 現状の問題

### ユーザーの混乱ポイント

```python
from railway import pipeline, typed_pipeline

# どちらを使うべき？
result1 = pipeline(step1(), step2, step3)
result2 = typed_pipeline(step1, step2, step3)
```

- TUTORIAL.md では `typed_pipeline` のみを使用
- `pipeline` の存在意義・使い分けが不明確
- 外部監査でも「混乱の元」との指摘あり

## 提案されたアプローチ

### Option A: pipeline を非推奨化（将来検討）

```python
# deprecated
from railway import pipeline  # DeprecationWarning

# recommended
from railway import typed_pipeline
```

**メリット**: API のシンプル化
**デメリット**: 後方互換性の破壊、動的ユースケースへの影響

### Option B: ドキュメントでの明確化（推奨）

TUTORIAL.md と README.md に使い分けセクションを追加:

#### 追加するドキュメント内容

**比較表:**

| 特徴 | `pipeline` | `typed_pipeline` |
|------|-----------|------------------|
| 型安全性 | なし | あり |
| IDE補完 | 限定的 | フル対応 |
| 推奨用途 | 動的パイプライン | 通常の開発 |
| 引数 | 最初の引数は評価済み値 | すべて関数 |

**推奨**: 通常は `typed_pipeline` を使用。

**`pipeline` のユースケース:**

```python
# ユースケース1: 動的なステップ構成
def build_pipeline(config: dict) -> Callable:
    steps = [load_data]
    if config.get("filter"):
        steps.append(filter_data)
    if config.get("transform"):
        steps.append(transform_data)
    steps.append(save_data)
    return lambda data: pipeline(data, *steps)

# ユースケース2: 既存データからのパイプライン開始
existing_data = load_from_cache()
result = pipeline(existing_data, process, save)
```

## 実装計画

1. TUTORIAL.md に「よくある質問」セクション追加
2. README.md の API セクションに使い分け表を追加
3. docstring の改善
4. `pipeline` の docstring にユースケース例を追加

## 受け入れ条件

- [ ] TUTORIAL.md に使い分けの説明を追加
- [ ] README.md に比較表を追加
- [ ] `typed_pipeline` の docstring に推奨の旨を記載
- [ ] `pipeline` の docstring に用途を明記

## 関連

- 外部監査（2026-01-22）: 優先度 中
- Issue #28: 部分的失敗とリカバリー（typed_pipeline の拡張）
