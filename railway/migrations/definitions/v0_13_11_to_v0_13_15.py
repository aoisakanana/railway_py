"""Migration from v0.13.11 to v0.13.15.

範囲マッチにより、0.13.11 以降のすべてのバージョンから
0.13.15 へマイグレーション可能。

Changes:
- TUTORIAL.md 出力表記を実際のログ形式に合わせて更新
- codegen 修正反映（深いネストノード import、flat dotted key）
- YAML --convert 品質改善（code フィールド除去、キー順序）
- dag_runner INFO レベルログ追加（フレームワーク側のみ）
- railway-framework バージョン制約更新
"""

from railway.migrations.changes import (
    CodeGuidance,
    MigrationDefinition,
)

MIGRATION_0_13_11_TO_0_13_15 = MigrationDefinition(
    from_version="0.13.11",
    to_version="0.13.15",
    description="TUTORIAL.md 出力修正、codegen バグ修正、YAML 変換品質改善",
    file_changes=(),
    config_changes=(),
    yaml_transforms=(),
    code_guidance=(
        CodeGuidance(
            description=(
                "TUTORIAL.md の出力表記が実際のログ出力と一致するよう更新してください。"
                " railway init で再生成するか、手動で修正してください"
            ),
            pattern=r"完了: exit_state=",
            replacement=(
                "[start] 完了 (start::success::done)\n"
                "ワークフロー完了: exit.success.done\n"
                "完了: success.done"
            ),
            file_patterns=("TUTORIAL.md",),
        ),
        CodeGuidance(
            description=(
                "railway-framework の依存バージョンを更新してください: "
                '"railway-framework>=0.13.15,<0.14.0"'
            ),
            pattern=r'"railway-framework>=0\.13\.\d+',
            replacement='"railway-framework>=0.13.15',
            file_patterns=("pyproject.toml",),
        ),
    ),
    post_migration_commands=(
        "railway sync transition --all",
    ),
    warnings=(
        "【推奨】TUTORIAL.md の出力表記が変更されました。再生成を推奨します:",
        "  railway init <entrypoint名> で TUTORIAL.md が更新されます",
    ),
)
