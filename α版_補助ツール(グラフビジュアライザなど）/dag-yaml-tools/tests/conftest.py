"""Pytest fixtures for DAG YAML Tools tests."""

import pytest
from pathlib import Path


@pytest.fixture
def sample_yaml_path() -> Path:
    """Return path to sample YAML file."""
    return Path(__file__).parent.parent / "examples" / "sample.yaml"


@pytest.fixture
def valid_yaml_content() -> str:
    """Return valid YAML content for testing."""
    return """
start: start_node

nodes:
  start_node:
    description: "開始ノード"
  process_a:
  exit:
    success:
    failure:

transitions:
  start_node:
    success: process_a
    failure: exit.failure
  process_a:
    done: exit.success
"""


@pytest.fixture
def invalid_cycle_yaml_content() -> str:
    """Return YAML content with a cycle."""
    return """
start: a

nodes:
  a:
  b:
  c:

transitions:
  a:
    next: b
  b:
    next: c
  c:
    next: a
"""


@pytest.fixture
def invalid_undefined_yaml_content() -> str:
    """Return YAML content with undefined node reference."""
    return """
start: start

nodes:
  start:
  exit:

transitions:
  start:
    success: undefined_node
"""
