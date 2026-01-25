"""DAG workflow support for Railway Framework."""

from railway.core.dag.callbacks import (
    AuditLogger,
    CompositeCallback,
    StepCallback,
    StepRecord,
    StepRecorder,
)
from railway.core.dag.codegen import (
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
    is_outcome,
    map_to_state,
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
    ExitOutcome,
    NodeOutcome,
    StateFormatError,
    make_exit,
    make_state,
    parse_exit,
    parse_state,
)
from railway.core.dag.runner import (
    DagRunnerResult,
    Exit,
    MaxIterationsError,
    UndefinedStateError,
    async_dag_runner,
    dag_runner,
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
    "ExitOutcome",
    "StateFormatError",
    "make_state",
    "make_exit",
    "parse_state",
    "parse_exit",
    # Codegen
    "generate_transition_code",
    "generate_state_enum",
    "generate_exit_enum",
    "generate_transition_table",
    "generate_imports",
    "generate_metadata",
    # Outcome
    "Outcome",
    "OutcomeMappingError",
    "is_outcome",
    "map_to_state",
    # Runner
    "dag_runner",
    "async_dag_runner",
    "DagRunnerResult",
    "Exit",
    "MaxIterationsError",
    "UndefinedStateError",
    # Callbacks
    "StepCallback",
    "StepRecord",
    "StepRecorder",
    "AuditLogger",
    "CompositeCallback",
]
