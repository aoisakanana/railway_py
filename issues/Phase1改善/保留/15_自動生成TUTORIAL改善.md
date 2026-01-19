# Issue #15: 自動生成TUTORIAL.md改善

## 概要
`railway init projectname`で自動生成されるTUTORIAL.mdを、新しいContext変数アーキテクチャに合わせて改善する。

## 背景
Issue #01-05で導入されるContext変数アーキテクチャにより、nodeの設計思想が大きく変わる：
- 旧: `def node(arg) -> result` （引数を受け取り、戻り値を返す）
- 新: `def node(ctx: Context) -> None` （Contextから読み取り、Contextに書き込む）

自動生成されるTUTORIAL.mdもこの新しいパラダイムを反映する必要がある。

## 依存関係
- Issue #01-05: コンテキスト変数アーキテクチャ（先行、必須）
- Issue #07: エントリポイントテンプレート簡素化（参考）
- Issue #09: ノードテンプレート簡素化（参考）
- Issue #11: TDD Red Phase省略問題対応（参考）

## 現状の問題
- 自動生成されるTUTORIAL.mdが旧形式のnode設計を前提としている
- Context変数の使い方が説明されていない
- `railway add node`コマンドの使い方が含まれていない

## 提案される解決策

### 更新すべきセクション

#### 1. Quick Start セクション
```markdown
## Quick Start

### プロジェクト作成後の最初のステップ

1. エントリポイントの作成
```bash
railway new entry hello
```

2. ノードの追加
```bash
railway add node fetch_data --entry hello
railway add node process_data --entry hello
```

3. ノードの実装
```python
# src/nodes/fetch_data.py
from railway import node
from railway.core.context import Context

@node
def fetch_data(ctx: Context) -> None:
    """データを取得"""
    ctx["fetch_data"] = {"message": "Hello, Railway!"}
```

4. 実行
```bash
railway run hello
```
```

#### 2. Context変数の基本セクション（新規追加）
```markdown
## Context変数の基本

Railwayでは、ノード間のデータ受け渡しにContextオブジェクトを使用します。

### データの書き込み
```python
@node
def fetch_data(ctx: Context) -> None:
    ctx["fetch_data"] = {"user": "Alice", "score": 100}
```

### データの読み取り
```python
@node
def process_data(ctx: Context) -> None:
    user = ctx["fetch_data"]["user"]
    ctx["process_data"] = {"greeting": f"Hello, {user}!"}
```

### パラメータの取得
```python
@node
def fetch_data(ctx: Context) -> None:
    user_id = ctx.get_param("user_id")
    ctx["fetch_data"] = {"id": user_id}
```
```

#### 3. TDDワークフローセクション（Red Phase対応）
```markdown
## TDDワークフロー

### Step 1: テストを書く（Red Phase）
```python
# tests/nodes/test_fetch_data.py
from railway import Context

def test_fetch_data():
    ctx = Context(entry_point="test")
    ctx.register_node("fetch_data")
    ctx.set_param("user_id", 1)

    from nodes.fetch_data import fetch_data
    fetch_data(ctx)

    assert ctx["fetch_data"]["id"] == 1
```

### Step 2: テスト実行（失敗を確認）
```bash
uv run pytest tests/nodes/test_fetch_data.py -v
# FAILED - これがRed Phaseです
```

### Step 3: 実装（Green Phase）
```python
# src/nodes/fetch_data.py
@node
def fetch_data(ctx: Context) -> None:
    user_id = ctx.get_param("user_id")
    ctx["fetch_data"] = {"id": user_id}
```

### Step 4: テスト実行（成功を確認）
```bash
uv run pytest tests/nodes/test_fetch_data.py -v
# PASSED - これがGreen Phaseです
```
```

#### 4. パイプライン実行セクション
```markdown
## パイプラインの実行

### エントリポイントから実行
```python
# src/hello.py
from railway import Context, pipeline

def main():
    ctx = Context.from_entry("hello")
    ctx.set_param("user_id", 1)

    result = pipeline(ctx)

    print(result["process_data"]["greeting"])

if __name__ == "__main__":
    main()
```

### CLIから実行
```bash
railway run hello --param user_id=1
```
```

#### 5. ノード管理セクション（新規追加）
```markdown
## ノード管理

### ノードの追加
```bash
railway add node validate_input --entry hello
```

### ノードの削除
```bash
railway remove node validate_input --entry hello
```

### ノード一覧の確認
```bash
railway list nodes --entry hello
```

### context.yaml
各エントリポイントには`context.yaml`が生成され、ノード構成が管理されます：
```yaml
# src/hello/context.yaml
entry_point: hello
nodes:
  - fetch_data
  - process_data
```
```

## 実装タスク

1. [ ] 現在のTUTORIAL.mdテンプレートの内容を確認
2. [ ] Quick Startセクションを新形式に更新
3. [ ] Context変数の基本セクションを追加
4. [ ] TDDワークフローにRed Phase体験を追加
5. [ ] パイプライン実行セクションを新形式に更新
6. [ ] ノード管理セクションを追加
7. [ ] 既存セクションとの整合性を確認

## 優先度
中（#01-05完了後に実施）

## 関連ファイル
- TUTORIAL.mdテンプレート生成処理
- `railway init`コマンド実装

## 参考情報
- Issue #11: TDD Red Phase省略問題対応
- Issue #13: コンテキスト変数アクセスチュートリアル
- Issue #14: ドキュメント新思想対応（README.md/TUTORIAL.md更新）

**注意**: Issue #14はリポジトリ本体のドキュメント更新、本Issue #15は`railway init`で生成されるプロジェクト内TUTORIAL.mdの更新。
