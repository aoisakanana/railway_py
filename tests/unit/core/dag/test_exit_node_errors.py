"""Issue #46: 終端ノード型エラーのテスト。

TDD Red Phase: 失敗するテストを先に作成。
"""
import pytest


class TestExitNodeTypeError:
    """終端ノード型エラーのテスト。"""

    def test_includes_node_name(self) -> None:
        from railway.core.dag.errors import ExitNodeTypeError

        error = ExitNodeTypeError(
            node_name="exit.success.done",
            actual_type="dict",
        )
        assert "exit.success.done" in str(error)

    def test_includes_actual_type(self) -> None:
        from railway.core.dag.errors import ExitNodeTypeError

        error = ExitNodeTypeError(
            node_name="exit.success.done",
            actual_type="dict",
        )
        assert "dict" in str(error)

    def test_includes_hint(self) -> None:
        from railway.core.dag.errors import ExitNodeTypeError

        error = ExitNodeTypeError(
            node_name="exit.success.done",
            actual_type="dict",
        )
        assert "railway sync transition" in str(error)

    def test_is_type_error(self) -> None:
        """TypeError のサブクラスである。"""
        from railway.core.dag.errors import ExitNodeTypeError

        error = ExitNodeTypeError(
            node_name="exit.success.done",
            actual_type="dict",
        )
        assert isinstance(error, TypeError)


class TestLegacyExitFormatError:
    """レガシー exit 形式エラーのテスト。"""

    def test_includes_legacy_format(self) -> None:
        from railway.core.dag.errors import LegacyExitFormatError

        error = LegacyExitFormatError(legacy_format="exit::green::done")
        assert "exit::green::done" in str(error)

    def test_includes_hint(self) -> None:
        from railway.core.dag.errors import LegacyExitFormatError

        error = LegacyExitFormatError(legacy_format="exit::green::done")
        assert "railway update" in str(error)

    def test_is_value_error(self) -> None:
        """ValueError のサブクラスである。"""
        from railway.core.dag.errors import LegacyExitFormatError

        error = LegacyExitFormatError(legacy_format="exit::green::done")
        assert isinstance(error, ValueError)
