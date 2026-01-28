"""終端ノード用 Contract 基底クラス。

ExitContract は終端ノードが返す Contract の基底クラスです。
ワークフロー終了時の状態と終了コードを型安全に表現します。

設計:
- Contract を継承（イミュータブル）
- exit_code は exit_state から自動導出可能
- execution_path と iterations は dag_runner が設定

使用例:
    class DoneResult(ExitContract):
        data: str
        exit_state: str = "success.done"

    @node(name="exit.success.done")
    def done(ctx: WorkflowContext) -> DoneResult:
        return DoneResult(data="completed")
"""
from typing import Any

from pydantic import ConfigDict, model_validator

from railway.core.contract import Contract


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
        """終了コードが 0 かどうか。"""
        return self.exit_code == 0

    @property
    def is_failure(self) -> bool:
        """終了コードが 0 以外かどうか。"""
        return self.exit_code != 0


class DefaultExitContract(ExitContract):
    """デフォルト終端 Contract（後方互換・ハンドラなし用）。

    終端ノードが ExitContract 以外を返した場合に、
    dag_runner がこのクラスでラップして返す。

    Attributes:
        context: 終端ノードが返した元の値
    """

    context: Any = None
