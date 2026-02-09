"""変換+ロールバックのテスト（v0.13.10rc3）。"""

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from railway.cli.sync import ConvertFileResult
from railway.migrations.yaml_converter import ConversionResult


class TestConvertYamlRollback:
    """変換失敗時のロールバックテスト。"""

    def test_schema_validation_failure_preserves_original(
        self, tmp_path: Path
    ) -> None:
        """変換結果がスキーマ検証に失敗した場合、元の内容が保持される。"""
        yaml_path = tmp_path / "test.yml"
        original_data = {
            "version": "1.0",
            "entrypoint": "test",
            "exits": {"green": {"code": 0}},
        }
        original_content = yaml.safe_dump(original_data, allow_unicode=True)
        yaml_path.write_text(original_content)

        with patch(
            "railway.cli.sync.convert_yaml_structure"
        ) as mock_convert:
            mock_convert.return_value = ConversionResult.ok(
                {"version": "1.0"}  # transitions 等が欠落
            )

            from railway.cli.sync import _convert_yaml_if_old_format

            result = _convert_yaml_if_old_format(yaml_path)

        assert yaml_path.read_text() == original_content
        assert result.converted is False

    def test_conversion_failure_preserves_original(
        self, tmp_path: Path
    ) -> None:
        """ConversionResult.fail の場合、ファイルは変更されない。"""
        yaml_path = tmp_path / "test.yml"
        original_data = {
            "version": "1.0",
            "exits": {"something": "invalid"},
        }
        original_content = yaml.safe_dump(original_data, allow_unicode=True)
        yaml_path.write_text(original_content)

        with patch(
            "railway.cli.sync.convert_yaml_structure"
        ) as mock_convert:
            mock_convert.return_value = ConversionResult.fail("未知の形式")

            from railway.cli.sync import _convert_yaml_if_old_format

            result = _convert_yaml_if_old_format(yaml_path)

        assert yaml_path.read_text() == original_content
        assert result.converted is False

    def test_exception_restores_original(self, tmp_path: Path) -> None:
        """変換中に例外が発生した場合、元の内容が復元される。"""
        yaml_path = tmp_path / "test.yml"
        original_data = {
            "version": "1.0",
            "exits": {"green_success": {"code": 0}},
        }
        original_content = yaml.safe_dump(original_data, allow_unicode=True)
        yaml_path.write_text(original_content)

        with patch(
            "railway.cli.sync.convert_yaml_structure",
            side_effect=RuntimeError("unexpected error"),
        ):
            from railway.cli.sync import _convert_yaml_if_old_format

            result = _convert_yaml_if_old_format(yaml_path)

        assert yaml_path.read_text() == original_content
        assert result.converted is False

    def test_successful_conversion_writes_new_content(
        self, tmp_path: Path
    ) -> None:
        """変換成功かつスキーマ検証成功時はファイルが更新される。"""
        yaml_path = tmp_path / "test.yml"
        yaml_path.write_text(
            yaml.safe_dump(
                {
                    "version": "1.0",
                    "entrypoint": "test",
                    "start": "step1",
                    "nodes": {"step1": {"description": "test"}},
                    "transitions": {
                        "step1": {"success::done": "exit::green"},
                    },
                    "exits": {"green": {"code": 0, "description": "OK"}},
                }
            )
        )

        from railway.cli.sync import _convert_yaml_if_old_format

        result = _convert_yaml_if_old_format(yaml_path)

        assert result.converted is True
        new_data = yaml.safe_load(yaml_path.read_text())
        assert "exits" not in new_data
        assert "exit" in new_data.get("nodes", {})

    def test_warning_message_on_schema_validation_failure(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """スキーマ検証失敗時に警告メッセージが stderr に出力される。"""
        yaml_path = tmp_path / "test.yml"
        yaml_path.write_text(
            yaml.safe_dump(
                {
                    "version": "1.0",
                    "exits": {"green": {"code": 0}},
                }
            )
        )

        with patch(
            "railway.cli.sync.convert_yaml_structure"
        ) as mock_convert:
            mock_convert.return_value = ConversionResult.ok(
                {"version": "1.0"}  # 不完全
            )

            from railway.cli.sync import _convert_yaml_if_old_format

            _convert_yaml_if_old_format(yaml_path)

        captured = capsys.readouterr()
        assert "無効" in captured.err or "ロールバック" in captured.err

    def test_warning_message_on_exception(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """例外発生時にエラーメッセージが stderr に出力される。"""
        yaml_path = tmp_path / "test.yml"
        yaml_path.write_text(
            yaml.safe_dump(
                {
                    "version": "1.0",
                    "exits": {"green": {"code": 0}},
                }
            )
        )

        with patch(
            "railway.cli.sync.convert_yaml_structure",
            side_effect=RuntimeError("test error"),
        ):
            from railway.cli.sync import _convert_yaml_if_old_format

            _convert_yaml_if_old_format(yaml_path)

        captured = capsys.readouterr()
        assert "例外" in captured.err or "エラー" in captured.err

    def test_dry_run_does_not_modify_file(self, tmp_path: Path) -> None:
        """dry_run=True の場合、ファイルは変更されない。"""
        yaml_path = tmp_path / "test.yml"
        original_data = {
            "version": "1.0",
            "entrypoint": "test",
            "start": "step1",
            "nodes": {"step1": {"description": "test"}},
            "transitions": {"step1": {"success::done": "exit::green"}},
            "exits": {"green": {"code": 0, "description": "OK"}},
        }
        original_content = yaml.safe_dump(original_data, allow_unicode=True)
        yaml_path.write_text(original_content)

        from railway.cli.sync import _convert_yaml_if_old_format

        result = _convert_yaml_if_old_format(yaml_path, dry_run=True)

        assert result.converted is True
        assert yaml_path.read_text() == original_content

    def test_no_exits_with_valid_schema_shows_message(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """exits なし + スキーマ有効の場合「既に新形式」メッセージを表示。"""
        yaml_path = tmp_path / "test.yml"
        yaml_path.write_text(
            yaml.safe_dump(
                {
                    "version": "1.0",
                    "entrypoint": "test",
                    "start": "step1",
                    "nodes": {
                        "step1": {"description": "test"},
                        "exit": {
                            "success": {"done": {"description": "OK"}},
                        },
                    },
                    "transitions": {
                        "step1": {
                            "success::done": "exit.success.done",
                        },
                    },
                }
            )
        )

        from railway.cli.sync import _convert_yaml_if_old_format

        result = _convert_yaml_if_old_format(yaml_path)

        assert result.converted is False
        captured = capsys.readouterr()
        assert "既に新形式" in captured.out


class TestConvertFileResult:
    """ConvertFileResult のテスト（Issue 13-01）。"""

    def test_frozen(self) -> None:
        """イミュータブルであること。"""
        r = ConvertFileResult(converted=True, data={"key": "value"})
        with pytest.raises(Exception):
            r.converted = False  # type: ignore[misc]

    def test_default_data_is_none(self) -> None:
        """data のデフォルトは None。"""
        r = ConvertFileResult(converted=False)
        assert r.data is None

    def test_with_data(self) -> None:
        """data を指定できる。"""
        data = {"version": "1.0", "nodes": {}}
        r = ConvertFileResult(converted=True, data=data)
        assert r.converted is True
        assert r.data == data


class TestConvertYamlReturnsConvertFileResult:
    """_convert_yaml_if_old_format が ConvertFileResult を返すテスト（Issue 13-01）。"""

    def test_returns_convert_file_result_on_success(
        self, tmp_path: Path
    ) -> None:
        """変換成功時に ConvertFileResult(converted=True, data=...) を返す。"""
        yaml_path = tmp_path / "test.yml"
        yaml_path.write_text(
            yaml.safe_dump(
                {
                    "version": "1.0",
                    "entrypoint": "test",
                    "start": "step1",
                    "nodes": {"step1": {"description": "test"}},
                    "transitions": {
                        "step1": {"success::done": "exit::green"},
                    },
                    "exits": {"green": {"code": 0, "description": "OK"}},
                }
            )
        )

        from railway.cli.sync import _convert_yaml_if_old_format

        result = _convert_yaml_if_old_format(yaml_path)

        assert isinstance(result, ConvertFileResult)
        assert result.converted is True
        assert result.data is not None
        assert "exits" not in result.data

    def test_returns_convert_file_result_on_no_conversion(
        self, tmp_path: Path
    ) -> None:
        """変換不要時に ConvertFileResult(converted=False) を返す。"""
        yaml_path = tmp_path / "test.yml"
        yaml_path.write_text(
            yaml.safe_dump(
                {
                    "version": "1.0",
                    "entrypoint": "test",
                    "start": "step1",
                    "nodes": {
                        "step1": {"description": "test"},
                        "exit": {
                            "success": {"done": {"description": "OK"}},
                        },
                    },
                    "transitions": {
                        "step1": {
                            "success::done": "exit.success.done",
                        },
                    },
                }
            )
        )

        from railway.cli.sync import _convert_yaml_if_old_format

        result = _convert_yaml_if_old_format(yaml_path)

        assert isinstance(result, ConvertFileResult)
        assert result.converted is False

    def test_returns_convert_file_result_on_failure(
        self, tmp_path: Path
    ) -> None:
        """変換失敗時に ConvertFileResult(converted=False) を返す。"""
        yaml_path = tmp_path / "test.yml"
        yaml_path.write_text(
            yaml.safe_dump(
                {
                    "version": "1.0",
                    "exits": {"something": "invalid"},
                }
            )
        )

        with patch(
            "railway.cli.sync.convert_yaml_structure"
        ) as mock_convert:
            mock_convert.return_value = ConversionResult.fail("未知の形式")

            from railway.cli.sync import _convert_yaml_if_old_format

            result = _convert_yaml_if_old_format(yaml_path)

        assert isinstance(result, ConvertFileResult)
        assert result.converted is False
        assert result.data is None

    def test_dry_run_returns_data(self, tmp_path: Path) -> None:
        """dry_run 成功時に data を含む ConvertFileResult を返す。"""
        yaml_path = tmp_path / "test.yml"
        yaml_path.write_text(
            yaml.safe_dump(
                {
                    "version": "1.0",
                    "entrypoint": "test",
                    "start": "step1",
                    "nodes": {"step1": {"description": "test"}},
                    "transitions": {"step1": {"success::done": "exit::green"}},
                    "exits": {"green": {"code": 0, "description": "OK"}},
                }
            )
        )

        from railway.cli.sync import _convert_yaml_if_old_format

        result = _convert_yaml_if_old_format(yaml_path, dry_run=True)

        assert isinstance(result, ConvertFileResult)
        assert result.converted is True
        assert result.data is not None


class TestSyncEntryDryRunConvert:
    """_sync_entry の dry-run + convert テスト（Issue 13-02）。"""

    def test_dry_run_convert_does_not_modify_file(self, tmp_path: Path) -> None:
        """dry-run + convert でファイルが変更されないこと。"""
        # Setup: 旧形式 YAML
        graphs_dir = tmp_path / "transition_graphs"
        graphs_dir.mkdir()
        output_dir = tmp_path / "_railway" / "generated"
        output_dir.mkdir(parents=True)

        old_format_data = {
            "version": "1.0",
            "entrypoint": "myflow",
            "start": "step1",
            "nodes": {"step1": {"description": "test"}},
            "transitions": {
                "step1": {"success::done": "exit::green"},
            },
            "exits": {"green": {"code": 0, "description": "OK"}},
        }
        yaml_path = graphs_dir / "myflow_20260101.yml"
        original_content = yaml.safe_dump(old_format_data, allow_unicode=True)
        yaml_path.write_text(original_content)

        from railway.cli.sync import _sync_entry

        # dry-run + convert で実行
        _sync_entry(
            entry_name="myflow",
            graphs_dir=graphs_dir,
            output_dir=output_dir,
            dry_run=True,
            validate_only=False,
            convert=True,
        )

        # ファイルが変更されていないこと
        assert yaml_path.read_text() == original_content

    def test_dry_run_convert_still_generates_preview(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """dry-run + convert でプレビューが出力されること。"""
        graphs_dir = tmp_path / "transition_graphs"
        graphs_dir.mkdir()
        output_dir = tmp_path / "_railway" / "generated"
        output_dir.mkdir(parents=True)

        old_format_data = {
            "version": "1.0",
            "entrypoint": "myflow",
            "start": "step1",
            "nodes": {"step1": {"description": "test"}},
            "transitions": {
                "step1": {"success::done": "exit::green"},
            },
            "exits": {"green": {"code": 0, "description": "OK"}},
        }
        yaml_path = graphs_dir / "myflow_20260101.yml"
        yaml_path.write_text(yaml.safe_dump(old_format_data, allow_unicode=True))

        from railway.cli.sync import _sync_entry

        _sync_entry(
            entry_name="myflow",
            graphs_dir=graphs_dir,
            output_dir=output_dir,
            dry_run=True,
            validate_only=False,
            convert=True,
        )

        captured = capsys.readouterr()
        assert "プレビュー" in captured.out
