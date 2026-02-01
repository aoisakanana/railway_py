# Issue #71: YAML スキーマの追加

## 優先度

**Medium**

## 問題

YAML の構造が文書化されておらず、エディタの補完や検証が効かない。また、旧形式と新形式の違いが明確でない。

## 解決策

JSON Schema 形式で YAML スキーマを定義し、sync コマンドや new entry コマンドで参照できるようにする。

### スキーマファイル構成

```
railway/
└── schemas/
    ├── transition_graph_v1.json      # 新形式（v0.13.0+）
    └── transition_graph_legacy.json  # 旧形式（v0.12.x 以前）
```

## 実装タスク

### 1. 新形式スキーマ定義

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "transition_graph_v1.json",
  "title": "Railway Transition Graph",
  "description": "Railway Framework の遷移グラフ定義（v0.13.0+）",
  "type": "object",
  "required": ["version", "entrypoint", "nodes", "start", "transitions"],
  "properties": {
    "version": {
      "type": "string",
      "const": "1.0",
      "description": "スキーマバージョン"
    },
    "entrypoint": {
      "type": "string",
      "pattern": "^[a-z_][a-z0-9_]*$",
      "description": "エントリポイント名"
    },
    "description": {
      "type": "string",
      "description": "ワークフローの説明"
    },
    "nodes": {
      "type": "object",
      "description": "ノード定義",
      "properties": {
        "exit": {
          "$ref": "#/definitions/exitNodes"
        }
      },
      "additionalProperties": {
        "$ref": "#/definitions/nodeDefinition"
      }
    },
    "start": {
      "type": "string",
      "description": "開始ノード名"
    },
    "transitions": {
      "type": "object",
      "description": "遷移定義",
      "additionalProperties": {
        "type": "object",
        "additionalProperties": {
          "type": "string"
        }
      }
    },
    "options": {
      "type": "object",
      "properties": {
        "max_iterations": {
          "type": "integer",
          "minimum": 1,
          "default": 100
        }
      }
    }
  },
  "definitions": {
    "nodeDefinition": {
      "type": "object",
      "properties": {
        "module": {
          "type": "string",
          "pattern": "^[a-z_][a-z0-9_.]*$"
        },
        "function": {
          "type": "string",
          "pattern": "^[a-z_][a-z0-9_]*$"
        },
        "description": {
          "type": "string"
        }
      }
    },
    "exitNodes": {
      "type": "object",
      "properties": {
        "success": {
          "type": "object",
          "additionalProperties": {
            "$ref": "#/definitions/exitNodeDefinition"
          }
        },
        "failure": {
          "type": "object",
          "additionalProperties": {
            "$ref": "#/definitions/exitNodeDefinition"
          }
        }
      }
    },
    "exitNodeDefinition": {
      "type": "object",
      "properties": {
        "module": {
          "type": "string"
        },
        "function": {
          "type": "string"
        },
        "description": {
          "type": "string"
        },
        "exit_code": {
          "type": "integer"
        }
      }
    }
  }
}
```

### 2. 旧形式スキーマ定義

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "transition_graph_legacy.json",
  "title": "Railway Transition Graph (Legacy)",
  "description": "Railway Framework の遷移グラフ定義（v0.12.x 以前）",
  "type": "object",
  "required": ["version", "entrypoint", "nodes", "exits", "start", "transitions"],
  "properties": {
    "exits": {
      "type": "object",
      "description": "終了定義（旧形式）",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "code": {
            "type": "integer"
          },
          "description": {
            "type": "string"
          }
        },
        "required": ["code"]
      }
    }
  }
}
```

### 3. スキーマ検証関数（純粋関数）

```python
# railway/core/dag/schema.py

import json
from pathlib import Path
from typing import NamedTuple

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


class SchemaValidation(NamedTuple):
    """スキーマ検証結果（イミュータブル）。"""
    is_valid: bool
    errors: tuple[str, ...]
    schema_version: str


def validate_yaml_schema(data: dict) -> SchemaValidation:
    """YAML データをスキーマで検証（純粋関数）。

    Args:
        data: パース済み YAML データ

    Returns:
        SchemaValidation: 検証結果
    """
    if not HAS_JSONSCHEMA:
        return SchemaValidation(
            is_valid=True,
            errors=(),
            schema_version="unknown"
        )

    # スキーマ選択
    if "exits" in data:
        schema_file = "transition_graph_legacy.json"
        schema_version = "legacy"
    else:
        schema_file = "transition_graph_v1.json"
        schema_version = "v1"

    schema_path = Path(__file__).parent.parent.parent / "schemas" / schema_file
    schema = json.loads(schema_path.read_text())

    errors = []
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        errors.append(str(e.message))

    return SchemaValidation(
        is_valid=len(errors) == 0,
        errors=tuple(errors),
        schema_version=schema_version
    )
```

### 4. テスト作成

```python
# tests/unit/core/dag/test_schema.py

class TestYamlSchema:
    """YAML スキーマ検証のテスト。"""

    def test_valid_v1_yaml(self):
        """新形式 YAML は検証をパス。"""
        data = {
            "version": "1.0",
            "entrypoint": "greeting",
            "nodes": {"start": {"description": "開始"}},
            "start": "start",
            "transitions": {}
        }
        result = validate_yaml_schema(data)
        assert result.is_valid
        assert result.schema_version == "v1"

    def test_legacy_yaml_detected(self):
        """旧形式 YAML は legacy として検出。"""
        data = {
            "version": "1.0",
            "entrypoint": "greeting",
            "nodes": {},
            "exits": {"success": {"code": 0}},
            "start": "start",
            "transitions": {}
        }
        result = validate_yaml_schema(data)
        assert result.schema_version == "legacy"

    def test_invalid_yaml_returns_errors(self):
        """無効な YAML はエラーを返す。"""
        data = {"version": "1.0"}  # 必須フィールド不足
        result = validate_yaml_schema(data)
        assert not result.is_valid
        assert len(result.errors) > 0
```

### 5. sync コマンドへの統合

```python
# railway/cli/sync.py

def _sync_entry(...) -> None:
    ...
    # スキーマ検証（オプション）
    if HAS_JSONSCHEMA:
        import yaml
        data = yaml.safe_load(yaml_path.read_text())
        validation = validate_yaml_schema(data)
        if not validation.is_valid:
            for error in validation.errors:
                typer.echo(f"  スキーマエラー: {error}", err=True)
    ...
```

## 影響範囲

| ファイル | 変更内容 |
|----------|----------|
| `railway/schemas/transition_graph_v1.json` | 新規（新形式スキーマ） |
| `railway/schemas/transition_graph_legacy.json` | 新規（旧形式スキーマ） |
| `railway/core/dag/schema.py` | 新規（検証関数） |
| `railway/cli/sync.py` | スキーマ検証統合（オプション） |
| `tests/unit/core/dag/test_schema.py` | 新規テスト |

## オプション依存

- `jsonschema` パッケージはオプション依存
- インストールされていない場合はスキーマ検証をスキップ

```toml
# pyproject.toml
[project.optional-dependencies]
schema = ["jsonschema>=4.0.0"]
```

## 完了条件

- [ ] 新形式スキーマ定義
- [ ] 旧形式スキーマ定義
- [ ] 検証関数実装
- [ ] テストが全てパス
- [ ] ドキュメントにスキーマ参照方法を記載
