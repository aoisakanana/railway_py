"""ProjectMetadata のテスト。

TDD Red Phase: まずテストを書き、失敗を確認する。
"""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from railway.core.project_metadata import (
    ProjectMetadata,
    RailwayInfo,
    ProjectInfo,
    CompatibilityInfo,
    parse_metadata,
    serialize_metadata,
    create_metadata,
    update_metadata_version,
    load_metadata,
    save_metadata,
)


class TestProjectMetadataImmutability:
    """メタデータがイミュータブルであることを検証。"""

    def test_project_metadata_is_frozen(self):
        """ProjectMetadataは変更不可であること。"""
        metadata = create_metadata("test", "0.9.0")

        with pytest.raises(Exception):  # ValidationError or TypeError
            metadata.railway = RailwayInfo(
                version="1.0.0",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

    def test_railway_info_is_frozen(self):
        """RailwayInfoは変更不可であること。"""
        info = RailwayInfo(
            version="0.9.0",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with pytest.raises(Exception):
            info.version = "1.0.0"


class TestPureFunctions:
    """純粋関数のテスト（副作用なし、参照透過性）。"""

    def test_create_metadata_returns_valid_metadata(self):
        """create_metadataは有効なメタデータを返す。"""
        now = datetime(2026, 1, 23, 10, 30, 0, tzinfo=timezone.utc)

        metadata = create_metadata("my_project", "0.9.0", now=now)

        assert metadata.project.name == "my_project"
        assert metadata.railway.version == "0.9.0"
        assert metadata.railway.created_at == now
        assert metadata.railway.updated_at == now
        assert metadata.compatibility.min_version == "0.9.0"
        assert metadata.compatibility.max_version is None

    def test_create_metadata_is_referentially_transparent(self):
        """同じ引数で同じ結果を返す（参照透過性）。"""
        now = datetime(2026, 1, 23, 10, 30, 0, tzinfo=timezone.utc)

        result1 = create_metadata("test", "0.9.0", now=now)
        result2 = create_metadata("test", "0.9.0", now=now)

        assert result1 == result2

    def test_update_metadata_version_does_not_mutate_original(self):
        """update_metadata_versionは元のインスタンスを変更しない。"""
        original = create_metadata("test", "0.9.0")
        original_version = original.railway.version

        updated = update_metadata_version(original, "1.0.0")

        assert original.railway.version == original_version  # 変更なし
        assert updated.railway.version == "1.0.0"
        assert updated is not original

    def test_update_metadata_version_preserves_created_at(self):
        """update_metadata_versionはcreated_atを保持する。"""
        created = datetime(2025, 1, 1, tzinfo=timezone.utc)
        original = ProjectMetadata(
            railway=RailwayInfo(
                version="0.9.0",
                created_at=created,
                updated_at=created,
            ),
            project=ProjectInfo(name="test"),
            compatibility=CompatibilityInfo(min_version="0.9.0"),
        )

        updated = update_metadata_version(original, "1.0.0")

        assert updated.railway.created_at == created

    def test_serialize_then_parse_roundtrip(self):
        """シリアライズ→パースで元のデータを復元できる。"""
        original = create_metadata("my_project", "0.9.0")

        yaml_str = serialize_metadata(original)
        restored = parse_metadata(yaml_str)

        assert restored.project.name == original.project.name
        assert restored.railway.version == original.railway.version

    def test_serialize_includes_header_comment(self):
        """シリアライズ結果にヘッダーコメントが含まれる。"""
        metadata = create_metadata("test", "0.9.0")

        yaml_str = serialize_metadata(metadata)

        assert "# Railway Framework Project Configuration" in yaml_str
        assert "# This file is auto-generated" in yaml_str


class TestIOFunctions:
    """IO関数のテスト（副作用あり）。"""

    def test_save_creates_railway_directory(self, tmp_path: Path):
        """save_metadataは.railwayディレクトリを作成する。"""
        metadata = create_metadata("test", "0.9.0")

        save_metadata(tmp_path, metadata)

        assert (tmp_path / ".railway").is_dir()

    def test_save_creates_project_yaml(self, tmp_path: Path):
        """save_metadataはproject.yamlを作成する。"""
        metadata = create_metadata("test", "0.9.0")

        save_metadata(tmp_path, metadata)

        assert (tmp_path / ".railway" / "project.yaml").exists()

    def test_load_returns_none_for_missing_file(self, tmp_path: Path):
        """load_metadataはファイルがない場合Noneを返す。"""
        result = load_metadata(tmp_path)

        assert result is None

    def test_save_then_load_roundtrip(self, tmp_path: Path):
        """save→loadでデータを復元できる。"""
        original = create_metadata("my_project", "0.9.0")

        save_metadata(tmp_path, original)
        loaded = load_metadata(tmp_path)

        assert loaded is not None
        assert loaded.project.name == "my_project"
        assert loaded.railway.version == "0.9.0"

    def test_load_invalid_yaml_raises_error(self, tmp_path: Path):
        """不正なYAMLはエラーを発生させる。"""
        railway_dir = tmp_path / ".railway"
        railway_dir.mkdir()
        (railway_dir / "project.yaml").write_text("invalid: yaml: content:")

        with pytest.raises(Exception):
            load_metadata(tmp_path)
