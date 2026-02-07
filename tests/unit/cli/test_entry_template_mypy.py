"""エントリポイントテンプレートの mypy 対応テスト。

TDD: Red → Green → Refactor
このテストは生成されるテンプレートが _typer_app() を使用することを検証する。
"""
from pathlib import Path

import pytest


class TestEntryTemplateMypy:
    """エントリポイントテンプレートのテスト"""

    def test_dag_entry_template_uses_typer_app(self) -> None:
        """dag テンプレートは _typer_app() を使用する"""
        from railway.cli.new import _get_dag_entry_template

        content = _get_dag_entry_template("greeting")

        assert 'if __name__ == "__main__":' in content
        assert "_typer_app()" in content, "Should use _typer_app()"
        assert "type: ignore[union-attr]" in content, "Should have type: ignore comment"
        # main() の直接呼び出しがないことを確認
        self._assert_no_direct_call(content, "main")

    def test_dag_entry_pending_template_uses_typer_app(self) -> None:
        """pending テンプレートも _typer_app() を使用する"""
        from railway.cli.new import _get_dag_entry_template_pending_sync

        content = _get_dag_entry_template_pending_sync("greeting")

        assert 'if __name__ == "__main__":' in content
        assert "_typer_app()" in content, "Should use _typer_app()"
        assert "type: ignore[union-attr]" in content, "Should have type: ignore comment"
        self._assert_no_direct_call(content, "main")

    def test_linear_entry_template_uses_typer_app(self) -> None:
        """linear テンプレートも _typer_app() を使用する"""
        from railway.cli.new import _get_linear_entry_template

        content = _get_linear_entry_template("greeting")

        assert 'if __name__ == "__main__":' in content
        assert "_typer_app()" in content, "Should use _typer_app()"
        assert "type: ignore[union-attr]" in content, "Should have type: ignore comment"
        self._assert_no_direct_call(content, "main")

    def test_entry_template_uses_typer_app(self) -> None:
        """_get_entry_template も _typer_app() を使用する"""
        from railway.cli.new import _get_entry_template

        content = _get_entry_template("greeting")

        assert 'if __name__ == "__main__":' in content
        assert "_typer_app()" in content, "Should use _typer_app()"
        assert "type: ignore[union-attr]" in content, "Should have type: ignore comment"

    def test_entry_example_template_uses_typer_app(self) -> None:
        """_get_entry_example_template も _typer_app() を使用する"""
        from railway.cli.new import _get_entry_example_template

        content = _get_entry_example_template("greeting")

        assert 'if __name__ == "__main__":' in content
        assert "_typer_app()" in content, "Should use _typer_app()"
        assert "type: ignore[union-attr]" in content, "Should have type: ignore comment"

    def _assert_no_direct_call(self, content: str, func_name: str) -> None:
        """__main__ ブロック内で関数の直接呼び出しがないことを確認"""
        lines = content.split("\n")
        main_block_started = False
        for line in lines:
            if '__name__ == "__main__"' in line:
                main_block_started = True
            if main_block_started and f"{func_name}()" in line and "_typer_app" not in line:
                pytest.fail(f"Found direct {func_name}() call: {line}")


class TestInitHelloTemplate:
    """railway init で生成される hello.py のテスト"""

    def test_hello_template_uses_typer_app(self, tmp_path: Path) -> None:
        """hello.py は _typer_app() を使用する"""
        from railway.cli.init import _create_simple_hello_entry

        project_path = tmp_path / "test_project"
        (project_path / "src").mkdir(parents=True)

        _create_simple_hello_entry(project_path)

        hello_content = (project_path / "src" / "hello.py").read_text()
        assert "_typer_app()" in hello_content, "Should use _typer_app()"
        assert "type: ignore[union-attr]" in hello_content, "Should have type: ignore comment"

    def test_example_entry_uses_typer_app(self, tmp_path: Path) -> None:
        """_create_example_entry も _typer_app() を使用する"""
        from railway.cli.init import _create_example_entry

        project_path = tmp_path / "test_project"
        (project_path / "src").mkdir(parents=True)

        _create_example_entry(project_path)

        hello_content = (project_path / "src" / "hello.py").read_text()
        assert "_typer_app()" in hello_content, "Should use _typer_app()"
        assert "type: ignore[union-attr]" in hello_content, "Should have type: ignore comment"
