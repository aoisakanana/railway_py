# Issue #38: リリース準備（ドキュメント・マイグレーション・E2E）

**優先度**: P1
**依存**: #37
**ブロック**: なし

---

## 概要

v0.12.2 リリースに向けて、ドキュメント更新・マイグレーション定義・E2E テストを整備する。

## 1. ドキュメント更新

### docs/adr/005_exit_contract_simplification.md

**作成済み**: ExitContract による API 簡素化の設計判断を記録。

- ADR-004 との関連を明記
- 削除する抽象化の一覧
- 後方互換性の説明

### readme.md

削除する記述:
- `Exit.GREEN`, `Exit.RED`, `Exit.YELLOW` の説明
- `EXIT_CODES` の説明
- `DagRunnerResult` の説明

追加/変更:
- `ExitContract` の使用方法
- 終端ノードが `ExitContract` を返す例

### TUTORIAL.md

`codegen` が自動生成する箇所の更新:
- `Exit Enum` → 削除
- `EXIT_CODES` → 削除
- `run()` 返り値: `DagRunnerResult` → `ExitContract`

### transition_graph_reference.md

終端ノード定義の説明更新:
- `exit_code` 属性は不要（終端ノードの Contract で定義）
- `ExitContract` サブクラスの作成例

## 2. マイグレーション定義

`railway/migrations/definitions/v0_12_1_to_v0_12_2.py` に追加:

```python
"""v0.12.1 → v0.12.2 マイグレーション: ExitContract 導入。"""
from railway.migrations.types import FileChange, MigrationDefinition

# 生成コードは _railway/generated/*_transitions.py に出力される
MIGRATION = MigrationDefinition(
    from_version="0.12.1",
    to_version="0.12.2",
    description="ExitContract 導入",
    file_changes=(
        # dag_runner インポート変更
        FileChange(
            pattern="_railway/generated/*_transitions.py",
            search="from railway.core.dag.runner import dag_runner, DagRunnerResult, Exit",
            replace="from railway.core.dag.runner import dag_runner",
        ),
        FileChange(
            pattern="_railway/generated/*_transitions.py",
            search="from railway.core.dag.state import ExitOutcome",
            replace="",
        ),
        # ExitContract インポート追加
        FileChange(
            pattern="_railway/generated/*_transitions.py",
            search="from railway.core.dag.runner import dag_runner",
            replace="from railway.core.dag.runner import dag_runner\nfrom railway import ExitContract",
        ),
        # DagRunnerResult → ExitContract 型ヒント
        FileChange(
            pattern="_railway/generated/*_transitions.py",
            search="-> DagRunnerResult:",
            replace="-> ExitContract:",
        ),
    ),
    config_changes=(),
    yaml_transforms=(),
    notes=(
        "- Exit Enum, EXIT_CODES の削除は手動確認が必要",
        "- 終端ノード関数が ExitContract を返すよう修正",
        "- 推奨: `railway sync transition --all --force` で再生成",
    ),
)
```

> **Note**: 生成コードの再生成を推奨。`railway sync transition --all --force` で ExitContract 対応コードが生成される。

## 3. E2E テスト更新

### 既存テスト修正

`tests/e2e/` 配下のテストを更新:
- `DagRunnerResult` → `ExitContract` アサーション変更
- `Exit.code()` 使用箇所の修正
- `EXIT_CODES` 参照の削除

### 新規 E2E テスト

```python
# tests/e2e/test_exit_contract_workflow.py
import subprocess
from pathlib import Path

import pytest

from railway import ExitContract, DefaultExitContract


class TestExitContractWorkflow:
    """ExitContract ワークフローの E2E テスト。"""

    @pytest.fixture
    def workflow_dir(self, tmp_path: Path) -> Path:
        """テスト用ワークフローディレクトリを作成。"""
        yaml_content = '''
version: "1.0"
nodes:
  start:
    outcomes: [success.done]
  exit:
    success:
      done: {}
'''
        (tmp_path / "transition_graphs").mkdir()
        (tmp_path / "transition_graphs" / "test.yml").write_text(yaml_content)
        return tmp_path

    def test_full_workflow_returns_exit_contract(
        self, workflow_dir: Path
    ) -> None:
        """完全なワークフローが ExitContract を返す。"""
        # 1. codegen 実行
        subprocess.run(
            ["railway", "codegen", str(workflow_dir / "transition_graphs" / "test.yml")],
            check=True,
        )

        # 2. 生成されたコードを確認
        transitions_path = workflow_dir / "transitions.py"
        assert transitions_path.exists()
        code = transitions_path.read_text()
        assert "-> ExitContract:" in code
        assert "EXIT_CODES" not in code

    def test_custom_exit_contract_preserved(self, workflow_dir: Path) -> None:
        """カスタム ExitContract のフィールドが保持される。"""
        # カスタム ExitContract を定義
        class DoneResult(ExitContract):
            data: str
            exit_state: str = "success.done"

        result = DoneResult(data="test_value")
        assert result.data == "test_value"
        assert result.is_success is True

    def test_backward_compat_context_only(self) -> None:
        """Context のみ返す終端ノードが DefaultExitContract でラップされる。"""
        # DefaultExitContract で context をラップ
        result = DefaultExitContract(
            exit_state="success.done",
            context={"key": "value"},
        )
        assert isinstance(result, ExitContract)
        assert result.context == {"key": "value"}
        assert result.is_success is True
```

## 4. CHANGELOG 更新

```markdown
## v0.12.2 (YYYY-MM-DD)

### Breaking Changes

- `dag_runner()` / `async_dag_runner()` の返り値が `DagRunnerResult` から `ExitContract` に変更
- `Exit` クラス削除（`Exit.GREEN`, `Exit.RED`, `Exit.YELLOW`, `Exit.code()`）
- `exit_codes` パラメータ削除
- codegen が `Exit Enum` / `EXIT_CODES` を生成しなくなった
- 以下のエクスポートを削除:
  - `DagRunnerResult`
  - `ExitOutcome`
  - `make_state`, `make_exit`, `parse_state`, `parse_exit`
  - `map_to_state`, `is_outcome`
  - `get_function_output_type`
  - `validate_contract`（`railway.core.contract` で直接インポート可能）
- `NodeDefinition.exit_code` 属性削除

### Added

- `ExitContract` 基底クラス追加
- `DefaultExitContract` フォールバッククラス追加

### Fixed

- `railway update` で YAML 変換が適用されない問題を修正（#34）

### Migration

`railway update` を実行してマイグレーションを適用してください。
終端ノード関数は `ExitContract` サブクラスを返すよう手動修正が必要です。
```

## 受け入れ条件

### ADR
- [x] ADR-005 が作成されている
- [x] ADR-004 に ADR-005 への参照が追加されている

### ドキュメント
- [ ] readme.md が更新されている
- [ ] TUTORIAL.md が更新されている
- [ ] transition_graph_reference.md が更新されている

### マイグレーション
- [ ] v0.12.1 → v0.12.2 マイグレーション定義が追加されている
- [ ] `railway update` でマイグレーションが動作する

### テスト
- [ ] E2E テストが更新されている
- [ ] 全テストがパス

### リリース
- [ ] CHANGELOG.md が更新されている

---

*リリース準備・ドキュメントとマイグレーション*
