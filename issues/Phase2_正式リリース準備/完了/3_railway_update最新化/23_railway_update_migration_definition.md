# Issue #23: railway update マイグレーション定義の実装

**Phase:** 2f
**優先度:** 高
**依存関係:** Issue #12, #17, #21（全て完了済み）
**見積もり:** 1日

---

## 概要

`railway update` コマンドのマイグレーションレジストリにマイグレーション定義を追加し、
v0.10.1 以前の既存プロジェクトを v0.11.3（DAGネイティブサポート）へ移行できるようにする。

---

## この改善がユーザーにもたらす恩恵

### 1. 既存プロジェクトを壊さずにアップグレード

| 手動アップグレード | `railway update` |
|------------------|------------------|
| 何が変わったか自分で調べる | **自動検出＆ガイダンス表示** |
| ディレクトリを手動で作成 | **自動作成** |
| コードを1つずつ修正 | **変更箇所を一覧表示** |

### 2. 安全なプレビュー機能

```bash
# 何が変わるか事前に確認（実行前に安心）
railway update --dry-run
```

### 3. 最新機能をすぐに使える

- DAGワークフロー（条件分岐）
- `railway new node` の新テンプレート
- YAML遷移グラフ

---

## 背景：v0.10.1 → v0.11.3 での主な変更

以下は `./issues/Phase2_正式リリース準備/完了/2/` 配下のissueで実装された変更:

| Issue | 変更内容 | マイグレーション対応 |
|-------|----------|---------------------|
| #001 | DAGパイプラインネイティブサポート | CodeGuidance（旧形式ノード検出） |
| #012 | プロジェクトテンプレート更新 | **FileChange**（ディレクトリ追加） |
| #017 | `railway new entry` デフォルト変更 | CodeGuidance（旧エントリポイント検出） |
| #021 | `railway new node` テンプレート最新化 | CodeGuidance（dict形式ノード検出） |

### git log v0.10.1..HEAD

```
ff9f289 v0.11.2
4f43976 railway new node コマンドが古いコードを生成していた問題を修正
fc2ea44 railway new node 対応issue
924ecc9 v0.11.1 railway run entrypoint が動作しない不具合修正
aedc70e v0.11.0
1bee06e DAG Workflowへのネイティブサポート実装
```

---

## 実装スコープ

### Phase 1: ディレクトリ追加マイグレーション（FileChange）

v0.10.1以前のプロジェクトには以下が存在しない:

```
# 追加するディレクトリ（Issue #12）
transition_graphs/          # 遷移グラフYAML
_railway/generated/         # 自動生成コード
```

**FileChange定義:**

```python
FileChange.create(
    path="transition_graphs/.gitkeep",
    content="# Transition graph YAML files\n",
    description="DAGワークフロー用ディレクトリを追加",
),
FileChange.create(
    path="_railway/generated/.gitkeep",
    content="# Auto-generated code\n",
    description="自動生成コード用ディレクトリを追加",
),
```

### Phase 2: 旧形式コード検出（CodeGuidance）

**検出パターン1: dict を返すノード（Issue #021）**

```python
CodeGuidance(
    description="dict 型を tuple[Contract, Outcome] に変更してください",
    pattern=r"@node\s*\ndef\s+\w+\([^)]*\)\s*->\s*dict:",
    replacement="# → tuple[YourContext, Outcome] を返すように変更",
    file_patterns=("src/nodes/**/*.py",),
)
```

**検出パターン2: data: dict パラメータ**

```python
CodeGuidance(
    description="data: dict を ctx: YourContext に変更してください",
    pattern=r"def\s+\w+\(data:\s*dict\)",
    replacement="# → ctx: YourContext を引数にしてください",
    file_patterns=("src/nodes/**/*.py",),
)
```

**検出パターン3: 旧形式エントリポイント（Issue #017）**

```python
CodeGuidance(
    description="pipeline() を dag_runner() または typed_pipeline() に変更してください",
    pattern=r"from railway import.*\bpipeline\b",
    replacement="# → dag_runner または typed_pipeline を使用",
    file_patterns=("src/*.py",),
)
```

### Phase 3: .gitignore 更新（ConfigChange相当）

```gitignore
# 追加する行
_railway/generated/*.py
!_railway/generated/.gitkeep
```

### Phase 4: ドキュメント更新

#### README.md 追加セクション: 「既存プロジェクトのアップグレード」

```markdown
## 既存プロジェクトのアップグレード

### なぜアップグレードが必要か？

| 問題 | v0.11.3 での解決策 |
|------|-------------------|
| 条件分岐が書きにくい | **dag_runner** で宣言的に定義 |
| ノードの戻り値が不明確 | **Outcome** で状態を明示 |
| 遷移ロジックがコードに埋まる | **YAML** で可視化 |

### アップグレード手順

1. **プレビュー**（変更内容を確認）
   ```bash
   railway update --dry-run
   ```

2. **バックアップ付きで実行**
   ```bash
   railway update
   ```

3. **ガイダンスに従ってコードを修正**
   - `dict` → `tuple[Contract, Outcome]`
   - `pipeline()` → `dag_runner()` または `typed_pipeline()`

### 検出される旧形式パターン

| パターン | 推奨変更 |
|----------|----------|
| `def node(data: dict) -> dict:` | `def node(ctx: Context) -> tuple[Context, Outcome]:` |
| `from railway import pipeline` | `from railway.core.dag import dag_runner` |
```

#### TUTORIAL.md Step 9 追加: 「既存プロジェクトのアップグレード」

**注意:** 現在のStep 8は「バージョン管理」。Step 9として追加する。

```markdown
## Step 9: 既存プロジェクトのアップグレード（3分）

v0.10.x 以前のプロジェクトを最新形式にアップグレードしましょう。

### 9.1 変更内容をプレビュー

```bash
railway update --dry-run
```

**出力例:**
```
マイグレーション: 0.10.1 → 0.12.0

ファイル追加:
  - transition_graphs/.gitkeep
  - _railway/generated/.gitkeep

コードガイダンス:
  src/nodes/process.py:5
    現在: def process(data: dict) -> dict:
    推奨: def process(ctx: ProcessContext) -> tuple[ProcessContext, Outcome]:

警告:
  - ノードの戻り値形式が変更されています
```

### 9.2 アップグレード実行

```bash
railway update
```

### 9.3 コードを修正

ガイダンスに従って、旧形式のノードを新形式に変更します。

**Before:**
```python
@node
def process(data: dict) -> dict:
    return data
```

**After:**
```python
@node
def process(ctx: ProcessContext) -> tuple[ProcessContext, Outcome]:
    return ctx, Outcome.success("done")
```

**恩恵:**
- Outcome で次の遷移先を制御できる
- Contract で型安全にデータを扱える
- YAML で遷移ロジックを可視化できる
```

---

## TDD 実装手順

### Step 1: FileChange テスト（Red）

```python
# tests/unit/migrations/test_v0_10_to_v0_12_migration.py
"""Tests for v0.10.1 → v0.11.3 migration."""

import pytest
from railway.migrations.registry import MIGRATIONS, find_migration
from railway.migrations.changes import ChangeType


class TestMigrationExists:
    """マイグレーション定義の存在テスト。"""

    def test_migration_0_10_to_0_12_exists(self):
        """0.10.1 → 0.12.0 マイグレーションが存在する。"""
        migration = find_migration("0.10.0", "0.12.0")
        assert migration is not None
        assert migration.from_version == "0.10.0"
        assert migration.to_version == "0.12.0"

    def test_migration_has_description(self):
        """マイグレーションに説明がある。"""
        migration = find_migration("0.10.0", "0.12.0")
        assert "DAG" in migration.description or "dag" in migration.description.lower()


class TestMigrationFileChanges:
    """ファイル変更のテスト。"""

    def test_creates_transition_graphs_dir(self):
        """transition_graphs ディレクトリを作成する。"""
        migration = find_migration("0.10.0", "0.12.0")

        paths = [fc.path for fc in migration.file_changes]
        assert any("transition_graphs" in p for p in paths)

    def test_creates_railway_generated_dir(self):
        """_railway/generated ディレクトリを作成する。"""
        migration = find_migration("0.10.0", "0.12.0")

        paths = [fc.path for fc in migration.file_changes]
        assert any("_railway/generated" in p for p in paths)

    def test_file_changes_are_create_type(self):
        """ファイル変更は CREATE タイプである。"""
        migration = find_migration("0.10.0", "0.12.0")

        for fc in migration.file_changes:
            assert fc.change_type == ChangeType.FILE_CREATE
```

### Step 2: CodeGuidance テスト（Red）

```python
class TestMigrationCodeGuidance:
    """コードガイダンスのテスト。"""

    def test_detects_dict_return_type(self):
        """dict を返すノードを検出する。"""
        migration = find_migration("0.10.0", "0.12.0")

        old_code = '''
@node
def process(data: dict) -> dict:
    return data
'''
        # 少なくとも1つのガイダンスがマッチする
        matches = []
        for guidance in migration.code_guidance:
            matches.extend(guidance.matches(old_code))

        assert len(matches) > 0

    def test_detects_dict_parameter(self):
        """data: dict パラメータを検出する。"""
        migration = find_migration("0.10.0", "0.12.0")

        old_code = '''
def fetch_data(data: dict):
    pass
'''
        matches = []
        for guidance in migration.code_guidance:
            matches.extend(guidance.matches(old_code))

        assert len(matches) > 0

    def test_detects_old_pipeline_import(self):
        """旧 pipeline import を検出する。"""
        migration = find_migration("0.10.0", "0.12.0")

        old_code = '''
from railway import pipeline, node
'''
        matches = []
        for guidance in migration.code_guidance:
            matches.extend(guidance.matches(old_code))

        assert len(matches) > 0


class TestMigrationWarnings:
    """警告メッセージのテスト。"""

    def test_has_warnings(self):
        """警告メッセージが含まれる。"""
        migration = find_migration("0.10.0", "0.12.0")
        assert len(migration.warnings) > 0

    def test_warnings_mention_node_format(self):
        """ノード形式変更の警告がある。"""
        migration = find_migration("0.10.0", "0.12.0")
        warnings_text = " ".join(migration.warnings)
        assert "ノード" in warnings_text or "node" in warnings_text.lower()
```

### Step 3: ドキュメントテスト（Red）

```python
# tests/unit/docs/test_readme_upgrade_section.py
"""Tests for README upgrade section."""

import pytest
from pathlib import Path


class TestReadmeUpgradeSection:
    """README.md のアップグレードセクションテスト。"""

    @pytest.fixture
    def readme_content(self):
        readme_path = Path(__file__).parents[3] / "readme.md"
        return readme_path.read_text()

    def test_has_upgrade_section(self, readme_content):
        """アップグレードセクションが存在する。"""
        has_section = (
            "アップグレード" in readme_content
            or "upgrade" in readme_content.lower()
        )
        assert has_section

    def test_shows_dry_run_command(self, readme_content):
        """--dry-run コマンドが記載されている。"""
        assert "railway update --dry-run" in readme_content

    def test_shows_benefit_comparison(self, readme_content):
        """恩恵の比較表がある。"""
        # 問題と解決策の対比がある
        has_comparison = (
            "問題" in readme_content or "解決" in readme_content
        )
        assert has_comparison

    def test_shows_pattern_examples(self, readme_content):
        """旧形式パターンの例がある。"""
        assert "dict" in readme_content
        assert "Outcome" in readme_content
```

```python
# tests/unit/docs/test_tutorial_upgrade_step.py
"""Tests for TUTORIAL upgrade step."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestTutorialUpgradeStep:
    """TUTORIAL.md のアップグレードステップテスト。"""

    @pytest.fixture
    def tutorial_content(self):
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])
                tutorial_path = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                return tutorial_path.read_text()
            finally:
                os.chdir(original_cwd)

    def test_has_upgrade_step(self, tutorial_content):
        """アップグレードステップが存在する。"""
        has_step = (
            "アップグレード" in tutorial_content
            or "upgrade" in tutorial_content.lower()
        )
        assert has_step

    def test_shows_dry_run_preview(self, tutorial_content):
        """--dry-run プレビューの説明がある。"""
        assert "dry-run" in tutorial_content.lower()

    def test_shows_before_after_example(self, tutorial_content):
        """Before/After の例がある。"""
        has_example = (
            "Before" in tutorial_content or "After" in tutorial_content
        )
        assert has_example

    def test_shows_outcome_benefit(self, tutorial_content):
        """Outcome の恩恵が説明されている。"""
        assert "Outcome" in tutorial_content
```

### Step 4: マイグレーション定義実装（Green）

**ディレクトリ構造:**
```
railway/migrations/definitions/
├── __init__.py              # 空ファイル（パッケージ化）
└── v0_10_to_v0_12.py        # マイグレーション定義
```

**注意:** `FileChange.create()` はディレクトリを自動作成する。
既に存在する場合はスキップされる（executor.py の実装による）。

```python
# railway/migrations/definitions/v0_10_to_v0_12.py
"""Migration from v0.10.x to v0.11.3.

DAGネイティブサポートへの移行。
"""

from railway.migrations.changes import (
    CodeGuidance,
    FileChange,
    MigrationDefinition,
)


MIGRATION_0_10_TO_0_12 = MigrationDefinition(
    from_version="0.10.0",
    to_version="0.12.0",
    description="DAGネイティブサポートへの移行",
    file_changes=(
        FileChange.create(
            path="transition_graphs/.gitkeep",
            content="# Transition graph YAML files\n# File naming: {entrypoint}_{YYYYMMDDHHmmss}.yml\n",
            description="DAGワークフロー用ディレクトリを追加",
        ),
        FileChange.create(
            path="_railway/generated/.gitkeep",
            content="# Auto-generated transition code\n# Do not edit manually - use `railway sync transition`\n",
            description="自動生成コード用ディレクトリを追加",
        ),
    ),
    code_guidance=(
        CodeGuidance(
            description="dict 型を tuple[Contract, Outcome] に変更してください",
            pattern=r"def\s+\w+\([^)]*\)\s*->\s*dict:",
            replacement="# → tuple[YourContext, Outcome] を返すように変更",
            file_patterns=("src/nodes/**/*.py",),
        ),
        CodeGuidance(
            description="data: dict を ctx: YourContext に変更してください",
            pattern=r"def\s+\w+\(data:\s*dict\)",
            replacement="# → ctx: YourContext を引数にしてください",
            file_patterns=("src/nodes/**/*.py", "src/**/*.py"),
        ),
        CodeGuidance(
            description="pipeline() を dag_runner() または typed_pipeline() に変更してください",
            pattern=r"from railway import[^)]*\bpipeline\b",
            replacement="# → dag_runner または typed_pipeline を使用",
            file_patterns=("src/*.py",),
        ),
    ),
    warnings=(
        "ノードの戻り値形式が変更されています: dict → tuple[Contract, Outcome]",
        "pipeline() は非推奨です。dag_runner() または typed_pipeline() を使用してください。",
        "詳細: railway docs または README.md の「既存プロジェクトのアップグレード」を参照",
    ),
)
```

### Step 5: registry.py 更新（Green）

```python
# railway/migrations/registry.py に追加

from railway.migrations.definitions.v0_10_to_v0_12 import MIGRATION_0_10_TO_0_12

MIGRATIONS: tuple[MigrationDefinition, ...] = (
    MIGRATION_0_10_TO_0_12,
)
```

### Step 6: ドキュメント更新（Green）

README.md と railway/cli/init.py（TUTORIAL.md生成）を更新。

---

## 関数型パラダイムの適用

### 純粋関数

| 関数 | 入力 | 出力 | 副作用 |
|------|------|------|--------|
| `find_migration()` | `from_ver, to_ver` | `Optional[MigrationDefinition]` | なし |
| `CodeGuidance.matches()` | `content: str` | `list[tuple[int, str, str]]` | なし |
| `calculate_migration_path()` | `from_ver, to_ver` | `MigrationPlan` | なし |

### 副作用の局所化

| 関数 | 副作用 | 呼び出し元 |
|------|--------|-----------|
| `display_preview()` | stdout | CLI (update.py) |
| `apply_file_change()` | ファイル書き込み | executor.py |
| `create_backup()` | ディレクトリ作成 | executor.py |

### イミュータブルデータ

- `MigrationDefinition`: `frozen=True`
- `FileChange`: `frozen=True`
- `CodeGuidance`: `frozen=True`
- `MIGRATIONS`: 不変タプル

---

## 完了条件

- [ ] `tests/unit/migrations/test_v0_10_to_v0_12_migration.py` 全テスト通過
- [ ] `tests/unit/docs/test_readme_upgrade_section.py` 全テスト通過
- [ ] `tests/unit/docs/test_tutorial_upgrade_step.py` 全テスト通過
- [ ] 既存の全テスト（~820件）が引き続き通過
- [ ] `railway update --dry-run` で旧形式ノードが検出される
- [ ] `railway update` で transition_graphs/ と _railway/generated/ が作成される
- [ ] README.md に「既存プロジェクトのアップグレード」セクションが追加されている
- [ ] TUTORIAL.md に Step 9 アップグレード手順が含まれている

---

## 依存関係

- **依存先**: Issue #12, #17, #21（全て完了済み）
- **依存元**: なし

---

## 参考資料

- `issues/Phase2_正式リリース準備/完了/2/` - 今回のリリース範囲のissue
- `railway/migrations/changes.py` - 変更定義の型
- `railway/migrations/executor.py` - 実行ロジック
- `git log v0.10.1..HEAD` - 変更履歴
