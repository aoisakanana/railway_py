# Issue #36: TUTORIAL.md テンプレートの更新

## 優先度: 中

## 概要

`railway init` で自動生成される TUTORIAL.md テンプレートに、3層エラーハンドリングの恩恵をユーザーが **体験できる** 形で追加する。

## 重要: 恩恵を「体験」させる設計

単なるドキュメント追加ではなく、ユーザーが手を動かして恩恵を感じられる設計にする。

### 検討: 統合 vs Appendix

| 方式 | メリット | デメリット |
|------|----------|------------|
| 既存Stepに統合 | 自然な学習フロー | 既存Stepが長くなる |
| Appendix追加 | 既存を壊さない | 読まれない可能性 |
| **ハイブリッド（推奨）** | 両方のメリット | - |

### 推奨: ハイブリッド方式

1. **既存Step内に軽く言及**（「詳しくはStep 8参照」）
2. **Step 8 として独立したエラーハンドリング体験**
3. **実践的なシナリオで恩恵を体感**

## TUTORIAL 更新計画

### 既存 Step への軽い統合

#### Step 4（Node作成）に追記

```markdown
### 4.x エラー時の動作

Nodeで例外が発生すると、パイプライン全体に伝播します（Python標準動作）。
これで問題ないケースが多いですが、より高度な制御が必要な場合は Step 8 を参照してください。
```

#### Step 5（Pipeline実行）に追記

```markdown
### 5.x 例外の伝播

\`\`\`python
# 例外が発生すると、そのまま伝播します
result = typed_pipeline(fetch_users, process_users, generate_report)
# → fetch_users で例外が発生した場合、スタックトレース付きで伝播
\`\`\`

高度なエラーハンドリング（フォールバック、条件分岐）については Step 8 で学びます。
```

### 新規 Step 8: エラーハンドリング体験

ユーザーが **実際に手を動かして恩恵を感じる** シナリオを設計。

```markdown
## Step 8: エラーハンドリング（実践）

このステップでは、Railway Framework のエラーハンドリングを実際に体験します。

### 8.1 シナリオ: 不安定な外部APIとの連携

外部APIが不安定で、時々接続エラーやタイムアウトが発生する状況を想定します。

\`\`\`python
# src/nodes/fetch_external_data.py
import random
from railway import node

class ConnectionError(Exception):
    pass

class NotFoundError(Exception):
    pass

@node
def fetch_external_data():
    """不安定な外部APIをシミュレート"""
    roll = random.random()
    if roll < 0.3:
        raise ConnectionError("Network timeout")
    if roll < 0.4:
        raise NotFoundError("Resource not found")
    return {"data": "success", "value": 42}
\`\`\`

### 8.2 レベル1: Node内での個別処理

まず、Node内で例外を処理してみましょう：

\`\`\`python
@node
def fetch_external_data_safe():
    """Node内でエラーを処理"""
    try:
        return fetch_external_data()
    except NotFoundError:
        return {"data": "not_found", "value": 0}  # フォールバック
    # ConnectionError は伝播させる（リトライで回復可能かもしれない）
\`\`\`

**体験**: これを実行して、NotFoundErrorがフォールバックされることを確認してください。

### 8.3 レベル1: retry_on で自動リトライ

一時的なエラーには自動リトライが有効です：

\`\`\`python
@node(retries=3, retry_on=(ConnectionError,))
def fetch_with_retry():
    """ConnectionError は3回までリトライ"""
    return fetch_external_data()
\`\`\`

**体験**: 何度か実行して、ConnectionErrorが自動リトライされることを確認してください。

\`\`\`bash
uv run railway run fetch_with_retry
\`\`\`

### 8.4 レベル2: デフォルト動作（例外伝播）

何も指定しなければ、例外はそのまま伝播します：

\`\`\`python
result = typed_pipeline(fetch_external_data, process_data, save_data)
# 例外発生時: スタックトレース付きで伝播
\`\`\`

**体験**: 例外が発生した時のスタックトレースを確認してください。
デバッグに必要な情報がすべて含まれていることが分かります。

### 8.5 レベル3: on_error でPipeline単位の制御

複数のNodeを跨いだ高度な制御が必要な場合：

\`\`\`python
def smart_error_handler(error: Exception, step_name: str):
    """例外タイプに応じて適切に処理"""
    match error:
        case ConnectionError():
            print(f"⚠️ {step_name}: 接続エラー、キャッシュを使用")
            return load_from_cache()

        case NotFoundError():
            print(f"ℹ️ {step_name}: 見つかりません、空データで継続")
            return {"data": "empty", "value": 0}

        case _:
            print(f"❌ {step_name}: 予期しないエラー")
            raise  # 再送出

result = typed_pipeline(
    fetch_external_data,
    process_data,
    save_data,
    on_error=smart_error_handler
)
\`\`\`

**体験**: これを実行して、各エラータイプがどう処理されるか確認してください。

### 8.6 恩恵のまとめ

| レベル | いつ使う | 恩恵 |
|--------|----------|------|
| Node内try/except | 個別処理で完結 | シンプル、局所的 |
| retry_on | 一時的エラー | 自動回復、コード簡潔 |
| デフォルト伝播 | 多くのケース | スタックトレース保持 |
| on_error | 高度な制御 | Pipeline単位の柔軟な対応 |

**重要**: 多くのケースでは「何もしない」（デフォルト伝播）で十分です。
高度な機能は必要な時だけ使いましょう。
```

### FAQ セクションへの追加

```markdown
## よくある質問 (FAQ)

### Q: Result型（Ok/Err）は提供しないの？

Railway Framework は意図的にResult型を採用していません。

理由：
- Pythonエコシステム（requests, sqlalchemy等）は例外ベース
- Result型だとすべてをラップする必要があり冗長
- スタックトレースが失われデバッグが困難に

代わりに、Python標準の例外機構 + on_error で十分な制御を提供します。

### Q: on_error と try/except の使い分けは？

| 状況 | 推奨 |
|------|------|
| 1つのNodeで完結 | Node内で try/except |
| 複数Nodeを跨ぐ | on_error |
| リトライで回復可能 | retry_on |
| 特に制御不要 | 何もしない（例外伝播） |
```

## 対象ファイル

- `railway/cli/init.py` 内の `_get_tutorial_content()` 関数

## テスト

```python
def test_tutorial_contains_error_handling_experience():
    """TUTORIAL にエラーハンドリング体験セクションがある"""
    content = _get_tutorial_content()
    assert "Step 8" in content
    assert "on_error" in content
    assert "retry_on" in content

def test_tutorial_contains_practical_scenario():
    """TUTORIAL に実践シナリオがある"""
    content = _get_tutorial_content()
    assert "fetch_external_data" in content or "シナリオ" in content

def test_tutorial_explains_why_no_result_type():
    """TUTORIAL がResult型を採用しない理由を説明"""
    content = _get_tutorial_content()
    assert "Result" in content
    # 採用しない理由の説明があること
```

## 受け入れ条件

- [ ] 既存Stepにエラーハンドリングへの軽い言及を追加
- [ ] Step 8 として実践的なエラーハンドリング体験を追加
- [ ] ユーザーが手を動かせるシナリオを提供
- [ ] 各レベルの恩恵を体感できる構成
- [ ] FAQ に「なぜResult型を採用しないか」を追加
- [ ] テストで内容を検証

## 依存関係

このIssueは以下のIssueの完了後に実施：

- [ ] #28 部分的失敗とリカバリーパターン（on_error）
- [ ] #31 リトライ対象例外指定（retry_on）

## 関連

- Issue #28: on_error の実装
- Issue #31: retry_on の実装
- Issue #35: README更新（設計思想の説明）
- `railway/cli/init.py`: 更新対象ファイル
