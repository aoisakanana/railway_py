"""Tests for find_latest_yaml file matching (Issue 29-01)."""
from __future__ import annotations

from pathlib import Path

from railway.cli.sync import find_latest_yaml


class TestFindLatestYaml:
    """find_latest_yaml のファイル名マッチテスト。"""

    def test_exact_match(self, tmp_path: Path) -> None:
        """正確なエントリ名にマッチすること。"""
        (tmp_path / "qsol_20260101000000.yml").touch()
        result = find_latest_yaml(tmp_path, "qsol")
        assert result is not None
        assert result.name == "qsol_20260101000000.yml"

    def test_prefix_mismatch_excluded(self, tmp_path: Path) -> None:
        """プレフィックス部分一致を除外すること。"""
        (tmp_path / "qsol_20260101000000.yml").touch()
        (tmp_path / "qsol_hoge_20260101000000.yml").touch()
        result = find_latest_yaml(tmp_path, "qsol")
        assert result is not None
        assert result.name == "qsol_20260101000000.yml"

    def test_underscore_entry_name(self, tmp_path: Path) -> None:
        """アンダースコア含みのエントリ名に正確マッチ。"""
        (tmp_path / "qsol_hoge_20260101000000.yml").touch()
        (tmp_path / "qsol_20260101000000.yml").touch()
        result = find_latest_yaml(tmp_path, "qsol_hoge")
        assert result is not None
        assert result.name == "qsol_hoge_20260101000000.yml"

    def test_latest_timestamp_selected(self, tmp_path: Path) -> None:
        """最新タイムスタンプが選択されること。"""
        (tmp_path / "my_workflow_20250101000000.yml").touch()
        (tmp_path / "my_workflow_20250201000000.yml").touch()
        (tmp_path / "my_workflow_20250301000000.yml").touch()
        result = find_latest_yaml(tmp_path, "my_workflow")
        assert result is not None
        assert result.name == "my_workflow_20250301000000.yml"

    def test_no_match_returns_none(self, tmp_path: Path) -> None:
        """マッチなしで None を返すこと。"""
        (tmp_path / "other_workflow_20260101000000.yml").touch()
        result = find_latest_yaml(tmp_path, "my_workflow")
        assert result is None

    def test_empty_directory(self, tmp_path: Path) -> None:
        """空ディレクトリで None を返すこと。"""
        result = find_latest_yaml(tmp_path, "my_workflow")
        assert result is None

    def test_non_yml_files_ignored(self, tmp_path: Path) -> None:
        """非 YML ファイルは無視されること。"""
        (tmp_path / "qsol_20260101000000.txt").touch()
        (tmp_path / "qsol_20260101000000.yaml").touch()
        result = find_latest_yaml(tmp_path, "qsol")
        assert result is None

    def test_numeric_ordering(self, tmp_path: Path) -> None:
        """タイムスタンプは数値順でソートされること。"""
        (tmp_path / "wf_9.yml").touch()
        (tmp_path / "wf_10.yml").touch()
        result = find_latest_yaml(tmp_path, "wf")
        assert result is not None
        assert result.name == "wf_10.yml"

    def test_pure_function_no_side_effects(self, tmp_path: Path) -> None:
        """純粋関数: 同じ入力に同じ出力。"""
        (tmp_path / "wf_20260101000000.yml").touch()
        r1 = find_latest_yaml(tmp_path, "wf")
        r2 = find_latest_yaml(tmp_path, "wf")
        assert r1 == r2

    def test_similar_prefix_not_matched(self, tmp_path: Path) -> None:
        """類似プレフィックスが誤ってマッチしないこと。"""
        # qsol_hoge_20260101.yml は "qsol" にマッチしてはいけない
        (tmp_path / "qsol_hoge_20260101000000.yml").touch()
        result = find_latest_yaml(tmp_path, "qsol")
        assert result is None

    def test_entry_name_with_multiple_underscores(self, tmp_path: Path) -> None:
        """複数アンダースコアを含むエントリ名の正確マッチ。"""
        (tmp_path / "my_long_workflow_20260101000000.yml").touch()
        (tmp_path / "my_long_20260101000000.yml").touch()
        result = find_latest_yaml(tmp_path, "my_long_workflow")
        assert result is not None
        assert result.name == "my_long_workflow_20260101000000.yml"

    def test_non_numeric_suffix_ignored(self, tmp_path: Path) -> None:
        """数値でないサフィックスは無視されること。"""
        (tmp_path / "wf_abc.yml").touch()
        result = find_latest_yaml(tmp_path, "wf")
        assert result is None
