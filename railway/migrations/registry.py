"""マイグレーションレジストリ。

関数型パラダイム:
- レジストリは不変のタプルとして定義
- パス計算は純粋関数

Note:
    MigrationDefinition は railway/migrations/changes.py で定義。
    実際のマイグレーション定義は railway/migrations/definitions/ 以下に配置。
"""

from packaging.version import Version

from railway.migrations.changes import MigrationDefinition
from railway.migrations.definitions.v0_10_to_v0_11 import MIGRATION_0_10_TO_0_11
from railway.migrations.definitions.v0_11_to_v0_12 import MIGRATION_0_11_TO_0_12
from railway.migrations.definitions.v0_13_3_to_v0_13_4 import MIGRATION_0_13_3_TO_0_13_4
from railway.migrations.definitions.v0_13_4_to_v0_13_11 import MIGRATION_0_13_4_TO_0_13_11
from railway.migrations.definitions.v0_13_11_to_v0_13_15 import MIGRATION_0_13_11_TO_0_13_15
from railway.migrations.types import MigrationPlan

# ============================================================
# マイグレーション定義（不変）
# definitions/ ディレクトリから登録
# ============================================================

MIGRATIONS: tuple[MigrationDefinition, ...] = (
    MIGRATION_0_10_TO_0_11,
    MIGRATION_0_11_TO_0_12,
    MIGRATION_0_13_3_TO_0_13_4,
    MIGRATION_0_13_4_TO_0_13_11,
    MIGRATION_0_13_11_TO_0_13_15,
)


# ============================================================
# 純粋関数: バージョン比較ヘルパー
# ============================================================

def _base_release(ver: str) -> tuple[int, ...]:
    """ベースリリースタプルを取得する純粋関数。

    プレリリース・ポストリリース・dev サフィックスを除去し、
    リリースセグメントのみを返す。

    Args:
        ver: バージョン文字列

    Returns:
        リリースセグメントのタプル

    Examples:
        >>> _base_release("0.13.10rc2")
        (0, 13, 10)
        >>> _base_release("0.13.11")
        (0, 13, 11)
    """
    return Version(ver).release


# ============================================================
# 純粋関数: マイグレーションパス計算
# ============================================================

def find_migration(from_ver: str, to_ver: str) -> MigrationDefinition | None:
    """指定されたバージョン間の直接マイグレーションを探す純粋関数。

    完全一致で検索する。テスト用途向け。

    Args:
        from_ver: 元のバージョン
        to_ver: 移行先バージョン

    Returns:
        MigrationDefinition if found, None otherwise
    """
    for migration in MIGRATIONS:
        if migration.from_version == from_ver and migration.to_version == to_ver:
            return migration
    return None


def find_next_migration(from_ver: str, target_ver: str) -> MigrationDefinition | None:
    """次のマイグレーションステップを探す純粋関数。

    範囲マッチ: マイグレーション M の from_version <= from_ver < to_version
    （ベースリリース比較）を満たすマイグレーションを検索する。
    これにより、プレリリースバージョン（rc, dev 等）からも
    適切なマイグレーションが見つかる。

    Args:
        from_ver: 現在のバージョン
        target_ver: 最終目標バージョン

    Returns:
        次のMigrationDefinition、または見つからない場合None
    """
    target_release = _base_release(target_ver)
    from_release = _base_release(from_ver)

    candidates = [
        m for m in MIGRATIONS
        if _base_release(m.from_version) <= from_release < _base_release(m.to_version)
        and _base_release(m.to_version) <= target_release
    ]

    if not candidates:
        return None

    # 最も大きなバージョンジャンプを優先
    return max(candidates, key=lambda m: Version(m.to_version))


def calculate_migration_path(from_ver: str, to_ver: str) -> MigrationPlan:
    """マイグレーションパスを計算する純粋関数。

    ベースリリース比較を使用するため、プレリリースバージョン間の
    マイグレーションも正しく処理される。

    Args:
        from_ver: 元のバージョン
        to_ver: 移行先バージョン

    Returns:
        MigrationPlan with ordered migrations

    Raises:
        ValueError: パスが見つからない場合
    """
    from_release = _base_release(from_ver)
    to_release = _base_release(to_ver)

    # 同じベースリリースまたはダウングレード
    if from_release >= to_release:
        return MigrationPlan(
            from_version=from_ver,
            to_version=to_ver,
            migrations=(),
        )

    # パスを構築
    path: list[MigrationDefinition] = []
    current = from_ver

    while _base_release(current) < to_release:
        next_migration = find_next_migration(current, to_ver)
        if next_migration is None:
            # マイグレーション定義がない場合は直接ジャンプ（空の計画）
            break
        path.append(next_migration)
        current = next_migration.to_version

    return MigrationPlan(
        from_version=from_ver,
        to_version=to_ver,
        migrations=tuple(path),
    )


def normalize_version(version: str) -> str:
    """バージョン文字列を正規化する純粋関数。

    Args:
        version: バージョン文字列

    Returns:
        MAJOR.MINOR.0 形式に正規化されたバージョン

    Examples:
        >>> normalize_version("0.9.5")
        "0.9.0"
        >>> normalize_version("1.2.3")
        "1.2.0"
    """
    v = Version(version)
    return f"{v.major}.{v.minor}.0"
