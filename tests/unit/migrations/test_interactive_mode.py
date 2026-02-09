"""Interactive mode tests."""
from pathlib import Path

from railway.migrations.changes import should_confirm_change


class TestShouldConfirmChange:
    """should_confirm_change 純粋関数のテスト."""

    def test_auto_never_confirms(self) -> None:
        assert should_confirm_change("pyproject.toml", "auto") is False
        assert should_confirm_change("TUTORIAL.md", "auto") is False
        assert should_confirm_change("src/nodes/start.py", "auto") is False

    def test_interactive_always_confirms(self) -> None:
        assert should_confirm_change("pyproject.toml", "interactive") is True
        assert should_confirm_change("tests/nodes/__init__.py", "interactive") is True
        assert should_confirm_change(".railway/project.yaml", "interactive") is True

    def test_lazy_confirms_pyproject(self) -> None:
        assert should_confirm_change("pyproject.toml", "lazy") is True

    def test_lazy_confirms_tutorial(self) -> None:
        assert should_confirm_change("TUTORIAL.md", "lazy") is True

    def test_lazy_confirms_user_py_files(self) -> None:
        assert should_confirm_change("src/nodes/start.py", "lazy") is True

    def test_lazy_auto_applies_init_py(self) -> None:
        assert should_confirm_change("tests/nodes/__init__.py", "lazy") is False

    def test_lazy_auto_applies_generated(self) -> None:
        assert should_confirm_change("_railway/generated/transitions.py", "lazy") is False

    def test_lazy_auto_applies_railway_meta(self) -> None:
        assert should_confirm_change(".railway/project.yaml", "lazy") is False

    def test_lazy_auto_applies_gitkeep(self) -> None:
        assert should_confirm_change("transition_graphs/.gitkeep", "lazy") is False


class TestApplyFileChangeInteractive:
    """apply_file_change のインタラクティブモードテスト."""

    def test_skipped_when_user_declines(self, tmp_path: Path) -> None:
        from railway.migrations.changes import FileChange
        from railway.migrations.executor import apply_file_change

        change = FileChange.create(
            path="pyproject.toml", content="test", description="test"
        )
        result = apply_file_change(
            tmp_path, change,
            on_confirm=lambda p, d: False,
            mode="interactive",
        )
        assert result is False
        assert not (tmp_path / "pyproject.toml").exists()

    def test_applied_when_user_accepts(self, tmp_path: Path) -> None:
        from railway.migrations.changes import FileChange
        from railway.migrations.executor import apply_file_change

        change = FileChange.create(
            path="test/__init__.py", content="", description="test"
        )
        result = apply_file_change(
            tmp_path, change,
            on_confirm=lambda p, d: True,
            mode="interactive",
        )
        assert result is True
        assert (tmp_path / "test" / "__init__.py").exists()

    def test_auto_mode_no_callback_needed(self, tmp_path: Path) -> None:
        from railway.migrations.changes import FileChange
        from railway.migrations.executor import apply_file_change

        change = FileChange.create(
            path="test.txt", content="hello", description="test"
        )
        result = apply_file_change(tmp_path, change, mode="auto")
        assert result is True

    def test_lazy_auto_applies_without_confirm(self, tmp_path: Path) -> None:
        from railway.migrations.changes import FileChange
        from railway.migrations.executor import apply_file_change

        confirm_called = False

        def on_confirm(p: str, d: str) -> bool:
            nonlocal confirm_called
            confirm_called = True
            return True

        change = FileChange.create(
            path="tests/nodes/__init__.py", content="", description="test"
        )
        apply_file_change(
            tmp_path, change, on_confirm=on_confirm, mode="lazy",
        )
        assert confirm_called is False
