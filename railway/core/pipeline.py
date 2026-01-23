"""Pipeline execution for Railway Framework."""

import inspect
from collections.abc import Callable
from typing import Any

from loguru import logger

from railway.core.type_check import (
    check_type_compatibility,
    format_type_error,
    get_function_input_type,
)


def pipeline(
    initial: Any,
    *steps: Callable[[Any], Any],
    type_check: bool = True,
    strict: bool = False,
) -> Any:
    """
    線形パイプライン実行（レガシー/動的ユースケース向け）

    Note:
        通常の開発では typed_pipeline を推奨します。
        このpipelineは以下のユースケースで使用してください:
        - 動的にステップを構成する場合
        - 既存の値からパイプラインを開始する場合

    typed_pipeline との違い:
        | 特徴 | pipeline | typed_pipeline |
        |------|----------|----------------|
        | 最初の引数 | 評価済みの値 | 関数 |
        | 型安全性 | 限定的 | Contract ベース |
        | IDE補完 | 限定的 | フル対応 |
        | 依存解決 | なし | 自動 |
        | 推奨用途 | 動的構成 | 通常開発 |

    Args:
        initial: パイプラインの開始値（関数ではなく値）
        *steps: 順次適用する処理関数
        type_check: ランタイム型チェック有効化（デフォルト: True）
        strict: 厳密な型チェック（デフォルト: False）

    Returns:
        最後のステップの出力

    Raises:
        Exception: ステップの実行失敗時
        TypeError: async関数が渡された場合、または厳密モードで型不一致

    Example:
        # 動的パイプライン構成
        def build_pipeline(config: dict):
            steps = [transform_data]
            if config.get("filter"):
                steps.append(filter_data)
            return lambda data: pipeline(data, *steps)

        # 既存データからのパイプライン開始
        existing_data = load_from_cache()
        result = pipeline(existing_data, process, save)

    See Also:
        typed_pipeline: 通常の開発で推奨される型安全なパイプライン
    """
    # Check for async functions
    for step in steps:
        # Check the original function if it's a decorated node
        is_async = getattr(step, "_is_async", False) or inspect.iscoroutinefunction(
            getattr(step, "_original_func", step)
        )
        if is_async:
            step_name = getattr(step, "_node_name", step.__name__)
            raise TypeError(
                f"Async function '{step_name}' cannot be used in pipeline(). "
                "Use async_pipeline() for async nodes."
            )

    logger.debug(f"パイプライン開始: {len(steps)} ステップ")

    # Return initial value if no steps
    if not steps:
        return initial

    current_value = initial
    current_step = 0

    try:
        for i, step in enumerate(steps, 1):
            current_step = i
            step_name = getattr(step, "_node_name", step.__name__)

            # Type check before execution (if strict mode)
            if strict:
                expected_type = get_function_input_type(step)
                if expected_type is not None:
                    if not check_type_compatibility(current_value, expected_type):
                        raise TypeError(
                            format_type_error(
                                step_num=i,
                                step_name=step_name,
                                expected_type=expected_type,
                                actual_type=type(current_value),
                                actual_value=current_value,
                            )
                        )

            logger.debug(f"パイプラインステップ {i}/{len(steps)}: {step_name}")

            try:
                result = step(current_value)
                current_value = result
                logger.debug(f"パイプラインステップ {i}/{len(steps)}: 成功")

            except Exception as e:
                logger.error(
                    f"パイプラインステップ {i}/{len(steps)} ({step_name}): "
                    f"失敗 {type(e).__name__}: {e}"
                )
                logger.info(f"パイプライン: 残り {len(steps) - i} ステップをスキップ")
                raise

        logger.debug("パイプライン正常完了")
        return current_value

    except Exception:
        logger.error(f"パイプライン失敗: ステップ {current_step}/{len(steps)}")
        raise


async def async_pipeline(
    initial: Any,
    *steps: Callable[[Any], Any],
    strict: bool = False,
) -> Any:
    """
    Execute an asynchronous pipeline of processing steps.

    Supports both sync and async nodes. Async nodes are awaited automatically.

    Args:
        initial: Initial value to pass to first step
        *steps: Processing functions to apply sequentially (sync or async)
        strict: Enable strict type checking between steps (default: False)

    Returns:
        Final result from the last step

    Raises:
        Exception: If any step fails
        TypeError: If type mismatch in strict mode

    Example:
        result = await async_pipeline(
            "https://api.example.com",
            async_fetch,   # Async step 1
            process_data,  # Sync step 2
            async_save,    # Async step 3
        )
    """
    logger.debug(f"非同期パイプライン開始: {len(steps)} ステップ")

    # Return initial value if no steps
    if not steps:
        return initial

    current_value = initial
    current_step = 0

    try:
        for i, step in enumerate(steps, 1):
            current_step = i
            step_name = getattr(step, "_node_name", step.__name__)
            is_async = getattr(step, "_is_async", False) or inspect.iscoroutinefunction(
                getattr(step, "_original_func", step)
            )

            # Type check before execution (if strict mode)
            if strict:
                expected_type = get_function_input_type(step)
                if expected_type is not None:
                    if not check_type_compatibility(current_value, expected_type):
                        raise TypeError(
                            format_type_error(
                                step_num=i,
                                step_name=step_name,
                                expected_type=expected_type,
                                actual_type=type(current_value),
                                actual_value=current_value,
                            )
                        )

            logger.debug(f"非同期パイプラインステップ {i}/{len(steps)}: {step_name}")

            try:
                if is_async:
                    result = await step(current_value)
                else:
                    result = step(current_value)
                current_value = result
                logger.debug(f"非同期パイプラインステップ {i}/{len(steps)}: 成功")

            except Exception as e:
                logger.error(
                    f"非同期パイプラインステップ {i}/{len(steps)} ({step_name}): "
                    f"失敗 {type(e).__name__}: {e}"
                )
                logger.info(f"非同期パイプライン: 残り {len(steps) - i} ステップをスキップ")
                raise

        logger.debug("非同期パイプライン正常完了")
        return current_value

    except Exception:
        logger.error(f"非同期パイプライン失敗: ステップ {current_step}/{len(steps)}")
        raise
