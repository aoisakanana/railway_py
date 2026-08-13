"""Tests for --with-examples の help と実挙動の整合 (v0.13.25 Issue 05).

実挙動（v0.13.24 で実測確認済み）:
- ファイル集合は両モードで同一
- src/hello.py の内容が切り替わる（デフォルト: 最小版 / --with-examples: pipeline 例付き）

本 Issue は help 文言のみ修正し、挙動は一切変更しない。
"""
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestHelpDescribesActualBehavior:
    """help が実挙動（hello.py の内容切替）を説明している。"""

    def test_help_mentions_hello_content_switch(self, runner: CliRunner) -> None:
        from railway.cli.main import app
        result = runner.invoke(app, ["init", "--help"])
        assert "hello.py" in result.stdout, (
            "help は『hello.py の内容が切り替わる』ことを説明すべき"
        )
        # 旧文言（エントリポイントが増えると誤読させる）が残っていないこと
        assert "Include example entry points" not in result.stdout


class TestBehaviorUnchanged:
    """挙動変更ゼロの固定（回帰防止）。"""

    def test_hello_content_differs_between_modes(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        from railway.cli.main import app
        old = os.getcwd()
        os.chdir(tmp_path)
        try:
            r1 = runner.invoke(app, ["init", "p_with", "--with-examples"])
            r2 = runner.invoke(app, ["init", "p_without", "--no-with-examples"])
            assert r1.exit_code == 0 and r2.exit_code == 0
        finally:
            os.chdir(old)

        with_hello = (tmp_path / "p_with/src/hello.py").read_text()
        without_hello = (tmp_path / "p_without/src/hello.py").read_text()
        assert with_hello != without_hello, (
            "--with-examples は hello.py の内容を切り替える（既存挙動の固定）"
        )

    def test_default_is_minimal_hello(self, runner: CliRunner, tmp_path: Path) -> None:
        """無指定は --no-with-examples と同じ（デフォルト False の固定）。"""
        from railway.cli.main import app
        old = os.getcwd()
        os.chdir(tmp_path)
        try:
            runner.invoke(app, ["init", "p_default"])
            runner.invoke(app, ["init", "p_without", "--no-with-examples"])
        finally:
            os.chdir(old)

        default_hello = (tmp_path / "p_default/src/hello.py").read_text()
        without_hello = (tmp_path / "p_without/src/hello.py").read_text()
        assert default_hello == without_hello

    def test_file_sets_identical_between_modes(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """ファイル集合は両モードで同一（既存挙動の固定）。"""
        from railway.cli.main import app
        old = os.getcwd()
        os.chdir(tmp_path)
        try:
            runner.invoke(app, ["init", "p_with", "--with-examples"])
            runner.invoke(app, ["init", "p_without", "--no-with-examples"])
        finally:
            os.chdir(old)

        def rel_files(root: Path) -> set[str]:
            return {
                str(p.relative_to(root))
                for p in root.rglob("*") if p.is_file()
                # タイムスタンプ付き YAML はファイル名が異なるため除外
                and not (p.suffix == ".yml" and p.parent.name == "transition_graphs")
            }

        assert rel_files(tmp_path / "p_with") == rel_files(tmp_path / "p_without")
