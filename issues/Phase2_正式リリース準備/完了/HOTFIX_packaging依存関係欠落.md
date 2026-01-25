# HOTFIX: packaging モジュール依存関係欠落

**重大度**: 🔴 Critical  
**発生バージョン**: v0.10.0  
**修正バージョン**: v0.10.1

## 問題

v0.10.0 で追加されたバージョン管理機能が `packaging` モジュールを使用しているが、`pyproject.toml` の依存関係に含まれていない。

### 影響

- **CLIが起動できない**: `railway` コマンド実行時に `ModuleNotFoundError: No module named 'packaging'` が発生
- **全ユーザーに影響**: v0.10.0 を新規インストールした全ユーザー

### 原因

Phase 2 実装時に以下のファイルで `packaging.version.Version` を使用:

```python
# railway/migrations/registry.py:13
from packaging.version import Version

# railway/core/version_checker.py:11
from packaging.version import Version
```

開発環境では `packaging` が他の依存関係（pytest等）の推移的依存として存在したため、問題が発覚しなかった。

## 修正

### pyproject.toml

```diff
 dependencies = [
     "tenacity>=8.2.0",
     "pydantic>=2.5.0",
     "pydantic-settings>=2.1.0",
     "typer>=0.9.0",
     "loguru>=0.7.0",
     "python-dotenv>=1.0.0",
     "PyYAML>=6.0",
     "Jinja2>=3.1.0",
+    "packaging>=21.0",
 ]
```

### バージョン

```diff
-version = "0.10.0"
+version = "0.10.1"
```

## 確認手順

```bash
# クリーンな環境でインストールして動作確認
uv venv --python 3.12 /tmp/test-railway
source /tmp/test-railway/bin/activate
pip install railway-framework==0.10.1
railway --version
railway update --help
```

## 再発防止

1. CI/CDにクリーン環境でのインストールテストを追加
2. `uv sync --no-dev` でテストを実行するステップを追加

## タイムライン

- 発見: 2026-01-23 (リリース直後)
- 修正: 2026-01-23
- v0.10.1 リリース: 2026-01-23
