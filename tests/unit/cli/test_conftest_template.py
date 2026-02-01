"""Tests for conftest.py template generation.

Issue #69: テスト自動生成のインポートパス修正
- conftest.py が src/ を sys.path に追加する
- 生成されたテストがエントリをインポートできる
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from railway.cli.main import app

runner = CliRunner()


class TestConftestTemplate:
    """conftest.py テンプレートのテスト。"""

    def test_conftest_adds_src_to_path(self, tmp_path: Path, monkeypatch):
        """conftest.py が src/ を sys.path に追加する。"""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init", "myproject"], catch_exceptions=False)
        assert result.exit_code == 0

        conftest = tmp_path / "myproject" / "tests" / "conftest.py"
        assert conftest.exists(), f"conftest.py not found at {conftest}"

        content = conftest.read_text()

        # sys.path への追加がある
        assert "sys.path" in content, "sys.path manipulation not found"
        assert "src" in content, "src directory reference not found"

    def test_conftest_imports_sys_and_path(self, tmp_path: Path, monkeypatch):
        """conftest.py が sys と Path をインポートする。"""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "myproject"])

        conftest = tmp_path / "myproject" / "tests" / "conftest.py"
        content = conftest.read_text()

        assert "import sys" in content
        assert "from pathlib import Path" in content or "Path" in content


class TestEntryTestTemplate:
    """エントリポイントテストテンプレートのテスト。"""

    def test_test_file_uses_correct_import(self, tmp_path: Path, monkeypatch):
        """生成されたテストファイルが src. プレフィックスなしでインポート。"""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init", "myproject"], catch_exceptions=False)
        assert result.exit_code == 0

        monkeypatch.chdir(tmp_path / "myproject")
        runner.invoke(app, ["new", "entry", "greeting"])

        test_file = tmp_path / "myproject" / "tests" / "test_greeting.py"
        if test_file.exists():
            content = test_file.read_text()
            # src. プレフィックスなしでインポート（conftest.py で path 追加済みのため）
            assert "from greeting import" in content or "import greeting" in content
            # src. プレフィックスは使わない
            assert "from src.greeting" not in content
