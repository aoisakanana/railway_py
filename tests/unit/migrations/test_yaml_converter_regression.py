"""回帰テスト: --convert オプションのファイル破損バグ (v0.13.10rc3)。

バグ報告の再現ケースをテスト化。
"""

import copy
from pathlib import Path

import pytest
import yaml

from railway.core.dag.schema import validate_yaml_schema
from railway.migrations.yaml_converter import convert_yaml_structure

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


class TestRegressionNestedExitsConversion:
    """バグ報告の再現ケース: ネスト形式 exits の変換。"""

    def test_bug_report_exact_input(self) -> None:
        """バグ報告と同一の入力 YAML を正しく変換する。"""
        yaml_data = {
            "version": "1.0",
            "entrypoint": "convert_test",
            "description": "変換テスト用ワークフロー",
            "start": "step1",
            "nodes": {
                "step1": {
                    "description": "ステップ1",
                    "transitions": {
                        "success::done": "step2",
                        "failure::error": "exit.failure.error",
                    },
                },
                "step2": {
                    "description": "ステップ2",
                    "transitions": {
                        "success::done": "exit.success.done",
                        "failure::error": "exit.failure.error",
                    },
                },
            },
            "exits": {
                "success": {
                    "done": {
                        "description": "正常終了",
                        "exit_code": 0,
                    },
                },
                "failure": {
                    "error": {
                        "description": "エラー終了",
                        "exit_code": 1,
                    },
                },
            },
        }

        result = convert_yaml_structure(yaml_data)

        # 変換が成功する
        assert result.success is True, f"変換失敗: {result.error}"

        data = result.data

        # exits セクションが削除されている
        assert "exits" not in data

        # nodes.exit が正しい構造
        assert data["nodes"]["exit"] == {
            "success": {"done": {"description": "正常終了"}},
            "failure": {"error": {"description": "エラー終了"}},
        }

        # トップレベル transitions が存在する
        assert "transitions" in data
        assert data["transitions"]["step1"]["success::done"] == "step2"
        assert data["transitions"]["step1"]["failure::error"] == "exit.failure.error"
        assert data["transitions"]["step2"]["success::done"] == "exit.success.done"

        # nodes 内の transitions が削除されている
        assert "transitions" not in data["nodes"]["step1"]
        assert "transitions" not in data["nodes"]["step2"]

    def test_converted_yaml_passes_schema_validation(self) -> None:
        """変換結果がスキーマ検証を通過する。"""
        yaml_data = {
            "version": "1.0",
            "entrypoint": "convert_test",
            "description": "変換テスト用ワークフロー",
            "start": "step1",
            "nodes": {
                "step1": {
                    "description": "ステップ1",
                    "transitions": {
                        "success::done": "exit.success.done",
                    },
                },
            },
            "exits": {
                "success": {
                    "done": {"description": "正常終了", "exit_code": 0},
                },
            },
        }

        result = convert_yaml_structure(yaml_data)
        assert result.success is True

        validation = validate_yaml_schema(result.data)
        assert validation.is_valid, f"スキーマ検証失敗: {validation.errors}"

    def test_original_yaml_not_modified(self) -> None:
        """変換関数が元の dict を変更しないことを確認（純粋性テスト）。"""
        yaml_data = {
            "version": "1.0",
            "entrypoint": "test",
            "start": "step1",
            "nodes": {
                "step1": {
                    "description": "test",
                    "transitions": {"success::done": "exit.success.done"},
                },
            },
            "exits": {
                "success": {"done": {"description": "OK", "exit_code": 0}},
            },
        }

        original = copy.deepcopy(yaml_data)
        convert_yaml_structure(yaml_data)

        assert yaml_data == original, "元の dict が変更された"

    def test_idempotent_conversion(self) -> None:
        """変換済みの結果を再度変換しても変化しない（冪等性テスト）。"""
        yaml_data = {
            "version": "1.0",
            "entrypoint": "test",
            "start": "step1",
            "nodes": {
                "step1": {
                    "description": "test",
                    "transitions": {"success::done": "exit.success.done"},
                },
            },
            "exits": {
                "success": {"done": {"description": "OK", "exit_code": 0}},
            },
        }

        # 1回目の変換
        result1 = convert_yaml_structure(yaml_data)
        assert result1.success is True

        # 2回目の変換（exits がないのでそのまま返る）
        result2 = convert_yaml_structure(result1.data)
        assert result2.success is True
        assert result2.data == result1.data


class TestRegressionLegacyFlatConversion:
    """回帰テスト: レガシーフラット形式の変換が壊れていないこと。"""

    def test_legacy_flat_still_works(self) -> None:
        """v0.11.x レガシー形式が引き続き変換できる。"""
        yaml_data = {
            "version": "1.0",
            "entrypoint": "test",
            "start": "step1",
            "nodes": {"step1": {"description": "test"}},
            "transitions": {
                "step1": {"success::done": "exit::green_success"},
            },
            "exits": {
                "green_success": {"code": 0, "description": "正常終了"},
                "red_timeout": {"code": 1, "description": "タイムアウト"},
            },
        }

        result = convert_yaml_structure(yaml_data)

        assert result.success is True
        assert "exits" not in result.data
        assert "exit" in result.data["nodes"]
        assert "success" in result.data["nodes"]["exit"]

    def test_legacy_flat_original_not_modified(self) -> None:
        """レガシーフラット形式でも元の dict が変更されない。"""
        yaml_data = {
            "version": "1.0",
            "entrypoint": "test",
            "start": "step1",
            "nodes": {"step1": {"description": "test"}},
            "transitions": {
                "step1": {"success::done": "exit::green_success"},
            },
            "exits": {
                "green_success": {"code": 0, "description": "正常終了"},
            },
        }
        original = copy.deepcopy(yaml_data)
        convert_yaml_structure(yaml_data)

        assert yaml_data == original, "元の dict が変更された"


class TestConvertFromFixtureFiles:
    """フィクスチャファイルからの変換テスト。"""

    def test_convert_nested_exits_fixture(self) -> None:
        """フィクスチャファイルからネスト形式を変換する。"""
        fixture_path = FIXTURES_DIR / "convert_test_nested_exits.yml"
        if not fixture_path.exists():
            pytest.skip("フィクスチャファイルが存在しない")

        data = yaml.safe_load(fixture_path.read_text())

        result = convert_yaml_structure(data)
        assert result.success is True

        validation = validate_yaml_schema(result.data)
        assert validation.is_valid, f"スキーマ検証失敗: {validation.errors}"

    def test_convert_legacy_flat_fixture(self) -> None:
        """フィクスチャファイルからレガシーフラット形式を変換する。"""
        fixture_path = FIXTURES_DIR / "convert_test_legacy_flat.yml"
        if not fixture_path.exists():
            pytest.skip("フィクスチャファイルが存在しない")

        data = yaml.safe_load(fixture_path.read_text())

        result = convert_yaml_structure(data)
        assert result.success is True

        validation = validate_yaml_schema(result.data)
        assert validation.is_valid, f"スキーマ検証失敗: {validation.errors}"

    def test_already_new_format_unchanged(self) -> None:
        """新形式のフィクスチャは変換不要で返る。"""
        fixture_path = FIXTURES_DIR / "convert_test_already_new_format.yml"
        if not fixture_path.exists():
            pytest.skip("フィクスチャファイルが存在しない")

        data = yaml.safe_load(fixture_path.read_text())

        result = convert_yaml_structure(data)
        assert result.success is True
        assert result.data == data


class TestConvertEndToEnd:
    """E2E テスト: ファイル読み込み → 変換 → スキーマ検証の一連の流れ。"""

    def test_convert_from_file(self, tmp_path: Path) -> None:
        """YAML ファイルから読み込み、変換、書き込みの一連の流れ。"""
        yaml_content = {
            "version": "1.0",
            "entrypoint": "e2e_test",
            "start": "step1",
            "nodes": {
                "step1": {
                    "description": "ステップ1",
                    "transitions": {
                        "success::done": "exit.success.done",
                        "failure::error": "exit.failure.error",
                    },
                },
            },
            "exits": {
                "success": {
                    "done": {"description": "正常終了", "exit_code": 0},
                },
                "failure": {
                    "error": {"description": "エラー終了", "exit_code": 1},
                },
            },
        }

        yaml_path = tmp_path / "e2e_test_20260208150000.yml"
        yaml_path.write_text(
            yaml.safe_dump(yaml_content, allow_unicode=True, sort_keys=False)
        )

        # ファイル読み込み
        data = yaml.safe_load(yaml_path.read_text())

        # 変換
        result = convert_yaml_structure(data)
        assert result.success is True

        # スキーマ検証
        validation = validate_yaml_schema(result.data)
        assert validation.is_valid, f"スキーマ検証失敗: {validation.errors}"

        # ファイル書き込み
        new_content = yaml.safe_dump(
            result.data, allow_unicode=True, sort_keys=False
        )
        yaml_path.write_text(new_content)

        # 再読み込みで整合性確認
        reloaded = yaml.safe_load(yaml_path.read_text())
        assert reloaded["version"] == "1.0"
        assert "transitions" in reloaded
        assert "exit" in reloaded["nodes"]
        assert "exits" not in reloaded

    def test_convert_write_reload_roundtrip(self, tmp_path: Path) -> None:
        """変換 → 書き込み → 再読み込み → 再変換で冪等であること。"""
        yaml_content = {
            "version": "1.0",
            "entrypoint": "roundtrip",
            "start": "step1",
            "nodes": {
                "step1": {
                    "description": "ステップ1",
                    "transitions": {
                        "success::done": "exit.success.done",
                    },
                },
            },
            "exits": {
                "success": {
                    "done": {"description": "正常終了", "exit_code": 0},
                },
            },
        }

        yaml_path = tmp_path / "roundtrip_20260208150000.yml"
        yaml_path.write_text(
            yaml.safe_dump(yaml_content, allow_unicode=True, sort_keys=False)
        )

        # 1回目: 変換 → 書き込み
        data1 = yaml.safe_load(yaml_path.read_text())
        result1 = convert_yaml_structure(data1)
        assert result1.success is True
        yaml_path.write_text(
            yaml.safe_dump(result1.data, allow_unicode=True, sort_keys=False)
        )

        # 2回目: 再読み込み → 再変換（exits がないのでそのまま）
        data2 = yaml.safe_load(yaml_path.read_text())
        result2 = convert_yaml_structure(data2)
        assert result2.success is True
        assert result2.data == result1.data


class TestConvertCliIntegration:
    """CLI レベルの統合テスト: _convert_yaml_if_old_format の全フロー。"""

    def test_nested_exits_full_flow(self, tmp_path: Path) -> None:
        """ネスト形式 YAML の変換 → スキーマ検証 → 書き込みの全フロー。"""
        yaml_content = {
            "version": "1.0",
            "entrypoint": "cli_test",
            "start": "step1",
            "nodes": {
                "step1": {
                    "description": "ステップ1",
                    "transitions": {
                        "success::done": "exit.success.done",
                        "failure::error": "exit.failure.error",
                    },
                },
            },
            "exits": {
                "success": {
                    "done": {"description": "正常終了", "exit_code": 0},
                },
                "failure": {
                    "error": {"description": "エラー終了", "exit_code": 1},
                },
            },
        }

        yaml_path = tmp_path / "cli_test_20260208150000.yml"
        yaml_path.write_text(
            yaml.safe_dump(yaml_content, allow_unicode=True, sort_keys=False)
        )

        from railway.cli.sync import _convert_yaml_if_old_format

        result = _convert_yaml_if_old_format(yaml_path)

        assert result.converted is True

        # 書き込まれた内容を検証
        new_data = yaml.safe_load(yaml_path.read_text())
        assert "exits" not in new_data
        assert "exit" in new_data["nodes"]
        assert "transitions" in new_data
        assert "step1" in new_data["transitions"]

        # スキーマ検証もパスすること
        validation = validate_yaml_schema(new_data)
        assert validation.is_valid
