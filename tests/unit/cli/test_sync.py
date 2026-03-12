"""Tests for railway sync transition CLI command."""
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a minimal project structure."""
    # Create transition_graphs directory
    graphs_dir = tmp_path / "transition_graphs"
    graphs_dir.mkdir()

    # Create _railway/generated directory
    railway_dir = tmp_path / "_railway" / "generated"
    railway_dir.mkdir(parents=True)

    # Create a sample YAML
    yaml_content = dedent(
        """
        version: "1.0"
        entrypoint: entry2
        description: "テストワークフロー"

        nodes:
          start:
            module: nodes.start
            function: start_node
            description: "開始ノード"

        exits:
          done:
            code: 0
            description: "完了"

        start: start

        transitions:
          start:
            success: exit::done
    """
    )
    (graphs_dir / "entry2_20250125120000.yml").write_text(yaml_content)

    return tmp_path


class TestSyncTransitionCommand:
    """Test railway sync transition command."""

    def test_sync_single_entry(self, project_dir: Path, monkeypatch):
        """Should sync a single entrypoint."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--entry", "entry2"])

        assert result.exit_code == 0
        assert "entry2" in result.stdout

        # Check generated file exists
        generated = project_dir / "_railway" / "generated" / "entry2_transitions.py"
        assert generated.exists()

    def test_sync_dry_run(self, project_dir: Path, monkeypatch):
        """Should show preview without writing files."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(
            app, ["sync", "transition", "--entry", "entry2", "--dry-run"]
        )

        assert result.exit_code == 0
        assert "プレビュー" in result.stdout or "dry-run" in result.stdout.lower()

        # Should NOT create file
        generated = project_dir / "_railway" / "generated" / "entry2_transitions.py"
        assert not generated.exists()

    def test_sync_validate_only(self, project_dir: Path, monkeypatch):
        """Should validate without generating code."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(
            app, ["sync", "transition", "--entry", "entry2", "--validate-only"]
        )

        assert result.exit_code == 0
        assert "検証" in result.stdout or "valid" in result.stdout.lower()

    def test_sync_entry_not_found(self, project_dir: Path, monkeypatch):
        """Should error when entrypoint YAML not found."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--entry", "nonexistent"])

        assert result.exit_code != 0
        # Error may be in stdout or combined output
        output = result.output if result.output else ""
        assert "見つかりません" in output or "not found" in output.lower()

    def test_sync_all_entries(self, project_dir: Path, monkeypatch):
        """Should sync all entrypoints with --all flag."""
        from railway.cli.main import app

        # Add another YAML
        yaml2 = dedent(
            """
            version: "1.0"
            entrypoint: other
            description: ""
            nodes:
              a:
                module: nodes.a
                function: func_a
                description: ""
            exits:
              done:
                code: 0
                description: ""
            start: a
            transitions:
              a:
                success: exit::done
        """
        )
        (project_dir / "transition_graphs" / "other_20250125130000.yml").write_text(
            yaml2
        )

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--all"])

        assert result.exit_code == 0

        # Both files should be generated
        assert (project_dir / "_railway" / "generated" / "entry2_transitions.py").exists()
        assert (
            project_dir / "_railway" / "generated" / "other_transitions.py"
        ).exists()

    def test_sync_validation_error(self, project_dir: Path, monkeypatch):
        """Should report validation errors."""
        from railway.cli.main import app

        # Create invalid YAML (missing start node)
        invalid_yaml = dedent(
            """
            version: "1.0"
            entrypoint: invalid
            description: ""
            nodes:
              a:
                module: nodes.a
                function: func_a
                description: ""
            exits: {}
            start: nonexistent
            transitions: {}
        """
        )
        (project_dir / "transition_graphs" / "invalid_20250125140000.yml").write_text(
            invalid_yaml
        )

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--entry", "invalid"])

        assert result.exit_code != 0
        # Error may be in stdout or combined output
        output = result.output if result.output else ""
        assert "エラー" in output or "error" in output.lower()


class TestFindLatestYaml:
    """Test YAML file discovery."""

    def test_find_latest_yaml(self, tmp_path: Path):
        """Should find the latest YAML by timestamp."""
        from railway.cli.sync import find_latest_yaml

        graphs_dir = tmp_path / "transition_graphs"
        graphs_dir.mkdir()

        # Create files with different timestamps
        (graphs_dir / "entry2_20250101000000.yml").write_text("old")
        (graphs_dir / "entry2_20250125120000.yml").write_text("new")
        (graphs_dir / "entry2_20250115000000.yml").write_text("middle")

        latest = find_latest_yaml(graphs_dir, "entry2")

        assert latest is not None
        assert latest.name == "entry2_20250125120000.yml"

    def test_find_latest_yaml_none(self, tmp_path: Path):
        """Should return None when no matching YAML exists."""
        from railway.cli.sync import find_latest_yaml

        graphs_dir = tmp_path / "transition_graphs"
        graphs_dir.mkdir()

        latest = find_latest_yaml(graphs_dir, "nonexistent")

        assert latest is None

    def test_find_all_entrypoints(self, tmp_path: Path):
        """Should find all unique entrypoints."""
        from railway.cli.sync import find_all_entrypoints

        graphs_dir = tmp_path / "transition_graphs"
        graphs_dir.mkdir()

        (graphs_dir / "entry2_20250101.yml").write_text("")
        (graphs_dir / "entry2_20250102.yml").write_text("")
        (graphs_dir / "other_20250101.yml").write_text("")

        entries = find_all_entrypoints(graphs_dir)

        assert set(entries) == {"entry2", "other"}


class TestConvertYamlIfOldFormat:
    """Test _convert_yaml_if_old_format function."""

    def test_new_format_valid_shows_message(self, tmp_path: Path, capsys):
        """新形式かつスキーマ検証成功時は「既に新形式」を表示。"""
        from railway.cli.sync import _convert_yaml_if_old_format

        yaml_content = """\
version: "1.0"
entrypoint: test
description: ""
nodes:
  start:
    module: nodes.start
    function: start
    description: ""
  exit:
    success:
      done:
        description: ""
start: start
transitions:
  start:
    success::done: exit.success.done
"""
        yaml_path = tmp_path / "test.yml"
        yaml_path.write_text(yaml_content)

        result = _convert_yaml_if_old_format(yaml_path)

        assert result.converted is False
        captured = capsys.readouterr()
        assert "既に新形式" in captured.out

    def test_new_format_invalid_no_message(self, tmp_path: Path, capsys):
        """新形式だがスキーマエラー時は「既に新形式」を表示しない。"""
        from railway.cli.sync import _convert_yaml_if_old_format

        # version がない不完全な YAML（exits もないので新形式扱い）
        yaml_content = """\
entrypoint: test
description: ""
nodes:
  start:
    description: ""
start: start
transitions: {}
"""
        yaml_path = tmp_path / "invalid.yml"
        yaml_path.write_text(yaml_content)

        result = _convert_yaml_if_old_format(yaml_path)

        assert result.converted is False
        captured = capsys.readouterr()
        # スキーマエラーがあるので「既に新形式」は表示されない
        assert "既に新形式" not in captured.out


class TestSyncOutput:
    """Test sync command output formatting."""

    def test_success_message(self, project_dir: Path, monkeypatch):
        """Should show success message with details."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--entry", "entry2"])

        assert (
            "✓" in result.stdout
            or "成功" in result.stdout
            or "Success" in result.stdout
        )

    def test_shows_generated_path(self, project_dir: Path, monkeypatch):
        """Should show path to generated file."""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        result = runner.invoke(app, ["sync", "transition", "--entry", "entry2"])

        assert "_railway/generated/entry2_transitions.py" in result.stdout


class TestSyncPyTyped:
    """sync で py.typed が生成されるかのテスト（mypy 対応）"""

    def test_creates_py_typed_in_generated(self, project_dir: Path, monkeypatch):
        """sync で _railway/generated/py.typed が生成される"""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        runner.invoke(app, ["sync", "transition", "--entry", "entry2"])

        py_typed = project_dir / "_railway" / "generated" / "py.typed"
        assert py_typed.exists(), "py.typed should be created in _railway/generated/"

    def test_py_typed_is_empty(self, project_dir: Path, monkeypatch):
        """py.typed は空ファイル"""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        runner.invoke(app, ["sync", "transition", "--entry", "entry2"])

        py_typed = project_dir / "_railway" / "generated" / "py.typed"
        assert py_typed.read_text() == "", "py.typed should be empty"

    def test_py_typed_not_recreated_if_exists(self, project_dir: Path, monkeypatch):
        """py.typed が既に存在する場合は再作成しない"""
        from railway.cli.main import app

        monkeypatch.chdir(project_dir)

        # 先に py.typed を作成
        py_typed = project_dir / "_railway" / "generated" / "py.typed"
        py_typed.write_text("existing")

        runner.invoke(app, ["sync", "transition", "--entry", "entry2"])

        # 上書きされていないことを確認
        assert py_typed.read_text() == "existing"


# =============================================================================
# Issue 30-02: _has_analysis_errors 純粋関数テスト
# =============================================================================


class TestHasAnalysisErrors:
    """_has_analysis_errors() の純粋関数テスト。"""

    def test_no_errors_returns_false(self) -> None:
        """エラーがなければ False を返すこと。"""
        from railway.cli.sync import _has_analysis_errors
        from railway.core.dag.path_validator import PathValidationResult

        path_result = PathValidationResult(issues=(), node_analyses={})
        assert _has_analysis_errors({}, path_result) is False

    def test_path_error_returns_true(self) -> None:
        """E010 経路エラーがあれば True を返すこと。"""
        from railway.cli.sync import _has_analysis_errors
        from railway.core.dag.path_validator import PathIssue, PathValidationResult

        path_result = PathValidationResult(
            issues=(
                PathIssue(
                    code="E010",
                    severity="error",
                    message="必須フィールドが不足",
                    node_name="escalate",
                    field_name="hostname",
                    file_path="nodes/escalate.py",
                    line=10,
                ),
            ),
            node_analyses={},
        )
        assert _has_analysis_errors({}, path_result) is True

    def test_e015_violation_returns_true(self) -> None:
        """E015 違反があれば True を返すこと。"""
        from railway.cli.sync import _has_analysis_errors
        from railway.core.dag.board_analyzer import AnalysisViolation, NodeAnalysis
        from railway.core.dag.path_validator import PathValidationResult

        analysis = NodeAnalysis(
            node_name="start",
            file_path="nodes/start.py",
            reads_required=frozenset(),
            reads_optional=frozenset(),
            branch_writes=(),
            all_writes=frozenset(),
            outcomes=(),
            violations=(
                AnalysisViolation(
                    code="E015",
                    message="第一引数が board でない",
                    line=5,
                    file_path="nodes/start.py",
                ),
            ),
        )
        path_result = PathValidationResult(
            issues=(), node_analyses={"start": analysis}
        )
        assert _has_analysis_errors({"start": analysis}, path_result) is True

    def test_warning_only_returns_false(self) -> None:
        """W001 のみ（warning）の場合は False を返すこと。"""
        from railway.cli.sync import _has_analysis_errors
        from railway.core.dag.path_validator import PathIssue, PathValidationResult

        path_result = PathValidationResult(
            issues=(
                PathIssue(
                    code="W001",
                    severity="warning",
                    message="未使用の writes",
                    node_name="check",
                    field_name="unused_field",
                    file_path="nodes/check.py",
                    line=15,
                ),
            ),
            node_analyses={},
        )
        assert _has_analysis_errors({}, path_result) is False

    def test_is_pure_function(self) -> None:
        """同じ入力で同じ出力を返すこと。"""
        from railway.cli.sync import _has_analysis_errors
        from railway.core.dag.path_validator import PathValidationResult

        path_result = PathValidationResult(issues=(), node_analyses={})
        r1 = _has_analysis_errors({}, path_result)
        r2 = _has_analysis_errors({}, path_result)
        assert r1 == r2


# =============================================================================
# Issue 30-02: sync Board codegen 統合テスト
# =============================================================================

BOARD_NODE_CODE = '''\
from railway import node
from railway.core.dag import Outcome


@node
def start(board) -> Outcome:
    board.result = "done"
    return Outcome.success("done")
'''

EXIT_NODE_CODE = '''\
from railway import node


@node(name="exit.success.done")
def done(board) -> None:
    pass
'''

SIMPLE_BOARD_YAML = '''\
version: "1.0"
entrypoint: test_wf
description: "テスト"
nodes:
  start:
    module: nodes.test_wf.start
    function: start
    description: "開始"
  exit:
    success:
      done:
        description: "正常終了"
start: start
transitions:
  start:
    success::done: exit.success.done
'''

E015_VIOLATION_CODE = '''\
from railway import node
from railway.core.dag import Outcome


@node
def start(ctx) -> Outcome:
    return Outcome.success("done")
'''


def _setup_board_project(
    tmp_path: Path,
    *,
    node_code: str = BOARD_NODE_CODE,
    exit_node_code: str = EXIT_NODE_CODE,
) -> tuple[Path, Path]:
    """Board モードのプロジェクト構造を tmp_path に構築する。"""
    graphs_dir = tmp_path / "transition_graphs"
    graphs_dir.mkdir()
    output_dir = tmp_path / "_railway" / "generated"
    output_dir.mkdir(parents=True)
    src_dir = tmp_path / "src"

    node_dir = src_dir / "nodes" / "test_wf"
    node_dir.mkdir(parents=True)
    (node_dir / "start.py").write_text(node_code)

    exit_dir = src_dir / "nodes" / "exit" / "success"
    exit_dir.mkdir(parents=True)
    (exit_dir / "done.py").write_text(exit_node_code)

    (graphs_dir / "test_wf_20260101000000.yml").write_text(SIMPLE_BOARD_YAML)

    return graphs_dir, output_dir


class TestSyncBoardCodegenIntegration:
    """sync パイプラインの Board codegen 統合テスト。"""

    def test_sync_generates_board_run_for_board_nodes(
        self, tmp_path: Path
    ) -> None:
        """Board ノードの sync で Board 用 run() が生成されること。"""
        from railway.cli.sync import _sync_entry

        graphs_dir, output_dir = _setup_board_project(tmp_path)
        _sync_entry(
            entry_name="test_wf",
            graphs_dir=graphs_dir,
            output_dir=output_dir,
            dry_run=False,
            validate_only=False,
        )

        generated = (output_dir / "test_wf_transitions.py").read_text()
        assert "WorkflowResult" in generated
        assert "BoardBase" in generated
        assert "ExitContract" not in generated
        assert "RAILWAY_TRACE" in generated

    def test_sync_without_src_dir_uses_contract_mode(
        self, tmp_path: Path
    ) -> None:
        """src/ がない場合は Contract モードにフォールバック。"""
        from railway.cli.sync import _sync_entry

        graphs_dir = tmp_path / "transition_graphs"
        graphs_dir.mkdir()
        output_dir = tmp_path / "_railway" / "generated"
        output_dir.mkdir(parents=True)
        (graphs_dir / "test_wf_20260101000000.yml").write_text(SIMPLE_BOARD_YAML)

        _sync_entry(
            entry_name="test_wf",
            graphs_dir=graphs_dir,
            output_dir=output_dir,
            dry_run=False,
            validate_only=False,
        )

        generated = (output_dir / "test_wf_transitions.py").read_text()
        assert "ExitContract" in generated
        assert "BoardBase" not in generated

    def test_dry_run_shows_board_mode_preview(
        self, tmp_path: Path, capsys
    ) -> None:
        """--dry-run でも Board モードのプレビューが表示されること。"""
        from railway.cli.sync import _sync_entry

        graphs_dir, output_dir = _setup_board_project(tmp_path)
        _sync_entry(
            entry_name="test_wf",
            graphs_dir=graphs_dir,
            output_dir=output_dir,
            dry_run=True,
            validate_only=False,
        )

        assert not (output_dir / "test_wf_transitions.py").exists()
        captured = capsys.readouterr()
        assert "WorkflowResult" in captured.out

    def test_dry_run_does_not_write_board_type_file(
        self, tmp_path: Path
    ) -> None:
        """dry-run では Board 型ファイルが生成されないこと。"""
        from railway.cli.sync import _sync_entry

        graphs_dir, output_dir = _setup_board_project(tmp_path)
        _sync_entry(
            entry_name="test_wf",
            graphs_dir=graphs_dir,
            output_dir=output_dir,
            dry_run=True,
            validate_only=False,
        )

        assert not (output_dir / "test_wf_board.py").exists()

    def test_validate_only_detects_e015_violations(
        self, tmp_path: Path
    ) -> None:
        """validate_only でも Board 解析の E015 エラーが SyncError を発生させること。"""
        from railway.cli.sync import SyncError, _sync_entry

        graphs_dir, output_dir = _setup_board_project(
            tmp_path,
            node_code=E015_VIOLATION_CODE,
        )

        with pytest.raises(SyncError):
            _sync_entry(
                entry_name="test_wf",
                graphs_dir=graphs_dir,
                output_dir=output_dir,
                dry_run=False,
                validate_only=True,
            )

    def test_validate_only_displays_e015_to_stderr(
        self, tmp_path: Path, capsys
    ) -> None:
        """validate_only で E015 違反が stderr に表示されること。"""
        from railway.cli.sync import SyncError, _sync_entry

        graphs_dir, output_dir = _setup_board_project(
            tmp_path,
            node_code=E015_VIOLATION_CODE,
        )

        with pytest.raises(SyncError):
            _sync_entry(
                entry_name="test_wf",
                graphs_dir=graphs_dir,
                output_dir=output_dir,
                dry_run=False,
                validate_only=True,
            )

        captured = capsys.readouterr()
        assert "E015" in captured.err

    def test_contract_nodes_in_src_use_contract_mode(
        self, tmp_path: Path
    ) -> None:
        """src/ に Contract ノードのみの場合は Contract モードになること。"""
        from railway.cli.sync import _sync_entry

        CONTRACT_NODE_CODE = '''\
from railway import node
from railway.core.dag import Outcome


class MyContext:
    pass


@node(output=MyContext)
def start(ctx=None) -> tuple[MyContext, Outcome]:
    return MyContext(), Outcome.success("done")
'''
        CONTRACT_EXIT_CODE = '''\
from railway import ExitContract, node


class DoneResult(ExitContract):
    exit_state: str = "success.done"


@node(name="exit.success.done")
def done(ctx) -> DoneResult:
    return DoneResult()
'''
        graphs_dir, output_dir = _setup_board_project(
            tmp_path,
            node_code=CONTRACT_NODE_CODE,
            exit_node_code=CONTRACT_EXIT_CODE,
        )

        _sync_entry(
            entry_name="test_wf",
            graphs_dir=graphs_dir,
            output_dir=output_dir,
            dry_run=False,
            validate_only=False,
        )

        generated = (output_dir / "test_wf_transitions.py").read_text()
        assert "ExitContract" in generated
        assert "BoardBase" not in generated
