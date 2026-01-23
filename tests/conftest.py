"""Pytest configuration and fixtures."""
import os
import sys
from pathlib import Path

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


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
