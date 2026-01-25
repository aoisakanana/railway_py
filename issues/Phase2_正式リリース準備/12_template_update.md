# Issue #12: プロジェクトテンプレート更新

**Phase:** 2d
**優先度:** 中
**依存関係:** #09
**見積もり:** 0.5日

---

## 概要

`railway init` で生成されるプロジェクトテンプレートに、
DAGワークフロー用のディレクトリとサンプルファイルを追加する。

---

## 変更内容

### 追加するディレクトリ

```
{project}/
├── transition_graphs/          # 新規追加
│   └── .gitkeep
└── _railway/                   # 新規追加
    └── generated/
        └── .gitkeep
```

### .gitignore への追加

```gitignore
# Railway generated code
_railway/generated/*.py
!_railway/generated/.gitkeep
```

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/cli/test_init_dag.py
"""Tests for DAG-related project initialization."""
import pytest
from pathlib import Path


class TestInitCreatesDAGDirectories:
    """Test that init creates DAG workflow directories."""

    def test_creates_transition_graphs_dir(self, tmp_path, monkeypatch):
        """Should create transition_graphs directory."""
        from typer.testing import CliRunner
        from railway.cli.main import app

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init", "my_project"])

        assert result.exit_code == 0
        project_dir = tmp_path / "my_project"
        assert (project_dir / "transition_graphs").exists()
        assert (project_dir / "transition_graphs" / ".gitkeep").exists()

    def test_creates_railway_generated_dir(self, tmp_path, monkeypatch):
        """Should create _railway/generated directory."""
        from typer.testing import CliRunner
        from railway.cli.main import app

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init", "my_project"])

        assert result.exit_code == 0
        project_dir = tmp_path / "my_project"
        assert (project_dir / "_railway" / "generated").exists()
        assert (project_dir / "_railway" / "generated" / ".gitkeep").exists()

    def test_gitignore_includes_generated(self, tmp_path, monkeypatch):
        """Should add generated files to .gitignore."""
        from typer.testing import CliRunner
        from railway.cli.main import app

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init", "my_project"])

        assert result.exit_code == 0
        gitignore = (tmp_path / "my_project" / ".gitignore").read_text()
        assert "_railway/generated" in gitignore


class TestInitCreatesSampleYAML:
    """Test that init creates sample transition graph YAML."""

    def test_creates_sample_yaml(self, tmp_path, monkeypatch):
        """Should create a sample transition graph YAML."""
        from typer.testing import CliRunner
        from railway.cli.main import app

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init", "my_project"])

        assert result.exit_code == 0
        graphs_dir = tmp_path / "my_project" / "transition_graphs"
        yaml_files = list(graphs_dir.glob("*.yml"))

        # Should have at least one sample YAML
        assert len(yaml_files) >= 1

    def test_sample_yaml_is_valid(self, tmp_path, monkeypatch):
        """Sample YAML should be parseable."""
        from typer.testing import CliRunner
        from railway.cli.main import app
        from railway.core.dag.parser import load_transition_graph

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init", "my_project"])

        graphs_dir = tmp_path / "my_project" / "transition_graphs"
        yaml_files = list(graphs_dir.glob("*.yml"))

        for yaml_file in yaml_files:
            # Should not raise
            graph = load_transition_graph(yaml_file)
            assert graph.version == "1.0"
```

```bash
pytest tests/unit/cli/test_init_dag.py -v
# Expected: FAILED
```

### Step 2: Green（最小限の実装）

#### テンプレートファイル追加

```yaml
# railway/templates/project/transition_graphs/hello_%Y%m%d%H%M%S.yml
version: "1.0"
entrypoint: hello
description: "サンプルワークフロー"

nodes:
  greet:
    module: nodes.greet
    function: greet
    description: "挨拶を出力"

exits:
  success:
    code: 0
    description: "正常終了"
  error:
    code: 1
    description: "異常終了"

start: greet

transitions:
  greet:
    success::done: exit::success
    failure::error: exit::error

options:
  max_iterations: 10
```

```
# railway/templates/project/_railway/generated/.gitkeep
# Auto-generated transition code
# Do not edit manually - use `railway sync transition`
```

```
# railway/templates/project/transition_graphs/.gitkeep
# Transition graph YAML files
# File naming: {entrypoint}_{YYYYMMDDHHmmss}.yml
```

#### .gitignore テンプレート更新

```gitignore
# railway/templates/project/.gitignore に追記
# Railway generated code
_railway/generated/*.py
!_railway/generated/.gitkeep
```

#### init.py の更新

```python
# railway/cli/init.py の _create_project_structure に追加

def _create_project_structure(project_dir: Path) -> None:
    """Create project directory structure."""
    # ... existing code ...

    # DAG workflow directories
    (project_dir / "transition_graphs").mkdir()
    (project_dir / "_railway" / "generated").mkdir(parents=True)

    # Create .gitkeep files
    (project_dir / "transition_graphs" / ".gitkeep").touch()
    (project_dir / "_railway" / "generated" / ".gitkeep").touch()

    # Copy sample YAML with timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    sample_yaml = _get_sample_transition_yaml()
    (project_dir / "transition_graphs" / f"hello_{timestamp}.yml").write_text(
        sample_yaml
    )
```

```bash
pytest tests/unit/cli/test_init_dag.py -v
# Expected: PASSED
```

---

## 完了条件

- [ ] `railway init` が `transition_graphs/` を作成
- [ ] `railway init` が `_railway/generated/` を作成
- [ ] `.gitkeep` ファイルが配置される
- [ ] サンプルYAMLが生成される
- [ ] サンプルYAMLがパース可能
- [ ] `.gitignore` に生成コードが追加
- [ ] テストカバレッジ90%以上

---

## 次のIssue

- #13: README.md 更新
