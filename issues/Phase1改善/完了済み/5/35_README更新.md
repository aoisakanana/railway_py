# Issue #35: README.md の更新

## 優先度: 中

## 概要

Issue #26-#34 で追加される機能をREADME.mdに反映する。特に **3層エラーハンドリングの設計思想** を分かりやすく伝えることを重視する。

## 重要: 3層エラーハンドリングの思想を伝える

README.md は Railway Framework の「顔」であり、設計思想を最初に伝える場所。
3層エラーハンドリングが **なぜこの設計なのか** を明確に説明する。

### 伝えるべきメッセージ

1. **Pythonらしさを大切にする**
   - Python標準の例外機構を活かす
   - 新しい概念（Result型等）を強制しない

2. **段階的な複雑さ**
   - シンプルなケースはシンプルに
   - 高度な制御が必要な時だけon_errorを使う

3. **実運用での現実性**
   - requests, sqlalchemy等の既存ライブラリとの親和性
   - スタックトレースの保持（デバッグ容易性）

## README.md への追記内容（案）

### 新セクション: エラーハンドリング哲学

```markdown
## エラーハンドリング

Railway Framework は **Python標準の例外機構を最大限活用** します。
新しい概念を導入せず、Pythonエンジニアが慣れ親しんだパターンで運用できます。

### 設計思想: 3層のエラーハンドリング

\`\`\`
┌─────────────────────────────────────────────────────────────┐
│ レベル1: Node内部                                            │
│   シンプル: 必要な箇所でtry/exceptを書く                      │
│   リトライ: retry_on で一時的エラーを自動リトライ             │
├─────────────────────────────────────────────────────────────┤
│ レベル2: Pipeline（デフォルト）                              │
│   何もしない: 例外はそのまま伝播                              │
│   スタックトレース保持、デバッグ容易                          │
├─────────────────────────────────────────────────────────────┤
│ レベル3: Pipeline（必要な時だけ）                            │
│   on_error: 例外をマッチしてフォールバック/ログ/再送出        │
└─────────────────────────────────────────────────────────────┘
\`\`\`

### なぜこの設計か？

| 設計判断 | 理由 |
|----------|------|
| Result型を採用しない | Pythonエコシステム（requests等）は例外ベース。ラップは冗長。 |
| デフォルトは例外伝播 | スタックトレースが保持され、デバッグしやすい。 |
| on_errorは任意 | 高度な制御が必要な時だけ使う。シンプルなケースを複雑にしない。 |

### 使用例

#### シンプルなケース（レベル2で十分）

\`\`\`python
# 例外はそのまま伝播。これで十分なケースが多い。
result = typed_pipeline(fetch_users, process, save)
\`\`\`

#### Node内で処理（レベル1）

\`\`\`python
@node
def fetch_users():
    try:
        return api.get_users()
    except NotFoundError:
        return []  # このNodeで完結
\`\`\`

#### 一時的エラーのリトライ（レベル1）

\`\`\`python
@node(retries=3, retry_on=(ConnectionError, TimeoutError))
def fetch_data():
    return requests.get(API_URL).json()
\`\`\`

#### Pipeline単位の高度な制御（レベル3）

\`\`\`python
def handle_error(error: Exception, step_name: str) -> Any:
    match error:
        case ConnectionError():
            return load_from_cache()  # フォールバック
        case _:
            raise  # 再送出

result = typed_pipeline(fetch, process, save, on_error=handle_error)
\`\`\`
```

### 既存セクションの更新

#### Features セクションに追加

```markdown
- **Pythonらしいエラーハンドリング** - 例外機構を活かした3層設計
```

#### Quick Start に一言追加

```markdown
# 例外はそのまま伝播（Pythonらしい動作）
# 高度な制御が必要な場合は on_error を使用
```

## 対象となる他の変更

| Issue | 機能 | README への追記 |
|-------|------|-----------------|
| #31 | retry_on | エラーハンドリングセクションに含める |
| #32 | on_step | デバッグセクションに追加 |
| #33 | inputs自動推論 | @node デコレータセクションに追記 |
| #29 | pipeline使い分け | API リファレンスに比較表 |

## 受け入れ条件

- [ ] 3層エラーハンドリングの設計思想を明確に説明
- [ ] 「なぜこの設計か」の理由を記載
- [ ] 各レベルの使用例を提示
- [ ] Features に「Pythonらしいエラーハンドリング」を追加
- [ ] retry_on, on_step, inputs自動推論の説明追加
- [ ] pipeline/typed_pipeline 比較表追加

## 依存関係

このIssueは以下のIssueの完了後に実施：

- [ ] #28 部分的失敗とリカバリーパターン（on_error）
- [ ] #31 リトライ対象例外指定（retry_on）
- [ ] #32 パイプライン中間結果アクセス（on_step）
- [ ] #33 inputs自動推論

## 関連

- Issue #28-#33: 対象となる機能追加
- ./readme.md: 更新対象ファイル
- Issue #36: TUTORIAL更新（並行して実施可能）
