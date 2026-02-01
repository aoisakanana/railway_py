# Issue #70: エラーメッセージの改善

## 優先度

**High**

## 問題

型エラーや設定エラー時のメッセージが技術的すぎて、修正方法がわかりにくい。

### 現状

```
TypeError: start() takes 0 positional arguments but 1 was given
```

### 期待される動作

```
Error: 開始ノード 'start' は引数を受け取る必要があります。

Hint: 以下のように修正してください:
  def start(ctx: Context | None = None) -> tuple[Context, Outcome]:
      ...

詳細: https://railway-framework.readthedocs.io/errors/E001
```

## 解決策

### 設計方針

1. **エラーコード導入**: `E001`, `E002` などの識別子
2. **ユーザーフレンドリーなメッセージ**: 問題と解決策を明示
3. **Hint 表示**: 具体的な修正例
4. **ドキュメントリンク**: 詳細情報への誘導

### エラーメッセージ構造

```python
@dataclass(frozen=True)
class RailwayError:
    """Railway フレームワークのエラー（イミュータブル）。"""
    code: str           # "E001"
    title: str          # "開始ノードの引数エラー"
    message: str        # 詳細メッセージ
    hint: str | None    # 修正提案
    doc_url: str | None # ドキュメントURL
```

## 実装タスク

### 1. エラーカタログ定義（純粋関数）

```python
# railway/core/errors.py

from dataclasses import dataclass
from typing import NamedTuple


@dataclass(frozen=True)
class ErrorInfo:
    """エラー情報（イミュータブル）。"""
    code: str
    title: str
    message_template: str
    hint_template: str | None = None


# エラーカタログ（イミュータブル）
ERROR_CATALOG: dict[str, ErrorInfo] = {
    "E001": ErrorInfo(
        code="E001",
        title="開始ノードの引数エラー",
        message_template="開始ノード '{node_name}' は引数を受け取る必要があります。",
        hint_template="def {node_name}(ctx: Context | None = None) -> tuple[Context, Outcome]:",
    ),
    "E002": ErrorInfo(
        code="E002",
        title="モジュールが見つかりません",
        message_template="モジュール '{module}' が見つかりません。",
        hint_template="YAML の module パスを確認してください: {expected_path}",
    ),
    "E003": ErrorInfo(
        code="E003",
        title="無効な識別子",
        message_template="'{identifier}' は Python の識別子として使用できません。",
        hint_template="'{suggestion}' に変更してください。",
    ),
    "E004": ErrorInfo(
        code="E004",
        title="終端ノードの戻り値エラー",
        message_template="終端ノード '{node_name}' は ExitContract を返す必要があります。",
        hint_template="return {class_name}Result(...) のように ExitContract サブクラスを返してください。",
    ),
}


DOC_BASE_URL = "https://github.com/your-org/railway-framework/wiki/errors"


def format_error(code: str, **kwargs) -> str:
    """エラーメッセージをフォーマット（純粋関数）。

    Args:
        code: エラーコード
        **kwargs: テンプレート変数

    Returns:
        フォーマットされたエラーメッセージ
    """
    info = ERROR_CATALOG.get(code)
    if info is None:
        return f"Unknown error: {code}"

    lines = [
        f"Error [{info.code}]: {info.title}",
        "",
        info.message_template.format(**kwargs),
    ]

    if info.hint_template:
        lines.extend([
            "",
            "Hint:",
            f"  {info.hint_template.format(**kwargs)}",
        ])

    # ドキュメントリンク（オプション）
    lines.extend([
        "",
        f"詳細: {DOC_BASE_URL}/{code}",
    ])

    return "\n".join(lines)
```

### 2. テスト作成（Red）

```python
# tests/unit/core/test_errors.py

class TestErrorCatalog:
    """エラーカタログのテスト。"""

    def test_format_error_with_valid_code(self):
        """有効なエラーコードでメッセージが生成される。"""
        result = format_error("E001", node_name="start")
        assert "E001" in result
        assert "start" in result
        assert "Hint:" in result

    def test_format_error_with_unknown_code(self):
        """未知のエラーコードでもクラッシュしない。"""
        result = format_error("E999")
        assert "Unknown error" in result

    def test_all_catalog_entries_have_required_fields(self):
        """カタログの全エントリに必須フィールドがある。"""
        for code, info in ERROR_CATALOG.items():
            assert info.code == code
            assert info.title
            assert info.message_template
```

### 3. dag_runner への統合

```python
# railway/core/dag/runner.py

def dag_runner(...) -> ExitContract:
    ...
    try:
        context, outcome = current_node(context)
    except TypeError as e:
        if "positional arguments" in str(e):
            node_name = getattr(current_node, "_node_name", "unknown")
            error_msg = format_error("E001", node_name=node_name)
            raise DagRunnerError(error_msg) from e
        raise
    ...
```

## 影響範囲

| ファイル | 変更内容 |
|----------|----------|
| `railway/core/errors.py` | 新規（エラーカタログ） |
| `railway/core/dag/runner.py` | エラーハンドリング改善 |
| `railway/cli/sync.py` | エラーメッセージ改善 |
| `tests/unit/core/test_errors.py` | 新規テスト |

## エラーコード一覧

| コード | タイトル | 発生箇所 |
|--------|----------|----------|
| E001 | 開始ノードの引数エラー | dag_runner |
| E002 | モジュールが見つかりません | sync transition |
| E003 | 無効な識別子 | sync transition |
| E004 | 終端ノードの戻り値エラー | dag_runner |

## 完了条件

- [ ] エラーカタログが実装されている
- [ ] 主要なエラーにユーザーフレンドリーなメッセージが表示される
- [ ] Hint が表示される
- [ ] テストが全てパス
