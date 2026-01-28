"""Migration from v0.12.1 to v0.12.2.

ExitContract 導入による API 簡素化。

関数型パラダイム:
- 全てのデータはイミュータブル（frozen=True）
- 定義は純粋なデータ構造

主な変更点:
- dag_runner() 返り値: DagRunnerResult → ExitContract
- Exit クラス削除（Exit.GREEN, Exit.RED 等）
- EXIT_CODES, exit_codes パラメータ削除
- ExitOutcome クラス削除
- 終端ノードが ExitContract を返すオプション追加

参照:
- ADR-005: ExitContract による API 簡素化
"""

from railway.migrations.changes import (
    CodeGuidance,
    MigrationDefinition,
)


MIGRATION_0_12_1_TO_0_12_2 = MigrationDefinition(
    from_version="0.12.1",
    to_version="0.12.2",
    description="ExitContract 導入による API 簡素化（ADR-005）",
    file_changes=(
        # 生成コードの変更は code_guidance で手動対応を推奨
    ),
    config_changes=(
        # project.yaml のバージョン更新は executor が自動実行
    ),
    yaml_transforms=(
        # YAML 構造に変更なし
    ),
    code_guidance=(
        CodeGuidance(
            description="DagRunnerResult → ExitContract に変更してください",
            pattern=r"DagRunnerResult",
            replacement="ExitContract",
            file_patterns=("_railway/generated/**/*.py", "src/transitions/**/*.py"),
        ),
        CodeGuidance(
            description="Exit.GREEN/RED/YELLOW は終端ノード関数に置き換えてください",
            pattern=r"Exit\.(GREEN|RED|YELLOW)",
            replacement="# 終端ノード関数 (exit_success_done など) に置き換え",
            file_patterns=("**/*.py",),
        ),
        CodeGuidance(
            description="ExitOutcome は削除されました",
            pattern=r"ExitOutcome",
            replacement="# ExitOutcome は削除。終端ノードは ExitContract を使用",
            file_patterns=("**/*.py",),
        ),
        CodeGuidance(
            description="exit_codes パラメータは削除されました",
            pattern=r"exit_codes\s*=",
            replacement="# exit_codes パラメータは削除",
            file_patterns=("**/*.py",),
        ),
        CodeGuidance(
            description="生成コードを再生成してください",
            pattern=r"# Auto-generated|# DO NOT EDIT",
            replacement="# `railway sync transition --all` を実行して再生成",
            file_patterns=("_railway/generated/**/*.py", "src/transitions/**/*.py"),
        ),
    ),
    post_migration_commands=(
        "railway sync transition --all",
    ),
    warnings=(
        "【重要】生成コードを再生成してください: `railway sync transition --all`",
        "【重要】dag_runner の返り値が ExitContract に変更されました",
        "Exit.GREEN/RED/YELLOW は削除されました。終端ノード関数を使用してください",
        "詳細: docs/adr/005_exit_contract_simplification.md を参照",
    ),
)
