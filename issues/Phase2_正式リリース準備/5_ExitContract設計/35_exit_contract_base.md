# Issue #35: ExitContract 基底クラス追加

**優先度**: P0
**依存**: なし
**ブロック**: #36

---

## 概要

終端ノード用の `ExitContract` 基底クラスを追加する。

## TDD 実装フロー

### Phase 1: Red（失敗するテストを先に作成）

まず `tests/unit/core/test_exit_contract.py` にテストを作成し、**失敗することを確認**する。

### Phase 2: Green（最小実装）

テストが通る最小限の実装を `railway/core/exit_contract.py` に追加する。

### Phase 3: Refactor（リファクタリング）

コード品質向上、ドキュメント追加。

---

## 実装

### 新規ファイル

`railway/core/exit_contract.py`:

```python
"""終端ノード用 Contract 基底クラス。"""
from typing import Any
from pydantic import ConfigDict, model_validator
from railway import Contract


class ExitContract(Contract):
    """終端ノードが返す Contract の基底クラス。

    Attributes:
        exit_state: 終了状態 (例: "success.done", "failure.timeout")
        exit_code: シェル連携用数値コード (0=成功, 非0=失敗)
            - 省略時は exit_state から自動導出:
              - "success.*" → 0
              - それ以外 → 1
        execution_path: 実行されたノードの履歴（dag_runner が設定）
        iterations: 実行回数（dag_runner が設定）

    Note:
        execution_path と iterations は dag_runner が自動設定する。
        ユーザーは通常これらを設定する必要はない。
    """
    model_config = ConfigDict(frozen=True)

    exit_state: str
    exit_code: int | None = None  # None = 自動導出
    execution_path: tuple[str, ...] = ()
    iterations: int = 0

    @model_validator(mode="after")
    def _derive_exit_code(self) -> "ExitContract":
        """exit_code が None なら exit_state から自動導出する。"""
        if self.exit_code is None:
            derived = 0 if self.exit_state.startswith("success") else 1
            # frozen なので object.__setattr__ を使用
            object.__setattr__(self, "exit_code", derived)
        return self

    @property
    def is_success(self) -> bool:
        return self.exit_code == 0

    @property
    def is_failure(self) -> bool:
        return self.exit_code != 0


class DefaultExitContract(ExitContract):
    """デフォルト終端 Contract（後方互換・ハンドラなし用）。"""
    context: Any = None
```

### テスト（Phase 1: Red）

```python
# tests/unit/core/test_exit_contract.py
import pytest
from pydantic import ValidationError

from railway import Contract
from railway.core.exit_contract import ExitContract, DefaultExitContract


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


class TestDefaultExitContract:
    """DefaultExitContract のテスト。"""

    def test_holds_context(self) -> None:
        """context を保持できる。"""
        result = DefaultExitContract(
            exit_state="success.done",
            context={"key": "value"},
        )
        assert result.context == {"key": "value"}

    def test_context_defaults_to_none(self) -> None:
        """context のデフォルトは None。"""
        result = DefaultExitContract(exit_state="success.done")
        assert result.context is None
```

### エクスポート

`railway/__init__.py` に追加:

```python
from railway.core.exit_contract import ExitContract, DefaultExitContract

__all__ = [
    ...
    "ExitContract",
    "DefaultExitContract",
]
```

## ユーザーガイド（ドキュメント用）

```python
# 成功時の ExitContract サブクラス例
class DoneResult(ExitContract):
    """処理完了時の結果。"""
    data: dict[str, Any]
    exit_state: str = "success.done"  # exit_code は自動で 0 になる

# 失敗時の ExitContract サブクラス例
class TimeoutResult(ExitContract):
    """タイムアウト時の結果。"""
    reason: str
    exit_state: str = "failure.timeout"  # exit_code は自動で 1 になる

# カスタム exit_code が必要な場合
class WarningResult(ExitContract):
    """警告で終了（exit_code=2）。"""
    message: str
    exit_state: str = "warning.low_disk"
    exit_code: int = 2  # 明示的に設定
```

**設計指針**:

| フィールド | 説明 | 規約 |
|------------|------|------|
| `exit_state` | 終端状態の識別子 | `exit.` プレフィックスを除いた形式（例: `success.done`） |
| `exit_code` | シェル連携用の終了コード | **自動導出**: `success.*`=0、それ以外=1。明示設定も可。 |

**exit_code 自動導出ルール**:

| exit_state パターン | exit_code |
|---------------------|-----------|
| `success.*` | 0（成功） |
| `failure.*` | 1（失敗） |
| `warning.*` | 1（失敗扱い、カスタム可） |
| その他 | 1（失敗扱い） |

```python
# ✅ Good: exit_code を省略（自動導出）
class DoneResult(ExitContract):
    exit_state: str = "success.done"
    # exit_code は自動で 0

# ✅ Good: exit_code を省略（自動導出）
class TimeoutResult(ExitContract):
    exit_state: str = "failure.timeout"
    # exit_code は自動で 1

# ✅ Good: カスタム exit_code を明示
class WarningResult(ExitContract):
    exit_state: str = "warning.low_disk"
    exit_code: int = 2  # 明示的に設定
```

**サブクラス設計のベストプラクティス**:
- **推奨**: `exit_code` は省略し、自動導出に任せる
- カスタム exit_code が必要な場合のみ明示的に設定
- ビジネスロジック固有のフィールドを追加

## 受け入れ条件

### 機能
- [ ] `ExitContract` クラスが `Contract` を継承
- [ ] `frozen=True` でイミュータブル
- [ ] `exit_code` が `exit_state` から自動導出される（`success.*` → 0、それ以外 → 1）
- [ ] 明示的な `exit_code` 指定で自動導出を上書き可能
- [ ] `is_success` / `is_failure` プロパティが動作
- [ ] `DefaultExitContract` が `context` を保持可能

### エクスポート
- [ ] `railway` パッケージから `ExitContract`, `DefaultExitContract` をエクスポート

### テスト
- [ ] TDD フェーズに従って実装（Red → Green → Refactor）
- [ ] 全テストがパス

---

*基盤となる変更*
