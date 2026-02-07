"""Migration from v0.10.x to v0.11.3.

DAGネイティブサポートへの移行。

関数型パラダイム:
- 全てのデータはイミュータブル（frozen=True）
- 定義は純粋なデータ構造
"""

from railway.migrations.changes import (
    CodeGuidance,
    FileChange,
    MigrationDefinition,
)

MIGRATION_0_10_TO_0_11 = MigrationDefinition(
    from_version="0.10.0",
    to_version="0.11.3",
    description="DAGネイティブサポートへの移行",
    file_changes=(
        FileChange.create(
            path="transition_graphs/.gitkeep",
            content="# Transition graph YAML files\n# File naming: {entrypoint}_{YYYYMMDDHHmmss}.yml\n",
            description="DAGワークフロー用ディレクトリを追加",
        ),
        FileChange.create(
            path="_railway/generated/.gitkeep",
            content="# Auto-generated transition code\n# Do not edit manually - use `railway sync transition`\n",
            description="自動生成コード用ディレクトリを追加",
        ),
    ),
    code_guidance=(
        CodeGuidance(
            description="dict 型を tuple[Contract, Outcome] に変更してください",
            pattern=r"def\s+\w+\([^)]*\)\s*->\s*dict:",
            replacement="# -> tuple[YourContext, Outcome] を返すように変更",
            file_patterns=("src/nodes/**/*.py",),
        ),
        CodeGuidance(
            description="data: dict を ctx: YourContext に変更してください",
            pattern=r"def\s+\w+\(data:\s*dict\)",
            replacement="# -> ctx: YourContext を引数にしてください",
            file_patterns=("src/nodes/**/*.py", "src/**/*.py"),
        ),
        CodeGuidance(
            description="pipeline() を dag_runner() または typed_pipeline() に変更してください",
            pattern=r"from railway import[^)]*\bpipeline\b",
            replacement="# -> dag_runner または typed_pipeline を使用",
            file_patterns=("src/*.py",),
        ),
    ),
    warnings=(
        "ノードの戻り値形式が変更されています: dict -> tuple[Contract, Outcome]",
        "pipeline() は非推奨です。dag_runner() または typed_pipeline() を使用してください。",
        "詳細: railway docs または README.md の「既存プロジェクトのアップグレード」を参照",
    ),
)
