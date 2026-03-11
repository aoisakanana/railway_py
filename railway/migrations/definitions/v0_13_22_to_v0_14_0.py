"""Migration from v0.13.22 to v0.14.0.

Changes:
- Board パターン導入（Riverboard）
- _railway/cache/ ディレクトリ追加
- コードガイダンス: Contract → Board パターンへの移行提案
- ADR-007 追加

Note:
    このマイグレーションは破壊的変更を含みます。
    Contract mode は引き続きサポートされますが、
    Board mode が新しいデフォルトとなります。
"""

from railway.migrations.changes import (
    CodeGuidance,
    FileChange,
    MigrationDefinition,
)

MIGRATION_0_13_22_TO_0_14_0 = MigrationDefinition(
    from_version="0.13.22",
    to_version="0.14.0",
    description="Riverboard パターン導入: Board mode, AST 解析, Trace モード",
    file_changes=(
        FileChange.create(
            path="_railway/cache/.gitkeep",
            content="",
            description="AST 解析キャッシュディレクトリ作成",
        ),
    ),
    config_changes=(),
    yaml_transforms=(),
    code_guidance=(
        CodeGuidance(
            description=(
                "model_copy() を使用しています。Board パターンでは board.field = value で直接更新できます"
            ),
            pattern=r"\.model_copy\(",
            replacement="# Board パターン: board.field = value で直接更新",
            file_patterns=("src/nodes/**/*.py",),
        ),
        CodeGuidance(
            description=(
                "@node(requires=..., provides=...) は v0.14.0 で削除されました。"
                "Board パターンでは AST 解析により自動検出されます"
            ),
            pattern=r"@node\([^)]*(?:requires|provides)",
            replacement="@node  # requires/provides は自動検出",
            file_patterns=("src/nodes/**/*.py",),
        ),
        CodeGuidance(
            description=(
                "tuple[Context, Outcome] 返り値を Board パターンに移行: "
                "board を直接変更し、Outcome のみ返す"
            ),
            pattern=r"-> tuple\[.*?, Outcome\]",
            replacement="-> Outcome  # Board パターン: board を直接変更",
            file_patterns=("src/nodes/**/*.py",),
        ),
        CodeGuidance(
            description=(
                "ExitContract サブクラスを Board mode 終端ノードに移行: "
                "board を受け取り None を返す"
            ),
            pattern=r"class \w+\(ExitContract\)",
            replacement="# Board mode: 終端ノードは board を受け取り None を返す",
            file_patterns=("src/nodes/exit/**/*.py",),
        ),
        CodeGuidance(
            description=(
                "railway-framework の依存バージョンを更新してください: "
                '"railway-framework>=0.14.0,<0.15.0"'
            ),
            pattern=r'"railway-framework>=0\.13\.\d+',
            replacement='"railway-framework>=0.14.0',
            file_patterns=("pyproject.toml",),
        ),
    ),
    post_migration_commands=(
        "railway sync transition --all",
    ),
    warnings=(
        "【重要】v0.14.0 は Riverboard パターンを導入します。",
        "",
        "主な変更:",
        "  - @node の第一引数は 'board' が必須（E015 エラー）",
        "  - @node(requires=..., provides=...) は削除（AST 解析で自動検出）",
        "  - Contract mode は引き続きサポート（@node(output=...) で利用可能）",
        "  - railway new node / new entry はデフォルトで Board mode テンプレートを生成",
        "",
        "移行手順:",
        "  1. railway update を実行（このコマンド）",
        "  2. CodeGuidance に従ってノードコードを更新",
        "  3. railway sync transition --all で再生成",
        "  4. テストを実行して動作確認",
    ),
)
