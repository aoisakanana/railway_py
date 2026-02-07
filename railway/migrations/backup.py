"""バックアップ機能。

関数型パラダイム:
- ロジック（マニフェスト生成）と IO（ファイル操作）を分離
- 結果はイミュータブルな Result 型で返す
"""
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

# バックアップ対象パターン（定数）
BACKUP_PATTERNS: tuple[str, ...] = (
    ".railway/project.yaml",
    "TUTORIAL.md",
    "pyproject.toml",
    ".gitignore",
    "config/*.yaml",
)


# ============================================================
# 型定義（イミュータブル）
# ============================================================

class BackupFile(BaseModel):
    """バックアップファイル情報（イミュータブル）。"""
    model_config = ConfigDict(frozen=True)

    path: str
    checksum: str
    size_bytes: int


class BackupManifest(BaseModel):
    """バックアップマニフェスト（イミュータブル）。"""
    model_config = ConfigDict(frozen=True)

    version: str
    created_at: datetime
    reason: str
    files: tuple[BackupFile, ...] = Field(default_factory=tuple)

    @property
    def total_size(self) -> int:
        """バックアップの合計サイズ。"""
        return sum(f.size_bytes for f in self.files)

    @property
    def file_count(self) -> int:
        """ファイル数。"""
        return len(self.files)


class BackupInfo(BaseModel):
    """バックアップ情報（イミュータブル）。"""
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    manifest: BackupManifest
    path: Path

    @property
    def version(self) -> str:
        return self.manifest.version

    @property
    def created_at(self) -> datetime:
        return self.manifest.created_at

    @property
    def reason(self) -> str:
        return self.manifest.reason

    @property
    def size_bytes(self) -> int:
        return self.manifest.total_size

    @property
    def name(self) -> str:
        return self.path.name


class RestoreResult(BaseModel):
    """復元操作結果（イミュータブル）。"""
    model_config = ConfigDict(frozen=True)

    success: bool
    restored_files: tuple[str, ...] = Field(default_factory=tuple)
    error: str | None = None


# ============================================================
# 純粋関数
# ============================================================

def compute_checksum(content: bytes) -> str:
    """コンテンツのチェックサムを計算する純粋関数。

    Args:
        content: チェックサム対象のバイト列

    Returns:
        "sha256:..." 形式のチェックサム
    """
    sha256 = hashlib.sha256(content)
    return f"sha256:{sha256.hexdigest()}"


def generate_backup_name(version: str, timestamp: datetime) -> str:
    """バックアップ名を生成する純粋関数。

    Args:
        version: バージョン
        timestamp: タイムスタンプ

    Returns:
        "{version}_{YYYYMMDD_HHMMSS}" 形式の名前
    """
    return f"{version}_{timestamp.strftime('%Y%m%d_%H%M%S')}"


def serialize_manifest(manifest: BackupManifest) -> str:
    """マニフェストをYAML文字列に変換する純粋関数。"""
    data = {
        "backup": {
            "version": manifest.version,
            "created_at": manifest.created_at.isoformat(),
            "reason": manifest.reason,
        },
        "files": [
            {
                "path": f.path,
                "checksum": f.checksum,
                "size_bytes": f.size_bytes,
            }
            for f in manifest.files
        ],
    }
    return yaml.dump(data, default_flow_style=False, allow_unicode=True)


def parse_manifest(yaml_content: str) -> BackupManifest:
    """YAML文字列からマニフェストをパースする純粋関数。"""
    data = yaml.safe_load(yaml_content)
    backup_data = data["backup"]
    files_data = data.get("files", [])

    files = tuple(
        BackupFile(
            path=f["path"],
            checksum=f["checksum"],
            size_bytes=f.get("size_bytes", 0),
        )
        for f in files_data
    )

    return BackupManifest(
        version=backup_data["version"],
        created_at=datetime.fromisoformat(backup_data["created_at"]),
        reason=backup_data["reason"],
        files=files,
    )


# ============================================================
# IO関数
# ============================================================

def collect_backup_files(
    project_path: Path,
    patterns: tuple[str, ...] = BACKUP_PATTERNS,
) -> list[tuple[Path, BackupFile]]:
    """バックアップ対象ファイルを収集する。"""
    files = []

    for pattern in patterns:
        for src in project_path.glob(pattern):
            if src.is_file():
                try:
                    content = src.read_bytes()
                    rel_path = src.relative_to(project_path)
                    files.append((
                        src,
                        BackupFile(
                            path=str(rel_path),
                            checksum=compute_checksum(content),
                            size_bytes=len(content),
                        ),
                    ))
                except (OSError, PermissionError):
                    continue

    return files


def create_backup(
    project_path: Path,
    version: str,
    reason: str = "Before update",
) -> Path:
    """バックアップを作成する。

    Args:
        project_path: プロジェクトルートパス
        version: バックアップ対象のバージョン
        reason: バックアップ理由

    Returns:
        バックアップディレクトリのパス
    """
    now = datetime.now().astimezone()
    backup_name = generate_backup_name(version, now)
    backup_path = project_path / ".railway" / "backups" / backup_name

    # ディレクトリ作成
    backup_path.mkdir(parents=True, exist_ok=True)

    # ファイル収集とコピー
    file_infos = collect_backup_files(project_path)
    backup_files: list[BackupFile] = []

    for src, file_info in file_infos:
        dst = backup_path / file_info.path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        backup_files.append(file_info)

    # マニフェスト作成
    manifest = BackupManifest(
        version=version,
        created_at=now,
        reason=reason,
        files=tuple(backup_files),
    )
    manifest_content = serialize_manifest(manifest)

    manifest_path = backup_path / "manifest.yaml"
    manifest_path.write_text(manifest_content, encoding="utf-8")

    return backup_path


def list_backups(project_path: Path) -> list[BackupInfo]:
    """利用可能なバックアップを一覧取得する。

    Args:
        project_path: プロジェクトルートパス

    Returns:
        作成日時の降順でソートされたBackupInfoのリスト
    """
    backup_dir = project_path / ".railway" / "backups"
    backups: list[BackupInfo] = []

    if not backup_dir.exists():
        return backups

    for backup_path in backup_dir.iterdir():
        manifest_path = backup_path / "manifest.yaml"
        if manifest_path.exists():
            try:
                content = manifest_path.read_text(encoding="utf-8")
                manifest = parse_manifest(content)
                backups.append(BackupInfo(manifest=manifest, path=backup_path))
            except Exception:
                continue

    # 作成日時の降順でソート
    backups.sort(key=lambda b: b.created_at, reverse=True)
    return backups


def restore_backup(project_path: Path, backup: BackupInfo) -> RestoreResult:
    """バックアップから復元する。

    Args:
        project_path: プロジェクトルートパス
        backup: 復元するバックアップ

    Returns:
        RestoreResult with success status
    """
    try:
        restored: list[str] = []

        for file_info in backup.manifest.files:
            src = backup.path / file_info.path
            dst = project_path / file_info.path

            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                restored.append(file_info.path)

        return RestoreResult(
            success=True,
            restored_files=tuple(restored),
        )

    except Exception as e:
        return RestoreResult(success=False, error=str(e))


def clean_backups(project_path: Path, keep: int = 5) -> tuple[int, list[str]]:
    """古いバックアップを削除する。

    Args:
        project_path: プロジェクトルートパス
        keep: 保持するバックアップ数

    Returns:
        (削除数, 削除されたバックアップ名のリスト)
    """
    backups = list_backups(project_path)
    to_remove = backups[keep:]
    removed_names: list[str] = []

    for backup in to_remove:
        try:
            shutil.rmtree(backup.path)
            removed_names.append(backup.name)
        except Exception:
            continue

    return len(removed_names), removed_names
