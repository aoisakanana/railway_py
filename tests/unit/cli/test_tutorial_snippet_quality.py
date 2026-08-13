"""Tests for TUTORIAL 掲載コードの品質ゲート準拠 (v0.13.26 Issue 03, NEW-2).

観測成立条件（Issue 03 で必須化）: ruff の isort first-party 判定は
import 先モジュールの実在に依存するため、スニペットは **scaffold 済み
プロジェクトの実パス**（src/nodes/greeting/ 等）に配置して検査する。
素朴な抽出先での検査は正しい修正形を FAIL させ、誤った Green に収束する。
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner


@pytest.fixture
def project(tmp_path: Path):
    """init + new entry greeting 済みプロジェクト。"""
    from railway.cli.main import app
    runner = CliRunner()
    old = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert runner.invoke(app, ["init", "snip_proj"]).exit_code == 0
        os.chdir(tmp_path / "snip_proj")
        assert runner.invoke(app, ["new", "entry", "greeting"]).exit_code == 0
        yield tmp_path / "snip_proj"
    finally:
        os.chdir(old)


def _extract_step4_snippets(tutorial: str) -> list[tuple[str, str]]:
    """Step 4 から (実パス, コード) のペアを抽出する。

    Step 4 は各コードブロックの直前にファイルパス（src/nodes/greeting/*.py）を
    明示する構成のため、パスとブロックを対応付けられる。
    """
    step4 = tutorial.split("## Step 4")[1].split("## Step 5")[0]
    pairs = re.findall(
        r"`(src/nodes/greeting/\w+\.py)`.*?```python\n(.*?)```",
        step4,
        re.DOTALL,
    )
    return pairs


class TestStep4SnippetsPassBundledRuff:
    """Step 4 の写経コードを実パスに配置すると同梱 ruff 設定を通る。"""

    def test_snippets_extracted(self, project: Path) -> None:
        tutorial = (project / "TUTORIAL.md").read_text()
        pairs = _extract_step4_snippets(tutorial)
        assert len(pairs) >= 4, (
            f"Step 4 のパス付きスニペットが想定より少ない: {len(pairs)}"
        )

    def test_snippets_placed_at_real_paths_pass_ruff(self, project: Path) -> None:
        tutorial = (project / "TUTORIAL.md").read_text()
        pairs = _extract_step4_snippets(tutorial)
        assert pairs, "スニペットが抽出できない"

        written: list[str] = []
        for rel_path, code in pairs:
            target = project / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(code)
            written.append(rel_path)

        proc = subprocess.run(
            [sys.executable, "-m", "ruff", "check", *written],
            capture_output=True, text=True, cwd=str(project), timeout=120,
        )
        assert proc.returncode == 0, (
            f"TUTORIAL 掲載コードが同梱 ruff 設定に違反:\n{proc.stdout}"
        )
