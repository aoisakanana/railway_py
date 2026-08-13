"""Tests for 階層 new node の __init__.py 生成 (v0.13.26 Issue 01).

同名リーフの階層ノードが共存しても pytest の collection が壊れないこと
（結果の性質）と、src/tests 両側の中間ディレクトリへの __init__.py 生成を検証。
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def project(tmp_path: Path):
    """init 済みプロジェクトを作成し cwd を移動する。"""
    from railway.cli.main import app
    old = os.getcwd()
    os.chdir(tmp_path)
    r = CliRunner().invoke(app, ["init", "init_proj"])
    assert r.exit_code == 0
    os.chdir(tmp_path / "init_proj")
    yield tmp_path / "init_proj"
    os.chdir(old)


class TestInitFilesGenerated:
    """階層生成時に src / tests 両側の中間ディレクトリへ __init__.py を生成。"""

    def test_hierarchical_node_creates_init_files(
        self, runner: CliRunner, project: Path
    ) -> None:
        from railway.cli.main import app
        r = runner.invoke(app, ["new", "node", "processing.validate"])
        assert r.exit_code == 0, r.output
        assert (project / "src/nodes/processing/__init__.py").exists()
        assert (project / "tests/nodes/processing/__init__.py").exists()

    def test_deep_hierarchy_creates_all_intermediate_inits(
        self, runner: CliRunner, project: Path
    ) -> None:
        from railway.cli.main import app
        r = runner.invoke(app, ["new", "node", "sub.deep.process"])
        assert r.exit_code == 0, r.output
        for rel in (
            "src/nodes/sub/__init__.py",
            "src/nodes/sub/deep/__init__.py",
            "tests/nodes/sub/__init__.py",
            "tests/nodes/sub/deep/__init__.py",
        ):
            assert (project / rel).exists(), f"欠落: {rel}"

    def test_flat_node_unchanged(self, runner: CliRunner, project: Path) -> None:
        """フラットノードの回帰防止（余計なディレクトリを作らない）。"""
        from railway.cli.main import app
        r = runner.invoke(app, ["new", "node", "check_status"])
        assert r.exit_code == 0
        assert (project / "src/nodes/check_status.py").exists()
        assert (project / "tests/nodes/test_check_status.py").exists()


class TestDuplicateLeafPytestCollection:
    """結果の性質: 同名リーフの階層ノードが共存しても全テストが実行可能。"""

    def test_duplicate_leaf_collection_succeeds(
        self, runner: CliRunner, project: Path
    ) -> None:
        from railway.cli.main import app
        assert runner.invoke(app, ["new", "node", "processing.validate"]).exit_code == 0
        assert runner.invoke(app, ["new", "node", "deep.validate"]).exit_code == 0

        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "--collect-only", "-q"],
            capture_output=True, text=True, cwd=str(project), timeout=120,
        )
        assert proc.returncode == 0, (
            f"pytest collection が失敗:\n{proc.stdout}\n{proc.stderr}"
        )
        assert "error" not in proc.stdout.lower()
