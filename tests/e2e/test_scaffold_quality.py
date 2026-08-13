"""E2E: 生成 scaffold の品質ゲート (v0.13.25 Issue 06).

tmp_path（隔離環境）で init + new entry + new node を実行し、
生成プロジェクト**自身の設定**で ruff / mypy がエラー 0 であることを検証する。

- 検査は `ruff check .`（extend-exclude による _railway 保護の検証を含む）
- 基準設定は生成 pyproject に同梱される [tool.ruff]（実行場所非依存）
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


def _scaffold(runner: CliRunner, tmp_path: Path, mode: str = "dag") -> Path:
    """隔離環境にプロジェクトを scaffold する。"""
    from railway.cli.main import app

    old = os.getcwd()
    os.chdir(tmp_path)
    try:
        r = runner.invoke(app, ["init", "qa_proj"])
        assert r.exit_code == 0, r.output
        os.chdir(tmp_path / "qa_proj")
        r = runner.invoke(app, ["new", "entry", "greeting", "--mode", mode])
        assert r.exit_code == 0, r.output
        r = runner.invoke(app, ["new", "node", "processing.validate"])
        assert r.exit_code == 0, r.output
        return tmp_path / "qa_proj"
    finally:
        os.chdir(old)


class TestScaffoldRuffGate:
    """生成直後の scaffold が自身の ruff 設定でエラー 0。"""

    def test_generated_pyproject_has_ruff_config(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        project = _scaffold(runner, tmp_path)
        pyproject = (project / "pyproject.toml").read_text()
        assert "[tool.ruff]" in pyproject
        assert "_railway" in pyproject, "extend-exclude で生成コードを除外すべき"

    def test_ruff_check_all_clean_dag(self, runner: CliRunner, tmp_path: Path) -> None:
        project = _scaffold(runner, tmp_path, mode="dag")
        proc = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "."],
            capture_output=True, text=True, cwd=str(project), timeout=120,
        )
        assert proc.returncode == 0, f"ruff errors:\n{proc.stdout}\n{proc.stderr}"

    def test_ruff_check_all_clean_linear(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        project = _scaffold(runner, tmp_path, mode="linear")
        proc = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "."],
            capture_output=True, text=True, cwd=str(project), timeout=120,
        )
        assert proc.returncode == 0, f"ruff errors:\n{proc.stdout}\n{proc.stderr}"


class TestScaffoldMypyGate:
    """`mypy src/` がエラー 0（既定設定の回帰防止。
    生成 transitions の型検証は Issue 01 の回帰テストが担当）。"""

    def test_mypy_src_clean(self, runner: CliRunner, tmp_path: Path) -> None:
        project = _scaffold(runner, tmp_path)
        proc = subprocess.run(
            [sys.executable, "-m", "mypy", "src/"],
            capture_output=True, text=True, cwd=str(project), timeout=180,
        )
        assert proc.returncode == 0, f"mypy errors:\n{proc.stdout}\n{proc.stderr}"
