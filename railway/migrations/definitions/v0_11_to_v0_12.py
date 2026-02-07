"""Migration from v0.11.x to v0.12.0.

終端ノードの nodes.exit 統合への移行。

関数型パラダイム:
- 全てのデータはイミュータブル（frozen=True）
- 定義は純粋なデータ構造

主な変更点:
- exits セクション → nodes.exit 配下の階層構造
- exit::name 遷移先 → exit.category.detail 形式
- module/function は省略可能（自動解決）
- 終端ノードの返り値: tuple[Context, Outcome] → Context のみ

参照:
- ADR-004: Exit ノードの設計と例外処理
"""

from railway.migrations.changes import (
    CodeGuidance,
    MigrationDefinition,
    YamlTransform,
)
from railway.migrations.yaml_converter import convert_yaml_structure

MIGRATION_0_11_TO_0_12 = MigrationDefinition(
    from_version="0.11.0",
    to_version="0.12.0",
    description="終端ノードの nodes.exit 統合（ADR-004）",
    file_changes=(
        # 生成コード用ディレクトリは v0.11 で作成済み
    ),
    config_changes=(
        # project.yaml のバージョン更新は executor が自動実行
    ),
    yaml_transforms=(
        YamlTransform(
            pattern="transition_graphs/**/*.yml",
            transform=convert_yaml_structure,
            description="exits セクションを nodes.exit 配下に変換",
        ),
    ),
    code_guidance=(
        CodeGuidance(
            description="終端ノードは Context のみを返すように変更してください（Outcome 不要）",
            pattern=r"def\s+\w+\([^)]*\)\s*->\s*tuple\[.*Outcome\]:",
            replacement="# 終端ノードは def done(ctx) -> FinalContext: のように Context のみを返す",
            file_patterns=("src/nodes/exit/**/*.py", "src/nodes/**/exit*.py"),
        ),
        CodeGuidance(
            description="生成コードを再生成してください（`railway sync transition`）",
            pattern=r"# Auto-generated|# DO NOT EDIT",
            replacement="# `railway sync transition` を実行して再生成してください",
            file_patterns=("_railway/generated/**/*.py", "src/transitions/**/*.py"),
        ),
        CodeGuidance(
            description="exit:: 形式は廃止されました。exit.success.done 形式に変更してください",
            pattern=r'exit::\w+',
            replacement="# exit.success.done 形式に変更",
            file_patterns=("**/*.py",),
        ),
    ),
    post_migration_commands=(
        "railway sync transition --all",
    ),
    warnings=(
        "【重要】YAML ファイルが自動変換されます。バックアップを確認してください。",
        "【重要】終端ノード（exit ハンドラ）の返り値を Context のみに変更してください。",
        "【重要】マイグレーション後、`railway sync transition --all` を実行してください。",
        "詳細: docs/adr/004_exit_node_design.md を参照",
    ),
)
