"""Tests for README 掲載 YAML の検証 (v0.13.26 Issue 04, NEW-3).

README の完全形式 YAML（version + entrypoint を持つ遷移グラフ）が
スキーマ検証・グラフ検証を通ることを機械的に固定し、旧形式の陳腐化を防ぐ。
"""
import re
from pathlib import Path

import pytest

from railway.core.dag.parser import parse_transition_graph
from railway.core.dag.schema import validate_yaml_schema
from railway.core.dag.validator import validate_graph

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _extract_full_yaml_blocks(md_path: Path) -> list[str]:
    """markdown から完全形式（version + entrypoint）の yaml ブロックを抽出。"""
    text = md_path.read_text()
    blocks = re.findall(r"```yaml\s*\n(.*?)```", text, re.DOTALL)
    result = []
    for b in blocks:
        # 行末スペース（markdown 改行記法）を除去
        cleaned = "\n".join(line.rstrip() for line in b.splitlines())
        if "version:" in cleaned and "entrypoint:" in cleaned:
            result.append(cleaned)
    return result


@pytest.mark.parametrize("md_name", ["readme.md", "readme_linear.md"])
def test_readme_full_yaml_blocks_are_valid(md_name: str) -> None:
    """README の完全形式 YAML はすべてスキーマ・グラフ検証を通る。"""
    md_path = _REPO_ROOT / md_name
    if not md_path.exists():
        pytest.skip(f"{md_name} なし")
    blocks = _extract_full_yaml_blocks(md_path)
    for i, block in enumerate(blocks):
        import yaml as yaml_mod
        data = yaml_mod.safe_load(block)
        schema = validate_yaml_schema(data)
        assert schema.is_valid, (
            f"{md_name} の YAML ブロック {i} がスキーマ検証エラー: {schema.errors}"
        )
        graph = parse_transition_graph(block)
        result = validate_graph(graph)
        assert result.is_valid, (
            f"{md_name} の YAML ブロック {i} がグラフ検証エラー: "
            f"{[(e.code, e.message) for e in result.errors]}"
        )


def test_readme_has_no_legacy_exit_transition() -> None:
    """旧形式の遷移先 `exit::` が README に残っていない。"""
    text = (_REPO_ROOT / "readme.md").read_text()
    assert ": exit::" not in text, "旧形式の遷移先 exit:: が残存"
