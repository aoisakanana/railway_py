"""Tests for railway new entry の出力真実性と YAML マッチ非対称の解消 (v0.13.25 Issue 02).

- _find_existing_yaml が sync.py の find_latest_yaml と同じ厳密マッチであること
- プレフィックス関係の別エントリ YAML を「既存」と誤認しないこと
- 出力（使用:/生成:）が実際の動作と一致すること
- exit code 規則: 正常 0 / sync 失敗 1 / --no-sync 明示 0
"""
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def project(tmp_path: Path):
    """最小プロジェクト構造を作成し cwd を移動する。"""
    (tmp_path / "src").mkdir()
    (tmp_path / "transition_graphs").mkdir()
    (tmp_path / "_railway/generated").mkdir(parents=True)
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(old_cwd)


class TestFindExistingYamlStrictMatch:
    """_find_existing_yaml の厳密マッチ（Issue 29-01 と同型）。"""

    def test_prefix_mismatch_excluded(self, tmp_path: Path) -> None:
        from railway.cli.new import _find_existing_yaml
        (tmp_path / "alert_hoge_20260101000000.yml").touch()
        assert _find_existing_yaml(tmp_path, "alert") is None

    def test_exact_match(self, tmp_path: Path) -> None:
        from railway.cli.new import _find_existing_yaml
        (tmp_path / "alert_20260101000000.yml").touch()
        result = _find_existing_yaml(tmp_path, "alert")
        assert result is not None
        assert result.name == "alert_20260101000000.yml"

    def test_underscore_entry_exact_match(self, tmp_path: Path) -> None:
        from railway.cli.new import _find_existing_yaml
        (tmp_path / "alert_20260101000000.yml").touch()
        (tmp_path / "alert_hoge_20260101000000.yml").touch()
        result = _find_existing_yaml(tmp_path, "alert_hoge")
        assert result is not None
        assert result.name == "alert_hoge_20260101000000.yml"

    def test_non_numeric_suffix_ignored(self, tmp_path: Path) -> None:
        from railway.cli.new import _find_existing_yaml
        (tmp_path / "alert_backup.yml").touch()
        assert _find_existing_yaml(tmp_path, "alert") is None

    def test_latest_numeric_selected(self, tmp_path: Path) -> None:
        from railway.cli.new import _find_existing_yaml
        (tmp_path / "alert_20260101000000.yml").touch()
        (tmp_path / "alert_20260201000000.yml").touch()
        result = _find_existing_yaml(tmp_path, "alert")
        assert result is not None
        assert result.name == "alert_20260201000000.yml"


class TestNewEntryPrefixScenario:
    """報告の再現手順: alert_hoge 存在下での new entry alert。"""

    def test_creates_own_yaml_and_transitions(
        self, runner: CliRunner, project: Path
    ) -> None:
        from railway.cli.main import app

        r1 = runner.invoke(app, ["new", "entry", "alert_hoge"])
        assert r1.exit_code == 0, r1.stdout

        r2 = runner.invoke(app, ["new", "entry", "alert"])
        assert r2.exit_code == 0, f"output={r2.output}"

        # alert 用 YAML が新規生成されている
        own_yamls = [
            p for p in (project / "transition_graphs").glob("alert_*.yml")
            if not p.name.startswith("alert_hoge_")
        ]
        assert len(own_yamls) == 1, "alert 用 YAML が新規生成されるべき"
        # transitions が実在する
        assert (project / "_railway/generated/alert_transitions.py").exists()

    def test_output_does_not_mention_other_entry(
        self, runner: CliRunner, project: Path
    ) -> None:
        from railway.cli.main import app

        runner.invoke(app, ["new", "entry", "alert_hoge"])
        r2 = runner.invoke(app, ["new", "entry", "alert"])
        assert "alert_hoge" not in r2.stdout.replace(
            "alert_hoge_transitions", ""
        ), f"別エントリの YAML 名が出力に現れてはならない: {r2.stdout}"


class TestOutputTruthfulness:
    """「生成:」「作成:」表示されたパスは実在する。"""

    def test_all_reported_paths_exist(self, runner: CliRunner, project: Path) -> None:
        from railway.cli.main import app

        result = runner.invoke(app, ["new", "entry", "alert"])
        assert result.exit_code == 0
        for line in result.stdout.splitlines():
            line = line.strip()
            for prefix in ("作成: ", "生成: ", "使用: "):
                if line.startswith(prefix):
                    reported = line[len(prefix):].strip()
                    if prefix == "使用: ":
                        reported = f"transition_graphs/{reported}"
                    assert (project / reported).exists(), (
                        f"表示されたパスが存在しない: {reported}"
                    )


class TestExitCodeRules:
    """exit code 規則（Issue 02 で決定）。"""

    def test_normal_flow_exit_zero(self, runner: CliRunner, project: Path) -> None:
        from railway.cli.main import app
        result = runner.invoke(app, ["new", "entry", "alert"])
        assert result.exit_code == 0

    def test_no_sync_explicit_exit_zero(
        self, runner: CliRunner, project: Path
    ) -> None:
        from railway.cli.main import app
        result = runner.invoke(app, ["new", "entry", "alert", "--no-sync"])
        assert result.exit_code == 0
        # --no-sync では transitions を生成しない（仕様）
        assert not (project / "_railway/generated/alert_transitions.py").exists()

    def test_sync_failure_exit_one_with_warning(
        self, runner: CliRunner, project: Path
    ) -> None:
        """既存 YAML が壊れていて sync が失敗する場合、exit 1 + stderr 警告。"""
        from railway.cli.main import app

        # 正確な名前の壊れた新形式 YAML（transitions が不正）
        broken = (
            'version: "1.0"\n'
            "entrypoint: alert\n"
            'description: "broken"\n'
            "nodes:\n"
            "  start:\n"
            "    module: nodes.alert.start\n"
            "    function: start\n"
            "start: start\n"
            "transitions:\n"
            "  start:\n"
            "    success::go: nonexistent_node\n"
        )
        (project / "transition_graphs/alert_20260101000000.yml").write_text(broken)

        result = runner.invoke(app, ["new", "entry", "alert"])
        assert result.exit_code == 1, (
            f"sync 失敗時は exit 1 であるべき: stdout={result.stdout}"
        )
        assert "警告" in result.stderr or "エラー" in result.stderr
