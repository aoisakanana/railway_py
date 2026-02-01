# Railway Framework アーキテクチャガイド

このドキュメントは Railway Framework の全体像を横断的に説明します。
個別の API リファレンスではなく、**なぜこの設計なのか**を理解するためのガイドです。

---

## 目次

1. [3つのコンポーネント](#3つのコンポーネント)
2. [5つの設計思想](#5つの設計思想)
3. [フィールドベース依存関係](#フィールドベース依存関係)
4. [コンポーネント間の関係](#コンポーネント間の関係)
5. [実践例](#実践例)

---

## 3つのコンポーネント

Railway Framework は 3 つのコンポーネントで構成されます。
ユーザーが触れるのはこの 3 つだけです。

```
┌─────────────────────────────────────────────────────────┐
│                    ユーザーの関心                        │
├─────────────┬─────────────────┬─────────────────────────┤
│   Contract  │      Node       │    Transition Graph     │
│   (データ)   │    (ロジック)    │       (関係性)          │
├─────────────┼─────────────────┼─────────────────────────┤
│  Python     │     Python      │         YAML            │
│  クラス定義  │     関数定義     │      宣言的定義          │
└─────────────┴─────────────────┴─────────────────────────┘
```

### Node: ロジックのすべて

**Node はユーザーが実装するロジックのすべてです。**

```python
@node
def check_severity(ctx: AlertContext) -> tuple[AlertContext, Outcome]:
    """アラートの重要度をチェックする。"""
    if ctx.severity == "critical":
        return ctx, Outcome.success("critical")
    return ctx, Outcome.success("normal")
```

Node の特徴:
- **純粋関数**: 入力を受け取り、出力を返すだけ
- **状態を返す**: `Outcome` で「この Node がどうなったか」を表現
- **次を知らない**: 自分の次に何が来るかを Node は知らない

Node が返す `Outcome` は、この Node が取りうる状態を表します:

```python
Outcome.success("done")      # 成功・完了
Outcome.success("skipped")   # 成功・スキップ
Outcome.failure("timeout")   # 失敗・タイムアウト
Outcome.failure("not_found") # 失敗・未検出
```

### Contract: データのすべて

**Contract はユーザーが定義するデータのすべてです。**

```python
class AlertContext(Contract):
    """アラート処理のコンテキスト。"""
    incident_id: str
    severity: str
    hostname: str | None = None
    handled: bool = False
```

Contract の特徴:
- **型安全**: IDE 補完、静的型チェックが効く
- **イミュータブル**: 変更は `model_copy()` で新しいインスタンスを作成
- **Node 間をリレー**: Contract が Node から Node へ渡される

Contract は Node 間の「契約」です:

```
Node A ──[AlertContext]──> Node B ──[AlertContext]──> Node C
```

#### コンテキストの流れ（重要）

**Railway Framework では、直前のノードの Contract のみが次のノードに渡されます。**

```python
# runner.py 内部実装
context, outcome = next_step(context)  # 直前の context のみ渡される
```

これは意図的な設計選択です：

| 設計原則 | 説明 |
|----------|------|
| **明示的なデータフロー** | 何が渡されるか Contract を見れば分かる |
| **暗黙的状態の排除** | グローバルコンテキストやDIコンテナを使わない |
| **テスト容易性** | ノードは入力 Contract のみに依存 |
| **デバッグ容易性** | 各ノードの入出力が追跡可能 |

#### model_copy によるデータの引き継ぎ

ワークフロー全体で必要なデータは、**Contract に含めてリレーする**必要があります。
Contract はイミュータブルなので、`model_copy()` で新しいインスタンスを作成します：

```python
class WorkflowContext(Contract):
    """ワークフロー全体で必要なデータを含む Contract。"""
    # 初期データ（開始ノードで設定）
    incident_id: str
    severity: str

    # 各ノードで追加されるデータ（Optional で定義）
    hostname: str | None = None        # check_host で設定
    escalated: bool = False            # escalate で設定
    notification_sent: bool = False    # notify で設定

@node
def check_host(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
    """ホスト情報を取得するノード。"""
    hostname = lookup_hostname(ctx.incident_id)

    # model_copy で既存データを保持しつつ、新しいフィールドを追加
    new_ctx = ctx.model_copy(update={"hostname": hostname})
    return new_ctx, Outcome.success("found")

@node
def escalate(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
    """エスカレーションするノード。"""
    # ctx.incident_id, ctx.severity, ctx.hostname すべて利用可能
    do_escalation(ctx.incident_id, ctx.hostname)

    return ctx.model_copy(update={"escalated": True}), Outcome.success("done")
```

**データフロー:**

```
[開始]
  incident_id="INC-001", severity="critical"
     │
     ▼
[check_host]
  model_copy(update={"hostname": "web-01"})
     │
     ▼
  incident_id="INC-001", severity="critical", hostname="web-01"
     │
     ▼
[escalate]
  model_copy(update={"escalated": True})
     │
     ▼
  incident_id="INC-001", severity="critical", hostname="web-01", escalated=True
     │
     ▼
[終端ノード]
```

#### なぜこの設計なのか？

**代替案との比較:**

| 代替案 | 問題点 |
|--------|--------|
| グローバルコンテキスト | 暗黙的な依存、テスト困難、副作用 |
| DI コンテナ | 複雑さ増加、型安全性低下 |
| 累積辞書（dict） | 型安全性なし、IDE 補完なし |

**Railway の選択:**
- 明示的なデータフロー → 追跡可能
- Contract による型安全性 → IDE 補完、静的チェック
- イミュータブル → 副作用なし、デバッグ容易

### Transition Graph: 関係性のすべて

**Transition Graph は Node の関係性を定義する YAML です。**

```yaml
nodes:
  check_severity:
    description: "重要度をチェック"
  escalate:
    description: "エスカレーション"
  log_only:
    description: "ログ出力のみ"
  exit:
    success:
      done:
        description: "正常終了"

start: check_severity

transitions:
  check_severity:
    success::critical: escalate
    success::normal: log_only
  escalate:
    success::done: exit.success.done
  log_only:
    success::done: exit.success.done
```

Transition Graph の特徴:
- **隣接リスト形式**: 各 Node から出る遷移を列挙
- **1 状態 = 1 遷移先**: 曖昧さがない
- **任意の DAG を表現可能**: 複雑な分岐も表現できる
- **コードを変更せず関係性を変更可能**: 運用者向けインターフェース

---

## 5つの設計思想

### 1. ステートマシンの単純化

> **Railway Oriented Programming の本質は「ステートマシンの単純化」である。**

従来の ROP では「Result 型」「エラー時に終端ノードへバイパス」が強調されます。
しかし、これらは単純化の**一例**にすぎません。

```
従来の ROP:
┌──────┐    ┌──────┐    ┌──────┐
│ Ok   │───>│ Ok   │───>│ Ok   │───> 成功
└──────┘    └──────┘    └──────┘
    │           │           │
    v           v           v
┌──────────────────────────────────┐
│              Err                  │───> 失敗
└──────────────────────────────────┘
```

Result 型は状態を **2 値**（Ok/Err）に単純化しています。
これは極端な単純化であり、現実の運用では不十分なことがあります。

**Railway Framework のアプローチ:**

```
┌──────────────┐
│check_severity│
└──────────────┘
   │success::critical    │success::normal
   v                     v
┌──────────────┐    ┌──────────────┐
│   escalate   │    │   log_only   │
└──────────────┘    └──────────────┘
   │success::done        │success::done
   v                     v
┌──────────────────────────────────┐
│         exit.success.done        │
└──────────────────────────────────┘
```

**原則:**
1. 任意の Node は**列挙可能な数の状態**しか取りえない
2. 1 つの状態は**1 つの遷移先**を持つ

これにより、Result 型と同様の単純化を、より柔軟に実現します。
「成功/失敗」の 2 値ではなく、「critical/normal/timeout/not_found...」など、
ドメインに適した状態を自由に定義できます。

### 2. 実装者の関心制御

> **Node のことだけ考えればよい。**

開発者の関心を Node に集中させます:

```
┌─────────────────────────────────────────────────┐
│              開発者の関心                        │
│  ┌─────────────────────────────────────────┐   │
│  │            Node の実装                   │   │
│  │  - 入力: Contract                        │   │
│  │  - 処理: ビジネスロジック                 │   │
│  │  - 出力: Contract + Outcome              │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│         フレームワークが担当                     │
│  - Node 間の接続                                │
│  - 状態に基づく遷移                              │
│  - 実行パスの記録                               │
│  - エラー伝播                                   │
└─────────────────────────────────────────────────┘
```

Node を実装する際、以下を考える必要がありません:
- 次の Node は何か
- エラー時にどこに飛ぶか
- 実行順序の管理
- ワークフロー全体の制御

### 3. ノード中心の境界設計

> **Contract / Node / Transition Graph により「データ」「ロジック」「関係性」を分離する。**

```
┌─────────────────────────────────────────────────────────────┐
│                       ワークフロー                           │
│                                                             │
│  ┌─────────────┐                                           │
│  │  Contract   │  ← データの形を定義                        │
│  │  (データ)    │    「何を渡すか」                          │
│  └──────┬──────┘                                           │
│         │                                                   │
│  ┌──────v──────┐                                           │
│  │    Node     │  ← ロジックを実装                          │
│  │  (ロジック)  │    「何をするか」                          │
│  └──────┬──────┘                                           │
│         │                                                   │
│  ┌──────v──────┐                                           │
│  │ Transition  │  ← 関係性を定義                            │
│  │   Graph     │    「どう繋がるか」                         │
│  │  (関係性)   │                                            │
│  └─────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

この分離により:
- **Contract**: データスキーマの変更が局所化
- **Node**: ビジネスロジックの変更が局所化
- **Transition Graph**: フローの変更がコード変更なしで可能

特に Transition Graph は YAML で定義されるため、
**運用者がコードを触らずにフローを変更**できます。

### 4. 品質保証

> **TDD ベースのワークフローと、純粋関数によるテスタビリティ。**

**純粋関数としての Node:**

```python
# Node は純粋関数: 同じ入力に対して同じ出力
def test_check_severity_critical():
    ctx = AlertContext(incident_id="INC-001", severity="critical")

    result_ctx, outcome = check_severity(ctx)

    assert outcome == Outcome.success("critical")
```

テストに必要なもの:
- モック: **不要**
- DI コンテナ: **不要**
- テストダブル: **不要**

入力を作って、関数を呼んで、出力を検証するだけです。

**TDD ワークフロー:**

```
1. Red:    失敗するテストを書く
2. Green:  テストを通す最小限の実装
3. Refactor: コードを整理
```

Railway Framework は生成コマンドでテストファイルも同時に生成します:

```bash
railway new node check_severity --output AlertContext
# → src/nodes/check_severity.py       (Node)
# → src/contracts/alert_context.py    (Contract)
# → tests/nodes/test_check_severity.py (テスト)
```

### 5. ボイラープレート極小化

> **3 つのコンポーネント以外は、フレームワークが自動で実装。**

ユーザーが書くもの:

| コンポーネント | ユーザーが書く内容 |
|---------------|-------------------|
| Contract | データの型定義 |
| Node | ビジネスロジック |
| Transition Graph | YAML で関係性を定義 |

フレームワークが自動で行うこと:

| 機能 | 自動化内容 |
|------|-----------|
| コード生成 | `railway sync transition` で遷移コード生成 |
| 実行制御 | `dag_runner` がフローを実行 |
| 状態遷移 | Outcome に基づく自動遷移 |
| 実行パス記録 | `execution_path` を自動記録 |
| 終了コード | `exit_state` から自動導出 |

**例外処理について:**

高度な制御が必要な場合のみ、例外処理の 3 層構造を意識します:

```python
# Level 1: Node 単位のリトライ
@node(retries=3, retry_on=(ConnectionError,))
def fetch_data() -> ...:
    ...

# Level 2: デフォルト（例外伝播）
# 何もしなければ Python 標準の例外伝播

# Level 3: Pipeline 単位の制御
result = typed_pipeline(
    fetch_data,
    on_error=lambda e, step: handle_error(e, step),
)
```

ほとんどの場合、Level 2（何もしない）で十分です。

---

## フィールドベース依存関係

### 問題: 暗黙的なデータ依存

従来の設計では、ノード間のデータ依存が暗黙的でした。
遷移グラフ（YAML）を変更すると、データ不整合が発生する可能性がありました。

```python
# 問題: hostname はどのノードが設定する？いつ利用可能？
class AlertContext(Contract):
    incident_id: str
    hostname: str | None = None  # 暗黙的な依存
```

### 解決: ノードコードで依存を宣言

フィールドベース依存関係では、各ノードが必要とするフィールドを
**ノードコードで明示的に宣言**します。YAML 記述者はこれを知る必要がありません。

```python
@node(
    requires=["incident_id"],           # 必須: なければ実行不可
    optional=["hostname"],              # 任意: あれば使用
    provides=["escalated", "notified"], # 提供: このノードが追加するフィールド
)
def escalate(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
    if ctx.hostname:  # optional なので存在チェック
        notify_with_host(ctx.hostname)
    return ctx.model_copy(update={"escalated": True}), Outcome.success("done")
```

### 関心の分離

| 役割 | 責務 | 知る必要があること |
|------|------|------------------|
| **ノード実装者** | `@node` で依存を宣言 | ノードが必要とするフィールド |
| **YAML 記述者** | 遷移を定義 | **ノード名と Outcome のみ** |
| **フレームワーク** | 依存の自動検証 | 両方を読み取って検証 |

### sync 時の自動検証

`railway sync transition` 実行時、フレームワークが:

1. ノードコードから依存情報を抽出
2. 遷移グラフの全経路を解析
3. 各経路で requires が満たされるか検証
4. 不整合があればエラー報告

```
$ railway sync transition --entry alert_workflow

❌ 依存関係エラー: 遷移 'check_severity → escalate' が無効です

  escalate が必要とするフィールド:
    requires: [hostname]     ❌ 利用不可
    optional: []

  この時点で利用可能なフィールド:
    [incident_id, severity]

  提案:
    - check_host を経由する遷移に変更してください
```

### 実行時の依存チェック（オプション）

`dag_runner` に `check_dependencies=True` を渡すと、実行時にも依存チェックが行われます:

```python
result = dag_runner(
    start=start,
    transitions=TRANSITIONS,
    check_dependencies=True,  # 実行時依存チェック有効
)
```

実行時に `requires` が満たされていない場合、`DependencyRuntimeError` が発生します。

### 利点

| 観点 | 効果 |
|------|------|
| **関心の分離** | YAML 記述者はノード実装詳細を知らなくてよい |
| **自動検証** | sync 時に依存エラーを検出 |
| **YAML のみで変更** | 遷移グラフ変更時、ノードコード変更不要 |
| **IDE 補完** | optional フィールドの存在チェックが明確 |
| **実行時検証** | オプションで実行時にも依存チェック可能 |

---

## コンポーネント間の関係

```
┌────────────────────────────────────────────────────────────────────┐
│                         開発フロー                                  │
│                                                                    │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐        │
│  │   Contract   │    │     Node     │    │  Transition  │        │
│  │    定義      │───>│     実装     │───>│    Graph     │        │
│  └──────────────┘    └──────────────┘    └──────────────┘        │
│         │                   │                   │                 │
│         v                   v                   v                 │
│  ┌──────────────────────────────────────────────────────┐        │
│  │              railway sync transition                 │        │
│  └──────────────────────────────────────────────────────┘        │
│                            │                                      │
│                            v                                      │
│  ┌──────────────────────────────────────────────────────┐        │
│  │              生成された遷移コード                      │        │
│  │  - TRANSITION_TABLE                                  │        │
│  │  - run() / run_async()                               │        │
│  └──────────────────────────────────────────────────────┘        │
│                            │                                      │
│                            v                                      │
│  ┌──────────────────────────────────────────────────────┐        │
│  │                  dag_runner 実行                      │        │
│  └──────────────────────────────────────────────────────┘        │
│                            │                                      │
│                            v                                      │
│  ┌──────────────────────────────────────────────────────┐        │
│  │                  ExitContract                        │        │
│  │  - exit_code, exit_state, is_success                 │        │
│  │  - execution_path, iterations                        │        │
│  └──────────────────────────────────────────────────────┘        │
└────────────────────────────────────────────────────────────────────┘
```

**データフロー:**

```
初期 Contract
     │
     v
┌─────────┐  Outcome   ┌─────────┐  Outcome   ┌─────────┐
│ Node A  │──────────> │ Node B  │──────────> │ Node C  │
└─────────┘            └─────────┘            └─────────┘
     │                      │                      │
     └──────────────────────┴──────────────────────┘
                            │
                            v
                    Transition Graph
                    (どの Outcome が
                     どの Node に行くか)
                            │
                            v
                      ExitContract
                    (最終結果)
```

---

## 実践例

### シナリオ: アラート処理ワークフロー

「アラートを受け取り、重要度に応じて処理する」ワークフローを実装します。

#### 1. Contract を定義

```python
# src/contracts/alert.py
from railway import Contract

class AlertContext(Contract):
    """アラート処理のコンテキスト。"""
    incident_id: str
    severity: str        # "critical" | "warning" | "info"
    notified: bool = False
```

#### 2. Node を実装（依存宣言付き）

```python
# src/nodes/check_severity.py
from railway import node
from railway.core.dag import Outcome
from contracts.alert import AlertContext

@node(requires=["incident_id", "severity"])  # 依存を明示
def check_severity(ctx: AlertContext) -> tuple[AlertContext, Outcome]:
    """重要度をチェックし、次のアクションを決定。"""
    match ctx.severity:
        case "critical":
            return ctx, Outcome.success("critical")
        case "warning":
            return ctx, Outcome.success("warning")
        case _:
            return ctx, Outcome.success("info")
```

```python
# src/nodes/escalate.py
from railway import node
from railway.core.dag import Outcome
from contracts.alert import AlertContext

@node(
    requires=["incident_id"],
    optional=["notified"],      # あれば使用
    provides=["escalated"],     # このノードが追加
)
def escalate(ctx: AlertContext) -> tuple[AlertContext, Outcome]:
    """エスカレーションを実行。"""
    do_escalation(ctx.incident_id)
    return ctx.model_copy(update={"escalated": True}), Outcome.success("done")
```

```python
# src/nodes/exit/success/done.py
from railway import ExitContract, node

class AlertResult(ExitContract):
    """アラート処理結果。"""
    exit_state: str = "success.done"
    incident_id: str
    action_taken: str

@node(name="exit.success.done", requires=["incident_id"])
def done(ctx: AlertContext) -> AlertResult:
    return AlertResult(
        incident_id=ctx.incident_id,
        action_taken="processed",
    )
```

#### 3. Transition Graph を定義

```yaml
# transition_graphs/alert_workflow.yml
version: "1.0"
entrypoint: alert_workflow

nodes:
  check_severity:
    description: "重要度チェック"
  escalate:
    description: "エスカレーション"
  notify:
    description: "通知"
  log_only:
    description: "ログのみ"
  exit:
    success:
      done:
        description: "処理完了"

start: check_severity

transitions:
  check_severity:
    success::critical: escalate
    success::warning: notify
    success::info: log_only
  escalate:
    success::done: exit.success.done
  notify:
    success::done: exit.success.done
  log_only:
    success::done: exit.success.done
```

#### 4. 生成と実行

```bash
# 遷移コード生成
railway sync transition --entry alert_workflow

# 実行
railway run alert_workflow
```

#### 5. 関係性の変更（コード変更なし）

運用中に「info レベルも通知が必要」になった場合:

```yaml
# YAML を変更するだけ
transitions:
  check_severity:
    success::critical: escalate
    success::warning: notify
    success::info: notify  # ← log_only から notify に変更
```

Python コードの変更は不要です。

---

## まとめ

| 観点 | Railway Framework のアプローチ |
|------|-------------------------------|
| **コンポーネント** | Contract（データ）、Node（ロジック）、Transition Graph（関係性） |
| **ROP の本質** | ステートマシンの単純化。列挙可能な状態と 1:1 の遷移 |
| **関心の分離** | Node だけに集中。フロー制御はフレームワークが担当 |
| **境界設計** | データ・ロジック・関係性を明確に分離 |
| **依存管理** | フィールドベース依存関係で YAML と実装を分離 |
| **品質保証** | 純粋関数による高いテスタビリティ |
| **ボイラープレート** | 3 つのコンポーネント以外は自動化 |

---

## 関連ドキュメント

- [readme.md](../readme.md) - クイックスタートと API リファレンス
- [TUTORIAL.md](../test_project/TUTORIAL.md) - ハンズオンチュートリアル
- [Transition Graph リファレンス](transition_graph_reference.md) - YAML 仕様
- [ADR-004: Exit ノードの設計](adr/004_exit_node_design.md) - 終端ノードの設計判断
- [ADR-005: ExitContract](adr/005_exit_contract_simplification.md) - API 簡素化の設計判断
