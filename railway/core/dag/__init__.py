"""DAG workflow support for Railway Framework."""

from railway.core.dag.callbacks import (
    AuditLogger,
    CompositeCallback,
    StepCallback,
    StepRecord,
    StepRecorder,
)
from railway.core.dag.codegen import (
    detect_context_type,
    generate_exit_enum,
    generate_imports,
    generate_metadata,
    generate_state_enum,
    generate_transition_code,
    generate_transition_table,
)
from railway.core.dag.outcome import (
    Outcome,
    OutcomeMappingError,
)
from railway.core.dag.parser import (
    ParseError,
    load_transition_graph,
    parse_transition_graph,
)
from railway.core.dag.types import (
    ExitDefinition,
    GeneratedFileMetadata,
    GraphOptions,
    NodeDefinition,
    StateTransition,
    TransitionGraph,
)
from railway.core.dag.state import (
    NodeOutcome,
    StateFormatError,
)
from railway.core.dag.runner import (
    MaxIterationsError,
    UndefinedStateError,
    async_dag_runner,
    dag_runner,
)
from railway.core.dag.errors import (
    DependencyRuntimeError,
    ExitNodeTypeError,
    LegacyExitFormatError,
)
from railway.core.dag.validator import (
    ValidationError,
    ValidationResult,
    ValidationWarning,
    combine_results,
    validate_graph,
    validate_no_duplicate_states,
    validate_no_infinite_loop,
    validate_reachability,
    validate_start_node_exists,
    validate_termination,
    validate_transition_targets,
)
from railway.core.dag.field_dependency import (
    AvailableFields,
    EMPTY_FIELD_DEPENDENCY,
    FieldDependency,
    field_dependency_from_dict,
    validate_transition_dependencies,
    ValidationResult as FieldValidationResult,
)
from railway.core.dag.dependency_extraction import (
    extract_field_dependency,
    extract_initial_fields_from_start_node,
    import_node_function,
    load_node_dependencies,
)
from railway.core.dag.dependency_validator import (
    DependencyValidationResult,
    find_all_paths,
    validate_all_paths,
    validate_path_dependencies,
    validate_requires_against_contract,
)

__all__ = [
    # Types
    "NodeDefinition",
    "ExitDefinition",
    "StateTransition",
    "GraphOptions",
    "TransitionGraph",
    "GeneratedFileMetadata",
    # Parser
    "ParseError",
    "parse_transition_graph",
    "load_transition_graph",
    # Validator
    "ValidationError",
    "ValidationWarning",
    "ValidationResult",
    "validate_graph",
    "validate_start_node_exists",
    "validate_transition_targets",
    "validate_reachability",
    "validate_termination",
    "validate_no_duplicate_states",
    "validate_no_infinite_loop",
    "combine_results",
    # State
    "NodeOutcome",
    "StateFormatError",
    # Codegen
    "detect_context_type",
    "generate_transition_code",
    "generate_state_enum",
    "generate_exit_enum",
    "generate_transition_table",
    "generate_imports",
    "generate_metadata",
    # Outcome
    "Outcome",
    "OutcomeMappingError",
    # Runner
    "dag_runner",
    "async_dag_runner",
    "MaxIterationsError",
    "UndefinedStateError",
    # Errors
    "DependencyRuntimeError",
    "ExitNodeTypeError",
    "LegacyExitFormatError",
    # Callbacks
    "StepCallback",
    "StepRecord",
    "StepRecorder",
    "AuditLogger",
    "CompositeCallback",
    # Field Dependency
    "FieldDependency",
    "AvailableFields",
    "EMPTY_FIELD_DEPENDENCY",
    "field_dependency_from_dict",
    "validate_transition_dependencies",
    "FieldValidationResult",
    # Dependency Extraction
    "extract_field_dependency",
    "extract_initial_fields_from_start_node",
    "import_node_function",
    "load_node_dependencies",
    # Dependency Validator
    "DependencyValidationResult",
    "find_all_paths",
    "validate_all_paths",
    "validate_path_dependencies",
    "validate_requires_against_contract",
]
