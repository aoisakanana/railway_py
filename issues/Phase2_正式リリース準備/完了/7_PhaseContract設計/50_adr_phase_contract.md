# Issue #50: ADR-006 フィールドベース依存関係

## 概要

フィールドベース依存関係パターンの設計決定を ADR として文書化する。

## 背景

### 目標
> 遷移グラフ（YAML）を変更して sync すれば、ノードのコードを変更せずにワークフローを変更できる

### 追加目標
> YAML 記述者がノードの実装詳細を知る必要がない

### 検討した代替案

**代替案A: 型ベース依存関係（Phase Contract）**

```python
class AfterHostCheck(InitialContext):
    hostname: str

@node
def escalate(ctx: AfterHostCheck) -> tuple[AfterEscalate, Outcome]:
    ...
```

**却下理由:**
- 型の継承階層がノードの実行順序を固定
- YAML 変更時にノードコードの変更が必要になるケースが多い
- 目標「YAML のみでワークフロー変更」を達成できない

**代替案B: YAML に依存情報を記述**

```yaml
nodes:
  escalate:
    requires: [incident_id]
    optional: [hostname]
    provides: [escalated]
```

**却下理由:**
- YAML 記述者がノードの実装詳細を知る必要がある
- 依存情報の二重管理（コードと YAML）

**採用案: ノードコードのみで依存を宣言**

```python
# ノードコードで依存を宣言（YAML には書かない）
@node(requires=["incident_id"], optional=["hostname"], provides=["escalated"])
def escalate(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
    ...
```

```yaml
# YAML には遷移のみ（依存情報なし）
nodes:
  escalate:
    description: "エスカレーション"

transitions:
  check_severity:
    success::critical: escalate  # ← フレームワークが自動検証
```

## タスク

### 1. Red Phase: ADR テンプレート検証

```bash
# ADR ファイルが存在しないことを確認
test ! -f docs/adr/006_field_dependency.md
```

### 2. Green Phase: ADR 作成

`docs/adr/006_field_dependency.md` を作成:

```markdown
# ADR-006: フィールドベース依存関係によるワークフロー柔軟性

## ステータス
承認済み (YYYY-MM-DD)

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
2. 遷移グラフの全経路を解析
3. 各経路で `requires` が満たされるか検証
4. `optional` が満たされない場合は警告（エラーではない）

遷移 `A → B` が有効であるためには:
- `B.requires` のすべてのフィールドが、A までの経路で `provides` されていること
- 開始ノードは初期コンテキストのフィールドを `provides` として扱う

### 利点

| 観点 | 効果 |
|------|------|
| **関心の分離** | YAML 記述者はノード実装詳細を知らなくてよい |
| **YAML 主導** | ワークフロー変更は YAML で完結 |
| **柔軟性** | ノードの順序変更・追加・削除が容易 |
| **再利用性** | 同じノードを異なるワークフローで使用可能 |
| **静的検証** | sync 時に依存関係の不整合を検出 |

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
```

### 3. Refactor Phase: レビューと調整

- 既存 ADR との整合性確認
- 用語の統一

## 完了条件

- [ ] `docs/adr/006_field_dependency.md` が作成されている
- [ ] ADR のステータスが「承認済み」
- [ ] 以下のセクションが含まれている:
  - コンテキスト（目標と現在の問題）
  - 決定（フィールドベース依存関係の詳細）
  - 代替案（型ベース、YAML 依存の却下理由）
  - 影響（破壊的変更、マイグレーション）

## 依存関係

- 依存なし（最初に実施）

## 関連ファイル

- `docs/adr/004_exit_node_design.md`
- `docs/adr/005_exit_contract_simplification.md`
- `docs/ARCHITECTURE.md`
