"""Migration from v0.13.3 to v0.13.4.

Changes:
- railway docs: デフォルトでターミナル出力、--browser でブラウザ起動
- YAML 自動解決: entrypoint を含む module パスに変更
  - 非 exit ノード: nodes.{entrypoint}.{path}
  - exit ノード: 変更なし（nodes.exit.{path}）
"""

from railway.migrations.changes import (
    CodeGuidance,
    MigrationDefinition,
)

MIGRATION_0_13_3_TO_0_13_4 = MigrationDefinition(
    from_version="0.13.3",
    to_version="0.13.4",
    description="YAML モジュールパス自動解決の改善",
    file_changes=(),
    config_changes=(),
    yaml_transforms=(),  # YAML 構造変更なし
    code_guidance=(
        CodeGuidance(
            description="YAML の module 自動解決が entrypoint を含むように変更",
            pattern=r"^nodes:\s*\n\s+\w+:\s*\n\s+description:",
            replacement=(
                "# module が省略されている場合、nodes.{entrypoint}.{name} に自動解決されます\n"
                "# 明示的に module を指定することで従来の動作を維持できます"
            ),
            file_patterns=("transition_graphs/**/*.yml",),
        ),
    ),
    post_migration_commands=(
        "railway sync transition --all",
    ),
    warnings=(
        "【注意】YAML で module を省略している場合、自動解決パスが変更されます",
        "  旧: nodes.{node_name}",
        "  新: nodes.{entrypoint}.{node_name}",
        "既に明示的に module を指定している YAML は影響を受けません",
    ),
)
