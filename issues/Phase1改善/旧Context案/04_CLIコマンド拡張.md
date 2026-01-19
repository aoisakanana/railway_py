# Issue #04: CLIコマンド拡張（add/remove node）

## 概要
`railway add node` と `railway remove node` コマンドを追加し、エントリーポイントのコンテキスト定義にnodeを登録・解除できるようにする。

## 依存関係
- Issue #01: コンテキスト変数基本設計（先行）
- Issue #02: Contextクラス実装（先行）

## 既存コマンドとの関係

| コマンド | 用途 |
|---------|------|
| `railway new node <name>` | nodeファイルを新規作成（既存） |
| `railway add node <name> --entry <entry>` | nodeをエントリーポイントに登録（新規） |
| `railway remove node <name> --entry <entry>` | nodeをエントリーポイントから解除（新規） |

**ワークフロー**:
1. `railway new node fetch_data` でnodeファイル作成
2. `railway add node fetch_data --entry my_entry` でエントリーポイントに登録

## 新しいCLIコマンド

### railway add node
```bash
# 単一nodeを登録
railway add node fetch_data --entry my_entry

# 複数nodeを登録
railway add node fetch_data process_data save_data --entry my_entry

# 順序を指定して登録
railway add node validate_data --entry my_entry --after fetch_data
railway add node validate_data --entry my_entry --before process_data
```

#### 動作
1. `src/<entry>/context.yaml`を読み込み
2. `nodes`配列にnode名を追加
3. ファイルを保存
4. 対応するnodeファイルが存在しない場合は警告

### railway remove node
```bash
# 単一nodeを解除
railway remove node fetch_data --entry my_entry

# 複数nodeを解除
railway remove node fetch_data process_data --entry my_entry
```

#### 動作
1. `src/<entry>/context.yaml`を読み込み
2. `nodes`配列からnode名を削除
3. ファイルを保存

### railway list nodes
```bash
railway list nodes --entry my_entry
```

出力例:
```
Entry point: my_entry
Registered nodes (3):
  1. fetch_data
  2. process_data
  3. save_data
```

## ディレクトリ構造

既存のRailway構造に合わせる:
```
src/
  my_entry.py              # エントリーポイント（既存形式）
  my_entry/
    context.yaml           # コンテキスト定義（新規）
  nodes/
    fetch_data.py
    process_data.py
    save_data.py
```

または新形式:
```
src/
  entries/
    my_entry/
      __init__.py          # エントリーポイント実装
      context.yaml         # コンテキスト定義
  nodes/
    fetch_data.py
    process_data.py
```

**決定**: 既存形式との互換性を優先し、`src/<entry>/context.yaml`を採用

## context.yaml の形式

```yaml
# src/my_entry/context.yaml
entry_point: my_entry
nodes:
  - fetch_data
  - process_data
  - save_data
```

**注意**: paramsのスキーマ定義は将来の拡張として保留

## 実装要件

### CLIコマンド
```python
import click

@cli.command("add")
@click.argument("resource", type=click.Choice(["node"]))
@click.argument("names", nargs=-1, required=True)
@click.option("--entry", required=True, help="Entry point name")
@click.option("--after", help="Insert after this node")
@click.option("--before", help="Insert before this node")
def add_resource(resource, names, entry, after, before):
    """Add resources to an entry point."""
    if resource == "node":
        add_nodes_to_entry(names, entry, after, before)

@cli.command("remove")
@click.argument("resource", type=click.Choice(["node"]))
@click.argument("names", nargs=-1, required=True)
@click.option("--entry", required=True, help="Entry point name")
def remove_resource(resource, names, entry):
    """Remove resources from an entry point."""
    if resource == "node":
        remove_nodes_from_entry(names, entry)
```

### コンテキスト定義の読み書き
```python
from pathlib import Path
import yaml

def load_context_definition(entry_name: str) -> dict:
    """context.yamlを読み込み"""
    path = Path("src") / entry_name / "context.yaml"
    if not path.exists():
        return {"entry_point": entry_name, "nodes": []}
    with open(path) as f:
        return yaml.safe_load(f)

def save_context_definition(entry_name: str, definition: dict) -> None:
    """context.yamlを保存"""
    path = Path("src") / entry_name / "context.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(definition, f, default_flow_style=False, allow_unicode=True)
```

## テスト要件
- `railway add node` コマンド動作
- `railway remove node` コマンド動作
- `railway list nodes` コマンド動作
- context.yaml の読み書き
- `--after`/`--before`オプション
- エラーケース（存在しないentry、重複node、存在しないnode指定等）

## 関連ファイル
- 修正: `railway/cli.py`
- 新規: `railway/core/context_definition.py`

## 優先度
最高
