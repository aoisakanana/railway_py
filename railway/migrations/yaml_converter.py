"""YAML structure conversion utilities.

Converts legacy YAML structure (v0.11.x exits section) to
new nested exit node format (v0.12.0+ nodes.exit).

Design:
- All functions are pure (no side effects)
- Data types are immutable (frozen dataclass)
- Conversion is lossless - all information is preserved

Example conversion:
    Old format:
        exits:
          green_success: {code: 0, description: "正常終了"}
          red_timeout: {code: 1, description: "タイムアウト"}

    New format:
        nodes:
          exit:
            success:
              done: {description: "正常終了"}
            failure:
              timeout: {description: "タイムアウト"}
"""
from __future__ import annotations

import copy
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

# =============================================================================
# Exits Format Detection (Pure Functions)
# =============================================================================

ExitsFormat = Literal["legacy_flat", "nested", "unknown"]


@dataclass(frozen=True)
class ExitsFormatDetection:
    """exits 形式の判別結果（イミュータブル）。"""

    format: ExitsFormat


def _detect_exits_format(exits: dict[str, Any]) -> ExitsFormatDetection:
    """exits セクションの形式を検出する（純粋関数）。

    全エントリをスキャンし、一貫した形式を判定する。
    混合フォーマット（フラットとネストが混在）は "unknown" として返す。

    Args:
        exits: YAML の exits セクション

    Returns:
        ExitsFormatDetection: 検出された形式
    """
    if not exits:
        return ExitsFormatDetection(format="unknown")

    detected: ExitsFormat | None = None

    for _key, value in exits.items():
        if not isinstance(value, dict):
            return ExitsFormatDetection(format="unknown")

        # 各エントリの形式を判定
        entry_format: ExitsFormat
        if "code" in value:
            entry_format = "legacy_flat"
        elif any(isinstance(v, dict) for v in value.values()):
            entry_format = "nested"
        elif "description" in value:
            entry_format = "legacy_flat"
        else:
            return ExitsFormatDetection(format="unknown")

        # 一貫性チェック
        if detected is None:
            detected = entry_format
        elif detected != entry_format:
            return ExitsFormatDetection(format="unknown")

    return ExitsFormatDetection(format=detected or "unknown")


@dataclass(frozen=True)
class ExitMapping:
    """Mapping from old exit name to new exit path.

    Attributes:
        old_name: Original exit name (e.g., "green_success")
        new_path: New exit path (e.g., "exit.success.done")
        code: Exit code (0=success, 1+=failure)
        description: Exit description
    """

    old_name: str
    new_path: str
    code: int
    description: str


@dataclass(frozen=True)
class ConversionResult:
    """Result of YAML structure conversion (immutable).

    Use factory methods ok() and fail() to create instances.

    Attributes:
        success: Whether conversion succeeded
        data: Converted YAML data (None if failed)
        error: Error message (None if succeeded)
        warnings: Tuple of warning messages
    """

    success: bool
    data: dict[str, Any] | None
    error: str | None
    warnings: tuple[str, ...] = ()

    @classmethod
    def ok(
        cls,
        data: dict[str, Any],
        warnings: Sequence[str] = (),
    ) -> ConversionResult:
        """Create a successful conversion result.

        Args:
            data: Converted YAML data
            warnings: Optional warning messages

        Returns:
            ConversionResult with success=True
        """
        return cls(
            success=True,
            data=data,
            error=None,
            warnings=tuple(warnings),
        )

    @classmethod
    def fail(cls, error: str) -> ConversionResult:
        """Create a failed conversion result.

        Args:
            error: Error message

        Returns:
            ConversionResult with success=False
        """
        return cls(
            success=False,
            data=None,
            error=error,
            warnings=(),
        )


# =============================================================================
# Exit Path Inference (Pure Functions)
# =============================================================================


def _infer_category(old_name: str, exit_code: int) -> str:
    """Infer category from old exit name and code.

    Mapping rules:
    - "green_*" or exit_code 0 → "success"
    - "red_*" or exit_code 1 → "failure"
    - "yellow_*" or exit_code 2 → "warning"

    Args:
        old_name: Original exit name (e.g., "green_success")
        exit_code: Exit code value

    Returns:
        Category string ("success", "failure", or "warning")
    """
    lower_name = old_name.lower()

    # Color prefix takes priority
    if lower_name.startswith("green_"):
        return "success"
    if lower_name.startswith("red_"):
        return "failure"
    if lower_name.startswith("yellow_"):
        return "warning"

    # Fall back to exit code
    if exit_code == 0:
        return "success"
    if exit_code == 2:
        return "warning"
    return "failure"


def _extract_detail_name(old_name: str, category: str) -> str:
    """Extract detail name from old exit name.

    Removes color prefix and handles redundant category names.

    Examples:
        ("green_success", "success") → "done"  # "success" is redundant
        ("green_resolved", "success") → "resolved"
        ("red_timeout", "failure") → "timeout"
        ("red_ssh_error", "failure") → "ssh_error"

    Args:
        old_name: Original exit name
        category: Inferred category

    Returns:
        Detail name for the exit
    """
    lower_name = old_name.lower()

    # Remove color prefix
    for prefix in ("green_", "red_", "yellow_"):
        if lower_name.startswith(prefix):
            detail = old_name[len(prefix):]
            break
    else:
        detail = old_name

    # Handle redundant category names
    if detail.lower() == category:
        return "done" if category == "success" else detail

    return detail


def _infer_new_exit_path(old_name: str, exit_code: int) -> str:
    """Infer new exit path from old exit name.

    Converts legacy exit name to new hierarchical format.

    Examples:
        ("green_success", 0) → "exit.success.done"
        ("green_resolved", 0) → "exit.success.resolved"
        ("red_timeout", 1) → "exit.failure.timeout"
        ("unknown", 0) → "exit.success.unknown"

    Args:
        old_name: Original exit name
        exit_code: Exit code value

    Returns:
        New exit path (e.g., "exit.success.done")
    """
    category = _infer_category(old_name, exit_code)
    detail = _extract_detail_name(old_name, category)
    return f"exit.{category}.{detail}"


# =============================================================================
# Exit Mapping Extraction (Pure Functions)
# =============================================================================


def _extract_exit_mappings(
    exits: dict[str, dict[str, Any]],
) -> tuple[ExitMapping, ...]:
    """Extract exit mappings from exits section.

    Args:
        exits: Old format exits section

    Returns:
        Tuple of ExitMapping objects
    """
    mappings: list[ExitMapping] = []

    for old_name, exit_data in exits.items():
        code = exit_data.get("code", 1)
        description = exit_data.get("description", "")
        new_path = _infer_new_exit_path(old_name, code)

        mappings.append(
            ExitMapping(
                old_name=old_name,
                new_path=new_path,
                code=code,
                description=description,
            )
        )

    return tuple(mappings)


# =============================================================================
# Transition Conversion (Pure Functions)
# =============================================================================


def _convert_transition_target(
    target: str,
    name_to_path: dict[str, str],
) -> str:
    """Convert a single transition target (legacy flat format).

    Converts "exit::old_name" format to "exit.category.detail" format.
    Non-exit targets are returned unchanged.

    Args:
        target: Original target (e.g., "exit::green_success" or "process")
        name_to_path: Mapping of old exit names to new paths

    Returns:
        Converted target string
    """
    if not target.startswith("exit::"):
        return target

    # Extract old exit name
    old_name = target[6:]  # Remove "exit::" prefix
    return name_to_path.get(old_name, target)


def _convert_nested_transition_target(target: str) -> str:
    """ネスト形式の遷移先を変換する（純粋関数）。

    v0.12.x 形式の exit::category::detail を
    v1.0 形式の exit.category.detail に変換する。

    非 exit 遷移先はそのまま返す。

    Examples:
        "exit::success::done"             → "exit.success.done"
        "exit::failure::ssh::handshake"   → "exit.failure.ssh.handshake"
        "process"                         → "process"

    Args:
        target: 遷移先文字列

    Returns:
        変換後の遷移先
    """
    if not target.startswith("exit::"):
        return target
    return target.replace("::", ".")


def _convert_transitions(
    transitions: dict[str, dict[str, str]],
    name_to_path: dict[str, str],
) -> dict[str, dict[str, str]]:
    """Convert all transitions to new format.

    Args:
        transitions: Original transitions section
        name_to_path: Mapping of old exit names to new paths

    Returns:
        Converted transitions
    """
    result: dict[str, dict[str, str]] = {}

    for node_name, node_transitions in transitions.items():
        result[node_name] = {}
        for state, target in node_transitions.items():
            result[node_name][state] = _convert_transition_target(
                target, name_to_path
            )

    return result


# =============================================================================
# Exit Tree Building (Pure Functions)
# =============================================================================


def _build_exit_tree(
    mappings: Sequence[ExitMapping],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Build nested exit tree structure from mappings.

    Converts flat mappings to nested dict suitable for YAML.

    Example output:
        {
            "success": {
                "done": {"description": "正常終了"},
            },
            "failure": {
                "timeout": {"description": "タイムアウト"},
            },
        }

    Args:
        mappings: Sequence of ExitMapping objects

    Returns:
        Nested dictionary for exit node structure
    """
    tree: dict[str, dict[str, dict[str, Any]]] = {}

    for mapping in mappings:
        # Parse path: "exit.category.detail"
        parts = mapping.new_path.split(".")
        if len(parts) != 3:
            continue

        _, category, detail = parts

        if category not in tree:
            tree[category] = {}

        tree[category][detail] = {"description": mapping.description}

    return tree


# =============================================================================
# Nested Exits Conversion (Pure Functions)
# =============================================================================


def _convert_nested_exits(
    exits: dict[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """ネスト形式の exits を nodes.exit ツリーに変換する（純粋関数）。

    ネスト形式はカテゴリ（success/failure/warning）をキーとし、
    配下にリーフノード定義を持つ。exit_code は ExitContract で
    管理されるため削除する。

    リーフノード判定: description キーを持つノードはリーフとして扱う。

    Args:
        exits: ネスト形式の exits セクション

    Returns:
        (exit_tree, warnings): 変換後のツリーと警告の tuple
    """
    warnings: list[str] = []

    def _strip_exit_code(node: dict[str, Any]) -> dict[str, Any]:
        """exit_code / code を除いた dict を返す（純粋関数）。

        v0.12.x 形式は `code` キーを使用し、新形式は `exit_code` を使用する。
        どちらも ExitContract で管理されるため、nodes.exit 配下では不要。
        """
        return {k: v for k, v in node.items() if k not in ("exit_code", "code")}

    def _process_level(data: dict[str, Any]) -> dict[str, Any]:
        """再帰的にネスト構造を処理する（純粋関数）。

        判定ルール:
        1. dict でない値 → スキップ
        2. description あり → リーフノード（exit_code 除去）
        3. description なし & ネスト dict あり → 中間ノード（再帰）
        """
        result: dict[str, Any] = {}
        for key, value in data.items():
            if not isinstance(value, dict):
                continue
            if "description" in value:
                result[key] = _strip_exit_code(value)
            else:
                result[key] = _process_level(value)
        return result

    exit_tree = _process_level(exits)
    return exit_tree, tuple(warnings)


# =============================================================================
# Transition Extraction from Nodes (Pure Functions)
# =============================================================================


@dataclass(frozen=True)
class TransitionExtractionResult:
    """transitions 抽出の結果（イミュータブル）。

    Attributes:
        nodes: transitions を除いた nodes
        transitions: 抽出された transitions
        extracted: 抽出が行われたか
    """

    nodes: dict[str, Any]
    transitions: dict[str, Any]
    extracted: bool


def _extract_transitions_from_nodes(
    nodes: dict[str, Any],
) -> TransitionExtractionResult:
    """nodes 内のネストされた transitions をトップレベルに抽出する（純粋関数）。

    nodes 内に transitions キーがある場合、それらをトップレベル形式に変換する。
    元の nodes dict は変更せず、新しい dict を返す。

    Args:
        nodes: YAML の nodes セクション

    Returns:
        TransitionExtractionResult: 抽出結果
    """
    transitions: dict[str, Any] = {}
    cleaned_nodes: dict[str, Any] = {}
    extracted = False

    for node_name, node_data in nodes.items():
        # exit ノードはスキップ
        if node_name == "exit":
            cleaned_nodes[node_name] = node_data
            continue

        if not isinstance(node_data, dict):
            cleaned_nodes[node_name] = node_data
            continue

        if "transitions" in node_data:
            transitions[node_name] = node_data["transitions"]
            # transitions を除いた新しい dict を作成（イミュータブル操作）
            cleaned_nodes[node_name] = {
                k: v for k, v in node_data.items() if k != "transitions"
            }
            extracted = True
        else:
            cleaned_nodes[node_name] = node_data

    return TransitionExtractionResult(
        nodes=cleaned_nodes,
        transitions=transitions,
        extracted=extracted,
    )


# =============================================================================
# Format-specific Conversion Functions (Pure Functions)
# =============================================================================


# Transition graph YAML の標準キー順序
_CANONICAL_KEY_ORDER: tuple[str, ...] = (
    "version",
    "entrypoint",
    "description",
    "nodes",
    "start",
    "transitions",
    "options",
)


def _order_yaml_keys(data: dict[str, Any]) -> dict[str, Any]:
    """変換後の dict を標準キー順序に並べ替える（純粋関数）。

    transition_graph_reference.md の定義順に従い、
    yaml.safe_dump(sort_keys=False) で可読性の高い出力を得る。

    未知のキーは末尾に追加される。

    Args:
        data: 変換結果の dict

    Returns:
        キー順序を整えた新しい dict
    """
    ordered: dict[str, Any] = {}
    for key in _CANONICAL_KEY_ORDER:
        if key in data:
            ordered[key] = data[key]
    # 未知のキーを末尾に
    for key in data:
        if key not in ordered:
            ordered[key] = data[key]
    return ordered


def _ensure_version_field(data: dict[str, Any]) -> None:
    """変換結果に version フィールドを補完する（破壊的更新）。

    旧形式 YAML は version フィールドを持たないことがあるため、
    変換後の新形式 YAML で version が必須であることを保証する。

    Note:
        この関数は deepcopy 済みの dict に対して呼ばれるため、
        元データの純粋性は保たれる。

    Args:
        data: 変換結果の dict（deepcopy 済み）
    """
    if "version" not in data:
        data["version"] = "1.0"


def _convert_legacy_flat(
    yaml_data: dict[str, Any],
    exits: dict[str, Any],
) -> ConversionResult:
    """レガシーフラット形式の YAML を変換する（純粋関数）。

    既存の convert_yaml_structure ロジックを抽出。

    Args:
        yaml_data: 元の YAML データ
        exits: フラット形式の exits セクション

    Returns:
        ConversionResult with converted data
    """
    result = copy.deepcopy(yaml_data)

    mappings = _extract_exit_mappings(exits)
    name_to_path: dict[str, str] = {m.old_name: m.new_path for m in mappings}
    exit_tree = _build_exit_tree(mappings)

    del result["exits"]

    nodes = result.get("nodes", {})
    nodes["exit"] = exit_tree
    result["nodes"] = nodes

    if "transitions" in result:
        result["transitions"] = _convert_transitions(
            result["transitions"],
            name_to_path,
        )

    _ensure_version_field(result)
    return ConversionResult.ok(_order_yaml_keys(result))


def _convert_nested(
    yaml_data: dict[str, Any],
    exits: dict[str, Any],
) -> ConversionResult:
    """ネスト形式の YAML を変換する（純粋関数）。

    変換パイプライン:
    1. exits → nodes.exit に変換
    2. nodes 内 transitions をトップレベルに抽出
    3. 既存トップレベル transitions とマージ（競合時はノード内優先 + 警告）

    Args:
        yaml_data: 元の YAML データ
        exits: ネスト形式の exits セクション

    Returns:
        ConversionResult with converted data
    """
    result = copy.deepcopy(yaml_data)
    all_warnings: list[str] = []

    # 1. exits → nodes.exit に変換
    exit_tree, exit_warnings = _convert_nested_exits(exits)
    all_warnings.extend(exit_warnings)
    del result["exits"]

    nodes = result.get("nodes", {})
    nodes["exit"] = exit_tree

    # 2. nodes 内 transitions をトップレベルに抽出
    extraction = _extract_transitions_from_nodes(nodes)
    result["nodes"] = extraction.nodes

    if extraction.extracted:
        existing = result.get("transitions", {})

        # キー単位マージ: ノード内 transitions を優先しつつ、
        # トップレベルにしかないキーも保持する
        merged: dict[str, Any] = dict(existing)
        for node_name, node_trans in extraction.transitions.items():
            if node_name in merged:
                # 同一ノードの競合をキー単位で検出
                conflicting_keys = set(merged[node_name]) & set(node_trans)
                if conflicting_keys:
                    all_warnings.append(
                        f"ノード '{node_name}' の transitions がトップレベルと"
                        f"ノード内の両方に存在します。競合キー "
                        f"{sorted(conflicting_keys)} はノード内の定義を"
                        f"優先しました。"
                    )
                # キー単位でマージ（ノード内が優先、トップレベル固有は保持）
                merged[node_name] = {**merged[node_name], **node_trans}
            else:
                merged[node_name] = node_trans
        result["transitions"] = merged

    # 3. 遷移先の exit:: 形式を exit. 形式に変換
    if "transitions" in result:
        converted_transitions: dict[str, Any] = {}
        for node_name, node_trans in result["transitions"].items():
            if isinstance(node_trans, dict):
                converted_transitions[node_name] = {
                    state: _convert_nested_transition_target(target)
                    for state, target in node_trans.items()
                }
            else:
                converted_transitions[node_name] = node_trans
        result["transitions"] = converted_transitions

    _ensure_version_field(result)
    return ConversionResult.ok(_order_yaml_keys(result), warnings=tuple(all_warnings))


# =============================================================================
# Main Conversion Function
# =============================================================================


def convert_yaml_structure(
    yaml_data: dict[str, Any],
) -> ConversionResult:
    """Convert YAML from old exits format to new nested exit format.

    形式を検出して適切な変換関数に委譲する。
    入力の yaml_data は変更しない（純粋関数）。

    Converts:
    - `exits` section → `nodes.exit` nested structure
    - `exit::name` transitions → `exit.category.detail` format

    Args:
        yaml_data: Original YAML data as dict

    Returns:
        ConversionResult with converted data or error
    """
    # No exits section - return unchanged
    if "exits" not in yaml_data:
        return ConversionResult.ok(yaml_data)

    exits = yaml_data.get("exits", {})
    if not exits:
        return ConversionResult.ok(yaml_data)

    format_type = _detect_exits_format(exits)

    if format_type.format == "legacy_flat":
        return _convert_legacy_flat(yaml_data, exits)
    elif format_type.format == "nested":
        return _convert_nested(yaml_data, exits)
    else:
        return ConversionResult.fail(
            "未知の exits 形式です。手動で変換してください。"
        )
