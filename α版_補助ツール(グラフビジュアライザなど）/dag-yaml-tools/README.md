# DAG YAML Tools

隣接リスト形式のYAMLで定義されたDAG（有向非巡回グラフ）を検証・可視化するCLIツール。

## 機能

- **検証**: 循環検出、到達可能性、未定義参照など6種類のチェック
- **可視化**: Cytoscape.js（インタラクティブ・推奨）、pyvis（HTML）、Graphviz（PNG）
- **インタラクティブ編集**: ノード/エッジの追加・編集・削除、グループ管理、YAML出力

## インストール

### 依存パッケージ

```bash
pip install -r requirements.txt
```

### Graphviz（PNG出力に必要）

```bash
# Ubuntu
sudo apt install graphviz

# macOS
brew install graphviz

# Windows
choco install graphviz
```

## 使用方法

### 検証

```bash
python validate_dag.py <yaml_file>
```

出力例:
```
✓ DAG検証: OK（循環なし）
✓ 到達可能性: OK
✓ 未定義ノード参照: OK
✓ 未使用ノード: OK
✓ 孤立ノード: OK
✓ 遷移元の網羅性: OK

検証完了: すべてのチェックに合格しました
```

### 可視化

```bash
# Cytoscape.js出力（デフォルト・推奨）
python visualize_dag.py <yaml_file>

# PNG出力（静的画像）
python visualize_dag.py <yaml_file> --format png

# Legacy出力（pyvis HTML・旧形式）
python visualize_dag.py <yaml_file> --format legacy

# 全形式出力
python visualize_dag.py <yaml_file> --format all

# 出力先指定
python visualize_dag.py <yaml_file> --output ./output/graph
```

### 出力形式

| 形式 | オプション | 説明 |
|------|-----------|------|
| Cytoscape.js | `cytoscape`（デフォルト） | 高機能インタラクティブビューア |
| PNG | `png` | Graphvizによる静的画像 |
| Legacy | `legacy` | pyvisによるHTML（旧形式） |
| All | `all` | 全形式を出力 |

## Cytoscape.js ビューア機能

### メニュー構成

| メニュー | 機能 |
|---------|------|
| **表示** | リセット / 全体表示 / ラベル切替 |
| **効果** | ハイライト / ローライト / 非表示 / 解除 / 復元 |
| **状態ラベル** | 展開 / 収束 |
| **色** | 設定（背景色・枠線・文字の縁・文字色） |
| **追加** | ノード / エッジ |
| **エッジ編集** | 付替 / 戻す / 全リセット |
| **統合** | 選択ノード / プレフィックス指定 / グループ内 / 戻す / 全リセット |
| **グループ** | 作成 / ノード追加 / ノード除外 |
| **出力** | YAML |

### 表示効果

| 機能 | 説明 |
|------|------|
| **ハイライト** | 選択したノード/エッジを強調、他を薄く表示 |
| **ローライト** | 選択したノード/エッジを薄く表示 |
| **非表示** | 選択したノード/エッジを非表示（復元可能） |

### 状態ラベル

統合されたエッジは「Any」ラベルで表示されますが、元の状態一覧を確認できます。

| 操作 | 説明 |
|------|------|
| エッジ/ノードを選択 → **展開** | 「Any」を元の状態一覧に展開表示 |
| **収束** | 展開したラベルを「Any」に戻す |

### 色設定

ノード・エッジ・グループの色をカスタマイズできます。

| 項目 | 説明 | 適用対象 |
|------|------|---------|
| **背景色** | ノードの塗りつぶし / エッジの線色 | 全要素 |
| **枠線** | ノードの外枠の色 | ノード・グループ |
| **文字の縁** | ラベルのアウトライン色 | ノード・グループ |
| **文字色** | ラベルの文字色 | 全要素 |

### ノード・エッジ追加

| ダイアログ | 入力項目 |
|-----------|---------|
| **ノード追加** | ノードID、ノードタイプ（処理/成功終端/失敗終端）、説明 |
| **エッジ追加** | 接続元、接続先、ラベル（状態名） |

### エッジ編集

| 操作 | 説明 |
|------|------|
| **付替: OFF/ON** | エッジ編集モードの切替 |
| エッジをクリック | 接続先を変更するダイアログを表示 |
| **戻す** | 直前の変更を取り消し（履歴数表示） |
| **全リセット** | すべてのエッジ変更を元に戻す |

### ノード統合

複数のノードを1つに統合して表示を簡略化できます。

| 方法 | 説明 |
|------|------|
| **選択ノード** | Ctrl+クリックで選択したノードを統合 |
| **プレフィックス指定** | 指定プレフィックスを持つノードを統合（例: `api.response`） |
| **グループ内** | SUCCESS/FAILUREグループ内のノードを統合 |

- 統合されたノードは紫色で表示
- 接続エッジのラベルは「Any」に統一
- **戻す**/**全リセット**で元に戻せる

### グループ管理

ノードを視覚的にグループ化できます（YAML構造には影響しません）。

| 操作 | 説明 |
|------|------|
| **作成** | 選択したノードで新しいグループを作成（名前・色を指定） |
| **ノード追加** | 選択したノードを既存グループに追加 |
| **ノード除外** | 選択したノードをグループから除外 |

### YAML出力

現在の表示状態をYAMLファイルとして出力できます。

- ファイル名: `dag_export_YYYYMMDD_HHMMSS.yaml`
- 非表示にしたノード/エッジは出力されない
- エッジの付け替え、ノードの追加が反映される
- 統合されたノードは統合後の状態で出力

## YAML形式

```yaml
start: start_node

nodes:
  start_node:
    description: "開始ノード"
  process_a:
  process_b:
  exit:
    success:
      pattern1:
        description: "成功パターン1"
    failure:
      unknown:

transitions:
  start_node:
    success: process_a
    failure: exit.failure.unknown
  process_a:
    done: process_b
  process_b:
    success: exit.success.pattern1
    failure: exit.failure.unknown
```

### 構造

| セクション | 必須 | 説明 |
|-----------|------|------|
| `start` | ○ | エントリーポイントのノード名 |
| `nodes` | ○ | ノード定義（ネスト構造可） |
| `transitions` | ○ | 状態遷移の定義 |

### ノード定義

- ネスト構造はドット区切りでフラット化される
- `exit.success.pattern1` のように階層を表現
- メタデータ（`description`, `module`, `function`）はオプション

### 終端ノード

- `exit.` で始まるノードは終端ノードとして扱われる
- `exit.success.*`: 成功系（緑色で表示）
- `exit.failure.*`: 失敗系（赤色で表示）

## 検証項目

| 項目 | 説明 |
|-----|------|
| DAG検証 | 循環がないことを確認 |
| 到達可能性 | 開始ノードから全終端ノードに到達可能か |
| 未定義ノード参照 | 遷移先が定義済みか |
| 未使用ノード | 定義のみで未使用のノード |
| 孤立ノード | 入次数・出次数ともに0のノード |
| 遷移元の網羅性 | 非終端ノードに遷移定義があるか |

## 可視化の色分け

| ノード種別 | 判定条件 | 色 |
|-----------|---------|-----|
| 開始ノード | `start` で指定 | 青 |
| 成功終端 | `exit.success.*` | 緑 |
| 失敗終端 | `exit.failure.*` | 赤 |
| 処理ノード | 上記以外 | グレー |
| 統合ノード | 複数ノードを統合 | 紫 |

## 開発

### セットアップ

```bash
# 開発用依存パッケージ
pip install -r requirements-dev.txt

# パッケージを開発モードでインストール
pip install -e .
```

### テスト実行

```bash
# 全テスト
pytest

# 特定のテスト
pytest tests/test_parser.py -v

# カバレッジ付き
pytest --cov=src/dag_yaml_tools
```

### 型チェック

```bash
mypy src/
```

## プロジェクト構成

```
dag-yaml-tools/
├── src/
│   └── dag_yaml_tools/
│       ├── __init__.py
│       ├── parser.py       # YAML解析・グラフ構築
│       ├── validators.py   # 検証関数群
│       └── visualizers.py  # 可視化関数群
├── tests/
│   ├── test_parser.py
│   ├── test_validators.py
│   ├── test_visualizers.py
│   └── integration/
├── examples/
│   ├── sample.yaml
│   └── sample_cytoscape.html  # Cytoscape.jsサンプル
├── validate_dag.py         # 検証CLI
├── visualize_dag.py        # 可視化CLI
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml
```

## ライセンス

MIT
