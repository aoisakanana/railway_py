#!/usr/bin/env python3
"""DAG YAML Validation CLI."""

import argparse
import sys
from pathlib import Path

import yaml

from dag_yaml_tools.parser import load_yaml, build_graph
from dag_yaml_tools.validators import (
    validate_dag,
    validate_reachability,
    validate_undefined_references,
    validate_unused_nodes,
    validate_isolated_nodes,
    validate_transition_coverage,
    aggregate_results,
    format_report,
)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Validate DAG YAML files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "yaml_file",
        type=Path,
        help="Path to the YAML file to validate",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )
    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    yaml_file: Path = args.yaml_file

    # Load YAML
    try:
        yaml_data = load_yaml(yaml_file)
    except FileNotFoundError:
        print(f"エラー: ファイル '{yaml_file}' が見つかりません", file=sys.stderr)
        return 2
    except yaml.YAMLError as e:
        print(f"エラー: YAML構文エラー: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 2

    # Build graph
    dag_graph = build_graph(yaml_data)

    # Run validations
    dag_result = validate_dag(dag_graph.graph)
    reachability_result = validate_reachability(
        dag_graph.graph, dag_graph.start_node, dag_graph.terminal_nodes
    )
    undefined_ref_result = validate_undefined_references(
        yaml_data["transitions"], dag_graph.all_nodes
    )
    unused_node_result = validate_unused_nodes(
        dag_graph.all_nodes, yaml_data["transitions"], dag_graph.start_node
    )
    isolated_node_result = validate_isolated_nodes(
        dag_graph.graph, dag_graph.start_node, dag_graph.terminal_nodes
    )
    coverage_result = validate_transition_coverage(
        dag_graph.all_nodes, yaml_data["transitions"], dag_graph.terminal_nodes
    )

    # Aggregate and format report
    report = aggregate_results(
        dag_result,
        reachability_result,
        undefined_ref_result,
        unused_node_result,
        isolated_node_result,
        coverage_result,
    )

    print(format_report(report))

    return 0 if report.is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
