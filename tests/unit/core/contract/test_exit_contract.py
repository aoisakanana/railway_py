"""ExitContract テスト（Issue #35）。

TDD Red Phase: 失敗するテストを先に作成。
"""
import pytest
from pydantic import ValidationError

from railway import Contract
from railway.core.exit_contract import ExitContract


class TestExitContract:
    """ExitContract 基底クラスのテスト。"""

    def test_inherits_from_contract(self) -> None:
        """Contract を継承している。"""
        assert issubclass(ExitContract, Contract)

    def test_is_frozen(self) -> None:
        """frozen=True でイミュータブル。"""
        result = ExitContract(exit_state="success.done")
        with pytest.raises(ValidationError):
            result.exit_state = "changed"  # type: ignore[misc]

    def test_is_success_when_exit_code_zero(self) -> None:
        """exit_code=0 のとき is_success=True。"""
        result = ExitContract(exit_state="success.done", exit_code=0)
        assert result.is_success is True
        assert result.is_failure is False

    def test_is_failure_when_exit_code_nonzero(self) -> None:
        """exit_code!=0 のとき is_failure=True。"""
        result = ExitContract(exit_state="failure.error", exit_code=1)
        assert result.is_success is False
        assert result.is_failure is True

    def test_default_values(self) -> None:
        """デフォルト値が正しい。"""
        result = ExitContract(exit_state="success.done")
        assert result.exit_code == 0  # 自動導出
        assert result.execution_path == ()
        assert result.iterations == 0


class TestExitCodeAutoDerivation:
    """exit_code 自動導出のテスト。"""

    def test_success_state_derives_exit_code_zero(self) -> None:
        """success.* は exit_code=0 に自動導出。"""
        result = ExitContract(exit_state="success.done")
        assert result.exit_code == 0
        assert result.is_success is True

    def test_failure_state_derives_exit_code_one(self) -> None:
        """failure.* は exit_code=1 に自動導出。"""
        result = ExitContract(exit_state="failure.timeout")
        assert result.exit_code == 1
        assert result.is_failure is True

    def test_warning_state_derives_exit_code_one(self) -> None:
        """warning.* は exit_code=1 に自動導出（成功系以外）。"""
        result = ExitContract(exit_state="warning.low_disk")
        assert result.exit_code == 1

    def test_explicit_exit_code_overrides_derivation(self) -> None:
        """明示的な exit_code は自動導出を上書きする。"""
        # カスタム exit_code
        result = ExitContract(exit_state="warning.low_disk", exit_code=2)
        assert result.exit_code == 2


class TestExitContractSubclass:
    """ユーザー定義 ExitContract サブクラスのテスト。"""

    def test_custom_subclass_with_default_exit_state(self) -> None:
        """exit_state をデフォルト値で定義できる。"""

        class DoneResult(ExitContract):
            data: str
            exit_state: str = "success.done"

        result = DoneResult(data="test")
        assert result.data == "test"
        assert result.exit_state == "success.done"
        assert result.is_success is True

    def test_failure_subclass_with_nonzero_exit_code(self) -> None:
        """失敗用サブクラスは exit_code をデフォルト非ゼロにできる。"""

        class TimeoutResult(ExitContract):
            reason: str
            exit_state: str = "failure.timeout"
            exit_code: int = 1

        result = TimeoutResult(reason="API timeout")
        assert result.is_failure is True
        assert result.exit_code == 1


class TestExitContractExport:
    """エクスポートのテスト。"""

    def test_can_import_from_railway(self) -> None:
        """railway パッケージからインポートできる。"""
        from railway import ExitContract

        assert ExitContract is not None
