"""Runner の依存チェックテスト。

@node デコレータから requires/optional/provides パラメータは削除された。
フィールド依存メタデータは _make_node_with_deps ヘルパーで直接設定する。
"""

from typing import Callable

import pytest

from railway import Contract, ExitContract, node
from railway.core.dag import dag_runner, Outcome
from railway.core.dag.errors import DependencyRuntimeError
from railway.core.dag.field_dependency import FieldDependency


class WorkflowContext(Contract):
    """テスト用 Contract。"""

    incident_id: str
    hostname: str | None = None
    field_a: str | None = None
    field_b: str | None = None
    processed: str | None = None


class SuccessResult(ExitContract):
    """テスト用終了結果。"""

    exit_state: str = "success.done"


def _make_node_with_deps(
    func, *, requires=None, optional=None, provides=None, name=None
):
    """Test helper: set field dependency metadata on a function."""
    func._is_railway_node = True
    func._node_name = name or func.__name__
    func._is_board_node = False
    func._is_async = False
    func._node_inputs = {}
    func._node_output = None
    func._requires = frozenset(requires or [])
    func._optional = frozenset(optional or [])
    func._provides = frozenset(provides or [])
    func._field_dependency = FieldDependency(
        requires=func._requires,
        optional=func._optional,
        provides=func._provides,
    )
    return func


class TestRunnerDependencyCheckDefault:
    """デフォルトの依存チェック動作テスト。"""

    def test_no_check_by_default(self) -> None:
        """デフォルトでは依存チェックしない。"""

        def start(
            _ctx: WorkflowContext | None = None,
        ) -> tuple[WorkflowContext, Outcome]:
            return WorkflowContext(incident_id="INC-001"), Outcome.success("init")

        _make_node_with_deps(start, name="start")

        # requires を宣言しているが、初期コンテキストに hostname がない
        def needs_hostname(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            # hostname が None でも実行される
            return ctx, Outcome.success("done")

        _make_node_with_deps(needs_hostname, requires=["hostname"])

        def done(ctx: WorkflowContext) -> SuccessResult:
            return SuccessResult()

        _make_node_with_deps(done, name="exit.success.done")

        # デフォルトではエラーにならない（sync 時に検証済みと仮定）
        result = dag_runner(
            start=start,
            transitions={
                "start::success::init": needs_hostname,
                "needs_hostname::success::done": done,
            },
        )
        # 依存チェックはされない
        assert result.is_success


class TestRunnerDependencyCheckEnabled:
    """依存チェック有効時のテスト。"""

    def test_check_dependencies_catches_missing_requires(self) -> None:
        """check_dependencies=True で不足を検出する。"""

        def start(
            _ctx: WorkflowContext | None = None,
        ) -> tuple[WorkflowContext, Outcome]:
            return WorkflowContext(incident_id="INC-001"), Outcome.success("init")

        _make_node_with_deps(start, name="start")

        def needs_hostname(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        _make_node_with_deps(needs_hostname, requires=["hostname"])

        with pytest.raises(DependencyRuntimeError) as exc_info:
            dag_runner(
                start=start,
                transitions={
                    "start::success::init": needs_hostname,
                },
                check_dependencies=True,
            )

        assert "hostname" in str(exc_info.value)
        assert "needs_hostname" in str(exc_info.value)

    def test_check_dependencies_passes_when_satisfied(self) -> None:
        """依存が満たされている場合は通過する。"""

        def start(
            _ctx: WorkflowContext | None = None,
        ) -> tuple[WorkflowContext, Outcome]:
            return WorkflowContext(
                incident_id="INC-001", hostname="server1"
            ), Outcome.success("init")

        _make_node_with_deps(start, name="start", provides=["hostname"])

        def needs_hostname(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        _make_node_with_deps(needs_hostname, requires=["hostname"])

        def done(ctx: WorkflowContext) -> SuccessResult:
            return SuccessResult()

        _make_node_with_deps(done, name="exit.success.done")

        result = dag_runner(
            start=start,
            transitions={
                "start::success::init": needs_hostname,
                "needs_hostname::success::done": done,
            },
            check_dependencies=True,
        )
        assert result.is_success

    def test_check_dependencies_with_initial_fields(self) -> None:
        """初期コンテキストのフィールドも利用可能として扱う。"""

        def start(
            _ctx: WorkflowContext | None = None,
        ) -> tuple[WorkflowContext, Outcome]:
            return WorkflowContext(incident_id="INC-001"), Outcome.success("init")

        _make_node_with_deps(start, name="start", requires=["incident_id"])

        def done(ctx: WorkflowContext) -> SuccessResult:
            return SuccessResult()

        _make_node_with_deps(done, name="exit.success.done")

        # incident_id は初期コンテキストに存在するので通過する
        result = dag_runner(
            start=start,
            transitions={
                "start::success::init": done,
            },
            check_dependencies=True,
        )
        assert result.is_success


class TestRunnerOptionalFieldCheck:
    """optional フィールドのチェックテスト。"""

    def test_optional_does_not_raise_error(self) -> None:
        """optional フィールドがなくてもエラーにならない。"""

        def start(
            _ctx: WorkflowContext | None = None,
        ) -> tuple[WorkflowContext, Outcome]:
            return WorkflowContext(incident_id="INC-001"), Outcome.success("init")

        _make_node_with_deps(start, name="start")

        def uses_hostname_optionally(
            ctx: WorkflowContext,
        ) -> tuple[WorkflowContext, Outcome]:
            # hostname がなくても動作する
            if ctx.hostname:
                pass
            return ctx, Outcome.success("done")

        _make_node_with_deps(uses_hostname_optionally, optional=["hostname"])

        def done(ctx: WorkflowContext) -> SuccessResult:
            return SuccessResult()

        _make_node_with_deps(done, name="exit.success.done")

        result = dag_runner(
            start=start,
            transitions={
                "start::success::init": uses_hostname_optionally,
                "uses_hostname_optionally::success::done": done,
            },
            check_dependencies=True,
        )
        assert result.is_success


class TestRunnerDependencyCheckWithProvides:
    """provides を考慮したチェックテスト。"""

    def test_provides_accumulates(self) -> None:
        """provides は累積される。"""

        def step_a(
            _ctx: WorkflowContext | None = None,
        ) -> tuple[WorkflowContext, Outcome]:
            return WorkflowContext(
                incident_id="INC-001", field_a="a"
            ), Outcome.success("done")

        _make_node_with_deps(step_a, name="step_a", provides=["field_a"])

        def step_b(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx.model_copy(update={"field_b": "b"}), Outcome.success("done")

        _make_node_with_deps(step_b, provides=["field_b"])

        def needs_both(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        _make_node_with_deps(needs_both, requires=["field_a", "field_b"])

        def done(ctx: WorkflowContext) -> SuccessResult:
            return SuccessResult()

        _make_node_with_deps(done, name="exit.success.done")

        result = dag_runner(
            start=step_a,
            transitions={
                "step_a::success::done": step_b,
                "step_b::success::done": needs_both,
                "needs_both::success::done": done,
            },
            check_dependencies=True,
        )
        assert result.is_success

    def test_provides_without_setting_still_passes(self) -> None:
        """provides を宣言しても設定しなくてもエラーにはならない（警告のみ）。"""

        def bad_node(
            _ctx: WorkflowContext | None = None,
        ) -> tuple[WorkflowContext, Outcome]:
            # hostname を設定しない!
            return WorkflowContext(incident_id="INC-001"), Outcome.success("done")

        _make_node_with_deps(bad_node, name="bad_node", provides=["hostname"])

        def done(ctx: WorkflowContext) -> SuccessResult:
            return SuccessResult()

        _make_node_with_deps(done, name="exit.success.done")

        # エラーにはならない（provides 未設定は警告レベル）
        result = dag_runner(
            start=bad_node,
            transitions={
                "bad_node::success::done": done,
            },
            check_dependencies=True,
        )
        assert result.is_success


class TestRunnerDependencyCheckExitNode:
    """終端ノードの依存チェックテスト。"""

    def test_exit_node_requires_checked(self) -> None:
        """終端ノードの requires もチェックされる。"""

        def start(
            _ctx: WorkflowContext | None = None,
        ) -> tuple[WorkflowContext, Outcome]:
            return WorkflowContext(incident_id="INC-001"), Outcome.success("init")

        _make_node_with_deps(start, name="start")

        def done(ctx: WorkflowContext) -> SuccessResult:
            return SuccessResult()

        _make_node_with_deps(done, name="exit.success.done", requires=["processed"])

        with pytest.raises(DependencyRuntimeError) as exc_info:
            dag_runner(
                start=start,
                transitions={
                    "start::success::init": done,
                },
                check_dependencies=True,
            )

        assert "processed" in str(exc_info.value)
