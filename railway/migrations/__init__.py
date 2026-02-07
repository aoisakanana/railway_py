"""Migration functionality for Railway Framework."""

from railway.migrations.field_dependency import (
    MigrationResult,
    NodeAnalysis,
    analyze_node_dependencies,
    generate_migration_guidance,
    infer_provides,
    infer_requires,
    migrate_to_field_dependency,
)

__all__ = [
    "NodeAnalysis",
    "MigrationResult",
    "analyze_node_dependencies",
    "infer_requires",
    "infer_provides",
    "generate_migration_guidance",
    "migrate_to_field_dependency",
]
