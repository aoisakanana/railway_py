# Issue #72: ドキュメント更新（readme.md, TUTORIAL.md）

## 優先度

**必須**（全タスク完了後に実施）

## 概要

v0.13.3 の変更を反映し、readme.md と TUTORIAL.md テンプレートを更新する。

## 前提条件

以下の issue がすべて完了していること:

- [x] #66 開始ノードの引数整合性問題
- [x] #67 モジュールパス自動解決の改善
- [x] #68 終端ノードファイル名の制約
- [x] #69 テスト自動生成のインポートパス修正
- [x] #70 エラーメッセージの改善
- [x] #71 YAML スキーマの追加

## 更新内容

### 1. readme.md

#### 1.1 開始ノードの例を更新

```python
# Before
@node
def start() -> tuple[Context, Outcome]:
    ...

# After
@node
def start(ctx: GreetingContext | None = None) -> tuple[GreetingContext, Outcome]:
    if ctx is None:
        ctx = GreetingContext()
    return ctx, Outcome.success("done")
```

#### 1.2 YAML の module パス例を更新

```yaml
# Before（省略形式）
nodes:
  start:
    description: "開始"

# After（明示的なパス）
nodes:
  start:
    module: nodes.greeting.start
    function: start
    description: "開始"
```

#### 1.3 エラーコードセクション追加

```markdown
## エラーコード

| コード | 説明 |
|--------|------|
| E001 | 開始ノードの引数エラー |
| E002 | モジュールが見つかりません |
| E003 | 無効な識別子 |
| E004 | 終端ノードの戻り値エラー |
```

#### 1.4 YAML スキーマへの参照

```markdown
## YAML スキーマ

エディタの補完を有効にするには、YAML ファイルの先頭に以下を追加:

```yaml
# yaml-language-server: $schema=./node_modules/railway-framework/schemas/transition_graph_v1.json
```

または、スキーマファイルをプロジェクトにコピーして相対パスで参照:

```yaml
# yaml-language-server: $schema=./.railway/schemas/transition_graph_v1.json
```
```

### 2. TUTORIAL.md テンプレート（init.py）

#### 2.1 開始ノードの例を更新

```python
# 開始ノードは optional なコンテキストを受け取る
@node
def start(ctx: GreetingContext | None = None) -> tuple[GreetingContext, Outcome]:
    if ctx is None:
        ctx = GreetingContext(message="Hello")
    return ctx, Outcome.success("done")
```

#### 2.2 module パスの説明を更新

```markdown
### module/function の指定

v0.13.3 以降、`module` と `function` は明示的に指定されます:

```yaml
nodes:
  start:
    module: nodes.greeting.start  # 完全なモジュールパス
    function: start
    description: "開始ノード"
```
```

#### 2.3 識別子の命名規則を追加

```markdown
### ノード名の命名規則

- アルファベット小文字とアンダースコアのみ使用
- 数字のみの名前は使用不可（例: `1`, `2`）
- Python キーワードは使用不可（例: `class`, `def`）

✅ 有効: `start`, `check_time`, `exit_1`
❌ 無効: `1`, `2`, `class`
```

#### 2.4 run() 関数の使い方を更新

```markdown
### run() 関数の使い方

```python
from _railway.generated.greeting_transitions import run

# 初期コンテキストを渡せる
result = run(GreetingContext(message="Custom message"))

# または省略してデフォルト値を使用
result = run(None)
```
```

## 実装タスク

### 1. readme.md の更新

```bash
# 更新対象セクション
- クイックスタート
- ノードの実装
- 遷移グラフ管理
- YAML リファレンス
```

### 2. TUTORIAL.md テンプレートの更新

```python
# railway/cli/init.py の TUTORIAL_TEMPLATE を更新
```

### 3. テスト

```python
# tests/unit/cli/test_init.py

def test_tutorial_contains_optional_context():
    """TUTORIAL に optional コンテキストの例が含まれる。"""
    from railway.cli.init import TUTORIAL_TEMPLATE
    assert "ctx: " in TUTORIAL_TEMPLATE or "context:" in TUTORIAL_TEMPLATE
    assert "None" in TUTORIAL_TEMPLATE
```

## チェックリスト

### readme.md

- [ ] 開始ノードの例が optional コンテキストを使用
- [ ] YAML の module パスが明示的
- [ ] エラーコードセクション追加
- [ ] YAML スキーマへの参照追加
- [ ] バージョン番号の更新（必要に応じて）

### TUTORIAL.md テンプレート

- [ ] 開始ノードの例が optional コンテキストを使用
- [ ] module パスの説明を更新
- [ ] 識別子の命名規則を追加
- [ ] run() 関数の使い方を更新

### リリースノート

- [ ] `docs/RELEASE_NOTES_v0.13.3.md` 作成（公開用）
- [ ] 全変更点を記載
- [ ] 破壊的変更を明記（後方互換なし）
- [ ] CHANGELOG.md への追記（該当する場合）

## 完了条件

- [ ] readme.md が最新の実装を反映
- [ ] TUTORIAL.md テンプレートが最新の実装を反映
- [ ] リリースノート作成
- [ ] 全テストがパス
