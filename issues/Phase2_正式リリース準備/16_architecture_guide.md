# Issue #16: アーキテクチャガイド（ADR追加）

**Phase:** 2d
**優先度:** 高
**依存関係:** #10, #15
**見積もり:** 0.5日

---

## 概要

`typed_pipeline` と `dag_runner` の2つの実行モデルの関係性、
および `@entry_point`, `@node` の責務を明確化するADR（Architecture Decision Record）を作成する。

---

## 背景

Phase2でDAGワークフローを追加することで、以下が不明瞭になる懸念がある：

1. `typed_pipeline()` は廃止されるのか？
2. `dag_runner()` との使い分けは？
3. `@entry_point` の責務は何か？
4. `@node` デコレータの役割はどう変わるか？

これらを明確化し、フレームワーク利用者が混乱しないようにする。

---

## 成果物

### ADR-002: 実行モデルの共存

```markdown
# ADR-002: typed_pipeline と dag_runner の共存

## ステータス
承認済み

## コンテキスト
Railway Framework v0.10.2で条件分岐対応のDAGワークフローを追加する。
既存の typed_pipeline API との関係を明確にする必要がある。

## 決定
typed_pipeline と dag_runner を**相互排他的な実行モデル**として共存させる。

### 2つの実行モデル

| モデル | 用途 | 遷移制御 | 分岐 |
|--------|------|----------|------|
| typed_pipeline | 線形パイプライン | 順番に実行 | 不可 |
| dag_runner | 条件分岐ワークフロー | 状態ベース | 可能 |

### 使い分けガイドライン

- **typed_pipeline**: ETL、データ変換、必ず順番に実行する処理
- **dag_runner**: 運用自動化、エラーパスが複数、条件分岐

## 結果

- 既存の typed_pipeline ユーザーに影響なし
- 新規ユーザーは用途に応じて選択可能
- ドキュメントで使い分けを明確に説明
```

### ADR-003: @entry_point と @node の責務

```markdown
# ADR-003: デコレータの責務定義

## ステータス
承認済み

## コンテキスト
DAGワークフロー追加に伴い、デコレータの責務を明確化する。

## 決定

### @entry_point の責務

1. **初期化**: 設定読み込み、ロギング設定
2. **実行モデル呼び出し**: typed_pipeline() または dag_runner()
3. **結果ハンドリング**: 終了コード、エラーレポート
4. **コールバック設定**: on_step, 監査ログ

### @node の責務（DAGモデル）

1. **入力処理**: Contract を受け取る
2. **ビジネスロジック**: 純粋関数として実行
3. **出力返却**: `tuple[Contract, Outcome]`
4. **遷移非関知**: 次のノードを知らない

### @node の責務（pipelineモデル）

1. **入力処理**: Contract を受け取る
2. **変換ロジック**: 純粋関数として実行
3. **出力返却**: `Contract`

## NOT 責務（共通）

- 次のノードの呼び出し
- 遷移先の決定
- グローバル状態の変更

## 結果

- 責務が明確になり、テスト容易性が向上
- 純粋関数パラダイムが維持される
- ノードの再利用性が高まる
```

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/docs/test_architecture_guide.py
"""Tests for architecture documentation."""
import pytest
from pathlib import Path


class TestADRExists:
    """Test that ADR files exist and contain required content."""

    @pytest.fixture
    def docs_dir(self):
        """Get docs directory."""
        return Path(__file__).parent.parent.parent.parent / "docs" / "adr"

    def test_adr_002_exists(self, docs_dir):
        """ADR-002 should exist."""
        adr_path = docs_dir / "002_execution_models.md"
        assert adr_path.exists()

    def test_adr_002_content(self, docs_dir):
        """ADR-002 should contain key sections."""
        content = (docs_dir / "002_execution_models.md").read_text()
        assert "typed_pipeline" in content
        assert "dag_runner" in content
        assert "相互排他" in content or "mutually exclusive" in content.lower()

    def test_adr_003_exists(self, docs_dir):
        """ADR-003 should exist."""
        adr_path = docs_dir / "003_decorator_responsibilities.md"
        assert adr_path.exists()

    def test_adr_003_content(self, docs_dir):
        """ADR-003 should contain key sections."""
        content = (docs_dir / "003_decorator_responsibilities.md").read_text()
        assert "@entry_point" in content
        assert "@node" in content
        assert "責務" in content or "responsibilit" in content.lower()


class TestReadmeArchitectureSection:
    """Test README has architecture section."""

    @pytest.fixture
    def readme_content(self):
        """Read README.md content."""
        readme_path = Path(__file__).parent.parent.parent.parent / "readme.md"
        return readme_path.read_text()

    def test_readme_has_execution_model_comparison(self, readme_content):
        """README should compare typed_pipeline vs dag_runner."""
        assert "typed_pipeline" in readme_content
        assert "dag_runner" in readme_content

    def test_readme_has_when_to_use(self, readme_content):
        """README should explain when to use each model."""
        # Either Japanese or English
        has_guidance = (
            "使い分け" in readme_content or
            "when to use" in readme_content.lower() or
            "どちらを" in readme_content
        )
        assert has_guidance
```

### Step 2: Green（ADRファイル作成）

```bash
# ディレクトリ作成
mkdir -p docs/adr

# ADR-002 作成
cat > docs/adr/002_execution_models.md << 'EOF'
# ADR-002: 実行モデルの共存（typed_pipeline と dag_runner）

## ステータス
承認済み (2025-01-25)

## コンテキスト

Railway Framework v0.10.2で条件分岐対応のDAGワークフローを追加する。
既存の `typed_pipeline` API との関係を明確にする必要がある。

## 決定

`typed_pipeline` と `dag_runner` を**相互排他的な実行モデル**として共存させる。
1つのエントリーポイントではどちらか一方のみを使用する。

### 2つの実行モデル

| モデル | 用途 | 遷移制御 | 分岐 | Contract解決 |
|--------|------|----------|------|--------------|
| `typed_pipeline` | 線形パイプライン | 順番に実行 | 不可 | 自動 |
| `dag_runner` | 条件分岐ワークフロー | 状態ベース | 可能 | ノードが返す |

### 使い分けガイドライン

**typed_pipeline を使う:**
- 処理が必ず順番に実行される（A→B→C→D）
- 条件分岐がない
- Contract の自動解決を活用したい
- ETL、データ変換パイプライン

**dag_runner を使う:**
- 条件分岐がある（if-else, switch）
- エラーパスが複数ある
- ワークフローをYAMLで可視化したい
- 運用自動化、複雑なワークフロー

## 結果

- 既存の `typed_pipeline` ユーザーに影響なし（後方互換性維持）
- 新規ユーザーは用途に応じて選択可能
- ドキュメントで使い分けを明確に説明
- 将来的な統合の可能性を残す

## 参照

- Issue #10: DAGランナー実装
- Issue #15: @node自動マッピング & Outcome
EOF

# ADR-003 作成
cat > docs/adr/003_decorator_responsibilities.md << 'EOF'
# ADR-003: デコレータの責務定義

## ステータス
承認済み (2025-01-25)

## コンテキスト

DAGワークフロー追加に伴い、`@entry_point` と `@node` デコレータの
責務を明確化する必要がある。

## 決定

### @entry_point の責務

| 責務 | 説明 |
|------|------|
| 初期化 | 設定読み込み、ロギング設定 |
| 実行モデル呼び出し | `typed_pipeline()` または `dag_runner()` |
| 結果ハンドリング | 終了コード、エラーレポート |
| コールバック設定 | on_step, 監査ログ設定 |

### @node の責務（DAGモデル）

| 責務 | 説明 |
|------|------|
| 入力処理 | Contract を受け取る |
| ビジネスロジック | 純粋関数として実行 |
| 出力返却 | `tuple[Contract, Outcome]` |
| 遷移非関知 | 次のノードを知らない |

### @node の責務（pipelineモデル）

| 責務 | 説明 |
|------|------|
| 入力処理 | Contract を受け取る |
| 変換ロジック | 純粋関数として実行 |
| 出力返却 | `Contract` |

### NOT 責務（共通）

- 次のノードの呼び出し
- 遷移先の決定
- グローバル状態の変更
- ロギング設定（entry_pointの責務）

## 結果

- 責務が明確になり、テスト容易性が向上
- 純粋関数パラダイムが維持される
- ノードの再利用性が高まる
- 新規開発者の学習曲線が緩やかに

## 参照

- ADR-001: Output Model Pattern
- Issue #15: @node自動マッピング & Outcome
EOF
```

---

## 完了条件

- [ ] `docs/adr/002_execution_models.md` 作成
- [ ] `docs/adr/003_decorator_responsibilities.md` 作成
- [ ] README.md に使い分けガイドラインを追加（Issue #13と連携）
- [ ] TUTORIAL.md に2つのモデルの説明を追加（Issue #14と連携）
- [ ] テストが通過

---

## 関連Issue

- Issue #10: DAGランナー実装
- Issue #13: README更新（使い分けガイドライン追加）
- Issue #14: TUTORIAL更新（2つのモデルの説明追加）
- Issue #15: @node自動マッピング & Outcome

---

## 参照ドキュメント

- `.claude_output/architecture_clarification_20250125.md`
