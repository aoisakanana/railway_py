"""Board pattern core types.

BoardBase: ノード間の共有状態を担う mutable オブジェクト。
WorkflowResult: dag_runner の返り値（frozen dataclass）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class BoardBase:
    """Board の基底クラス。

    任意の属性を動的に受け付ける mutable オブジェクト。
    テスト時には sync 不要で直接使用できる。

    Example:
        board = BoardBase(incident_id="INC-001")
        board.hostname = "server-01"
        board.escalated = True
    """

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            object.__setattr__(self, key, value)

    def __repr__(self) -> str:
        fields = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{type(self).__name__}({fields})"

    def _snapshot(self) -> dict[str, Any]:
        """現在の状態のスナップショットを取得（trace 用）。"""
        return dict(self.__dict__)

    def _field_names(self) -> frozenset[str]:
        """設定済みフィールド名を取得。"""
        return frozenset(self.__dict__.keys())


@dataclass(frozen=True)
class WorkflowResult:
    """dag_runner の実行結果。

    ExitContract を廃止し、dag_runner はこの型を返す。
    終端ノードが board を更新した後、dag_runner が構築する。

    Example:
        result = dag_runner(start=start, transitions=T, board=board)
        if result.is_success:
            print(f"Total: {result.board.total}")
    """

    exit_state: str
    exit_code: int
    board: BoardBase
    execution_path: tuple[str, ...] = ()
    iterations: int = 0
    trace: Any | None = None  # WorkflowTrace（Issue 25 で定義）。初期は Any

    @property
    def is_success(self) -> bool:
        """成功かどうか。"""
        return self.exit_code == 0

    @property
    def is_failure(self) -> bool:
        """失敗かどうか。"""
        return self.exit_code != 0
