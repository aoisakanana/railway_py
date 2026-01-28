"""Pytest configuration and fixtures."""
import os
import sys
from pathlib import Path

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# DAG workflow test fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "transition_graphs"


@pytest.fixture
def exit_node_fixtures() -> Path:
    """終端ノードテスト用フィクスチャディレクトリ。

    用途:
    - Issue #23-#30 の TDD テスト
    - 終端ノード（nodes.exit 配下）の各種パターン
    """
    return FIXTURES_DIR / "exit_node"


@pytest.fixture
def invalid_fixtures() -> Path:
    """無効な YAML テスト用フィクスチャディレクトリ。

    用途:
    - バリデータのエラーケーステスト
    - パーサーの異常系テスト
    """
    return FIXTURES_DIR / "invalid"


def load_fixture(fixture_dir: Path, name: str) -> Path:
    """フィクスチャファイルのパスを取得（純粋関数）。

    Args:
        fixture_dir: フィクスチャディレクトリ
        name: ファイル名

    Returns:
        フィクスチャファイルのパス

    Raises:
        FileNotFoundError: ファイルが存在しない場合
    """
    path = fixture_dir / name
    if not path.exists():
        raise FileNotFoundError(f"Fixture not found: {path}")
    return path


@pytest.fixture
def simple_yaml() -> Path:
    """最小構成YAML（1ノード、2終了）

    用途:
    - パーサーの基本動作確認
    - バリデータの正常系テスト
    - コード生成器の最小構成テスト
    """
    return FIXTURES_DIR / "simple_20250125000000.yml"


@pytest.fixture
def branching_yaml() -> Path:
    """分岐テストYAML（5ノード、3分岐→合流）

    用途:
    - 条件分岐のパース・検証
    - 合流点の到達可能性テスト
    - 複数パスのコード生成テスト
    """
    return FIXTURES_DIR / "branching_20250125000000.yml"


@pytest.fixture
def invalid_yaml_missing_start(tmp_path: Path) -> Path:
    """開始ノードが未定義のYAML（バリデータエラーテスト用）"""
    content = '''
version: "1.0"
entrypoint: invalid
description: ""
nodes:
  a:
    module: nodes.a
    function: func_a
    description: ""
exits: {}
start: nonexistent
transitions: {}
'''
    yaml_path = tmp_path / "invalid_start.yml"
    yaml_path.write_text(content)
    return yaml_path


@pytest.fixture
def invalid_yaml_orphan_node(tmp_path: Path) -> Path:
    """到達不能ノードを含むYAML（バリデータ警告テスト用）"""
    content = '''
version: "1.0"
entrypoint: orphan
description: ""
nodes:
  a:
    module: nodes.a
    function: func_a
    description: ""
  orphan:
    module: nodes.orphan
    function: orphan_func
    description: "到達不能ノード"
exits:
  done:
    code: 0
    description: ""
start: a
transitions:
  a:
    success::done: exit::done
'''
    yaml_path = tmp_path / "orphan.yml"
    yaml_path.write_text(content)
    return yaml_path


@pytest.fixture
def invalid_yaml_cycle(tmp_path: Path) -> Path:
    """循環参照を含むYAML（バリデータエラーテスト用）"""
    content = '''
version: "1.0"
entrypoint: cycle
description: ""
nodes:
  a:
    module: nodes.a
    function: func_a
    description: ""
  b:
    module: nodes.b
    function: func_b
    description: ""
exits:
  done:
    code: 0
    description: ""
start: a
transitions:
  a:
    success::done: b
  b:
    success::done: a
'''
    yaml_path = tmp_path / "cycle.yml"
    yaml_path.write_text(content)
    return yaml_path


@pytest.fixture(autouse=True)
def preserve_cwd():
    """各テストの前後でcwdを保護する。

    テストがos.chdir()を使用して一時ディレクトリに移動し、
    その後ディレクトリが削除された場合でも、後続のテストが
    影響を受けないようにする。

    このfixtureは全テストに自動適用される（autouse=True）。
    """
    original_cwd = os.getcwd()
    try:
        yield
    finally:
        try:
            os.chdir(original_cwd)
        except FileNotFoundError:
            # テストがcwdを削除した場合はプロジェクトルートに戻る
            os.chdir(project_root)
