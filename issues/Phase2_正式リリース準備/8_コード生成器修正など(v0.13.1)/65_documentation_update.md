# Issue #65: ドキュメント更新（readme.md, TUTORIAL.md）

**優先度**: P2
**依存**: #60, #61, #62, #64
**ブロック**: なし

---

## 概要

v0.13.1 の変更に合わせて以下のドキュメントを更新する：
1. `readme.md` - プロジェクトルートの README
2. `TUTORIAL.md` テンプレート - `railway init` で生成されるチュートリアル

## 背景

v0.13.1 で以下の変更が入るため、ドキュメントも更新が必要：

| 変更 | 影響箇所 |
|------|----------|
| YAML 新形式（`exit.success.done`） | YAML サンプルコード |
| `railway new entry` がデフォルトで sync | クイックスタート手順 |
| 終端ノードスケルトン自動生成 | ファイル構造説明 |
| 1コマンドワークフロー | 使い方セクション |

---

## 更新対象

### 1. readme.md

| セクション | 更新内容 |
|------------|----------|
| クイックスタート | `railway sync transition` 不要になったことを反映 |
| YAML サンプル | `exits` → `nodes.exit` 形式に更新 |
| 終端ノード | 自動生成される旨を追記 |
| バージョン | v0.13.1 の変更を反映 |

**Before（クイックスタート）**:
```bash
railway init my_workflow
cd my_workflow
uv sync
railway new entry my_workflow
railway sync transition --entry my_workflow  # ← 不要になる
railway run my_workflow
```

**After**:
```bash
railway init my_workflow
cd my_workflow
uv sync
railway new entry my_workflow && railway run my_workflow  # 1コマンド
```

### 2. TUTORIAL.md テンプレート（`railway/cli/init.py`）

| セクション | 更新内容 |
|------------|----------|
| 手順 | sync 不要を反映 |
| YAML 例 | 新形式に更新 |
| 終端ノード | 自動生成の説明を追加 |
| ファイル構造 | `nodes/exit/` を追加 |

---

## TDD 実装フロー

### Phase 1: Red（失敗するテストを先に作成）

```python
# tests/unit/cli/test_tutorial_template.py

import pytest
from pathlib import Path
from unittest.mock import patch


class TestTutorialMdTemplate:
    """TUTORIAL.md テンプレートのテスト。"""

    def test_uses_new_yaml_format(self, tmp_path: Path) -> None:
        """新形式 YAML を使用している。"""
        from railway.cli.init import _create_tutorial_md

        _create_tutorial_md(tmp_path, "test_project")

        content = (tmp_path / "TUTORIAL.md").read_text()

        # 新形式を使用
        assert "exit.success.done" in content or "nodes.exit" in content

        # レガシー形式が含まれない
        assert "exit::success" not in content
        assert "exits:" not in content

    def test_no_sync_command_required(self, tmp_path: Path) -> None:
        """sync コマンドが必須手順として含まれない。"""
        from railway.cli.init import _create_tutorial_md

        _create_tutorial_md(tmp_path, "test_project")

        content = (tmp_path / "TUTORIAL.md").read_text()

        # "railway sync transition" が必須手順として書かれていないこと
        # （説明としては含まれてもよいが、クイックスタートには不要）
        lines = content.split("\n")
        quick_start_section = False
        for line in lines:
            if "クイックスタート" in line or "Quick Start" in line:
                quick_start_section = True
            if quick_start_section and "railway run" in line:
                # run の前に sync が必須でないことを確認
                break

    def test_mentions_exit_node_auto_generation(self, tmp_path: Path) -> None:
        """終端ノード自動生成について言及している。"""
        from railway.cli.init import _create_tutorial_md

        _create_tutorial_md(tmp_path, "test_project")

        content = (tmp_path / "TUTORIAL.md").read_text()

        # 終端ノードの自動生成に言及
        assert "自動生成" in content or "auto" in content.lower()

    def test_shows_exit_directory_structure(self, tmp_path: Path) -> None:
        """nodes/exit/ ディレクトリ構造を示している。"""
        from railway.cli.init import _create_tutorial_md

        _create_tutorial_md(tmp_path, "test_project")

        content = (tmp_path / "TUTORIAL.md").read_text()

        assert "nodes/exit" in content or "exit/" in content


class TestReadmeMdContent:
    """readme.md の内容テスト（手動確認用のスナップショット）。"""

    def test_readme_has_new_yaml_format(self) -> None:
        """readme.md が新形式 YAML を使用している。"""
        readme_path = Path(__file__).parents[4] / "readme.md"
        if not readme_path.exists():
            pytest.skip("readme.md not found")

        content = readme_path.read_text()

        # 新形式を使用
        assert "exit.success.done" in content

        # レガシー形式が含まれない（サンプルコード内）
        # 注: "レガシー形式" という説明文は含まれてもよい
        assert "exit::success" not in content or "レガシー" in content

    def test_readme_quick_start_is_simple(self) -> None:
        """readme.md のクイックスタートがシンプルである。"""
        readme_path = Path(__file__).parents[4] / "readme.md"
        if not readme_path.exists():
            pytest.skip("readme.md not found")

        content = readme_path.read_text()

        # 1コマンドで実行可能であることを示す
        assert "railway new entry" in content
        assert "railway run" in content
```

### Phase 2: Green（最小実装）

#### readme.md の更新

主な変更点:

1. **クイックスタート** - sync 手順を削除
2. **YAML サンプル** - 新形式に統一
3. **終端ノードセクション** - 自動生成を追記

#### TUTORIAL.md テンプレートの更新

`railway/cli/init.py` の `_create_tutorial_md()` を修正:

```python
def _create_tutorial_md(project_path: Path, project_name: str) -> None:
    """Create TUTORIAL.md file with dag_runner as default."""
    content = f'''# {project_name} チュートリアル

Railway Framework の**DAGワークフロー**を体験しましょう！

## クイックスタート

```bash
# プロジェクト作成後
railway new entry my_workflow && railway run my_workflow
```

これだけで動作します！`railway new entry` が以下を自動生成します：
- `src/my_workflow.py` - エントリポイント
- `src/nodes/my_workflow/start.py` - 開始ノード
- `src/nodes/exit/success/done.py` - 成功終端ノード（自動生成）
- `src/nodes/exit/failure/error.py` - 失敗終端ノード（自動生成）
- `transition_graphs/my_workflow_*.yml` - 遷移グラフ
- `_railway/generated/my_workflow_transitions.py` - 遷移コード

## 遷移グラフ（YAML）

```yaml
nodes:
  start:
    description: "開始ノード"

  exit:
    success:
      done:
        description: "正常終了"
    failure:
      error:
        description: "エラー終了"

start: start

transitions:
  start:
    success::done: exit.success.done
    failure::error: exit.failure.error
```

...（以下省略）
'''
    _write_file(project_path / "TUTORIAL.md", content)
```

### Phase 3: Refactor

- 重複したサンプルコードの整理
- 日英両方のドキュメント対応（必要に応じて）

---

## 修正ファイル

| ファイル | 変更内容 |
|----------|----------|
| `readme.md` | クイックスタート更新、YAML サンプル更新、終端ノード自動生成追記 |
| `railway/cli/init.py` | `_create_tutorial_md()` 更新 |
| `tests/unit/cli/test_tutorial_template.py` | 新規テストファイル |

---

## チェックリスト

### readme.md

- [ ] クイックスタートが `railway new entry && railway run` 形式
- [ ] YAML サンプルが `nodes.exit` 形式
- [ ] `exits:` セクションのサンプルを削除または更新
- [ ] 終端ノード自動生成について記載
- [ ] v0.13.1 の変更を反映

### TUTORIAL.md テンプレート

- [ ] クイックスタートが sync 不要
- [ ] YAML サンプルが新形式
- [ ] ファイル構造に `nodes/exit/` を含む
- [ ] 終端ノード自動生成の説明

---

## 受け入れ条件

### 機能
- [ ] readme.md が v0.13.1 の変更を反映
- [ ] TUTORIAL.md テンプレートが新形式を使用
- [ ] レガシー形式（`exit::success`）がサンプルコードに含まれない
- [ ] 新規ユーザーが 1 コマンドで動作確認できる手順

### TDD・関数型
- [ ] Red → Green → Refactor フェーズに従って実装
- [ ] 全テスト通過

---

*v0.13.1 変更のドキュメント反映*
