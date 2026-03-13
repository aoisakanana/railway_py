"""Migration from v0.14.0 to v0.14.3.

Changes:
- 未使用の生成 Board 型ファイル削除 (glob)
- linear mode → DAG mode 移行ガイダンス
- Contract mode → Board mode 移行ガイダンス
- exit code 修正ガイダンス
- handle_result 削除ガイダンス
- 依存バージョン更新ガイダンス

Note:
    このマイグレーションは破壊的変更を含みます。
    linear mode (typed_pipeline) は v0.14.3 で削除されます。
"""

from railway.migrations.changes import (
    CodeGuidance,
    FileChange,
    MigrationDefinition,
)

MIGRATION_0_14_0_TO_0_14_3 = MigrationDefinition(
    from_version="0.14.0",
    to_version="0.14.3",
    description="破壊的変更: linear mode 削除、exit code 修正、handle_result 削除",
    file_changes=(
        FileChange.delete(
            path="_railway/generated/*_board.py",
            description="未使用の生成 Board 型ファイル削除",
        ),
    ),
    config_changes=(),
    yaml_transforms=(),
    code_guidance=(
        CodeGuidance(
            description=(
                "typed_pipeline() は v0.14.3 で削除されました。"
                "DAG mode (dag_runner) に移行してください"
            ),
            pattern=r"typed_pipeline\(",
            replacement="dag_runner(  # typed_pipeline は削除されました",
            file_patterns=("src/**/*.py",),
        ),
        CodeGuidance(
            description=(
                "@node(output=...) は Contract mode です。"
                "Board mode への移行を推奨します"
            ),
            pattern=r"@node\(output=",
            replacement="@node  # Board mode: board を直接変更し Outcome を返す",
            file_patterns=("src/**/*.py",),
        ),
        CodeGuidance(
            description=(
                "@node(inputs=...) は Contract mode です。"
                "Board mode への移行を推奨します"
            ),
            pattern=r"@node\(inputs=",
            replacement="@node  # Board mode: board から直接読み取る",
            file_patterns=("src/**/*.py",),
        ),
        CodeGuidance(
            description=(
                "print による失敗表示の代わりに sys.exit() を使用してください。"
                "exit code が正しく設定されるようになりました"
            ),
            pattern=r'print\(f"✗ 失敗',
            replacement="sys.exit(1)  # exit code を正しく設定",
            file_patterns=("src/**/*.py",),
        ),
        CodeGuidance(
            description=(
                "@entry_point(...handle_result) は v0.14.3 で削除されました。"
                "handle_result パラメータを削除してください"
            ),
            pattern=r"@entry_point\([^)]*handle_result",
            replacement="@entry_point(  # handle_result は削除されました",
            file_patterns=("src/**/*.py",),
        ),
        CodeGuidance(
            description=(
                "railway-framework の依存バージョンを 0.14.3 以上に更新してください"
            ),
            pattern=r'"railway-framework>=0\.14\.[0-2]',
            replacement='"railway-framework>=0.14.3',
            file_patterns=("pyproject.toml",),
        ),
    ),
    post_migration_commands=(
        "railway sync transition --all",
    ),
    warnings=(
        "【重要】v0.14.3 は以下の破壊的変更を含みます。",
        "",
        "1. linear mode (typed_pipeline) の削除:",
        "   - typed_pipeline() は使用できません",
        "   - dag_runner() に移行してください",
        "",
        "2. exit code の修正:",
        "   - ワークフロー失敗時に正しい exit code が設定されます",
        "   - print による失敗表示を sys.exit() に置き換えてください",
        "",
        "3. handle_result の削除:",
        "   - @entry_point の handle_result パラメータは削除されました",
        "   - 結果処理はワークフロー終端ノードで行ってください",
    ),
)
