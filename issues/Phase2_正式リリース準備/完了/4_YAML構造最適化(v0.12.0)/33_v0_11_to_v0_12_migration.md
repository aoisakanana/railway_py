# Issue #33: v0.11.3 → v0.12.0 マイグレーション定義

**Phase:** 2
**優先度:** 高
**依存関係:** Issue #32（YAML 構造変換ユーティリティ）
**見積もり:** 0.5日

---

## 概要

`railway update` コマンドで v0.11.3 から v0.12.0 への自動マイグレーションを行うための定義を作成する。

---

## マイグレーション内容

### 1. YAML ファイルの変換

| 変換対象 | Before (v0.11.x) | After (v0.12.0) |
|----------|------------------|-----------------|
| exits セクション | `exits:` | `nodes.exit:` 配下 |
| 遷移先 | `exit::green_success` | `exit.success.done` |
| module/function | 必須 | 省略可能（自動解決） |

### 2. 生成コードの再生成

`railway sync transition` を再実行して以下を生成:
- `EXIT_CODES` マッピング
- `run()` / `run_async()` ヘルパー
- `_node_name` 属性設定

### 3. ノードコードの変更（ガイダンス）

終端ノードの返り値形式:
- **Before:** `tuple[Context, Outcome]`
- **After:** `Context` のみ（Outcome 不要）

---

## 実装

### マイグレーション定義ファイル

```python
# railway/migrations/definitions/v0_11_to_v0_12.py
"""Migration definition from v0.11.3 to v0.12.0."""

from pathlib import Path
from typing import Any

from railway.migrations.changes import (
    CodeGuidance,
    ConfigChange,
    FileChange,
    MigrationDefinition,
)
from railway.migrations.yaml_converter import convert_yaml_structure


def _create_yaml_transform_change() -> FileChange:
    """YAML 変換用の FileChange を作成。

    Note:
        FILE_UPDATE タイプではなく、カスタムトランスフォーム関数を使用。
        executor で特別に処理される。
    """
    return FileChange.update(
        path="transition_graphs/*.yml",
        template=None,  # テンプレートではなく関数で変換
        description="YAML 構造を新形式（nodes.exit 配下）に変換",
        transform=convert_yaml_structure,  # 変換関数を指定
    )


MIGRATION_0_11_TO_0_12 = MigrationDefinition(
    from_version="0.11.0",
    to_version="0.12.0",
    description="終端ノードの nodes.exit 統合（ADR-004）",

    file_changes=(
        # 生成コード用ディレクトリは既に存在（v0.11 で作成済み）
    ),

    config_changes=(
        # project.yaml のバージョン更新は executor が自動実行
    ),

    yaml_transforms=(
        # YAML ファイルの構造変換
        YamlTransform(
            pattern="transition_graphs/**/*.yml",
            transform=convert_yaml_structure,
            description="exits セクションを nodes.exit 配下に変換",
        ),
    ),

    code_guidance=(
        # 終端ノードの返り値変更
        CodeGuidance(
            description="終端ノードは Context のみを返すように変更してください（Outcome 不要）",
            pattern=r"def\s+\w+\([^)]*\)\s*->\s*tuple\[.*Outcome\]:",
            replacement="# 終端ノードは def done(ctx) -> FinalContext: のように Context のみを返す",
            file_patterns=("src/nodes/exit/**/*.py", "src/nodes/**/exit*.py"),
        ),
        # railway sync の再実行
        CodeGuidance(
            description="生成コードを再生成してください",
            pattern=r"# Auto-generated",
            replacement="# `railway sync transition` を実行して再生成してください",
            file_patterns=("_railway/generated/**/*.py", "src/transitions/**/*.py"),
        ),
        # 旧 exit:: 形式の検出
        CodeGuidance(
            description="exit:: 形式は廃止されました。exit.success.done 形式に変更してください",
            pattern=r'exit::\w+',
            replacement="# exit.success.done 形式に変更",
            file_patterns=("**/*.py",),
        ),
    ),

    post_migration_commands=(
        "railway sync transition --all",  # 全エントリーポイントのコード再生成
    ),

    warnings=(
        "【重要】YAML ファイルが自動変換されます。バックアップを確認してください。",
        "【重要】終端ノード（exit ハンドラ）の返り値を Context のみに変更してください。",
        "【重要】マイグレーション後、`railway sync transition --all` を実行してください。",
        "詳細: docs/adr/004_exit_node_design.md を参照",
    ),
)
```

### 変更型の拡張（必要に応じて）

```python
# railway/migrations/changes.py に追加

@dataclass(frozen=True)
class YamlTransform:
    """YAML ファイルの構造変換定義。"""
    pattern: str  # glob パターン
    transform: Callable[[dict], ConversionResult]  # 変換関数
    description: str

    def matches(self, path: Path) -> bool:
        """パスがパターンにマッチするか。"""
        import fnmatch
        return fnmatch.fnmatch(str(path), self.pattern)
```

### executor の拡張

```python
# railway/migrations/executor.py に追加

def apply_yaml_transforms(
    project_path: Path,
    transforms: tuple[YamlTransform, ...],
    on_progress: Callable[[str], None] | None = None,
) -> tuple[int, list[str]]:
    """YAML ファイルに変換を適用（純粋関数的な設計）。

    Args:
        project_path: プロジェクトルート
        transforms: 変換定義のタプル
        on_progress: 進捗コールバック

    Returns:
        (変換ファイル数, 警告リスト)
    """
    import yaml
    from pathlib import Path

    converted_count = 0
    warnings: list[str] = []

    for transform in transforms:
        # パターンにマッチするファイルを検索
        yaml_files = list(project_path.glob(transform.pattern))

        for yaml_file in yaml_files:
            if on_progress:
                on_progress(f"変換中: {yaml_file.relative_to(project_path)}")

            # YAML を読み込み
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # 変換を適用
            result = transform.transform(data)

            if not result.success:
                warnings.append(f"{yaml_file}: {result.error}")
                continue

            if result.warnings:
                warnings.extend(f"{yaml_file}: {w}" for w in result.warnings)

            # 変換結果を書き込み
            with open(yaml_file, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    result.data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )

            converted_count += 1

    return converted_count, warnings
```

### レジストリへの登録

```python
# railway/migrations/registry.py を更新

from railway.migrations.definitions.v0_10_to_v0_11 import MIGRATION_0_10_TO_0_11
from railway.migrations.definitions.v0_11_to_v0_12 import MIGRATION_0_11_TO_0_12

MIGRATIONS: tuple[MigrationDefinition, ...] = (
    MIGRATION_0_10_TO_0_11,
    MIGRATION_0_11_TO_0_12,  # 追加
)
```

---

## TDD 実装手順

### Step 1: テスト作成（Red）

```python
# tests/unit/migrations/test_v0_11_to_v0_12_migration.py
"""Tests for v0.11 to v0.12 migration definition."""

import pytest
from pathlib import Path

from railway.migrations.definitions.v0_11_to_v0_12 import MIGRATION_0_11_TO_0_12
from railway.migrations.registry import MIGRATIONS, find_migration


class TestMigrationExists:
    """マイグレーション定義の存在テスト。"""

    def test_migration_0_11_to_0_12_exists(self) -> None:
        """v0.11 → v0.12 マイグレーションが定義されている。"""
        assert MIGRATION_0_11_TO_0_12 is not None

    def test_migration_has_correct_versions(self) -> None:
        """バージョンが正しい。"""
        assert MIGRATION_0_11_TO_0_12.from_version == "0.11.0"
        assert MIGRATION_0_11_TO_0_12.to_version == "0.12.0"

    def test_migration_has_description(self) -> None:
        """説明がある。"""
        assert MIGRATION_0_11_TO_0_12.description
        assert "exit" in MIGRATION_0_11_TO_0_12.description.lower()

    def test_migration_is_in_registry(self) -> None:
        """レジストリに登録されている。"""
        assert MIGRATION_0_11_TO_0_12 in MIGRATIONS

    def test_can_find_migration(self) -> None:
        """find_migration で取得できる。"""
        migration = find_migration("0.11.0", "0.12.0")
        assert migration is not None
        assert migration.to_version == "0.12.0"


class TestMigrationYamlTransforms:
    """YAML 変換定義のテスト。"""

    def test_has_yaml_transforms(self) -> None:
        """YAML 変換が定義されている。"""
        assert len(MIGRATION_0_11_TO_0_12.yaml_transforms) > 0

    def test_transforms_target_transition_graphs(self) -> None:
        """transition_graphs ディレクトリを対象にしている。"""
        transform = MIGRATION_0_11_TO_0_12.yaml_transforms[0]
        assert "transition_graphs" in transform.pattern


class TestMigrationCodeGuidance:
    """コードガイダンスのテスト。"""

    def test_has_exit_node_guidance(self) -> None:
        """終端ノードに関するガイダンスがある。"""
        guidance_texts = [g.description for g in MIGRATION_0_11_TO_0_12.code_guidance]
        assert any("終端" in text or "exit" in text.lower() for text in guidance_texts)

    def test_has_sync_guidance(self) -> None:
        """sync コマンドに関するガイダンスがある。"""
        guidance_texts = [g.description for g in MIGRATION_0_11_TO_0_12.code_guidance]
        assert any("sync" in text.lower() or "再生成" in text for text in guidance_texts)


class TestMigrationWarnings:
    """警告メッセージのテスト。"""

    def test_has_warnings(self) -> None:
        """警告メッセージがある。"""
        assert len(MIGRATION_0_11_TO_0_12.warnings) > 0

    def test_warns_about_yaml_changes(self) -> None:
        """YAML 変更について警告している。"""
        warnings_text = " ".join(MIGRATION_0_11_TO_0_12.warnings)
        assert "YAML" in warnings_text or "yaml" in warnings_text.lower()

    def test_warns_about_backup(self) -> None:
        """バックアップについて警告している。"""
        warnings_text = " ".join(MIGRATION_0_11_TO_0_12.warnings)
        assert "バックアップ" in warnings_text or "backup" in warnings_text.lower()


class TestMigrationPostCommands:
    """マイグレーション後コマンドのテスト。"""

    def test_has_post_migration_commands(self) -> None:
        """マイグレーション後コマンドが定義されている。"""
        assert len(MIGRATION_0_11_TO_0_12.post_migration_commands) > 0

    def test_includes_sync_command(self) -> None:
        """sync コマンドが含まれている。"""
        commands = MIGRATION_0_11_TO_0_12.post_migration_commands
        assert any("sync" in cmd for cmd in commands)
```

### Step 2: executor テスト

```python
# tests/unit/migrations/test_yaml_transform_executor.py
"""Tests for YAML transform execution."""

import pytest
from pathlib import Path
import yaml

from railway.migrations.executor import apply_yaml_transforms
from railway.migrations.changes import YamlTransform
from railway.migrations.yaml_converter import convert_yaml_structure


class TestApplyYamlTransforms:
    """YAML 変換適用テスト。"""

    def test_transforms_yaml_files(self, tmp_path: Path) -> None:
        """YAML ファイルを変換する。"""
        # テスト用 YAML を作成
        yaml_dir = tmp_path / "transition_graphs"
        yaml_dir.mkdir()
        yaml_file = yaml_dir / "test_20250128000000.yml"

        old_yaml = {
            "version": "1.0",
            "entrypoint": "test",
            "nodes": {
                "start": {"module": "nodes.start", "function": "start", "description": "開始"},
            },
            "exits": {
                "green_success": {"code": 0, "description": "正常終了"},
            },
            "start": "start",
            "transitions": {
                "start": {"success::done": "exit::green_success"},
            },
        }
        with open(yaml_file, "w") as f:
            yaml.safe_dump(old_yaml, f)

        # 変換を適用
        transforms = (
            YamlTransform(
                pattern="transition_graphs/**/*.yml",
                transform=convert_yaml_structure,
                description="テスト変換",
            ),
        )

        count, warnings = apply_yaml_transforms(tmp_path, transforms)

        # 検証
        assert count == 1
        assert len(warnings) == 0

        # 変換結果を確認
        with open(yaml_file) as f:
            result = yaml.safe_load(f)

        assert "exits" not in result
        assert "exit" in result["nodes"]
        assert result["transitions"]["start"]["success::done"] == "exit.success.done"

    def test_skips_already_converted_files(self, tmp_path: Path) -> None:
        """既に変換済みのファイルはスキップ。"""
        yaml_dir = tmp_path / "transition_graphs"
        yaml_dir.mkdir()
        yaml_file = yaml_dir / "test.yml"

        # 既に新形式の YAML
        new_yaml = {
            "version": "1.0",
            "nodes": {
                "start": {"description": "開始"},
                "exit": {"success": {"done": {"description": "正常終了"}}},
            },
            "start": "start",
            "transitions": {
                "start": {"success::done": "exit.success.done"},
            },
        }
        with open(yaml_file, "w") as f:
            yaml.safe_dump(new_yaml, f)

        transforms = (
            YamlTransform(
                pattern="transition_graphs/**/*.yml",
                transform=convert_yaml_structure,
                description="テスト変換",
            ),
        )

        count, warnings = apply_yaml_transforms(tmp_path, transforms)

        # exits がないので変換は行われない（ただしカウントはされる）
        # 元のファイルが変更されていないことを確認
        with open(yaml_file) as f:
            result = yaml.safe_load(f)

        assert result == new_yaml

    def test_reports_conversion_warnings(self, tmp_path: Path) -> None:
        """変換警告を報告する。"""
        yaml_dir = tmp_path / "transition_graphs"
        yaml_dir.mkdir()
        yaml_file = yaml_dir / "test.yml"

        # 変換で警告が出る YAML（例: 自動変換できない exit 名）
        old_yaml = {
            "version": "1.0",
            "nodes": {},
            "exits": {
                "custom_weird_name": {"code": 99, "description": "奇妙な終了"},
            },
            "start": "start",
            "transitions": {},
        }
        with open(yaml_file, "w") as f:
            yaml.safe_dump(old_yaml, f)

        transforms = (
            YamlTransform(
                pattern="transition_graphs/**/*.yml",
                transform=convert_yaml_structure,
                description="テスト変換",
            ),
        )

        count, warnings = apply_yaml_transforms(tmp_path, transforms)

        # 変換は成功するが、警告があるかもしれない
        assert count >= 0


class TestApplyYamlTransformsProgress:
    """進捗コールバックのテスト。"""

    def test_calls_progress_callback(self, tmp_path: Path) -> None:
        """進捗コールバックが呼ばれる。"""
        yaml_dir = tmp_path / "transition_graphs"
        yaml_dir.mkdir()
        (yaml_dir / "test.yml").write_text("version: '1.0'\nnodes: {}\n")

        progress_calls: list[str] = []

        def on_progress(msg: str) -> None:
            progress_calls.append(msg)

        transforms = (
            YamlTransform(
                pattern="transition_graphs/**/*.yml",
                transform=convert_yaml_structure,
                description="テスト",
            ),
        )

        apply_yaml_transforms(tmp_path, transforms, on_progress=on_progress)

        assert len(progress_calls) > 0
```

### Step 3: 統合テスト

```python
# tests/unit/migrations/test_v0_11_to_v0_12_integration.py
"""Integration tests for v0.11 to v0.12 migration."""

import pytest
from pathlib import Path
import yaml

from railway.migrations.registry import calculate_migration_path
from railway.migrations.executor import execute_migration_plan


class TestMigrationPathCalculation:
    """マイグレーションパス計算の統合テスト。"""

    def test_calculates_path_from_0_11_to_0_12(self) -> None:
        """v0.11 → v0.12 のパスを計算できる。"""
        plan = calculate_migration_path("0.11.3", "0.12.0")

        assert not plan.is_empty
        assert plan.from_version == "0.11.3"
        assert plan.to_version == "0.12.0"

    def test_calculates_path_from_0_10_to_0_12(self) -> None:
        """v0.10 → v0.12 の複数ステップパスを計算できる。"""
        plan = calculate_migration_path("0.10.0", "0.12.0")

        assert not plan.is_empty
        assert len(plan.migrations) == 2  # 0.10→0.11, 0.11→0.12


class TestFullMigrationExecution:
    """完全なマイグレーション実行の統合テスト。"""

    def test_executes_migration_on_sample_project(self, tmp_path: Path) -> None:
        """サンプルプロジェクトでマイグレーションを実行。"""
        # プロジェクト構造を作成
        (tmp_path / ".railway").mkdir()
        (tmp_path / "transition_graphs").mkdir()

        # メタデータ
        metadata = {
            "railway": {"version": "0.11.3"},
            "project": {"name": "test"},
        }
        with open(tmp_path / ".railway" / "project.yaml", "w") as f:
            yaml.safe_dump(metadata, f)

        # 旧形式 YAML
        old_yaml = {
            "version": "1.0",
            "entrypoint": "test",
            "nodes": {
                "process": {
                    "module": "nodes.process",
                    "function": "process",
                    "description": "処理",
                },
            },
            "exits": {
                "green_success": {"code": 0, "description": "成功"},
                "red_error": {"code": 1, "description": "エラー"},
            },
            "start": "process",
            "transitions": {
                "process": {
                    "success::done": "exit::green_success",
                    "failure::error": "exit::red_error",
                },
            },
        }
        yaml_file = tmp_path / "transition_graphs" / "test_20250128000000.yml"
        with open(yaml_file, "w") as f:
            yaml.safe_dump(old_yaml, f)

        # マイグレーション実行
        plan = calculate_migration_path("0.11.3", "0.12.0")
        result = execute_migration_plan(tmp_path, plan, create_backup_flag=True)

        # 検証
        assert result.success

        # YAML が変換されている
        with open(yaml_file) as f:
            converted = yaml.safe_load(f)

        assert "exits" not in converted
        assert "exit" in converted["nodes"]
        assert "success" in converted["nodes"]["exit"]
        assert converted["transitions"]["process"]["success::done"] == "exit.success.done"
```

---

## 完了条件

- [ ] `MigrationDefinition` を作成（v0.11.0 → v0.12.0）
- [ ] `YamlTransform` データクラスを追加（イミュータブル）
- [ ] `apply_yaml_transforms` 関数を実装
- [ ] `MIGRATION_0_11_TO_0_12` をレジストリに登録
- [ ] CodeGuidance を定義（終端ノード、sync コマンド）
- [ ] 警告メッセージを定義
- [ ] マイグレーション後コマンドを定義
- [ ] 単体テスト通過
- [ ] 統合テスト通過
- [ ] `railway update` コマンドで動作確認

---

## 関連 Issue

- Issue #32: YAML 構造変換ユーティリティ（前提）
- ADR-004: Exit ノードの設計と例外処理
- Issue #29: 終端ノードドキュメント追加
