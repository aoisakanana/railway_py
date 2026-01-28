# Issue #56: Runner 依存チェック

## 概要

`dag_runner` に実行時の依存チェックを追加する（オプション）。
sync 時に検証済みのため、実行時チェックはデバッグ用途。

## 背景

フィールドベース依存関係では、`railway sync transition` 時に全経路の依存が検証される。
実行時チェックは以下の用途で有用:

1. **デバッグ**: 開発中のエラー検出
2. **動的ワークフロー**: 実行時に遷移が変わる場合の検証
3. **防御的プログラミング**: sync を通さずに実行された場合の保護

## 設計

### オプションによる制御

```python
# デフォルト: 実行時チェックなし（sync 時に検証済み）
result = dag_runner(
    start=start,
    transitions=TRANSITIONS,
)

# デバッグモード: 実行時チェックあり
result = dag_runner(
    start=start,
    transitions=TRANSITIONS,
    check_dependencies=True,
)
```

### チェックのタイミング

```
ノード実行前:
1. ノードの _field_dependency を取得
2. 現在の context のフィールドを取得
3. requires がすべて存在するか確認
4. 不足があれば DependencyRuntimeError
```

### エラー時の動作

```python
class DependencyRuntimeError(Exception):
    """依存関係の実行時エラー。"""


# エラーメッセージ例
raise DependencyRuntimeError(
    f"ノード 'escalate' の依存が満たされていません。\n"
    f"  requires: {{'hostname'}}\n"
    f"  利用可能: {{'incident_id', 'severity'}}\n"
    f"  不足: {{'hostname'}}"
)
```

## タスク

### 1. Red Phase: 失敗するテストを作成

`tests/unit/core/dag/test_runner_dependency_check.py`:

```python
"""Runner の依存チェックテスト。"""

import pytest
from railway import Contract, node
from railway.core.dag import dag_runner, Outcome
from railway.core.dag.exceptions import DependencyRuntimeError


class WorkflowContext(Contract):
    incident_id: str
    hostname: str | None = None


class TestRunnerDependencyCheck:
    """依存チェックテスト。"""

    def test_no_check_by_default(self) -> None:
        """デフォルトでは依存チェックしない。"""
        @node
        def start(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        # requires を宣言しているが、初期コンテキストに hostname がない
        @node(requires=["hostname"])
        def needs_hostname(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        @node(name="exit.success.done")
        def done(ctx: WorkflowContext):
            from railway import ExitContract
            class Result(ExitContract):
                exit_state: str = "success.done"
            return Result()

        # デフォルトではエラーにならない（sync 時に検証済みと仮定）
        result = dag_runner(
            start=lambda: (WorkflowContext(incident_id="INC-001"), Outcome.success("start")),
            transitions={
                "start::success::done": needs_hostname,
                "needs_hostname::success::done": done,
            },
        )
        # 実際の実行ではエラーになる可能性があるが、依存チェックはしない
        # （hostname が None でアクセスすると AttributeError になる）

    def test_check_dependencies_catches_missing_requires(self) -> None:
        """check_dependencies=True で不足を検出する。"""
        @node
        def start(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        @node(requires=["hostname"])
        def needs_hostname(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        with pytest.raises(DependencyRuntimeError) as exc_info:
            dag_runner(
                start=lambda: (WorkflowContext(incident_id="INC-001"), Outcome.success("start")),
                transitions={
                    "start::success::done": needs_hostname,
                },
                check_dependencies=True,
            )

        assert "hostname" in str(exc_info.value)
        assert "needs_hostname" in str(exc_info.value)

    def test_check_dependencies_passes_when_satisfied(self) -> None:
        """依存が満たされている場合は通過する。"""
        @node(provides=["hostname"])
        def start(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx.model_copy(update={"hostname": "server1"}), Outcome.success("done")

        @node(requires=["hostname"])
        def needs_hostname(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        @node(name="exit.success.done")
        def done(ctx: WorkflowContext):
            from railway import ExitContract
            class Result(ExitContract):
                exit_state: str = "success.done"
            return Result()

        result = dag_runner(
            start=lambda: (WorkflowContext(incident_id="INC-001"), Outcome.success("start")),
            transitions={
                "start::success::done": needs_hostname,
                "needs_hostname::success::done": done,
            },
            check_dependencies=True,
        )
        assert result.is_success


class TestRunnerOptionalFieldCheck:
    """optional フィールドのチェックテスト。"""

    def test_optional_does_not_raise_error(self) -> None:
        """optional フィールドがなくてもエラーにならない。"""
        @node
        def start(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        @node(optional=["hostname"])
        def uses_hostname_optionally(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            # hostname がなくても動作する
            if ctx.hostname:
                pass
            return ctx, Outcome.success("done")

        @node(name="exit.success.done")
        def done(ctx: WorkflowContext):
            from railway import ExitContract
            class Result(ExitContract):
                exit_state: str = "success.done"
            return Result()

        result = dag_runner(
            start=lambda: (WorkflowContext(incident_id="INC-001"), Outcome.success("start")),
            transitions={
                "start::success::done": uses_hostname_optionally,
                "uses_hostname_optionally::success::done": done,
            },
            check_dependencies=True,
        )
        assert result.is_success


class TestRunnerDependencyCheckWithProvides:
    """provides を考慮したチェックテスト。"""

    def test_provides_accumulates(self) -> None:
        """provides は累積される。"""
        @node(provides=["field_a"])
        def step_a(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        @node(provides=["field_b"])
        def step_b(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        @node(requires=["field_a", "field_b"])
        def needs_both(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx, Outcome.success("done")

        @node(name="exit.success.done")
        def done(ctx: WorkflowContext):
            from railway import ExitContract
            class Result(ExitContract):
                exit_state: str = "success.done"
            return Result()

        result = dag_runner(
            start=lambda: (WorkflowContext(incident_id="INC-001"), Outcome.success("start")),
            transitions={
                "step_a::success::done": step_b,
                "step_b::success::done": needs_both,
                "needs_both::success::done": done,
            },
            check_dependencies=True,
        )
        assert result.is_success
```

### 2. Green Phase: Runner 更新

`railway/core/dag/runner.py` を更新:

```python
from railway.core.dag.exceptions import DependencyRuntimeError
from railway.core.dag.dependency_extraction import extract_field_dependency


def _check_node_dependencies(
    node_func: Callable,
    context: Any,
    available_fields: set[str],
    node_name: str,
) -> None:
    """ノードの依存をチェックする。

    Args:
        node_func: ノード関数
        context: 現在のコンテキスト
        available_fields: 利用可能なフィールド
        node_name: ノード名

    Raises:
        DependencyRuntimeError: 依存が満たされていない場合
    """
    dep = extract_field_dependency(node_func)
    if dep is None:
        return  # 依存宣言がない

    missing = dep.requires - available_fields
    if missing:
        raise DependencyRuntimeError(
            f"ノード '{node_name}' の依存が満たされていません。\n"
            f"  requires: {dep.requires}\n"
            f"  利用可能: {available_fields}\n"
            f"  不足: {missing}"
        )


def _get_available_fields(context: Any) -> set[str]:
    """コンテキストの利用可能フィールドを取得する。"""
    if hasattr(context, "model_fields"):
        # Pydantic model
        return {
            name for name, value in context.model_dump().items()
            if value is not None
        }
    elif hasattr(context, "__dict__"):
        return {
            name for name, value in context.__dict__.items()
            if value is not None
        }
    return set()


def dag_runner(
    start: Callable,
    transitions: dict,
    *,
    check_dependencies: bool = False,  # 追加
    on_step: Callable | None = None,
    max_iterations: int = 100,
) -> ExitContract:
    """DAG ワークフローを実行する。

    Args:
        start: 開始関数
        transitions: 遷移マッピング
        check_dependencies: 実行時依存チェック（デフォルト: False）
        on_step: ステップコールバック
        max_iterations: 最大イテレーション数
    """
    context, outcome = start()
    available_fields = _get_available_fields(context)

    for iteration in range(max_iterations):
        transition_key = _build_transition_key(current_node, outcome)
        next_step = transitions.get(transition_key)

        if next_step is None:
            break

        node_name = getattr(next_step, "_node_name", next_step.__name__)

        # 依存チェック（オプション）
        if check_dependencies:
            _check_node_dependencies(next_step, context, available_fields, node_name)

        # ノード実行
        if _is_exit_node(node_name):
            result = next_step(context)
            return _wrap_exit_result(result, node_name)

        context, outcome = next_step(context)

        # provides を追加
        if check_dependencies:
            dep = extract_field_dependency(next_step)
            if dep:
                available_fields |= dep.provides
                available_fields |= _get_available_fields(context)

        # ... 残りの処理 ...
```

`railway/core/dag/exceptions.py` を追加:

```python
"""DAG ワークフローの例外。"""


class DependencyRuntimeError(Exception):
    """依存関係の実行時エラー。

    check_dependencies=True で実行した際に、
    ノードの requires が満たされていない場合に発生する。
    """
    pass
```

### 3. provides の実行時検証オプション

ノードが `provides=["field"]` と宣言したのに、実際にフィールドを設定しない場合を検出:

```python
def _check_provides_satisfied(
    node_func: Callable,
    before_context: Any,
    after_context: Any,
    node_name: str,
    warn_on_violation: bool = True,
) -> None:
    """provides が実際に追加されたか検証する。

    Args:
        node_func: ノード関数
        before_context: 実行前のコンテキスト
        after_context: 実行後のコンテキスト
        node_name: ノード名
        warn_on_violation: 違反時に警告を出すか

    Note:
        provides を宣言したのに None のままなら警告（エラーではない）。
        sync 時の静的検証を補完するデバッグ用途。
    """
    dep = extract_field_dependency(node_func)
    if dep is None:
        return

    for field in dep.provides:
        before_value = getattr(before_context, field, None)
        after_value = getattr(after_context, field, None)

        # provides 宣言したのに None のまま、かつ before も None なら警告
        if after_value is None and before_value is None:
            if warn_on_violation:
                logger.warning(
                    f"ノード '{node_name}' は provides=['{field}'] を宣言していますが、"
                    f"実際には設定されていません"
                )
```

**テストケース:**

```python
class TestProvidesValidation:
    """provides 検証テスト。"""

    def test_warns_when_provides_not_set(self, caplog) -> None:
        """provides 宣言したのに設定しない場合は警告。"""
        @node(provides=["hostname"])
        def bad_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            # hostname を設定しない!
            return ctx, Outcome.success("done")

        @node(name="exit.success.done")
        def done(ctx: WorkflowContext):
            from railway import ExitContract
            class Result(ExitContract):
                exit_state: str = "success.done"
            return Result()

        dag_runner(
            start=lambda: (WorkflowContext(incident_id="INC-001"), Outcome.success("start")),
            transitions={
                "bad_node::success::done": done,
            },
            check_dependencies=True,
            warn_on_provides_violation=True,  # 新オプション
        )

        assert "provides=['hostname']" in caplog.text
        assert "設定されていません" in caplog.text

    def test_no_warning_when_provides_set(self, caplog) -> None:
        """provides を正しく設定した場合は警告なし。"""
        @node(provides=["hostname"])
        def good_node(ctx: WorkflowContext) -> tuple[WorkflowContext, Outcome]:
            return ctx.model_copy(update={"hostname": "server1"}), Outcome.success("done")

        # ... 実行 ...

        assert "設定されていません" not in caplog.text
```

### 4. Refactor Phase

- エラーメッセージの改善
- パフォーマンス最適化（依存チェックのオーバーヘッド削減）
- ログ出力の追加

## 完了条件

- [ ] `check_dependencies` オプションが動作する
- [ ] `warn_on_provides_violation` オプションが動作する
- [ ] デフォルトでは依存チェックしない
- [ ] `DependencyRuntimeError` が適切に発生する
- [ ] optional フィールドではエラーにならない
- [ ] provides が累積される
- [ ] provides 宣言したのに設定しない場合は警告
- [ ] すべてのテストが通過

## 依存関係

- Issue #52 (Node 依存宣言拡張) が完了していること
- Issue #53 (依存情報の自動抽出) が完了していること

## 関連ファイル

- `railway/core/dag/runner.py` (更新)
- `railway/core/dag/exceptions.py` (新規)
- `tests/unit/core/dag/test_runner_dependency_check.py` (新規)
