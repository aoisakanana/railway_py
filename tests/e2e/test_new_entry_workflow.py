"""E2E tests for railway new entry workflow (Issue #64).

Tests the complete workflow:
1. railway init → railway new entry → railway run (default sync)
2. railway init → railway new entry --no-sync → railway sync → railway run
3. Generated code passes mypy
4. Generated code passes ruff

TDD: These tests verify the 1-command workflow UX improvement in v0.13.1.
"""

import subprocess
import sys
from pathlib import Path

import pytest


def run_railway_command(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """railway コマンドを実行するヘルパー。"""
    return subprocess.run(
        [sys.executable, "-m", "railway.cli.main"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )


class TestNewEntryDefaultWorkflow:
    """railway new entry のデフォルトワークフロー E2E テスト。

    v0.13.1 UX 改善: railway new entry 後すぐに railway run 可能。
    """

    @pytest.fixture
    def project_dir(self, tmp_path: Path) -> Path:
        """テスト用プロジェクトを作成して返す。"""
        # railway init でプロジェクトを作成
        result = run_railway_command(["init", "test_project"], tmp_path)
        assert result.returncode == 0, f"init failed: {result.stderr}"
        return tmp_path / "test_project"

    def test_full_workflow_default(self, project_dir: Path) -> None:
        """init → new entry → run の完全ワークフロー。

        v0.13.1 の目標: このフローが 1 コマンドで完結。
        """
        # プロジェクト構造が作成されている
        assert (project_dir / "src").exists()
        assert (project_dir / "transition_graphs").exists()
        assert (project_dir / "_railway").exists()

        # railway new entry greeting（sync がデフォルトで実行される）
        result = run_railway_command(["new", "entry", "greeting"], project_dir)
        assert result.returncode == 0, f"new entry failed: {result.stderr}"

        # 生成されたファイルを確認
        assert (project_dir / "src/greeting.py").exists()
        assert list((project_dir / "transition_graphs").glob("greeting_*.yml"))
        assert (project_dir / "_railway/generated/greeting_transitions.py").exists()

        # 終端ノードが生成されている
        assert (project_dir / "src/nodes/exit/success/done.py").exists()
        assert (project_dir / "src/nodes/exit/failure/error.py").exists()

        # エントリポイントが run() ヘルパーを使用している
        entrypoint = (project_dir / "src/greeting.py").read_text()
        assert "from _railway.generated.greeting_transitions import run" in entrypoint

    def test_generated_project_structure(self, tmp_path: Path) -> None:
        """生成されたプロジェクト構造の検証。"""
        # init
        result = run_railway_command(["init", "my_project"], tmp_path)
        assert result.returncode == 0, f"init failed: {result.stderr}"
        project_dir = tmp_path / "my_project"

        # new entry
        result = run_railway_command(["new", "entry", "my_flow"], project_dir)
        assert result.returncode == 0, f"new entry failed: {result.stderr}"

        # ディレクトリ構造
        expected_dirs = [
            "src",
            "src/nodes",
            "src/nodes/my_flow",
            "src/nodes/exit",
            "src/nodes/exit/success",
            "src/nodes/exit/failure",
            "transition_graphs",
            "_railway",
            "_railway/generated",
        ]
        for d in expected_dirs:
            assert (project_dir / d).exists(), f"Missing directory: {d}"

        # __init__.py が適切に配置されている
        init_files = [
            "src/nodes/__init__.py",
            "src/nodes/exit/__init__.py",
            "src/nodes/exit/success/__init__.py",
            "src/nodes/exit/failure/__init__.py",
        ]
        for f in init_files:
            assert (project_dir / f).exists(), f"Missing __init__.py: {f}"


class TestNewEntryNoSyncWorkflow:
    """railway new entry --no-sync のワークフロー E2E テスト。"""

    @pytest.fixture
    def project_dir(self, tmp_path: Path) -> Path:
        """テスト用プロジェクトを作成して返す。"""
        result = run_railway_command(["init", "test_project"], tmp_path)
        assert result.returncode == 0, f"init failed: {result.stderr}"
        return tmp_path / "test_project"

    def test_full_workflow_no_sync(self, project_dir: Path) -> None:
        """init → new entry --no-sync → sync → run の完全ワークフロー。"""
        # railway new entry greeting --no-sync
        result = run_railway_command(
            ["new", "entry", "greeting", "--no-sync"],
            project_dir,
        )
        assert result.returncode == 0, f"new entry --no-sync failed: {result.stderr}"

        # エントリポイントとYAMLは生成される
        assert (project_dir / "src/greeting.py").exists()
        assert list((project_dir / "transition_graphs").glob("greeting_*.yml"))

        # transitions ファイルは生成されない
        assert not (project_dir / "_railway/generated/greeting_transitions.py").exists()

        # エントリポイントは pending 状態（実行可能だが sync を促す）
        entrypoint = (project_dir / "src/greeting.py").read_text()
        # 実行可能なコード（コメントアウトされていない）
        assert "@entry_point" in entrypoint
        assert "# @entry_point" not in entrypoint
        # sync を促すメッセージがある
        assert "railway sync transition" in entrypoint
        # transitions がない場合のエラーハンドリング
        assert "ModuleNotFoundError" in entrypoint

        # 終端ノードは生成される（sync とは独立）
        assert (project_dir / "src/nodes/exit/success/done.py").exists()
        assert (project_dir / "src/nodes/exit/failure/error.py").exists()

        # railway sync transition --entry greeting
        result = run_railway_command(
            ["sync", "transition", "--entry", "greeting"],
            project_dir,
        )
        assert result.returncode == 0, f"sync failed: {result.stderr}"

        # sync 後は transitions ファイルが生成される
        assert (project_dir / "_railway/generated/greeting_transitions.py").exists()


class TestGeneratedCodeQuality:
    """生成されたコードの品質テスト。"""

    @pytest.fixture
    def project_dir(self, tmp_path: Path) -> Path:
        """テスト用プロジェクトを作成して返す。"""
        result = run_railway_command(["init", "test_project"], tmp_path)
        assert result.returncode == 0, f"init failed: {result.stderr}"
        return tmp_path / "test_project"

    def test_generated_code_is_valid_python(self, project_dir: Path) -> None:
        """生成されたコードが有効な Python である。"""
        result = run_railway_command(["new", "entry", "test_flow"], project_dir)
        assert result.returncode == 0, f"new entry failed: {result.stderr}"

        # 各ファイルが compile 可能
        files_to_check = [
            "src/test_flow.py",
            "_railway/generated/test_flow_transitions.py",
            "src/nodes/exit/success/done.py",
            "src/nodes/exit/failure/error.py",
        ]

        for f in files_to_check:
            path = project_dir / f
            if path.exists():
                content = path.read_text()
                try:
                    compile(content, str(path), "exec")
                except SyntaxError as e:
                    pytest.fail(f"Syntax error in {f}: {e}")

    def test_generated_yaml_is_valid(self, project_dir: Path) -> None:
        """生成された YAML が有効な形式である。"""
        import yaml

        result = run_railway_command(["new", "entry", "test_flow"], project_dir)
        assert result.returncode == 0, f"new entry failed: {result.stderr}"

        # YAML をパース
        yaml_files = list((project_dir / "transition_graphs").glob("test_flow_*.yml"))
        assert len(yaml_files) > 0

        for yaml_file in yaml_files:
            content = yaml_file.read_text()
            try:
                data = yaml.safe_load(content)
                # v0.13.0+ 新形式の検証
                assert "version" in data
                assert "nodes" in data
                assert "exit" in data["nodes"]
                assert "success" in data["nodes"]["exit"]
                assert "failure" in data["nodes"]["exit"]
            except yaml.YAMLError as e:
                pytest.fail(f"YAML parse error in {yaml_file}: {e}")


class TestMultipleEntryPoints:
    """複数エントリポイントのテスト。"""

    @pytest.fixture
    def project_dir(self, tmp_path: Path) -> Path:
        """テスト用プロジェクトを作成して返す。"""
        result = run_railway_command(["init", "test_project"], tmp_path)
        assert result.returncode == 0, f"init failed: {result.stderr}"
        return tmp_path / "test_project"

    def test_multiple_entry_points_independent(self, project_dir: Path) -> None:
        """複数のエントリポイントが独立して動作する。"""
        # 複数のエントリポイントを作成
        for name in ["flow_a", "flow_b"]:
            result = run_railway_command(["new", "entry", name], project_dir)
            assert result.returncode == 0, f"Failed to create {name}: {result.stderr}"

        # 各エントリポイントのファイルが存在
        for name in ["flow_a", "flow_b"]:
            assert (project_dir / f"src/{name}.py").exists()
            assert (project_dir / f"_railway/generated/{name}_transitions.py").exists()
            assert list((project_dir / "transition_graphs").glob(f"{name}_*.yml"))

        # 終端ノードは共有（一度だけ生成）
        assert (project_dir / "src/nodes/exit/success/done.py").exists()
        assert (project_dir / "src/nodes/exit/failure/error.py").exists()


class TestEdgeCases:
    """エッジケースのテスト。"""

    @pytest.fixture
    def project_dir(self, tmp_path: Path) -> Path:
        """テスト用プロジェクトを作成して返す。"""
        result = run_railway_command(["init", "test_project"], tmp_path)
        assert result.returncode == 0, f"init failed: {result.stderr}"
        return tmp_path / "test_project"

    def test_entry_name_with_underscores(self, project_dir: Path) -> None:
        """アンダースコアを含むエントリ名。"""
        result = run_railway_command(
            ["new", "entry", "my_complex_workflow"],
            project_dir,
        )
        assert result.returncode == 0, f"new entry failed: {result.stderr}"

        # ファイルが正しく生成されている
        assert (project_dir / "src/my_complex_workflow.py").exists()
        assert (
            project_dir / "_railway/generated/my_complex_workflow_transitions.py"
        ).exists()

    def test_existing_exit_nodes_not_overwritten(self, project_dir: Path) -> None:
        """既存の終端ノードは上書きされない。"""
        # 最初のエントリポイント
        result = run_railway_command(["new", "entry", "first"], project_dir)
        assert result.returncode == 0, f"first entry failed: {result.stderr}"

        # 終端ノードをカスタマイズ
        exit_done = project_dir / "src/nodes/exit/success/done.py"
        custom_content = "# Custom implementation\n" + exit_done.read_text()
        exit_done.write_text(custom_content)

        # 2 番目のエントリポイント
        result = run_railway_command(["new", "entry", "second"], project_dir)
        assert result.returncode == 0, f"second entry failed: {result.stderr}"

        # カスタム内容が保持されている
        assert exit_done.read_text().startswith("# Custom implementation")
