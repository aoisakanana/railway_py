# Issue #34: executor の YamlTransform 適用

**優先度**: P0（バグ修正）
**依存**: なし
**ブロック**: なし（独立）

---

## 概要

`executor.py` の `apply_migration()` が `yaml_transforms` を適用していない。
`railway update` で YAML 自動変換が動作するように修正する。

## 現状の問題

```python
# executor.py - apply_migration()
def apply_migration(project_path: Path, migration: MigrationDefinition) -> None:
    for change in migration.file_changes:
        apply_file_change(project_path, change)
    for change in migration.config_changes:
        apply_config_change(project_path, change)
    # ← yaml_transforms が適用されていない！
```

## 実装

### TDD Phase 1: テスト作成（Red）

まずテストを作成し、**失敗することを確認**する。

```python
# tests/unit/migrations/test_executor.py
class TestApplyYamlTransform:
    def test_applies_yaml_transform(self, tmp_path: Path) -> None:
        """yaml_transforms が適用される。"""
        yaml_dir = tmp_path / "transition_graphs"
        yaml_dir.mkdir()
        (yaml_dir / "test.yml").write_text("""
version: "1.0"
exits:
  green_done: {code: 0, description: "done"}
""")

        migration = MigrationDefinition(
            from_version="0.11.0",
            to_version="0.12.0",
            description="test",
            yaml_transforms=(
                YamlTransform(
                    pattern="transition_graphs/**/*.yml",
                    transform=convert_yaml_structure,
                    description="test",
                ),
            ),
        )

        apply_migration(tmp_path, migration)

        result = yaml.safe_load((yaml_dir / "test.yml").read_text())
        assert "exits" not in result
        assert "exit" in result.get("nodes", {})
```

### TDD Phase 2: 最小実装（Green）

テストが通る最小限の実装を行う。

```python
# executor.py に追加
def apply_yaml_transform(project_path: Path, transform: YamlTransform) -> None:
    """YAML 変換を適用する。"""
    import glob
    pattern = str(project_path / transform.pattern)
    for file_path in glob.glob(pattern, recursive=True):
        file_path = Path(file_path)
        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            continue
        result = transform.transform(data)
        converted = result.data if hasattr(result, "data") else result
        if converted != data:
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(converted, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

def apply_migration(...) -> None:
    ...
    for transform in migration.yaml_transforms:
        apply_yaml_transform(project_path, transform)
```

### TDD Phase 3: リファクタリング（Refactor）

コード品質を向上させる（必要に応じて）:
- 関数の責務を明確化
- エラーハンドリングの追加（ファイル読み込み失敗時など）

## 受け入れ条件

- [ ] `apply_yaml_transform()` 関数が追加されている
- [ ] `apply_migration()` が `yaml_transforms` を適用する
- [ ] `railway update` で YAML が自動変換される
- [ ] 全テストがパス

---

*バグ修正・独立実行可能*
