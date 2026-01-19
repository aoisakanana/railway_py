# Issue #11: TDD Red Phase省略問題対応

## 概要
TUTORIAL.mdのStep 2でTDDのRed Phaseが省略されており、実装が同時に提供されている。

## 問題点
- TDDの本質である「Red → Green → Refactor」サイクルが体験できない
- テストが失敗する状態を経験しないため、TDDの意義が伝わりにくい
- 「テストファーストの開発」の概念が薄れている

## 現状のチュートリアル構成
1. テストを書く
2. 実装を書く（同時に提供）
3. テストを実行（すぐに成功）

## 提案される解決策
Red Phaseを明示的に体験できるようチュートリアルを改善する。

### 改善案

```markdown
## Step 2: TDDワークフロー

### 2.1 テストを書く（Red Phase）
まず、失敗するテストを書きます。

```python
# tests/nodes/test_fetch_user.py
import pytest
from railway import Context

class TestFetchUser:
    def test_fetch_user_returns_user_data(self):
        from nodes.fetch_user import fetch_user

        ctx = Context(entry_point="test")
        ctx.register_node("fetch_user")
        ctx.set_param("user_id", 1)

        fetch_user(ctx)

        assert "fetch_user" in ctx
        assert ctx["fetch_user"]["id"] == 1
```

### 2.2 テストを実行して失敗を確認
```bash
uv run pytest tests/nodes/test_fetch_user.py -v
# → FAILED（まだ実装がないため）
```

**これがTDDの「Red」フェーズです。テストが失敗することを確認することが重要です。**

### 2.3 最小限の実装を書く（Green Phase）
テストを通すための最小限の実装を書きます。

```python
# src/nodes/fetch_user.py
from railway import node
from railway.core.context import Context

@node
def fetch_user(ctx: Context) -> None:
    """ユーザー情報を取得"""
    user_id = ctx.get_param("user_id")
    ctx["fetch_user"] = {"id": user_id, "name": "User"}
```

### 2.4 テストを実行して成功を確認
```bash
uv run pytest tests/nodes/test_fetch_user.py -v
# → PASSED
```

**これがTDDの「Green」フェーズです。**

### 2.5 リファクタリング（Refactor Phase）
必要に応じてコードを改善します（例：実際のDB接続、エラーハンドリング追加）。
```

**注意**: コード例はIssue #01-05のContext変数アーキテクチャに準拠。

## 優先度
中

## 依存関係
- Issue #01-05: コンテキスト変数アーキテクチャ（先行）

## 関連ファイル
- `TUTORIAL.md`

## 参考情報
ユーザーレビューより:
> Step 2のTDDでRed Phaseを省略している（実装を同時に提供）
