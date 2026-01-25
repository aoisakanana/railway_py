"""マイグレーション定義パッケージ。

各バージョン間のマイグレーション定義を格納。
"""

from railway.migrations.definitions.v0_10_to_v0_11 import MIGRATION_0_10_TO_0_11

__all__ = ["MIGRATION_0_10_TO_0_11"]
