"""Migration from v0.13.4 to v0.13.11.

範囲マッチにより、0.13.4 以降（0.13.10rc2 等のプレリリース含む）の
すべてのバージョンから 0.13.11 へマイグレーション可能。

Changes:
- pyproject.toml に [tool.mypy] セクション追加
- railway-framework バージョン制約を更新
- tests/nodes/__init__.py 追加
- ネストノードパス生成の修正（再 sync で反映）
- --convert --dry-run バグ修正（フレームワーク側のみ、プロジェクト変更なし）
- サンプル YAML 新形式対応
- FILE_CREATE 上書き防止
"""

from railway.migrations.changes import (
    CodeGuidance,
    FileChange,
    MigrationDefinition,
)

MIGRATION_0_13_4_TO_0_13_11 = MigrationDefinition(
    from_version="0.13.4",
    to_version="0.13.11",
    description="プロジェクト品質改善（mypy 設定、バージョン固定、テスト構造、バグ修正）",
    file_changes=(
        FileChange.create(
            path="tests/nodes/__init__.py",
            content="",
            description="tests/nodes/ に __init__.py を追加（テスト検出の安定化）",
        ),
    ),
    config_changes=(),
    yaml_transforms=(),
    code_guidance=(
        CodeGuidance(
            description="pyproject.toml に [tool.mypy] セクションを追加してください",
            pattern=r"\[tool\.mypy\]",
            replacement=(
                "# pyproject.toml に以下を追加:\n"
                "[tool.mypy]\n"
                'mypy_path = "src"\n'
                "explicit_package_bases = true\n"
                "ignore_missing_imports = true"
            ),
            file_patterns=("pyproject.toml",),
        ),
        CodeGuidance(
            description=(
                "railway-framework の依存バージョンを更新してください: "
                '"railway-framework>=0.13.11,<0.14.0"'
            ),
            pattern=r'"railway-framework>=0\.1\.0"',
            replacement='"railway-framework>=0.13.11,<0.14.0"',
            file_patterns=("pyproject.toml",),
        ),
    ),
    post_migration_commands=(
        "railway sync transition --all",
    ),
    warnings=(
        "【注意】深いネストノード（sub.deep.process 等）のファイルパスが変更されます",
        "  旧: src/nodes/{entry}/sub.deep.process.py",
        "  新: src/nodes/{entry}/sub/deep/process.py",
    ),
)
