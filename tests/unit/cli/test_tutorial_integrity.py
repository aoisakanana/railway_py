"""Tests for TUTORIAL の記載と生成物の整合 (v0.13.25 Issue 07 + Issue 06 の ruff 案内).

- Step 3.1 の掲載コードが生成物（start.py テンプレート）と一致する
- TUTORIAL 内の相対リンク先が生成プロジェクトに実在する
- Step 1 にログ出力の注記がある
- ruff の品質チェック案内（`ruff check .`）がある
"""
import os
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner


@pytest.fixture
def generated(tmp_path: Path):
    """init + new entry greeting 済みプロジェクトの TUTORIAL と生成物。"""
    from railway.cli.main import app
    runner = CliRunner()
    old = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert runner.invoke(app, ["init", "tut_proj"]).exit_code == 0
        os.chdir(tmp_path / "tut_proj")
        assert runner.invoke(app, ["new", "entry", "greeting"]).exit_code == 0
        project = tmp_path / "tut_proj"
        return {
            "project": project,
            "tutorial": (project / "TUTORIAL.md").read_text(),
            "start_py": (project / "src/nodes/greeting/start.py").read_text(),
        }
    finally:
        os.chdir(old)


class TestStep31MatchesGeneratedCode:
    """DOC-1: Step 3.1 の掲載コードと生成物の一致。"""

    def test_no_stale_message_text(self, generated: dict) -> None:
        assert 'message="Hello, Railway!"' not in generated["tutorial"]

    def test_message_matches_generated(self, generated: dict) -> None:
        assert 'message="Hello"' in generated["tutorial"]
        assert 'message="Hello"' in generated["start_py"]

    def test_import_form_matches_generated(self, generated: dict) -> None:
        """TUTORIAL の Outcome import はテンプレートと同一形に統一されている。"""
        assert "from railway.core.dag.outcome import Outcome" in generated["start_py"]
        assert "from railway.core.dag import Outcome" not in generated["tutorial"]

    def test_generated_start_body_appears_in_tutorial(self, generated: dict) -> None:
        """生成された start 関数の本体（分岐と返り値）が TUTORIAL に載っている。"""
        for fragment in (
            "def start(ctx: GreetingContext | None = None)",
            "if ctx is None:",
            'return ctx, Outcome.success("done")',
        ):
            assert fragment in generated["tutorial"], f"欠落: {fragment}"
            assert fragment in generated["start_py"], f"生成物に欠落: {fragment}"


class TestRelativeLinksResolve:
    """DOC-2: TUTORIAL 内の相対リンクが生成プロジェクト内で解決できる。"""

    def test_all_relative_links_exist(self, generated: dict) -> None:
        links = re.findall(r"\]\(([^)#]+)\)", generated["tutorial"])
        relative = [
            l for l in links
            if not l.startswith(("http://", "https://", "mailto:"))
        ]
        missing = [
            l for l in relative if not (generated["project"] / l).exists()
        ]
        assert not missing, f"リンク切れ: {missing}"


class TestStep1LogNote:
    """DOC-4: Step 1 の期待出力にログ行の注記がある。"""

    def test_log_note_present(self, generated: dict) -> None:
        assert "Running entry point" in generated["tutorial"], (
            "Step 1 に実際の出力（ログ行が先行する旨）の注記が必要"
        )


class TestRuffGuidance:
    """Issue 06: ruff の品質チェック案内が `ruff check .` で統一されている。"""

    def test_ruff_check_dot_present(self, generated: dict) -> None:
        assert "ruff check ." in generated["tutorial"]


class TestStep23YamlMatchesGenerated:
    """Step 2.3 の掲載 YAML が生成物と一致する (v0.13.26 NEW-6)。"""

    def test_step23_yaml_equals_generated_template(self, generated: dict) -> None:
        from railway.cli.new import _get_dag_yaml_template
        expected = _get_dag_yaml_template("greeting").strip()
        tutorial = generated["tutorial"]
        step2 = tutorial.split("## Step 2")[1].split("## Step 3")[0]
        blocks = re.findall(r"```yaml\s*\n(.*?)```", step2, re.DOTALL)
        assert blocks, "Step 2.3 に yaml ブロックがない"
        assert any(b.strip() == expected for b in blocks), (
            "Step 2.3 の YAML が生成テンプレートと一致しない"
        )
