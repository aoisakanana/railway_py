"""マイグレーション定義パッケージ。

各バージョン間のマイグレーション定義を格納。
"""

from railway.migrations.definitions.v0_10_to_v0_11 import MIGRATION_0_10_TO_0_11
from railway.migrations.definitions.v0_11_to_v0_12 import MIGRATION_0_11_TO_0_12
from railway.migrations.definitions.v0_12_1_to_v0_12_2 import MIGRATION_0_12_1_TO_0_12_2

__all__ = [
    "MIGRATION_0_10_TO_0_11",
    "MIGRATION_0_11_TO_0_12",
    "MIGRATION_0_12_1_TO_0_12_2",
]
