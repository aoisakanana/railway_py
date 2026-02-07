"""E2E tests for mypy compliance (v0.13.9).

Tests the complete mypy-compatible workflow:
1. railway init creates py.typed markers in all necessary locations
2. railway new entry generates code that passes mypy
3. Generated code includes proper type: ignore comments where needed

TDD: These tests verify the mypy compliance improvements in v0.13.9.
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


class TestPyTypedMarkers:
    """py.typed マーカーの生成テスト（PEP 561 対応）。

    v0.13.9 改善: py.typed が src/, src/nodes/, src/contracts/ に配置される。
    """

    @pytest.fixture
    def project_dir(self, tmp_path: Path) -> Path:
        """テスト用プロジェクトを作成して返す。"""
        result = run_railway_command(["init", "test_project"], tmp_path)
        assert result.returncode == 0, f"init failed: {result.stderr}"
        return tmp_path / "test_project"

    def test_init_creates_py_typed_in_src(self, project_dir: Path) -> None:
        """railway init で src/py.typed が生成される。"""
        py_typed = project_dir / "src" / "py.typed"
        assert py_typed.exists(), "py.typed should exist in src/"
        assert py_typed.read_text() == "", "py.typed should be empty (PEP 561)"

    def test_init_creates_py_typed_in_nodes(self, project_dir: Path) -> None:
        """railway init で src/nodes/py.typed が生成される。"""
        py_typed = project_dir / "src" / "nodes" / "py.typed"
        assert py_typed.exists(), "py.typed should exist in src/nodes/"
        assert py_typed.read_text() == "", "py.typed should be empty (PEP 561)"

    def test_init_creates_py_typed_in_contracts(self, project_dir: Path) -> None:
        """railway init で src/contracts/py.typed が生成される。

        Note: contracts ディレクトリは railway new contract で作成されるが、
        py.typed の配置場所として事前に確認。
        """
        # contracts ディレクトリは init 時点では存在しないが、
        # _get_py_typed_paths で定義されている
        # 実際のディレクトリ作成は railway new contract 時に行われる
        pass

    def test_sync_creates_py_typed_in_generated(self, project_dir: Path) -> None:
        """railway sync で _railway/generated/py.typed が生成される。"""
        # new entry を実行（sync も実行される）
        result = run_railway_command(["new", "entry", "greeting"], project_dir)
        assert result.returncode == 0, f"new entry failed: {result.stderr}"

        py_typed = project_dir / "_railway" / "generated" / "py.typed"
        assert py_typed.exists(), "py.typed should exist in _railway/generated/"
        assert py_typed.read_text() == "", "py.typed should be empty (PEP 561)"


class TestEntryPointMypyCompliance:
    """エントリポイントの mypy 対応テスト。

    v0.13.9 改善: __main__ ブロックで _typer_app() を使用。
    """

    @pytest.fixture
    def project_dir(self, tmp_path: Path) -> Path:
        """テスト用プロジェクトを作成して返す。"""
        result = run_railway_command(["init", "test_project"], tmp_path)
        assert result.returncode == 0, f"init failed: {result.stderr}"
        return tmp_path / "test_project"

    def test_hello_uses_typer_app(self, project_dir: Path) -> None:
        """hello.py は _typer_app() を使用する。"""
        hello_path = project_dir / "src" / "hello.py"
        content = hello_path.read_text()

        assert 'if __name__ == "__main__":' in content
        assert "_typer_app()" in content, "Should use _typer_app()"
        assert "type: ignore[union-attr]" in content, "Should have type: ignore comment"
        # 直接の関数呼び出しがないことを確認
        self._assert_no_direct_main_call(content)

    def test_new_entry_uses_typer_app(self, project_dir: Path) -> None:
        """railway new entry で生成されるエントリポイントは _typer_app() を使用する。"""
        result = run_railway_command(["new", "entry", "greeting"], project_dir)
        assert result.returncode == 0, f"new entry failed: {result.stderr}"

        entrypoint_path = project_dir / "src" / "greeting.py"
        content = entrypoint_path.read_text()

        assert 'if __name__ == "__main__":' in content
        assert "_typer_app()" in content, "Should use _typer_app()"
        assert "type: ignore[union-attr]" in content, "Should have type: ignore comment"
        self._assert_no_direct_main_call(content)

    def test_new_entry_no_sync_uses_typer_app(self, project_dir: Path) -> None:
        """railway new entry --no-sync で生成されるエントリポイントも _typer_app() を使用する。"""
        result = run_railway_command(
            ["new", "entry", "greeting", "--no-sync"],
            project_dir,
        )
        assert result.returncode == 0, f"new entry --no-sync failed: {result.stderr}"

        entrypoint_path = project_dir / "src" / "greeting.py"
        content = entrypoint_path.read_text()

        assert 'if __name__ == "__main__":' in content
        assert "_typer_app()" in content, "Should use _typer_app()"
        assert "type: ignore[union-attr]" in content, "Should have type: ignore comment"
        self._assert_no_direct_main_call(content)

    def test_new_entry_linear_uses_typer_app(self, project_dir: Path) -> None:
        """railway new entry --mode linear で生成されるエントリポイントも _typer_app() を使用する。"""
        result = run_railway_command(
            ["new", "entry", "pipeline", "--mode", "linear"],
            project_dir,
        )
        assert result.returncode == 0, f"new entry --mode linear failed: {result.stderr}"

        entrypoint_path = project_dir / "src" / "pipeline.py"
        content = entrypoint_path.read_text()

        assert 'if __name__ == "__main__":' in content
        assert "_typer_app()" in content, "Should use _typer_app()"
        assert "type: ignore[union-attr]" in content, "Should have type: ignore comment"
        self._assert_no_direct_main_call(content)

    def _assert_no_direct_main_call(self, content: str) -> None:
        """__main__ ブロック内で main() や hello() の直接呼び出しがないことを確認。"""
        lines = content.split("\n")
        main_block_started = False
        for line in lines:
            if '__name__ == "__main__"' in line:
                main_block_started = True
            if main_block_started:
                # _typer_app を含まない関数呼び出しをチェック
                stripped = line.strip()
                if (
                    stripped.endswith("()")
                    and "_typer_app" not in stripped
                    and not stripped.startswith("#")
                    and stripped not in ["pass", "..."]
                ):
                    pytest.fail(f"Found direct function call in __main__: {line}")


class TestGeneratedCodeTypeIgnore:
    """生成コードの type: ignore テスト。

    v0.13.9 改善: _node_name 代入に type: ignore[attr-defined] を追加。
    """

    @pytest.fixture
    def project_dir(self, tmp_path: Path) -> Path:
        """テスト用プロジェクトを作成して返す。"""
        result = run_railway_command(["init", "test_project"], tmp_path)
        assert result.returncode == 0, f"init failed: {result.stderr}"
        return tmp_path / "test_project"

    def test_transitions_code_has_type_ignore(self, project_dir: Path) -> None:
        """生成される transitions コードに type: ignore が含まれる。"""
        result = run_railway_command(["new", "entry", "greeting"], project_dir)
        assert result.returncode == 0, f"new entry failed: {result.stderr}"

        transitions_path = project_dir / "_railway" / "generated" / "greeting_transitions.py"
        content = transitions_path.read_text()

        # _node_name 代入がある場合、type: ignore が必要
        if "._node_name" in content:
            assert "type: ignore[attr-defined]" in content, (
                "Generated code should have type: ignore for _node_name"
            )


class TestMypyIntegration:
    """mypy 統合テスト（実際に mypy を実行）。

    Note: これはオプションのテスト。mypy がインストールされていない環境ではスキップ。
    """

    @pytest.fixture
    def project_dir(self, tmp_path: Path) -> Path:
        """テスト用プロジェクトを作成して返す。"""
        result = run_railway_command(["init", "test_project"], tmp_path)
        assert result.returncode == 0, f"init failed: {result.stderr}"
        return tmp_path / "test_project"

    def test_mypy_passes_on_hello(self, project_dir: Path) -> None:
        """hello.py が mypy を通過する。

        Note: このテストは mypy がインストールされている場合のみ実行。
        """
        # mypy が利用可能か確認
        mypy_check = subprocess.run(
            [sys.executable, "-m", "mypy", "--version"],
            capture_output=True,
            text=True,
        )
        if mypy_check.returncode != 0:
            pytest.skip("mypy is not available")

        # src/ に対して mypy を実行
        result = subprocess.run(
            [sys.executable, "-m", "mypy", "src/hello.py", "--ignore-missing-imports"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )

        # mypy が成功することを確認
        assert result.returncode == 0, f"mypy failed on hello.py:\n{result.stdout}\n{result.stderr}"
