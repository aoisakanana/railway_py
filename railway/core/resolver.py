"""Dependency resolution for typed pipeline execution.

This module provides the DependencyResolver class for resolving
node inputs based on Contract types, enabling the Output Model pattern.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from loguru import logger
from pydantic import create_model

if TYPE_CHECKING:
    from railway.core.contract import Contract


class DependencyError(Exception):
    """Raised when a dependency cannot be resolved.

    This exception is raised when:
    - A required input type is not available in the resolver
    - A Tagged input references a node that hasn't been executed
    """

    pass


class DependencyResolver:
    """Resolves dependencies between nodes based on Contract types.

    The resolver stores execution results by their type and source node name,
    enabling automatic dependency injection when executing typed nodes.

    Example:
        resolver = DependencyResolver()
        resolver.register_result(users_result, source_name="fetch_users")

        # Later, resolve inputs for a node that needs UsersFetchResult
        inputs = resolver.resolve_inputs(process_users)
    """

    def __init__(self) -> None:
        """Initialize the resolver with empty result stores."""
        self._results: dict[type[Contract], Contract] = {}
        self._named_results: dict[str, Contract] = {}

    def register_result(
        self, result: Contract, source_name: str | None = None
    ) -> None:
        """Register a node's result by its type and optionally by source name.

        Args:
            result: The Contract instance to register.
            source_name: Optional name of the source node (for Tagged resolution).
        """
        result_type = type(result)
        self._results[result_type] = result
        if source_name:
            self._named_results[source_name] = result

    def get_result(self, result_type: type[Contract]) -> Contract:
        """Get a result by its Contract type.

        Args:
            result_type: The Contract type to retrieve.

        Returns:
            The registered Contract instance.

        Raises:
            DependencyError: If no result of the given type is available.
        """
        if result_type not in self._results:
            raise DependencyError(
                f"No result of type {result_type.__name__} available"
            )
        return self._results[result_type]

    def get_named_result(self, source_name: str) -> Contract:
        """Get a result by source node name.

        Args:
            source_name: The name of the source node.

        Returns:
            The registered Contract instance.

        Raises:
            DependencyError: If no result from the given source is available.
        """
        if source_name not in self._named_results:
            raise DependencyError(f"No result from node '{source_name}'")
        return self._named_results[source_name]

    def resolve_inputs(self, node_func: Callable) -> dict[str, Contract]:
        """Resolve inputs for a node from registered results.

        Uses the node's _node_inputs metadata to determine which Contract
        types are needed, then looks them up in the registered results.

        Supports both type-based resolution and Tagged resolution for
        disambiguating multiple outputs of the same type.

        Args:
            node_func: The decorated node function.

        Returns:
            Dictionary mapping parameter names to resolved Contract instances.

        Raises:
            DependencyError: If a required input cannot be resolved.
        """
        from railway.core.contract import Tagged

        inputs_spec = getattr(node_func, "_node_inputs", {})
        resolved: dict[str, Contract] = {}

        for param_name, spec in inputs_spec.items():
            if isinstance(spec, Tagged):
                # Tagged: resolve by source node name
                if spec.source not in self._named_results:
                    raise DependencyError(
                        f"No result from node '{spec.source}'"
                    )
                resolved[param_name] = self._named_results[spec.source]
            else:
                # Type-based: resolve by Contract type
                if spec in self._results:
                    resolved[param_name] = self._results[spec]
                else:
                    node_name = getattr(node_func, "_node_name", node_func.__name__)
                    raise DependencyError(
                        f"Cannot resolve input '{param_name}' of type "
                        f"{spec.__name__} for node '{node_name}'"
                    )

        return resolved


def typed_pipeline(
    *nodes: Callable,
    params: Contract | dict | None = None,
    on_error: Callable[[Exception, str], Any] | None = None,
    on_step: Callable[[str, Any], None] | None = None,
) -> Contract:
    """型安全なパイプライン実行（推奨）

    Contract 型による依存性注入を使用した型安全なパイプラインです。
    各ノードは入出力を宣言し、パイプラインが自動的に依存関係を解決します。

    通常の開発ではこちらを推奨:
        - IDE補完がフルに動作
        - Contract による型保証
        - 依存関係の自動解決
        - on_error による高度なエラーハンドリング

    pipeline との違い:
        | 特徴 | typed_pipeline | pipeline |
        |------|----------------|----------|
        | 最初の引数 | 関数（@node） | 評価済みの値 |
        | 型安全性 | Contract ベース | 限定的 |
        | IDE補完 | フル対応 | 限定的 |
        | 依存解決 | 自動 | なし |
        | エラーハンドリング | on_error | 例外伝播のみ |

    Args:
        *nodes: 順次実行するノード関数（@node デコレータ付き）
        params: 初期パラメータ（Params Contract または dict）
        on_error: エラーハンドラ (exception, step_name) -> fallback_value or raise
            - 値を返すとその値で次のステップを継続
            - raise すると例外伝播（スタックトレース保持）
        on_step: ステップ完了コールバック (step_name, output) -> None
            - 各ステップ完了後に呼ばれる
            - デバッグ、監査ログ、メトリクス収集に使用

    Returns:
        最後のノードの出力（Contract）

    Raises:
        ValueError: ノードが指定されていない場合
        DependencyError: ノードの依存関係を解決できない場合

    Example:
        # 基本的な使用法
        result = typed_pipeline(
            fetch_users,      # UsersFetchResult を出力
            process_users,    # UsersFetchResult を入力 → ProcessResult を出力
            generate_report,  # ProcessResult を入力 → ReportResult を出力
        )

        # エラーハンドリング付き
        def handle_error(error: Exception, step: str) -> Any:
            match error:
                case ConnectionError():
                    return load_from_cache()  # フォールバック
                case _:
                    raise  # 再送出

        result = typed_pipeline(fetch, process, on_error=handle_error)

        # 中間結果の取得（デバッグ/監査）
        steps = []
        def capture_step(name: str, output: Any) -> None:
            steps.append({"step": name, "output": output})

        result = typed_pipeline(fetch, process, on_step=capture_step)

    See Also:
        pipeline: 動的構成や既存値からの開始に使用
        on_error: 3層エラーハンドリングのレベル3
    """
    from railway.core.contract import Params

    if not nodes:
        raise ValueError("Pipeline requires at least one node")

    resolver = DependencyResolver()

    # Register initial params
    if params is not None:
        if isinstance(params, dict):
            # Convert dict to dynamic Params Contract
            field_definitions = {k: (type(v), v) for k, v in params.items()}
            DynamicParams = create_model(  # noqa: N806
                "DynamicParams", __base__=Params, **field_definitions
            )
            params = DynamicParams(**params)
        resolver.register_result(params, source_name="_params")

    logger.debug(f"型付きパイプライン開始: {len(nodes)} ノード")

    last_result: Contract | None = None

    for node_func in nodes:
        node_name = getattr(node_func, "_node_name", node_func.__name__)

        try:
            # Resolve inputs from previous results
            inputs = resolver.resolve_inputs(node_func)

            # Execute the node
            result = node_func(**inputs)

            # Register result for subsequent nodes
            if result is not None:
                resolver.register_result(result, source_name=node_name)
                last_result = result

            # Call on_step callback after successful execution
            if on_step is not None:
                on_step(node_name, result)

        except DependencyError as e:
            logger.error(f"依存関係エラー ノード '{node_name}': {e}")
            raise
        except Exception as e:
            if on_error is None:
                logger.error(f"パイプライン失敗 ノード '{node_name}': {e}")
                raise

            # Call error handler
            try:
                result = on_error(e, node_name)
                # Handler returned a value - use it as fallback
                if result is not None:
                    resolver.register_result(result, source_name=node_name)
                    last_result = result

                # Call on_step callback after fallback
                if on_step is not None:
                    on_step(node_name, result)
            except BaseException:
                # Handler re-raised - propagate with original traceback
                raise e from None

    logger.debug("型付きパイプライン正常完了")
    return last_result  # type: ignore[return-value]


async def typed_async_pipeline(
    *nodes: Callable,
    params: Contract | dict | None = None,
) -> Contract:
    """Execute an async pipeline of typed nodes with automatic dependency resolution.

    Async version of typed_pipeline. Supports both sync and async nodes.

    Args:
        *nodes: Node functions to execute in order (sync or async).
        params: Initial parameters (Params Contract or dict).

    Returns:
        The output of the last node.

    Raises:
        ValueError: If no nodes are provided.
        DependencyError: If a node's dependencies cannot be resolved.

    Example:
        result = await typed_async_pipeline(
            async_fetch_users,
            process_users,
            async_generate_report,
            params=FetchParams(user_id=1),
        )
    """
    from railway.core.contract import Params

    if not nodes:
        raise ValueError("Pipeline requires at least one node")

    resolver = DependencyResolver()

    # Register initial params
    if params is not None:
        if isinstance(params, dict):
            field_definitions = {k: (type(v), v) for k, v in params.items()}
            DynamicParams = create_model(  # noqa: N806
                "DynamicParams", __base__=Params, **field_definitions
            )
            params = DynamicParams(**params)
        resolver.register_result(params, source_name="_params")

    logger.debug(f"非同期型付きパイプライン開始: {len(nodes)} ノード")

    last_result: Contract | None = None

    for node_func in nodes:
        node_name = getattr(node_func, "_node_name", node_func.__name__)

        try:
            # Resolve inputs
            inputs = resolver.resolve_inputs(node_func)

            # Determine if async
            original = getattr(node_func, "_original_func", node_func)
            is_async = inspect.iscoroutinefunction(original)

            # Execute
            if is_async:
                result = await node_func(**inputs)
            else:
                result = node_func(**inputs)

            # Register result
            if result is not None:
                resolver.register_result(result, source_name=node_name)
                last_result = result

        except DependencyError as e:
            logger.error(f"依存関係エラー ノード '{node_name}': {e}")
            raise
        except Exception as e:
            logger.error(f"非同期パイプライン失敗 ノード '{node_name}': {e}")
            raise

    logger.debug("非同期型付きパイプライン正常完了")
    return last_result  # type: ignore[return-value]
