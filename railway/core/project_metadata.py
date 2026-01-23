"""プロジェクトメタデータの定義と操作。

関数型パラダイム:
- データモデルはイミュータブル (frozen=True)
- パース/シリアライズは純粋関数
- IO操作は専用関数で分離
"""
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict
import yaml


class RailwayInfo(BaseModel):
    """Railway framework information (immutable)."""
    model_config = ConfigDict(frozen=True)

    version: str
    created_at: datetime
    updated_at: datetime


class ProjectInfo(BaseModel):
    """Project information (immutable)."""
    model_config = ConfigDict(frozen=True)

    name: str


class CompatibilityInfo(BaseModel):
    """Version compatibility information (immutable)."""
    model_config = ConfigDict(frozen=True)

    min_version: str
    max_version: Optional[str] = None


class ProjectMetadata(BaseModel):
    """Complete project metadata (immutable)."""
    model_config = ConfigDict(frozen=True)

    railway: RailwayInfo
    project: ProjectInfo
    compatibility: CompatibilityInfo


# ============================================================
# 純粋関数: パース/シリアライズ（副作用なし）
# ============================================================

def parse_metadata(yaml_content: str) -> ProjectMetadata:
    """YAML文字列からProjectMetadataを生成する純粋関数。

    Args:
        yaml_content: YAML形式の文字列

    Returns:
        パースされたProjectMetadata

    Raises:
        ValueError: パース失敗時
    """
    data = yaml.safe_load(yaml_content)
    return ProjectMetadata.model_validate(data)


def serialize_metadata(metadata: ProjectMetadata) -> str:
    """ProjectMetadataをYAML文字列に変換する純粋関数。

    Args:
        metadata: シリアライズ対象

    Returns:
        YAML形式の文字列（ヘッダーコメント付き）
    """
    header = (
        "# Railway Framework Project Configuration\n"
        "# This file is auto-generated. Do not edit manually.\n\n"
    )
    body = yaml.dump(
        metadata.model_dump(mode="json"),
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    return header + body


def create_metadata(
    project_name: str,
    version: str,
    now: Optional[datetime] = None,
) -> ProjectMetadata:
    """新規プロジェクト用のメタデータを生成する純粋関数。

    Args:
        project_name: プロジェクト名
        version: railway-framework バージョン
        now: 現在時刻（テスト用にオプショナル）

    Returns:
        新規ProjectMetadata
    """
    timestamp = now or datetime.now().astimezone()
    return ProjectMetadata(
        railway=RailwayInfo(
            version=version,
            created_at=timestamp,
            updated_at=timestamp,
        ),
        project=ProjectInfo(name=project_name),
        compatibility=CompatibilityInfo(
            min_version=version,
            max_version=None,
        ),
    )


def update_metadata_version(
    metadata: ProjectMetadata,
    new_version: str,
    now: Optional[datetime] = None,
) -> ProjectMetadata:
    """メタデータのバージョンを更新した新しいインスタンスを返す純粋関数。

    Args:
        metadata: 元のメタデータ
        new_version: 新しいバージョン
        now: 現在時刻（テスト用にオプショナル）

    Returns:
        更新されたProjectMetadata（元のインスタンスは変更されない）
    """
    timestamp = now or datetime.now().astimezone()
    return ProjectMetadata(
        railway=RailwayInfo(
            version=new_version,
            created_at=metadata.railway.created_at,
            updated_at=timestamp,
        ),
        project=metadata.project,
        compatibility=CompatibilityInfo(
            min_version=new_version,
            max_version=metadata.compatibility.max_version,
        ),
    )


# ============================================================
# IO関数: ファイル操作（副作用あり、分離）
# ============================================================

def get_metadata_path(project_path: Path) -> Path:
    """メタデータファイルのパスを取得する。"""
    return project_path / ".railway" / "project.yaml"


def load_metadata(project_path: Path) -> Optional[ProjectMetadata]:
    """プロジェクトからメタデータを読み込む。

    Args:
        project_path: プロジェクトルートパス

    Returns:
        ProjectMetadata、またはファイルが存在しない場合はNone

    Raises:
        ValueError: ファイルは存在するがパース失敗時
    """
    metadata_path = get_metadata_path(project_path)
    if not metadata_path.exists():
        return None

    content = metadata_path.read_text(encoding="utf-8")
    return parse_metadata(content)


def save_metadata(project_path: Path, metadata: ProjectMetadata) -> Path:
    """メタデータをプロジェクトに保存する。

    Args:
        project_path: プロジェクトルートパス
        metadata: 保存するメタデータ

    Returns:
        保存先のパス
    """
    railway_dir = project_path / ".railway"
    railway_dir.mkdir(exist_ok=True)

    metadata_path = get_metadata_path(project_path)
    content = serialize_metadata(metadata)
    metadata_path.write_text(content, encoding="utf-8")

    return metadata_path
