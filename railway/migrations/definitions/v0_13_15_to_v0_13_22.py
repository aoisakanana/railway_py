"""Migration from v0.13.15 to v0.13.22.

範囲マッチにより、0.13.15 以降のすべてのバージョンから
0.13.22 へマイグレーション可能。

Changes:
- codegen: _exit_path_to_contract_name の PascalCase 変換修正（BUG-3）
- codegen: generate_run_helper が YAML options.max_iterations を反映（INC-1）
- CLI: railway new node 階層ノード作成時の出力パス修正
- CLI: 入力バリデーション強化（v0.13.18）
- codegen: 深いネストノードの import / _node_name 修正
- codegen: description 内特殊文字のエスケープ修正
"""

from railway.migrations.changes import (
    CodeGuidance,
    MigrationDefinition,
)

MIGRATION_0_13_15_TO_0_13_22 = MigrationDefinition(
    from_version="0.13.15",
    to_version="0.13.22",
    description="codegen PascalCase 修正、max_iterations 反映、CLI 出力修正",
    file_changes=(),
    config_changes=(),
    yaml_transforms=(),
    code_guidance=(
        CodeGuidance(
            description=(
                "railway-framework の依存バージョンを更新してください: "
                '"railway-framework>=0.13.22,<0.14.0"'
            ),
            pattern=r'"railway-framework>=0\.13\.\d+',
            replacement='"railway-framework>=0.13.22',
            file_patterns=("pyproject.toml",),
        ),
    ),
    post_migration_commands=(
        "railway sync transition --all",
    ),
    warnings=(
        "【推奨】codegen の修正が複数含まれます。sync --all で再生成してください:",
        "  - PascalCase 変換修正: アンダースコア入り exit 名のクラス名が正規化されます",
        "  - max_iterations: run() のデフォルト値が YAML options と一致するようになります",
        "  - description: 特殊文字を含む description が正しくエスケープされます",
    ),
)
