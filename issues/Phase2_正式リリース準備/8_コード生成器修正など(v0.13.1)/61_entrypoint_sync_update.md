# Issue #61: エントリポイントテンプレート更新（run() 使用）

**優先度**: P1
**依存**: #60
**ブロック**: #64

---

## 概要

エントリポイントのテンプレートを更新し、`run()` ヘルパーを使用する形式に変更する。

**本 Issue の責務**:
- `_get_dag_entry_template()` の更新
- `_get_dag_entry_template_pending_sync()` の新規追加（sync 前用）
- これらのユニットテスト

**#64 の責務**:
- デフォルト動作の変更
- E2E 統合テスト

## 背景

現在のエントリポイントテンプレートは `dag_runner()` を直接呼び出しており、
YAML の `start` 定義と Python コードの `start` import が二重管理になっている。

**現状** (`_get_dag_entry_template()`):
```python
from nodes.{name}.start import start  # ← YAML と二重管理
from _railway.generated.{name}_transitions import TRANSITION_TABLE

result = dag_runner(start=start, transitions=TRANSITION_TABLE)
```

**改善後**:
```python
from _railway.generated.{name}_transitions import run  # ← run() が start を内包

result = run({})  # シンプル
```

---

## 既存コードの確認

修正対象は `railway/cli/new.py` の `_get_dag_entry_template()` 関数:

```python
# 現在の実装
def _get_dag_entry_template(name: str) -> str:
    return f'''...
from _railway.generated.{name}_transitions import (
    TRANSITION_TABLE,
    GRAPH_METADATA,
)
from nodes.{name}.start import start

result = dag_runner(
    start=start,
    transitions=TRANSITION_TABLE,
    ...
)
'''
```

---

## 設計: 2種類のテンプレート

| テンプレート | 使用場面 | 内容 |
|--------------|----------|------|
| `_get_dag_entry_template()` | sync 実行後 | `run()` を import して実行 |
| `_get_dag_entry_template_pending_sync()` | sync 実行前 | 次のステップを案内するメッセージ |

この分離により、`--no-sync` で生成した場合でも、ユーザーに明確な次のステップを示せる。

---

## TDD 実装フロー

### Phase 1: Red（失敗するテストを先に作成）

```python
# tests/unit/cli/test_dag_entry_template.py

import pytest
from railway.cli.new import (
    _get_dag_entry_template,
    _get_dag_entry_template_pending_sync,
)


class TestGetDagEntryTemplate:
    """sync 後のエントリポイントテンプレートのテスト。"""

    def test_uses_run_helper(self) -> None:
        """run() ヘルパーを使用する。"""
        py_content = _get_dag_entry_template("greeting")

        assert "from _railway.generated.greeting_transitions import run" in py_content
        # dag_runner を直接使用しない
        assert "dag_runner" not in py_content

    def test_handles_result_success(self) -> None:
        """result.is_success を確認する。"""
        py_content = _get_dag_entry_template("greeting")

        assert "result.is_success" in py_content
        assert "result.exit_state" in py_content

    def test_handles_result_failure(self) -> None:
        """失敗時に exit code を返す。"""
        py_content = _get_dag_entry_template("greeting")

        assert "SystemExit(result.exit_code)" in py_content

    def test_includes_main_block(self) -> None:
        """if __name__ == '__main__' ブロックがある。"""
        py_content = _get_dag_entry_template("greeting")

        assert 'if __name__ == "__main__":' in py_content

    def test_generated_code_is_valid_python(self) -> None:
        """生成されたコードは構文的に正しい。"""
        py_content = _get_dag_entry_template("greeting")

        compile(py_content, "<string>", "exec")

    @pytest.mark.parametrize("name", ["greeting", "my_workflow", "alert_handler"])
    def test_works_with_various_names(self, name: str) -> None:
        """様々な名前で動作する。"""
        py_content = _get_dag_entry_template(name)

        assert f"from _railway.generated.{name}_transitions import run" in py_content


class TestGetDagEntryTemplatePendingSync:
    """sync 前のエントリポイントテンプレートのテスト。"""

    def test_includes_guidance_message(self) -> None:
        """次のステップを案内するメッセージがある。"""
        py_content = _get_dag_entry_template_pending_sync("greeting")

        assert "railway sync transition" in py_content

    def test_suggests_no_sync_alternative(self) -> None:
        """--no-sync オプションについて言及する。"""
        py_content = _get_dag_entry_template_pending_sync("greeting")

        assert "--no-sync" in py_content

    def test_raises_not_implemented_error(self) -> None:
        """NotImplementedError を raise する。"""
        py_content = _get_dag_entry_template_pending_sync("greeting")

        assert "NotImplementedError" in py_content

    def test_generated_code_is_valid_python(self) -> None:
        """生成されたコードは構文的に正しい。"""
        py_content = _get_dag_entry_template_pending_sync("greeting")

        compile(py_content, "<string>", "exec")

    def test_commented_code_shows_expected_structure(self) -> None:
        """コメントアウトされたコードが期待される構造を示す。"""
        py_content = _get_dag_entry_template_pending_sync("greeting")

        assert "# from _railway.generated.greeting_transitions import run" in py_content
```

### Phase 2: Green（最小実装）

```python
# railway/cli/new.py の修正

def _get_dag_entry_template(name: str) -> str:
    """Get dag_runner style entry point template (sync 後用).

    純粋関数: name -> Python コード文字列

    Args:
        name: エントリーポイント名

    Returns:
        Python コード文字列（run() を使用）
    """
    class_name = _to_pascal_case(name)
    return f'''"""
{name} エントリーポイント

Usage:
    railway run {name}
    # または
    python -m src.{name}
"""
from _railway.generated.{name}_transitions import run


def main() -> None:
    """ワークフローを実行する。"""
    # TODO: 初期コンテキストを設定してください
    # from contracts.{name}_context import {class_name}Context
    # initial_context = {class_name}Context(...)

    result = run({{}})

    if result.is_success:
        print(f"完了: {{result.exit_state}}")
    else:
        print(f"失敗: {{result.exit_state}}")
        raise SystemExit(result.exit_code)


if __name__ == "__main__":
    main()
'''


def _get_dag_entry_template_pending_sync(name: str) -> str:
    """Get dag_runner style entry point template (sync 前用).

    純粋関数: name -> Python コード文字列

    Args:
        name: エントリーポイント名

    Returns:
        Python コード文字列（次のステップを案内）
    """
    return f'''"""
{name} エントリーポイント

このファイルは `railway new entry {name}` で --no-sync オプションを
使用したため、まだ実行できません。

次のステップ:
    railway sync transition --entry {name}
    railway run {name}
"""

# TODO: sync 実行後、以下のコメントを解除してください
# from _railway.generated.{name}_transitions import run
#
# def main() -> None:
#     result = run({{}})
#     if result.is_success:
#         print(f"完了: {{result.exit_state}}")
#     else:
#         raise SystemExit(result.exit_code)
#
# if __name__ == "__main__":
#     main()

raise NotImplementedError(
    "先に `railway sync transition --entry {name}` を実行してください。"
)
'''
```

### Phase 3: Refactor

- 非同期版テンプレート追加（必要に応じて）
- Context 型を使用する上級者向けテンプレート

---

## 修正ファイル

| ファイル | 変更内容 |
|----------|----------|
| `railway/cli/new.py` | `_get_dag_entry_template()` 修正、`_get_dag_entry_template_pending_sync()` 追加 |
| `tests/unit/cli/test_dag_entry_template.py` | 新規テストファイル |

---

## 変更前後の比較

### Before

```python
# greeting.py
from railway import entry_point
from railway.core.dag.runner import dag_runner
from railway.core.dag.callbacks import StepRecorder

from _railway.generated.greeting_transitions import (
    TRANSITION_TABLE,
    GRAPH_METADATA,
)
from nodes.greeting.start import start


@entry_point
def main():
    recorder = StepRecorder()

    result = dag_runner(
        start=start,
        transitions=TRANSITION_TABLE,
        max_iterations=GRAPH_METADATA.get("max_iterations", 100),
        on_step=recorder,
    )

    if result.is_success:
        print(f"✓ 完了: {result.exit_code}")
    else:
        print(f"✗ 失敗: {result.exit_code}")

    return result
```

### After

```python
# greeting.py
"""
greeting エントリーポイント

Usage:
    railway run greeting
"""
from _railway.generated.greeting_transitions import run


def main() -> None:
    """ワークフローを実行する。"""
    result = run({})

    if result.is_success:
        print(f"完了: {result.exit_state}")
    else:
        print(f"失敗: {result.exit_state}")
        raise SystemExit(result.exit_code)


if __name__ == "__main__":
    main()
```

---

## 受け入れ条件

### 機能（純粋関数）
- [ ] `_get_dag_entry_template()` が `run()` を使用するコードを生成
- [ ] `_get_dag_entry_template_pending_sync()` が案内メッセージ付きコードを生成
- [ ] 生成されたコードが構文的に正しい（compile テスト）
- [ ] 様々なエントリポイント名で動作する

### TDD・関数型
- [ ] Red → Green → Refactor フェーズに従って実装
- [ ] 両関数が純粋関数（副作用なし）
- [ ] パラメタライズドテストで網羅
- [ ] 全テスト通過

### 注意
- 実際のファイル書き込みは本 Issue の責務外（#64 で実装）
- E2E 動作確認は #64 で実施

---

*テンプレート生成の純粋関数を提供*
