# Issue #16: README.md 新アーキテクチャ対応

## 概要
README.mdを新しいContext変数アーキテクチャに合わせて更新する。

## 背景
Issue #01-05で導入されるContext変数アーキテクチャにより、Railwayの基本的な使い方が変わる：
- nodeはContextを受け取り、Contextに書き込む
- pipelineはContextを中心に実行される
- `railway add node`コマンドでノード管理

README.mdはフレームワークの「顔」であり、新しいアーキテクチャを正確に反映する必要がある。

## 依存関係
- Issue #01-05: コンテキスト変数アーキテクチャ（先行、必須）

## Issue #14との関係
| Issue | 焦点 |
|-------|------|
| #14 | `--example`オプション追加の反映（#07, #09依存） |
| #16 | Context変数アーキテクチャの反映（#01-05依存） |

両方の変更をREADME.mdに反映する必要があるが、#16が先に実施され、#14で追加の更新を行う。

## 提案される解決策

### 1. 概要セクションの更新

```markdown
## Railwayとは

Railwayは運用自動化のためのPythonフレームワークです。

### 特徴
- **Context変数**: ノード間のデータ共有を明確に管理
- **ステートレスなノード**: 各ノードはContextから読み取り、Contextに書き込む
- **宣言的なパイプライン**: context.yamlでノード構成を定義
- **TDD支援**: テストファーストの開発ワークフロー
```

### 2. Quick Startセクションの更新

```markdown
## Quick Start

### インストール
```bash
pip install railway-framework
```

### プロジェクト作成
```bash
railway init myproject
cd myproject
```

### ノードの作成
```bash
railway new entry hello
railway add node greet --entry hello
```

### ノードの実装
```python
# src/nodes/greet.py
from railway import node
from railway.core.context import Context

@node
def greet(ctx: Context) -> None:
    """挨拶メッセージを生成"""
    name = ctx.get_param("name", "World")
    ctx["greet"] = {"message": f"Hello, {name}!"}
```

### 実行
```bash
railway run hello --param name=Railway
# => Hello, Railway!
```
```

### 3. アーキテクチャセクション（新規または更新）

```markdown
## アーキテクチャ

### Context変数

Railwayでは、ノード間のデータ共有にContextオブジェクトを使用します。

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  fetch_data │ ──> │ process_data│ ──> │  save_data  │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       └───────────────────┴───────────────────┘
                           │
                    ┌──────┴──────┐
                    │   Context   │
                    │ ─────────── │
                    │ fetch_data  │
                    │ process_data│
                    │ save_data   │
                    └─────────────┘
```

### ノードの設計原則

1. **ステートレス**: ノードは内部状態を持たない
2. **単一責任**: 1つのノードは1つの処理を担当
3. **明示的な依存**: 必要なデータはContextから明示的に取得

```python
@node
def process_data(ctx: Context) -> None:
    # 前段のノードの結果を取得
    raw_data = ctx["fetch_data"]

    # 処理
    processed = transform(raw_data)

    # 結果をContextに書き込み
    ctx["process_data"] = processed
```
```

### 4. CLIコマンドセクションの更新

```markdown
## CLIコマンド

### プロジェクト管理
| コマンド | 説明 |
|----------|------|
| `railway init <name>` | 新規プロジェクト作成 |
| `railway new entry <name>` | エントリポイント作成 |

### ノード管理
| コマンド | 説明 |
|----------|------|
| `railway add node <name> --entry <entry>` | ノードを追加 |
| `railway remove node <name> --entry <entry>` | ノードを削除 |
| `railway list nodes --entry <entry>` | ノード一覧表示 |

### 実行
| コマンド | 説明 |
|----------|------|
| `railway run <entry>` | エントリポイント実行 |
| `railway run <entry> --param key=value` | パラメータ付き実行 |
| `railway test` | テスト実行 |
```

### 5. APIリファレンスセクション（新規または更新）

```markdown
## API リファレンス

### Context

```python
from railway import Context

# 作成
ctx = Context(entry_point="my_entry")
ctx = Context.from_entry("my_entry")  # context.yamlから

# パラメータ
ctx.set_param("user_id", 1)
user_id = ctx.get_param("user_id")

# ノード結果
ctx["node_name"] = {"key": "value"}  # 書き込み
result = ctx["node_name"]             # 読み取り
result = ctx.get("node_name", {})     # 安全な読み取り

# メタ情報
ctx.meta.entry_point  # エントリポイント名
ctx.meta.nodes        # 登録されたノード一覧
```

### @node デコレータ

```python
from railway import node
from railway.core.context import Context

@node
def my_node(ctx: Context) -> None:
    """ノードの処理"""
    ctx["my_node"] = {"result": "value"}
```

### pipeline

```python
from railway import pipeline, Context

# context.yamlに定義されたノードを順次実行
ctx = Context.from_entry("my_entry")
result = pipeline(ctx)

# 明示的にノードを指定
from nodes.fetch import fetch_data
from nodes.process import process_data
result = pipeline(ctx, fetch_data, process_data)
```
```

## 実装タスク

1. [ ] 現在のREADME.mdの構成を確認
2. [ ] 概要セクションを新アーキテクチャに更新
3. [ ] Quick Startセクションを新形式に更新
4. [ ] アーキテクチャセクションを追加/更新
5. [ ] CLIコマンド一覧を更新（add/remove/list node追加）
6. [ ] APIリファレンスセクションを追加/更新
7. [ ] 既存の例示コードをContext形式に更新

## 優先度
中（#01-05完了後に実施）

## 関連ファイル
- `README.md`

## 参考情報
- Issue #01: コンテキスト変数基本設計
- Issue #02: Contextクラス実装
- Issue #04: CLIコマンド拡張
- Issue #14: ドキュメント新思想対応（--exampleオプション反映）
