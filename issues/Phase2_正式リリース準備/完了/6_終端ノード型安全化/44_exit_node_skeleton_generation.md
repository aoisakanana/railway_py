# Issue #44: 終端ノードスケルトン自動生成

**優先度**: P0
**依存**: #39, #40, #41（前提Issue完了後）
**ブロック**: #45, #46

---

## 概要

`railway sync transition` 実行時、未実装の終端ノードに対して型安全なスケルトンコードを自動生成する。

## 背景

終端ノードは `ExitContract` サブクラスを返す必要があるが、手動で正しい構造を書くのは面倒。スケルトン生成により、開発者は正しい構造のコードを最初から得られる。

**開発者体験の向上**:
```
YAML で終端ノードを定義
    ↓ railway sync transition
型安全なスケルトンが自動生成される（TODO コメント付き）
    ↓ 開発者
TODO を実装するだけで完了
```

---

## TDD 実装フロー

### Phase 1: Red（失敗するテストを先に作成）

#### 1-1. 純粋関数のユニットテスト

```python
# tests/unit/core/dag/test_codegen_exit_skeleton.py

import pytest
from railway.core.dag.codegen import (
    generate_exit_node_skeleton,
    _exit_path_to_contract_name,
    _exit_path_to_exit_state,
)
from railway.core.dag.types import NodeDefinition


class TestExitPathToContractName:
    """Contract 名生成のテスト（純粋関数）。"""

    @pytest.mark.parametrize(
        "exit_path,expected",
        [
            ("exit.success.done", "SuccessDoneResult"),
            ("exit.failure.timeout", "FailureTimeoutResult"),
            ("exit.failure.ssh.handshake", "FailureSshHandshakeResult"),
            ("exit.done", "DoneResult"),
            ("exit.success.api.created", "SuccessApiCreatedResult"),
        ],
    )
    def test_converts_exit_path_to_pascal_case_result(
        self, exit_path: str, expected: str
    ) -> None:
        assert _exit_path_to_contract_name(exit_path) == expected


class TestExitPathToExitState:
    """exit_state 生成のテスト（純粋関数）。"""

    @pytest.mark.parametrize(
        "exit_path,expected",
        [
            ("exit.success.done", "success.done"),
            ("exit.failure.ssh.handshake", "failure.ssh.handshake"),
            ("exit.warning.disk_full", "warning.disk_full"),
        ],
    )
    def test_removes_exit_prefix(self, exit_path: str, expected: str) -> None:
        assert _exit_path_to_exit_state(exit_path) == expected


class TestGenerateExitNodeSkeleton:
    """終端ノードスケルトン生成のテスト。"""

    @pytest.fixture
    def success_done_node(self) -> NodeDefinition:
        """正常終了ノードのフィクスチャ。"""
        return NodeDefinition(
            name="exit.success.done",
            module="nodes.exit.success.done",
            function="done",
            description="正常終了",
            is_exit=True,
        )

    @pytest.fixture
    def deep_nested_node(self) -> NodeDefinition:
        """深いネストの終端ノードフィクスチャ。"""
        return NodeDefinition(
            name="exit.failure.ssh.handshake",
            module="nodes.exit.failure.ssh.handshake",
            function="handshake",
            description="SSHハンドシェイク失敗",
            is_exit=True,
        )

    def test_generates_exit_contract_subclass(
        self, success_done_node: NodeDefinition
    ) -> None:
        """ExitContract サブクラスを生成する。"""
        code = generate_exit_node_skeleton(success_done_node)

        assert "class SuccessDoneResult(ExitContract):" in code
        assert 'exit_state: str = "success.done"' in code

    def test_generates_node_decorator_with_name(
        self, success_done_node: NodeDefinition
    ) -> None:
        """@node デコレータに name を付与する。"""
        code = generate_exit_node_skeleton(success_done_node)

        assert '@node(name="exit.success.done")' in code

    def test_function_has_exit_contract_type_hint(
        self, success_done_node: NodeDefinition
    ) -> None:
        """関数の ctx パラメータに ExitContract 型ヒントがある。

        Note:
            Any ではなく ExitContract を使用することで型安全性を確保。
            開発者は必要に応じてより具体的な型に変更できる。
        """
        code = generate_exit_node_skeleton(success_done_node)

        assert "def done(ctx: ExitContract) -> SuccessDoneResult:" in code

    def test_imports_exit_contract_and_node(
        self, success_done_node: NodeDefinition
    ) -> None:
        """ExitContract と node をインポートする。"""
        code = generate_exit_node_skeleton(success_done_node)

        assert "from railway import ExitContract, node" in code

    def test_includes_todo_comments(
        self, success_done_node: NodeDefinition
    ) -> None:
        """TODO コメントが含まれる。"""
        code = generate_exit_node_skeleton(success_done_node)

        assert "TODO:" in code

    def test_deep_nested_exit_node(
        self, deep_nested_node: NodeDefinition
    ) -> None:
        """深いネストの終端ノードにも対応。"""
        code = generate_exit_node_skeleton(deep_nested_node)

        assert "class FailureSshHandshakeResult(ExitContract):" in code
        assert 'exit_state: str = "failure.ssh.handshake"' in code
        assert "def handshake(ctx: ExitContract) -> FailureSshHandshakeResult:" in code

    def test_generated_code_is_valid_python(
        self, success_done_node: NodeDefinition
    ) -> None:
        """生成されたコードは構文的に正しい。"""
        code = generate_exit_node_skeleton(success_done_node)

        # 構文エラーがなければ compile が成功する
        compile(code, "<string>", "exec")

    def test_includes_docstring_with_description(
        self, success_done_node: NodeDefinition
    ) -> None:
        """description が docstring に含まれる。"""
        code = generate_exit_node_skeleton(success_done_node)

        assert '"""正常終了' in code
```

#### 1-2. 副作用を含む関数のテスト（統合テスト）

```python
# tests/unit/cli/test_sync_exit_nodes.py

import pytest
from pathlib import Path
from railway.cli.sync import sync_exit_nodes, SyncResult
from railway.core.dag.types import TransitionGraph, NodeDefinition


class TestSyncExitNodes:
    """終端ノード同期のテスト（副作用を含む）。"""

    @pytest.fixture
    def exit_node(self) -> NodeDefinition:
        return NodeDefinition(
            name="exit.success.done",
            module="nodes.exit.success.done",
            function="done",
            description="正常終了",
            is_exit=True,
        )

    @pytest.fixture
    def graph_with_exit(self, exit_node: NodeDefinition) -> TransitionGraph:
        return TransitionGraph(
            nodes=(exit_node,),
            transitions={},
            start="start",
        )

    def test_generates_skeleton_for_missing_exit_node(
        self,
        tmp_path: Path,
        graph_with_exit: TransitionGraph,
    ) -> None:
        """未実装の終端ノードにスケルトンを生成する。"""
        result = sync_exit_nodes(graph_with_exit, tmp_path)

        assert isinstance(result, SyncResult)
        assert len(result.generated) == 1
        assert (tmp_path / "src/nodes/exit/success/done.py").exists()

    def test_skips_existing_exit_node(
        self,
        tmp_path: Path,
        graph_with_exit: TransitionGraph,
    ) -> None:
        """既存の終端ノードファイルはスキップする。"""
        # 既存ファイルを作成
        file_path = tmp_path / "src/nodes/exit/success/done.py"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("# existing code")

        result = sync_exit_nodes(graph_with_exit, tmp_path)

        assert len(result.skipped) == 1
        assert len(result.generated) == 0
        # 既存コードが上書きされていない
        assert file_path.read_text() == "# existing code"

    def test_creates_init_files(
        self,
        tmp_path: Path,
        graph_with_exit: TransitionGraph,
    ) -> None:
        """__init__.py を各階層に生成する。"""
        sync_exit_nodes(graph_with_exit, tmp_path)

        assert (tmp_path / "src/nodes/__init__.py").exists()
        assert (tmp_path / "src/nodes/exit/__init__.py").exists()
        assert (tmp_path / "src/nodes/exit/success/__init__.py").exists()

    def test_returns_immutable_result(
        self,
        tmp_path: Path,
        graph_with_exit: TransitionGraph,
    ) -> None:
        """戻り値は不変（frozen dataclass）。"""
        result = sync_exit_nodes(graph_with_exit, tmp_path)

        with pytest.raises((TypeError, AttributeError)):
            result.generated = ()  # type: ignore
```

### Phase 2: Green（最小実装）

#### 2-1. 命名規則関数（純粋関数）

```python
# railway/core/dag/codegen.py

def _exit_path_to_contract_name(exit_path: str) -> str:
    """終端ノードパスから Contract クラス名を生成（純粋関数）。

    Args:
        exit_path: "exit.success.done" 形式のパス

    Returns:
        "SuccessDoneResult" 形式のクラス名

    Examples:
        >>> _exit_path_to_contract_name("exit.success.done")
        'SuccessDoneResult'
        >>> _exit_path_to_contract_name("exit.failure.ssh.handshake")
        'FailureSshHandshakeResult'
    """
    # "exit." を除去し、各パートを PascalCase に変換
    parts = exit_path.replace("exit.", "", 1).split(".")
    pascal_parts = [part.capitalize() for part in parts]
    return "".join(pascal_parts) + "Result"


def _exit_path_to_exit_state(exit_path: str) -> str:
    """終端ノードパスから exit_state を生成（純粋関数）。

    Args:
        exit_path: "exit.success.done" 形式のパス

    Returns:
        "success.done" 形式の exit_state
    """
    return exit_path.replace("exit.", "", 1)
```

#### 2-2. スケルトン生成関数（純粋関数）

```python
# railway/core/dag/codegen.py

def generate_exit_node_skeleton(node: NodeDefinition) -> str:
    """終端ノードのスケルトンコードを生成（純粋関数）。

    Args:
        node: 終端ノード定義

    Returns:
        生成された Python コード文字列

    Note:
        生成されたコードは構文的に正しく、型チェックを通過する。
        開発者は TODO コメントの部分を実装するだけでよい。

        ctx の型は ExitContract としている。これは：
        - Any より型安全
        - 開発者が具体的な型に変更可能
        - IDE 補完が効く
    """
    contract_name = _exit_path_to_contract_name(node.name)
    exit_state = _exit_path_to_exit_state(node.name)
    function_name = node.function

    return f'''"""終端ノード: {node.description}

Auto-generated by `railway sync transition`.
"""
from railway import ExitContract, node


class {contract_name}(ExitContract):
    """{node.description}の結果。

    TODO: カスタムフィールドを追加してください。
    例:
        processed_count: int
        summary: str
    """
    exit_state: str = "{exit_state}"


@node(name="{node.name}")
def {function_name}(ctx: ExitContract) -> {contract_name}:
    """{node.description}

    Args:
        ctx: 直前のノードからのコンテキスト

    Returns:
        {contract_name}: 終了結果

    TODO: 実装してください。
    """
    return {contract_name}()
'''
```

#### 2-3. 同期結果型（イミュータブル）

```python
# railway/cli/sync.py

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SyncResult:
    """終端ノード同期の結果（イミュータブル）。

    Attributes:
        generated: 生成されたファイルパス
        skipped: スキップされたファイルパス（既存）
        warnings: 警告メッセージ

    Note:
        dataclass を採用した理由:
        - 内部処理用でユーザーに直接公開されない
        - シリアライズ不要
        - ValidationResult 等の既存内部型と一貫性がある
        - BaseModel より軽量
    """
    generated: tuple[Path, ...]
    skipped: tuple[Path, ...]
    warnings: tuple[str, ...] = ()
```

#### 2-4. 同期関数（副作用あり）

```python
# railway/cli/sync.py

def sync_exit_nodes(graph: TransitionGraph, project_root: Path) -> SyncResult:
    """未実装の終端ノードにスケルトンを生成（副作用あり）。

    Args:
        graph: 遷移グラフ
        project_root: プロジェクトルート

    Returns:
        SyncResult: 同期結果

    Note:
        この関数は以下の副作用を持つ：
        - ファイル書き込み
        - ディレクトリ作成
    """
    generated: list[Path] = []
    skipped: list[Path] = []

    for node_def in graph.nodes:
        if not node_def.is_exit:
            continue

        file_path = _calculate_file_path(node_def, project_root)

        if file_path.exists():
            skipped.append(file_path)
            continue

        # 純粋関数でコード生成
        code = generate_exit_node_skeleton(node_def)

        # 副作用: ファイル書き込み
        _write_skeleton_file(file_path, code)
        generated.append(file_path)

    return SyncResult(
        generated=tuple(generated),
        skipped=tuple(skipped),
    )


def _calculate_file_path(node: NodeDefinition, project_root: Path) -> Path:
    """ノード定義からファイルパスを計算（純粋関数）。"""
    module_path = node.module.replace(".", "/") + ".py"
    return project_root / "src" / module_path


def _write_skeleton_file(file_path: Path, content: str) -> None:
    """スケルトンファイルを書き込み（副作用あり）。"""
    _ensure_package_directory(file_path.parent)
    file_path.write_text(content)


def _ensure_package_directory(directory: Path) -> None:
    """ディレクトリを作成し、__init__.py も生成する（副作用あり）。

    Note:
        src ディレクトリ自体には __init__.py を作成しない。
        src/nodes/ 以下の階層にのみ作成する。
    """
    directory.mkdir(parents=True, exist_ok=True)

    # src ディレクトリまでの各階層に __init__.py を作成
    # ただし src 自体には作成しない
    current = directory
    while current.name and current.name != "src":
        init_file = current / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Auto-generated package."""\n')
        current = current.parent
```

### Phase 3: Refactor

- `--force` オプションで上書き生成
- 生成ファイル一覧の表示フォーマット改善
- codegen モジュールのエクスポート整理

---

## 修正ファイル

| ファイル | 変更内容 |
|----------|----------|
| `railway/core/dag/codegen.py` | `generate_exit_node_skeleton()` 等を追加 |
| `railway/cli/sync.py` | `SyncResult` 型、`sync_exit_nodes()` を追加 |
| `tests/unit/core/dag/test_codegen_exit_skeleton.py` | 新規テストファイル |
| `tests/unit/cli/test_sync_exit_nodes.py` | 新規テストファイル |

---

## 生成されるコード例

**YAML 定義**:
```yaml
nodes:
  exit:
    success:
      done:
        description: "正常終了"
    failure:
      timeout:
        description: "タイムアウト"
```

**生成コード** (`src/nodes/exit/success/done.py`):
```python
"""終端ノード: 正常終了

Auto-generated by `railway sync transition`.
"""
from railway import ExitContract, node


class SuccessDoneResult(ExitContract):
    """正常終了の結果。

    TODO: カスタムフィールドを追加してください。
    例:
        processed_count: int
        summary: str
    """
    exit_state: str = "success.done"


@node(name="exit.success.done")
def done(ctx: ExitContract) -> SuccessDoneResult:
    """正常終了

    Args:
        ctx: 直前のノードからのコンテキスト

    Returns:
        SuccessDoneResult: 終了結果

    TODO: 実装してください。
    """
    return SuccessDoneResult()
```

**生成されるディレクトリ構造**:
```
src/
└── nodes/
    ├── __init__.py  # 自動生成
    └── exit/
        ├── __init__.py  # 自動生成
        ├── success/
        │   ├── __init__.py  # 自動生成
        │   └── done.py
        └── failure/
            ├── __init__.py  # 自動生成
            └── timeout.py
```

---

## 受け入れ条件

### 機能
- [ ] 未実装の終端ノードに対してスケルトンが生成される
- [ ] 既存ファイルは上書きされない（スキップ）
- [ ] 生成されたコードは構文的に正しい（compile テスト）
- [ ] 生成されたコードは型安全（`ctx: ExitContract`）
- [ ] `__init__.py` が自動生成される

### 命名規則
- [ ] `exit.success.done` → `SuccessDoneResult` クラス
- [ ] 深いネスト（`exit.failure.ssh.handshake`）にも対応

### TDD・関数型
- [ ] Red → Green → Refactor フェーズに従って実装
- [ ] 純粋関数のユニットテスト（パラメタライズ）
- [ ] 副作用を含む関数は分離してテスト
- [ ] `SyncResult` はイミュータブル（`frozen=True`）
- [ ] 全テスト通過

---

*開発者体験向上のための基盤機能*
