#!/usr/bin/env python3
"""DAG YAML Visualization CLI."""

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

from dag_yaml_tools.parser import load_yaml, build_graph, flatten_nodes, METADATA_KEYS
from dag_yaml_tools.visualizers import visualize_html, visualize_png, visualize_cytoscape


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Visualize DAG YAML files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "yaml_file",
        type=Path,
        help="Path to the YAML file to visualize",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["cytoscape", "png", "legacy", "all"],
        default="cytoscape",
        help="Output format: cytoscape (default, interactive), png (static image), legacy (pyvis html), all",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output file path (without extension)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )
    return parser


def extract_descriptions(
    nodes: dict[str, Any], prefix: str = ""
) -> dict[str, str]:
    """
    Extract node descriptions from nested node definitions.

    Args:
        nodes: Nested node dictionary.
        prefix: Current path prefix.

    Returns:
        Mapping of flattened node names to descriptions.
    """
    result: dict[str, str] = {}

    for key, value in nodes.items():
        full_path = f"{prefix}.{key}" if prefix else key

        if value is None:
            continue
        elif isinstance(value, dict):
            if all(k in METADATA_KEYS for k in value.keys()):
                # Leaf node with metadata
                if "description" in value:
                    result[full_path] = value["description"]
            else:
                # Nested node
                result.update(extract_descriptions(value, full_path))

    return result


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    yaml_file: Path = args.yaml_file
    output_format: str = args.format
    output_path: Path | None = args.output

    # Determine output base path
    if output_path is None:
        output_base = yaml_file.parent / f"{yaml_file.stem}_graph"
    else:
        output_base = output_path

    # Load YAML
    try:
        yaml_data = load_yaml(yaml_file)
    except FileNotFoundError:
        print(f"エラー: ファイル '{yaml_file}' が見つかりません", file=sys.stderr)
        return 1
    except yaml.YAMLError as e:
        print(f"エラー: YAML構文エラー: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1

    # Build graph
    dag_graph = build_graph(yaml_data)

    # Extract descriptions
    node_descriptions = extract_descriptions(yaml_data["nodes"])

    # Generate outputs
    generated_files: list[Path] = []

    try:
        if output_format in ("cytoscape", "all"):
            cytoscape_path = output_base.with_suffix(".html")
            visualize_cytoscape(
                dag_graph.graph,
                dag_graph.start_node,
                node_descriptions,
                cytoscape_path,
            )
            generated_files.append(cytoscape_path)

        if output_format in ("legacy", "all"):
            legacy_path = output_base.with_suffix(".html") if output_format == "legacy" else output_base.parent / f"{output_base.stem}_legacy.html"
            visualize_html(
                dag_graph.graph,
                dag_graph.start_node,
                node_descriptions,
                legacy_path,
            )
            generated_files.append(legacy_path)

        if output_format in ("png", "all"):
            png_path = output_base.with_suffix(".png")
            visualize_png(
                dag_graph.graph,
                dag_graph.start_node,
                node_descriptions,
                png_path,
            )
            generated_files.append(png_path)

    except RuntimeError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1

    # Print success message
    if len(generated_files) == 1:
        print(f"✓ グラフを生成しました: {generated_files[0]}")
    else:
        print("✓ グラフを生成しました:")
        for f in generated_files:
            print(f"  - {f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
