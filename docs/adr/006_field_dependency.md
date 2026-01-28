# ADR-006: フィールドベース依存関係によるワークフロー柔軟性

## ステータス
承認済み (2026-01-29)

## コンテキスト

Railway Framework の目標の一つは「YAML のみでワークフローを変更できること」である。
しかし、現在の設計ではノード間のデータ依存が暗黙的であり、YAML 変更後に
実行時エラーが発生する可能性がある。

### 要件

1. **YAML のみでワークフロー変更**: ノードコードを変更せずに遷移グラフを変更できる
2. **関心の分離**: YAML 記述者がノードの実装詳細を知る必要がない
3. **静的検証**: sync 時に依存関係の不整合を検出できる

### 検討した代替案

#### 代替案A: 型ベース依存関係（Phase Contract）

各ノードが明示的な入出力 Contract 型を持ち、継承関係で依存を表現。

```python
class AfterHostCheck(InitialContext):
    hostname: str  # 必須

@node
def escalate(ctx: AfterHostCheck) -> ...:
```

**却下理由:**
- 型の継承階層がノードの実行順序を固定する
- ノードの追加・削除・順序変更で型定義の変更が必要
- 「YAML のみでワークフロー変更」という目標を達成できない

#### 代替案B: YAML に依存情報を記述

```yaml
nodes:
  escalate:
    requires: [incident_id]
    optional: [hostname]
    provides: [escalated]
```

**却下理由:**
- YAML 記述者がノードの実装詳細（必要なフィールド）を知る必要がある
- 依存情報の二重管理（コードと YAML）になるリスク

## 決定

### フィールドベース依存関係（ノードコードのみで宣言）を採用

各ノードが `@node` デコレータで `requires`（必須）、`optional`（オプション）、`provides`（提供）を宣言。
**YAML には依存情報を書かない。**

```python
# ノード実装者: 依存を宣言
@node(requires=["incident_id"], optional=["hostname"], provides=["escalated"])
def escalate(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
    if ctx.hostname:  # optional なので存在チェック
        notify_with_host(ctx.hostname)
    return ctx.model_copy(update={"escalated": True}), Outcome.success("done")
```

```yaml
# YAML 記述者: 遷移のみを定義（依存情報不要）
nodes:
  check_severity:
    description: "重要度チェック"
  check_host:
    description: "ホスト情報取得"
  escalate:
    description: "エスカレーション"

transitions:
  check_severity:
    success::critical: check_host
    success::normal: escalate   # ← フレームワークが自動検証
  check_host:
    success::found: escalate
```

### 関心の分離

| 役割 | 責務 | 知る必要があること |
|------|------|------------------|
| **ノード実装者** | `@node` で依存を宣言 | ノードが必要とするフィールド |
| **YAML 記述者** | 遷移を定義 | **ノード名と Outcome のみ** |
| **フレームワーク** | 依存の自動検証 | 両方を読み取って検証 |

### バリデーションルール

`railway sync transition` 実行時:

1. 各ノードの `_field_dependency` 属性から依存情報を抽出
2. 開始ノードの Contract から初期フィールドを自動導出
3. 遷移グラフの全経路を解析
4. 各経路で `requires` が満たされるか検証
5. `optional` が満たされない場合は警告（エラーではない）

遷移 `A → B` が有効であるためには:
- `B.requires` のすべてのフィールドが、A までの経路で `provides` されていること
- 開始ノードは初期コンテキストのフィールドを `provides` として扱う

### 初期フィールドの自動導出

**YAML には `initial_context` を書かない。** 開始ノードの Contract 型から自動導出:

```python
def extract_initial_fields_from_start_node(graph: TransitionGraph) -> AvailableFields:
    """開始ノードの Contract から初期フィールドを自動導出する。"""
    # 開始ノードの型ヒントから Contract 型を取得
    # Contract の必須フィールド（デフォルト値なし）を初期フィールドとして扱う
```

### 利点

| 観点 | 効果 |
|------|------|
| **関心の分離** | YAML 記述者はノード実装詳細を知らなくてよい |
| **YAML 主導** | ワークフロー変更は YAML で完結 |
| **柔軟性** | ノードの順序変更・追加・削除が容易 |
| **再利用性** | 同じノードを異なるワークフローで使用可能 |
| **静的検証** | sync 時に依存関係の不整合を検出 |
| **実行時検証** | `check_dependencies=True` でデバッグ可能 |

## 影響

### 破壊的変更

- `@node` デコレータに `requires`/`optional`/`provides` パラメータ追加
- `sync` コマンドが依存関係を検証
- YAML に `contracts` セクションは追加しない（依存はコードで管理）

### マイグレーション

`railway update` で既存プロジェクトを自動変換:
1. 既存ノードのコードを AST 解析してフィールドアクセスを推論
2. `@node` デコレータへの依存宣言追加をガイダンスとして出力
3. YAML は変更不要

## 参考資料

- ADR-004: Exit ノードの設計と例外処理
- ADR-005: ExitContract による dag_runner API 簡素化
