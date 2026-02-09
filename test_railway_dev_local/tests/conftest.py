"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path

# src/ を sys.path に追加（テストからのインポートを可能に）
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import pytest


@pytest.fixture
def sample_user_data() -> dict:
    """サンプルユーザーデータを提供するフィクスチャ"""
    return {
        "user_id": 1,
        "name": "Test User",
        "email": "test@example.com",
    }


@pytest.fixture
def empty_data() -> dict:
    """空のデータを提供するフィクスチャ"""
    return {}
