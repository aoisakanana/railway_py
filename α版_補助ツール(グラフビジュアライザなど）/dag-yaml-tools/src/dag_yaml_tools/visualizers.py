"""Visualizers module for DAG YAML visualization."""

from pathlib import Path
from typing import NamedTuple
import json

import networkx as nx
from graphviz import Digraph
from pyvis.network import Network


class NodeStyle(NamedTuple):
    """Style definition for a node."""

    color: str
    font_color: str
    shape: str
    border_color: str


# Color constants
COLOR_START = "#4A90D9"  # Blue
COLOR_SUCCESS = "#5CB85C"  # Green
COLOR_FAILURE = "#D9534F"  # Red
COLOR_PROCESS = "#6C757D"  # Gray
COLOR_WHITE = "#FFFFFF"


def get_node_style(node_name: str, start_node: str) -> NodeStyle:
    """
    Determine the visual style for a node.

    Args:
        node_name: Name of the node.
        start_node: Name of the start node.

    Returns:
        NodeStyle with color, font_color, shape, and border_color.
    """
    if node_name == start_node:
        return NodeStyle(
            color=COLOR_START,
            font_color=COLOR_WHITE,
            shape="ellipse",
            border_color=COLOR_START,
        )
    elif node_name.startswith("exit.success"):
        return NodeStyle(
            color=COLOR_SUCCESS,
            font_color=COLOR_WHITE,
            shape="box",
            border_color=COLOR_SUCCESS,
        )
    elif node_name.startswith("exit.failure"):
        return NodeStyle(
            color=COLOR_FAILURE,
            font_color=COLOR_WHITE,
            shape="box",
            border_color=COLOR_FAILURE,
        )
    else:
        return NodeStyle(
            color=COLOR_PROCESS,
            font_color=COLOR_WHITE,
            shape="ellipse",
            border_color=COLOR_PROCESS,
        )


def get_node_label(node_name: str, description: str | None = None) -> str:
    """
    Generate a display label for a node.

    Args:
        node_name: Name of the node.
        description: Optional description.

    Returns:
        Display label string.
    """
    if description:
        return f"{node_name}\n({description})"
    return node_name


def create_pyvis_network(
    graph: nx.DiGraph,
    start_node: str,
    node_descriptions: dict[str, str],
) -> Network:
    """
    Create a pyvis Network object from a NetworkX graph.

    Args:
        graph: The NetworkX DiGraph.
        start_node: Name of the start node.
        node_descriptions: Mapping of node names to descriptions.

    Returns:
        Configured pyvis Network object.
    """
    net = Network(
        height="800px",
        width="100%",
        directed=True,
        bgcolor="#ffffff",
        font_color="#000000",
    )

    # Configure layout and physics
    # Physics is disabled after initial stabilization so nodes can be freely dragged
    net.set_options("""
    {
        "physics": {
            "enabled": true,
            "stabilization": {
                "enabled": true,
                "iterations": 200,
                "updateInterval": 25,
                "onlyDynamicEdges": false,
                "fit": true
            },
            "barnesHut": {
                "gravitationalConstant": -8000,
                "springConstant": 0.001,
                "springLength": 200
            }
        },
        "layout": {
            "hierarchical": false
        },
        "interaction": {
            "dragNodes": true,
            "dragView": true,
            "zoomView": true
        },
        "configure": {
            "enabled": false
        }
    }
    """)

    # Add nodes
    for node in graph.nodes:
        style = get_node_style(node, start_node)
        description = node_descriptions.get(node, "")
        label = get_node_label(node, description if description else None)

        net.add_node(
            node,
            label=label,
            color=style.color,
            font={"color": style.font_color},
            shape=style.shape,
            title=description if description else node,
        )

    # Add edges
    for source, target, data in graph.edges(data=True):
        label = data.get("label", "")
        net.add_edge(
            source,
            target,
            label=label,
            arrows="to",
            font={"size": 10, "align": "middle"},
        )

    return net


def visualize_html(
    graph: nx.DiGraph,
    start_node: str,
    node_descriptions: dict[str, str],
    output_path: Path,
) -> Path:
    """
    Generate an interactive HTML visualization using pyvis.

    Args:
        graph: The NetworkX DiGraph.
        start_node: Name of the start node.
        node_descriptions: Mapping of node names to descriptions.
        output_path: Path to the output HTML file.

    Returns:
        Path to the generated HTML file.
    """
    net = create_pyvis_network(graph, start_node, node_descriptions)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write HTML file
    net.write_html(str(output_path))

    # Add JavaScript to disable physics after stabilization
    html_content = output_path.read_text(encoding="utf-8")
    
    # Insert script to disable physics after stabilization
    disable_physics_script = """
    <script type="text/javascript">
        // Disable physics after stabilization so nodes can be freely dragged
        network.on("stabilizationIterationsDone", function () {
            network.setOptions({ physics: { enabled: false } });
        });
    </script>
</body>"""
    
    html_content = html_content.replace("</body>", disable_physics_script)
    output_path.write_text(html_content, encoding="utf-8")

    return output_path


def create_graphviz_digraph(
    graph: nx.DiGraph,
    start_node: str,
    node_descriptions: dict[str, str],
) -> Digraph:
    """
    Create a Graphviz Digraph object from a NetworkX graph.

    Args:
        graph: The NetworkX DiGraph.
        start_node: Name of the start node.
        node_descriptions: Mapping of node names to descriptions.

    Returns:
        Configured Graphviz Digraph object.
    """
    dot = Digraph(
        comment="DAG Visualization",
        format="png",
        engine="dot",
    )

    # Graph attributes
    dot.attr(
        rankdir="TB",
        splines="ortho",
        nodesep="0.5",
        ranksep="0.8",
    )

    # Default node attributes
    dot.attr(
        "node",
        fontsize="12",
    )

    # Default edge attributes
    dot.attr(
        "edge",
        fontsize="10",
    )

    # Add nodes
    for node in graph.nodes:
        style = get_node_style(node, start_node)
        description = node_descriptions.get(node, "")
        label = get_node_label(node, description if description else None)

        # Map shape names for Graphviz
        gv_shape = "ellipse" if style.shape == "ellipse" else "box"

        dot.node(
            node,
            label=label,
            style="filled",
            fillcolor=style.color,
            fontcolor=style.font_color,
            shape=gv_shape,
        )

    # Add edges
    for source, target, data in graph.edges(data=True):
        label = data.get("label", "")
        dot.edge(source, target, label=label, fontsize="9")

    return dot


def visualize_png(
    graph: nx.DiGraph,
    start_node: str,
    node_descriptions: dict[str, str],
    output_path: Path,
) -> Path:
    """
    Generate a static PNG visualization using Graphviz.

    Args:
        graph: The NetworkX DiGraph.
        start_node: Name of the start node.
        node_descriptions: Mapping of node names to descriptions.
        output_path: Path to the output PNG file (without extension).

    Returns:
        Path to the generated PNG file.

    Raises:
        RuntimeError: If Graphviz is not installed.
    """
    dot = create_graphviz_digraph(graph, start_node, node_descriptions)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove .png extension if present (graphviz adds it)
    output_base = output_path.with_suffix("")

    try:
        dot.render(str(output_base), cleanup=True)
    except Exception as e:
        if "failed to execute" in str(e).lower():
            raise RuntimeError(
                "Graphviz is not installed. "
                "Install it with: sudo apt install graphviz (Ubuntu) "
                "or brew install graphviz (macOS)"
            ) from e
        raise

    return output_path


def visualize_cytoscape(
    graph: nx.DiGraph,
    start_node: str,
    node_descriptions: dict[str, str],
    output_path: Path,
) -> Path:
    """
    Generate an interactive HTML visualization using Cytoscape.js.

    Args:
        graph: The NetworkX DiGraph.
        start_node: Name of the start node.
        node_descriptions: Mapping of node names to descriptions.
        output_path: Path to the output HTML file.

    Returns:
        Path to the generated HTML file.
    """
    # Determine which compound groups are needed
    has_success = any(n.startswith("exit.success") for n in graph.nodes)
    has_failure = any(n.startswith("exit.failure") for n in graph.nodes)

    # Build nodes data
    nodes_data = []
    
    # Add compound parent nodes for grouping
    if has_success:
        nodes_data.append({
            "data": {
                "id": "_group_success",
                "label": "SUCCESS",
                "nodeType": "group_success",
            }
        })
    
    if has_failure:
        nodes_data.append({
            "data": {
                "id": "_group_failure",
                "label": "FAILURE",
                "nodeType": "group_failure",
            }
        })

    for node in graph.nodes:
        style = get_node_style(node, start_node)
        description = node_descriptions.get(node, "")
        node_type = _get_node_type_str(node, start_node)
        
        node_data: dict = {
            "data": {
                "id": node,
                "label": node,
                "description": description,
                "nodeType": node_type,
                "color": style.color,
                "fontColor": style.font_color,
            }
        }
        
        # Assign parent for grouping
        if node.startswith("exit.success"):
            node_data["data"]["parent"] = "_group_success"
        elif node.startswith("exit.failure"):
            node_data["data"]["parent"] = "_group_failure"
        
        nodes_data.append(node_data)

    # Build edges data
    edges_data = []
    for i, (source, target, data) in enumerate(graph.edges(data=True)):
        label = data.get("label", "")
        edges_data.append({
            "data": {
                "id": f"edge_{i}",
                "source": source,
                "target": target,
                "label": label,
            }
        })

    elements = {"nodes": nodes_data, "edges": edges_data}

    # Generate HTML
    html_content = _generate_cytoscape_html(elements)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write HTML file
    output_path.write_text(html_content, encoding="utf-8")

    return output_path


def _get_node_type_str(node_name: str, start_node: str) -> str:
    """Get node type as string for CSS styling."""
    if node_name == start_node:
        return "start"
    elif node_name.startswith("exit.success"):
        return "success"
    elif node_name.startswith("exit.failure"):
        return "failure"
    return "process"


def _generate_cytoscape_html(elements: dict) -> str:
    """Generate complete HTML with Cytoscape.js."""
    elements_json = json.dumps(elements, ensure_ascii=False, indent=2)
    
    return f'''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DAG Visualization</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/dagre/0.8.5/dagre.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/cytoscape-dagre@2.5.0/cytoscape-dagre.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f5f5;
        }}
        #cy {{
            width: 100%;
            height: 100vh;
            background: #ffffff;
        }}
        #controls {{
            position: fixed;
            top: 10px;
            left: 10px;
            z-index: 1000;
            background: white;
            padding: 8px 12px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            max-width: calc(100% - 40px);
        }}
        .menu-group {{
            position: relative;
        }}
        .menu-toggle {{
            padding: 8px 12px;
            border: none;
            border-radius: 4px;
            background: #495057;
            color: white;
            cursor: pointer;
            font-size: 12px;
            font-weight: bold;
            white-space: nowrap;
        }}
        .menu-toggle:hover {{
            background: #343a40;
        }}
        .menu-items {{
            display: none;
            position: absolute;
            top: 100%;
            left: 0;
            margin-top: 4px;
            background: white;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            padding: 6px;
            z-index: 1001;
            min-width: 120px;
        }}
        .menu-items.open {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        .menu-items button {{
            padding: 8px 12px;
            border: none;
            border-radius: 4px;
            background: #4A90D9;
            color: white;
            cursor: pointer;
            font-size: 12px;
            white-space: nowrap;
            text-align: left;
        }}
        .menu-items button:hover {{
            background: #357ABD;
        }}
        .menu-items button.active {{
            background: #28a745;
        }}
        .menu-items button.edit-active {{
            background: #dc3545;
        }}
        .menu-items button:disabled {{
            background: #ccc;
            cursor: not-allowed;
        }}
        .dialog {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 2000;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            min-width: 350px;
            display: none;
        }}
        .dialog h3 {{
            margin: 0 0 15px 0;
            color: #333;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }}
        .dialog div {{
            margin-bottom: 12px;
        }}
        .dialog label {{
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }}
        .dialog input, .dialog select {{
            width: 100%;
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
        }}
        .dialog input:focus, .dialog select:focus {{
            border-color: #4A90D9;
            outline: none;
        }}
        .dialog-buttons {{
            margin-top: 20px;
            text-align: right;
        }}
        .dialog-buttons button {{
            margin-left: 10px;
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}
        .dialog-buttons button:first-child {{
            background: #4A90D9;
            color: white;
        }}
        .dialog-buttons button:last-child {{
            background: #6c757d;
            color: white;
        }}
        .color-swatch {{
            width: 30px;
            height: 30px;
            border-radius: 4px;
            cursor: pointer;
            border: 2px solid transparent;
            transition: border-color 0.2s;
        }}
        .color-swatch:hover {{
            border-color: #333;
        }}
        .color-swatch.selected {{
            border-color: #000;
            box-shadow: 0 0 5px rgba(0,0,0,0.3);
        }}
        .color-settings-grid {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-top: 10px;
        }}
        .color-setting-row {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .color-setting-row label {{
            width: 80px;
            font-size: 12px;
            font-weight: normal;
        }}
        .color-setting-row input[type="color"] {{
            width: 40px;
            height: 30px;
            padding: 0;
            border: 1px solid #ccc;
            cursor: pointer;
            border-radius: 4px;
        }}
        .color-setting-row input[type="text"] {{
            width: 80px;
            padding: 6px;
            font-size: 12px;
        }}
        .color-setting-row button {{
            padding: 6px 10px;
            font-size: 11px;
            background: #6c757d;
        }}
        #dialog-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1999;
            display: none;
        }}
        #edge-edit-panel {{
            position: fixed;
            top: 60px;
            left: 10px;
            z-index: 1000;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            max-width: 300px;
            font-size: 14px;
            display: none;
        }}
        #edge-edit-panel h3 {{
            margin-bottom: 10px;
            color: #333;
        }}
        #edge-edit-panel select {{
            width: 100%;
            padding: 8px;
            margin-top: 5px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }}
        #edge-edit-panel button {{
            margin: 5px 5px 0 0;
            padding: 8px 12px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }}
        #edge-edit-panel button:first-of-type {{
            background: #4A90D9;
            color: white;
        }}
        #edge-edit-panel button:last-of-type {{
            background: #6c757d;
            color: white;
        }}
        #info {{
            position: fixed;
            bottom: 10px;
            left: 10px;
            z-index: 1000;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            max-width: 400px;
            font-size: 14px;
            display: none;
        }}
        #info h3 {{
            margin-bottom: 10px;
            color: #333;
        }}
        #info p {{
            margin: 5px 0;
            color: #666;
            word-break: break-all;
        }}
        #info .label {{
            font-weight: bold;
            color: #333;
        }}
    </style>
</head>
<body>
    <div id="controls">
        <div class="menu-group">
            <button class="menu-toggle" onclick="toggleMenu('menu-display')">表示 ▼</button>
            <div id="menu-display" class="menu-items">
                <button onclick="resetLayout()">リセット</button>
                <button onclick="fitGraph()">全体表示</button>
                <button onclick="toggleLabels()">ラベル切替</button>
            </div>
        </div>
        <div class="menu-group">
            <button class="menu-toggle" onclick="toggleMenu('menu-effect')">効果 ▼</button>
            <div id="menu-effect" class="menu-items">
                <button id="highlightBtn" onclick="setMode('highlight')">ハイライト</button>
                <button id="lowlightBtn" onclick="setMode('lowlight')">ローライト</button>
                <button id="hideBtn" onclick="setMode('hide')">非表示</button>
                <button onclick="clearEffects()">解除</button>
                <button onclick="restoreHidden()">復元</button>
            </div>
        </div>
        <div class="menu-group">
            <button class="menu-toggle" onclick="toggleMenu('menu-label')">状態ラベル ▼</button>
            <div id="menu-label" class="menu-items">
                <button onclick="expandEdgeLabels()">展開</button>
                <button onclick="collapseEdgeLabels()">収束</button>
            </div>
        </div>
        <div class="menu-group">
            <button class="menu-toggle" onclick="toggleMenu('menu-color')">色 ▼</button>
            <div id="menu-color" class="menu-items">
                <button onclick="showColorDialog()">設定</button>
            </div>
        </div>
        <div class="menu-group">
            <button class="menu-toggle" onclick="toggleMenu('menu-add')">追加 ▼</button>
            <div id="menu-add" class="menu-items">
                <button onclick="showAddNodeDialog()">ノード</button>
                <button onclick="showAddEdgeDialog()">エッジ</button>
            </div>
        </div>
        <div class="menu-group">
            <button class="menu-toggle" onclick="toggleMenu('menu-edge-edit')">エッジ編集 ▼</button>
            <div id="menu-edge-edit" class="menu-items">
                <button id="edgeEditBtn" onclick="toggleEdgeEditMode()">付替: OFF</button>
                <button onclick="undoEdgeChange()" id="undoBtn" disabled>戻す</button>
                <button onclick="resetAllEdges()">全リセット</button>
            </div>
        </div>
        <div class="menu-group">
            <button class="menu-toggle" onclick="toggleMenu('menu-merge')">統合 ▼</button>
            <div id="menu-merge" class="menu-items">
                <button onclick="showMergeSelectedDialog()">選択ノード</button>
                <button onclick="showMergeChildrenDialog()">プレフィックス指定</button>
                <button onclick="showMergeGroupDialog()">グループ内</button>
                <button onclick="undoMerge()" id="undoMergeBtn" disabled>戻す</button>
                <button onclick="resetAllMerges()">全リセット</button>
            </div>
        </div>
        <div class="menu-group">
            <button class="menu-toggle" onclick="toggleMenu('menu-group')">グループ ▼</button>
            <div id="menu-group" class="menu-items">
                <button onclick="showCreateGroupDialog()">作成</button>
                <button onclick="showAddToGroupDialog()">ノード追加</button>
                <button onclick="removeFromGroup()">ノード除外</button>
            </div>
        </div>
        <div class="menu-group">
            <button class="menu-toggle" onclick="toggleMenu('menu-output')">出力 ▼</button>
            <div id="menu-output" class="menu-items">
                <button onclick="exportYaml()">YAML</button>
            </div>
        </div>
    </div>
    <div id="edge-edit-panel">
        <h3>エッジ編集</h3>
        <p id="edge-edit-status">エッジを選択してください</p>
        <div id="edge-edit-form" style="display: none;">
            <p><span class="label">エッジ:</span> <span id="edit-edge-id"></span></p>
            <p><span class="label">ラベル:</span> <span id="edit-edge-label"></span></p>
            <div style="margin-top: 10px;">
                <label>新しい接続先:</label>
                <select id="new-target-select"></select>
            </div>
            <div style="margin-top: 10px;">
                <button onclick="applyEdgeChange()">変更を適用</button>
                <button onclick="cancelEdgeEdit()">キャンセル</button>
            </div>
        </div>
    </div>
    <div id="add-node-dialog" class="dialog">
        <h3>追加: ノード</h3>
        <div>
            <label>ノードID (必須):</label>
            <input type="text" id="new-node-id" placeholder="例: process_x">
        </div>
        <div>
            <label>ノードタイプ:</label>
            <select id="new-node-type">
                <option value="process">処理ノード</option>
                <option value="success">成功終端 (exit.success.*)</option>
                <option value="failure">失敗終端 (exit.failure.*)</option>
            </select>
        </div>
        <div>
            <label>説明 (任意):</label>
            <input type="text" id="new-node-desc" placeholder="ノードの説明">
        </div>
        <div class="dialog-buttons">
            <button onclick="addNode()">追加</button>
            <button onclick="closeDialog('add-node-dialog')">キャンセル</button>
        </div>
    </div>
    <div id="add-edge-dialog" class="dialog">
        <h3>追加: エッジ</h3>
        <div>
            <label>接続元ノード:</label>
            <select id="new-edge-source"></select>
        </div>
        <div>
            <label>接続先ノード:</label>
            <select id="new-edge-target"></select>
        </div>
        <div>
            <label>ラベル (状態名):</label>
            <input type="text" id="new-edge-label" placeholder="例: success, done">
        </div>
        <div class="dialog-buttons">
            <button onclick="addEdge()">追加</button>
            <button onclick="closeDialog('add-edge-dialog')">キャンセル</button>
        </div>
    </div>
    <div id="merge-selected-dialog" class="dialog">
        <h3>統合: 選択ノード</h3>
        <p style="color: #666; font-size: 12px;">Ctrl+クリックで複数ノードを選択してください</p>
        <div>
            <label>選択中のノード:</label>
            <div id="selected-nodes-list" style="max-height: 150px; overflow-y: auto; border: 1px solid #ccc; padding: 8px; border-radius: 4px; background: #f9f9f9;"></div>
        </div>
        <div>
            <label>まとめ後の表示名:</label>
            <input type="text" id="merge-display-name" placeholder="例: 処理グループA">
        </div>
        <div class="dialog-buttons">
            <button onclick="mergeSelectedNodes()">まとめる</button>
            <button onclick="closeDialog('merge-selected-dialog')">キャンセル</button>
        </div>
    </div>
    <div id="merge-children-dialog" class="dialog">
        <h3>統合: プレフィックス指定</h3>
        <p style="color: #666; font-size: 12px;">指定したプレフィックスを持つノードを統合します</p>
        <div>
            <label>親プレフィックス:</label>
            <input type="text" id="merge-parent-prefix" placeholder="例: api.response">
        </div>
        <div>
            <label>まとめ後の表示名:</label>
            <input type="text" id="merge-children-display-name" placeholder="例: API応答処理">
        </div>
        <div>
            <label>対象ノード (プレビュー):</label>
            <div id="children-preview-list" style="max-height: 150px; overflow-y: auto; border: 1px solid #ccc; padding: 8px; border-radius: 4px; background: #f9f9f9;"></div>
        </div>
        <div class="dialog-buttons">
            <button onclick="mergeChildrenNodes()">まとめる</button>
            <button onclick="closeDialog('merge-children-dialog')">キャンセル</button>
        </div>
    </div>
    <div id="merge-group-dialog" class="dialog">
        <h3>統合: グループ内</h3>
        <p style="color: #666; font-size: 12px;">表示グループ内のノードを統合します</p>
        <div>
            <label>まとめるグループ:</label>
            <select id="merge-group-select">
                <option value="">-- 選択してください --</option>
            </select>
        </div>
        <div>
            <label>対象ノード:</label>
            <div id="group-nodes-preview" style="max-height: 150px; overflow-y: auto; border: 1px solid #ccc; padding: 8px; border-radius: 4px; background: #f9f9f9;"></div>
        </div>
        <div class="dialog-buttons">
            <button onclick="mergeSelectedGroup()">まとめる</button>
            <button onclick="closeDialog('merge-group-dialog')">キャンセル</button>
        </div>
    </div>
    <div id="color-dialog" class="dialog" style="min-width: 450px;">
        <h3>色: 設定</h3>
        <p style="color: #666; font-size: 12px;">選択中の要素に色を設定します</p>
        <div>
            <label>選択中:</label>
            <div id="color-target-preview" style="border: 1px solid #ccc; padding: 8px; border-radius: 4px; background: #f9f9f9; max-height: 80px; overflow-y: auto;"></div>
        </div>
        <div class="color-settings-grid">
            <div class="color-setting-row">
                <label>背景色:</label>
                <input type="color" id="color-bg" value="#4A90D9">
                <input type="text" id="color-bg-text" placeholder="#4A90D9" maxlength="7">
                <button onclick="applyColorSetting('bg')">適用</button>
            </div>
            <div class="color-setting-row">
                <label>枠線:</label>
                <input type="color" id="color-border" value="#357ABD">
                <input type="text" id="color-border-text" placeholder="#357ABD" maxlength="7">
                <button onclick="applyColorSetting('border')">適用</button>
            </div>
            <div class="color-setting-row">
                <label>文字の縁:</label>
                <input type="color" id="color-text-outline" value="#000000">
                <input type="text" id="color-text-outline-text" placeholder="#000000" maxlength="7">
                <button onclick="applyColorSetting('textOutline')">適用</button>
            </div>
            <div class="color-setting-row">
                <label>文字色:</label>
                <input type="color" id="color-text" value="#FFFFFF">
                <input type="text" id="color-text-text" placeholder="#FFFFFF" maxlength="7">
                <button onclick="applyColorSetting('text')">適用</button>
            </div>
        </div>
        <div style="margin-top: 15px;">
            <label>カラーパレット (クリックで背景色に適用):</label>
            <div id="color-palette" style="display: flex; flex-wrap: wrap; gap: 5px; margin-top: 5px;">
            </div>
        </div>
        <div class="dialog-buttons">
            <button onclick="applyAllColors()">全て適用</button>
            <button onclick="resetSelectedColors()">リセット</button>
            <button onclick="closeDialog('color-dialog')">閉じる</button>
        </div>
    </div>
    <div id="create-group-dialog" class="dialog">
        <h3>グループ: 作成</h3>
        <p style="color: #666; font-size: 12px;">選択中のノードで新しいグループを作成します</p>
        <div>
            <label>選択中のノード:</label>
            <div id="create-group-nodes-preview" style="max-height: 100px; overflow-y: auto; border: 1px solid #ccc; padding: 8px; border-radius: 4px; background: #f9f9f9;"></div>
        </div>
        <div>
            <label>グループ名:</label>
            <input type="text" id="new-group-name" placeholder="例: 処理グループA">
        </div>
        <div>
            <label>グループ色:</label>
            <div style="display: flex; gap: 10px; align-items: center; margin-top: 5px;">
                <input type="color" id="new-group-color" value="#9C27B0" style="width: 50px; height: 35px; padding: 0; border: 1px solid #ccc; cursor: pointer;">
                <span id="new-group-color-label">#9C27B0</span>
            </div>
        </div>
        <div class="dialog-buttons">
            <button onclick="createNewGroup()">作成</button>
            <button onclick="closeDialog('create-group-dialog')">キャンセル</button>
        </div>
    </div>
    <div id="add-to-group-dialog" class="dialog">
        <h3>グループ: ノード追加</h3>
        <p style="color: #666; font-size: 12px;">選択中のノードを既存グループに追加します</p>
        <div>
            <label>選択中のノード:</label>
            <div id="add-to-group-nodes-preview" style="max-height: 100px; overflow-y: auto; border: 1px solid #ccc; padding: 8px; border-radius: 4px; background: #f9f9f9;"></div>
        </div>
        <div>
            <label>追加先グループ:</label>
            <select id="target-group-select">
                <option value="">-- 選択してください --</option>
            </select>
        </div>
        <div class="dialog-buttons">
            <button onclick="addNodesToGroup()">追加</button>
            <button onclick="closeDialog('add-to-group-dialog')">キャンセル</button>
        </div>
    </div>
    <div id="dialog-overlay" onclick="closeAllDialogs()"></div>
    <div id="info">
        <h3 id="info-title">ノード情報</h3>
        <p><span class="label">ID:</span> <span id="info-id"></span></p>
        <p><span class="label">説明:</span> <span id="info-desc"></span></p>
    </div>
    <div id="cy"></div>

    <script>
        const elements = {elements_json};
        
        let showFullLabels = false;
        let currentMode = null; // null, 'highlight', 'lowlight', 'hide'
        let hiddenElements = [];
        let edgeEditMode = false;
        let selectedEdgeForEdit = null;
        let originalStartNode = null;
        let currentOpenMenu = null;
        
        // Menu toggle function
        function toggleMenu(menuId) {{
            const menu = document.getElementById(menuId);
            const allMenus = document.querySelectorAll('.menu-items');
            
            // Close all other menus
            allMenus.forEach(m => {{
                if (m.id !== menuId) {{
                    m.classList.remove('open');
                }}
            }});
            
            // Toggle current menu
            menu.classList.toggle('open');
            currentOpenMenu = menu.classList.contains('open') ? menuId : null;
        }}
        
        // Close menus when clicking outside
        document.addEventListener('click', function(e) {{
            if (!e.target.closest('.menu-group')) {{
                document.querySelectorAll('.menu-items').forEach(m => m.classList.remove('open'));
                currentOpenMenu = null;
            }}
        }});
        
        // Edge edit history for undo
        let edgeEditHistory = [];
        
        // Merge history for undo
        let mergeHistory = [];
        
        // Store original labels for edges before merging (for expansion)
        const edgeOriginalLabels = new Map();
        
        // Custom groups created by user
        const customGroups = new Map();
        
        // Store original edges for full reset
        const originalEdges = JSON.parse(JSON.stringify(elements.edges));
        
        // Store original graph data for YAML export
        const originalNodes = elements.nodes.filter(n => !n.data.id.startsWith('_group_'));
        
        const cy = cytoscape({{
            container: document.getElementById('cy'),
            elements: [...elements.nodes, ...elements.edges],
            style: [
                {{
                    selector: 'node',
                    style: {{
                        'label': 'data(label)',
                        'text-wrap': 'wrap',
                        'text-max-width': '150px',
                        'font-size': '12px',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'background-color': 'data(color)',
                        'color': 'data(fontColor)',
                        'padding': '15px',
                        'shape': 'roundrectangle',
                        'width': 'label',
                        'height': 'label',
                        'border-width': 2,
                        'border-color': '#ffffff',
                        'text-outline-color': 'data(color)',
                        'text-outline-width': 2,
                    }}
                }},
                {{
                    selector: '$node > node',
                    style: {{
                        'padding-top': '10px',
                        'padding-left': '10px',
                        'padding-bottom': '10px',
                        'padding-right': '10px',
                    }}
                }},
                {{
                    selector: 'node[nodeType="group_success"]',
                    style: {{
                        'background-color': '#E8F5E9',
                        'background-opacity': 0.8,
                        'border-width': 3,
                        'border-color': '#5CB85C',
                        'border-style': 'dashed',
                        'shape': 'roundrectangle',
                        'text-valign': 'top',
                        'text-halign': 'center',
                        'font-size': '14px',
                        'font-weight': 'bold',
                        'color': '#2E7D32',
                        'text-margin-y': 10,
                        'text-outline-width': 0,
                        'padding': '20px',
                    }}
                }},
                {{
                    selector: 'node[nodeType="group_failure"]',
                    style: {{
                        'background-color': '#FFEBEE',
                        'background-opacity': 0.8,
                        'border-width': 3,
                        'border-color': '#D9534F',
                        'border-style': 'dashed',
                        'shape': 'roundrectangle',
                        'text-valign': 'top',
                        'text-halign': 'center',
                        'font-size': '14px',
                        'font-weight': 'bold',
                        'color': '#C62828',
                        'text-margin-y': 10,
                        'text-outline-width': 0,
                        'padding': '20px',
                    }}
                }},
                {{
                    selector: 'node[nodeType="start"]',
                    style: {{
                        'shape': 'ellipse',
                        'background-color': '#4A90D9',
                    }}
                }},
                {{
                    selector: 'node[nodeType="success"]',
                    style: {{
                        'background-color': '#5CB85C',
                    }}
                }},
                {{
                    selector: 'node[nodeType="failure"]',
                    style: {{
                        'background-color': '#D9534F',
                    }}
                }},
                {{
                    selector: 'node[nodeType="process"]',
                    style: {{
                        'background-color': '#6C757D',
                    }}
                }},
                {{
                    selector: 'edge',
                    style: {{
                        'width': 2,
                        'line-color': '#999',
                        'target-arrow-color': '#999',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'label': 'data(label)',
                        'font-size': '10px',
                        'text-rotation': 'autorotate',
                        'text-margin-y': -10,
                        'color': '#666',
                        'text-background-color': '#ffffff',
                        'text-background-opacity': 0.8,
                        'text-background-padding': '3px',
                    }}
                }},
                {{
                    selector: 'node:selected',
                    style: {{
                        'border-width': 4,
                        'border-color': '#FFD700',
                    }}
                }},
                {{
                    selector: 'edge:selected',
                    style: {{
                        'line-color': '#FFD700',
                        'target-arrow-color': '#FFD700',
                        'width': 4,
                    }}
                }},
                {{
                    selector: '.highlighted',
                    style: {{
                        'opacity': 1,
                        'z-index': 999,
                    }}
                }},
                {{
                    selector: '.highlighted-edge',
                    style: {{
                        'opacity': 1,
                        'width': 4,
                        'line-color': '#FF6B35',
                        'target-arrow-color': '#FF6B35',
                        'z-index': 999,
                    }}
                }},
                {{
                    selector: '.lowlighted',
                    style: {{
                        'opacity': 0.15,
                    }}
                }},
                {{
                    selector: '.hidden-element',
                    style: {{
                        'display': 'none',
                    }}
                }},
                {{
                    selector: '.edge-editing',
                    style: {{
                        'line-color': '#FF6B35',
                        'target-arrow-color': '#FF6B35',
                        'width': 4,
                        'line-style': 'dashed',
                    }}
                }},
                {{
                    selector: '.merged-node',
                    style: {{
                        'background-color': '#9C27B0',
                        'border-width': 3,
                        'border-color': '#7B1FA2',
                        'border-style': 'double',
                    }}
                }},
                {{
                    selector: '.merged-hidden',
                    style: {{
                        'display': 'none',
                    }}
                }},
                {{
                    selector: '.expanded-label',
                    style: {{
                        'font-size': '11px',
                        'text-wrap': 'wrap',
                        'text-max-width': '200px',
                        'color': '#c00',
                        'font-weight': 'bold',
                        'text-background-color': '#ffffcc',
                        'text-background-opacity': 1,
                        'text-background-padding': '4px',
                        'text-border-width': 1,
                        'text-border-color': '#999',
                        'text-border-opacity': 1,
                    }}
                }},
                {{
                    selector: '.custom-group',
                    style: {{
                        'background-opacity': 0.3,
                        'border-width': 3,
                        'border-style': 'dashed',
                        'shape': 'roundrectangle',
                        'text-valign': 'top',
                        'text-halign': 'center',
                        'font-size': '14px',
                        'font-weight': 'bold',
                        'text-margin-y': 10,
                        'text-outline-width': 0,
                        'padding': '20px',
                    }}
                }}
            ],
            layout: {{
                name: 'dagre',
                rankDir: 'TB',
                nodeSep: 80,
                rankSep: 100,
                padding: 50,
            }},
            wheelSensitivity: 0.3,
        }});

        // Show info panel on node click
        cy.on('tap', 'node', function(evt) {{
            const node = evt.target;
            
            // Skip group nodes for info display
            if (node.data('nodeType') === 'group_success' || node.data('nodeType') === 'group_failure') {{
                return;
            }}
            
            document.getElementById('info').style.display = 'block';
            document.getElementById('info-title').textContent = node.data('nodeType').toUpperCase();
            document.getElementById('info-id').textContent = node.data('id');
            document.getElementById('info-desc').textContent = node.data('description') || '(なし)';
            
            // Apply effect based on current mode
            if (currentMode) {{
                applyNodeEffect(node, currentMode);
            }}
        }});

        // Hide info panel when clicking background
        cy.on('tap', function(evt) {{
            if (evt.target === cy) {{
                document.getElementById('info').style.display = 'none';
            }}
        }});
        
        function applyNodeEffect(node, mode) {{
            const connectedEdges = node.connectedEdges();
            const neighborNodes = node.neighborhood('node');
            
            if (mode === 'highlight') {{
                // Clear previous highlight
                cy.elements().removeClass('highlighted highlighted-edge lowlighted');
                
                // Lowlight all elements first
                cy.elements().addClass('lowlighted');
                
                // Highlight selected node and connections
                node.removeClass('lowlighted').addClass('highlighted');
                connectedEdges.removeClass('lowlighted').addClass('highlighted-edge');
                neighborNodes.removeClass('lowlighted').addClass('highlighted');
                
                // Also highlight parent group if exists
                const parent = node.parent();
                if (parent.length > 0) {{
                    parent.removeClass('lowlighted');
                }}
            }} else if (mode === 'lowlight') {{
                // Lowlight only selected node and its connections
                node.addClass('lowlighted');
                connectedEdges.addClass('lowlighted');
            }} else if (mode === 'hide') {{
                // Hide selected node and its connections
                node.addClass('hidden-element');
                connectedEdges.addClass('hidden-element');
                hiddenElements.push(node);
                connectedEdges.forEach(e => hiddenElements.push(e));
            }}
        }}
        
        function applyEdgeEffect(edge, mode) {{
            const sourceNode = edge.source();
            const targetNode = edge.target();
            
            if (mode === 'highlight') {{
                // Clear previous highlight
                cy.elements().removeClass('highlighted highlighted-edge lowlighted');
                
                // Lowlight all elements first
                cy.elements().addClass('lowlighted');
                
                // Highlight the edge and connected nodes
                edge.removeClass('lowlighted').addClass('highlighted-edge');
                sourceNode.removeClass('lowlighted').addClass('highlighted');
                targetNode.removeClass('lowlighted').addClass('highlighted');
            }} else if (mode === 'lowlight') {{
                // Lowlight only selected edge
                edge.addClass('lowlighted');
            }} else if (mode === 'hide') {{
                // Hide selected edge
                edge.addClass('hidden-element');
                hiddenElements.push(edge);
            }}
        }}
        
        function setMode(mode) {{
            // Toggle mode if clicking same button
            if (currentMode === mode) {{
                currentMode = null;
            }} else {{
                currentMode = mode;
            }}
            
            // Update button styles
            document.getElementById('highlightBtn').classList.remove('active');
            document.getElementById('lowlightBtn').classList.remove('active');
            document.getElementById('hideBtn').classList.remove('active');
            
            if (currentMode) {{
                document.getElementById(currentMode + 'Btn').classList.add('active');
            }}
            
            // Clear effects when switching modes (except for hide)
            if (mode !== 'hide') {{
                cy.elements().removeClass('highlighted highlighted-edge lowlighted');
            }}
        }}
        
        function clearEffects() {{
            cy.elements().removeClass('highlighted highlighted-edge lowlighted');
        }}
        
        function expandEdgeLabels() {{
            // Get selected elements
            const selectedEdges = cy.edges(':selected');
            const selectedNodes = cy.nodes(':selected').filter(n => {{
                const nodeType = n.data('nodeType');
                return nodeType !== 'group_success' && nodeType !== 'group_failure';
            }});
            
            let edgesToExpand = cy.collection();
            
            if (selectedEdges.length > 0) {{
                // If edges are selected, expand those
                edgesToExpand = selectedEdges;
            }} else if (selectedNodes.length > 0) {{
                // If nodes are selected, expand connected edges
                selectedNodes.forEach(node => {{
                    edgesToExpand = edgesToExpand.union(node.connectedEdges());
                }});
            }} else {{
                alert('エッジまたはノードを選択してください\\n(Ctrl+クリックで複数選択可能)');
                return;
            }}
            
            // Filter to only merged edges
            const mergedEdges = edgesToExpand.filter(e => e.data('isMergedEdge'));
            
            if (mergedEdges.length === 0) {{
                alert('選択されたエッジにまとめられた状態がありません');
                return;
            }}
            
            // Expand labels
            mergedEdges.forEach(edge => {{
                const edgeKey = edge.data('edgeKey');
                if (edgeKey && edgeOriginalLabels.has(edgeKey)) {{
                    const labels = edgeOriginalLabels.get(edgeKey);
                    const uniqueLabels = [...new Set(labels)];
                    const expandedLabel = uniqueLabels.join('\\n');
                    
                    // Store original 'Any' label if not already stored
                    if (!edge.data('_originalLabel')) {{
                        edge.data('_originalLabel', edge.data('label'));
                    }}
                    
                    edge.data('label', expandedLabel);
                    edge.addClass('expanded-label');
                }}
            }});
            
            // Adjust layout slightly to avoid overlaps
            adjustExpandedEdgePositions(mergedEdges);
        }}
        
        function adjustExpandedEdgePositions(edges) {{
            // Group edges by source-target pair and adjust curve style to avoid overlap
            const edgeGroups = {{}};
            
            edges.forEach(edge => {{
                const key = `${{edge.data('source')}}-${{edge.data('target')}}`;
                if (!edgeGroups[key]) {{
                    edgeGroups[key] = [];
                }}
                edgeGroups[key].push(edge);
            }});
            
            // For edges that might overlap, use bezier curves with different control points
            Object.values(edgeGroups).forEach(group => {{
                if (group.length > 1) {{
                    group.forEach((edge, index) => {{
                        const offset = (index - (group.length - 1) / 2) * 50;
                        edge.style('control-point-step-size', Math.abs(offset) + 40);
                    }});
                }}
            }});
        }}
        
        function collapseEdgeLabels() {{
            // Collapse all expanded labels back to 'Any'
            cy.edges('.expanded-label').forEach(edge => {{
                const originalLabel = edge.data('_originalLabel');
                if (originalLabel !== undefined) {{
                    edge.data('label', originalLabel);
                }}
                edge.removeClass('expanded-label');
            }});
        }}
        
        // ===== Color Setting Functions =====
        
        const colorPalette = [
            // Row 1: Basic colors
            '#E53935', '#D81B60', '#8E24AA', '#5E35B1', '#3949AB',
            '#1E88E5', '#039BE5', '#00ACC1', '#00897B', '#43A047',
            // Row 2: Light colors
            '#7CB342', '#C0CA33', '#FDD835', '#FFB300', '#FB8C00',
            '#F4511E', '#6D4C41', '#757575', '#546E7A', '#78909C',
            // Row 3: Pastel colors
            '#FFCDD2', '#F8BBD9', '#E1BEE7', '#D1C4E9', '#C5CAE9',
            '#BBDEFB', '#B3E5FC', '#B2EBF2', '#B2DFDB', '#C8E6C9',
        ];
        
        function showColorDialog() {{
            const selectedNodes = cy.nodes(':selected').filter(n => {{
                const nodeType = n.data('nodeType');
                // Allow custom groups and regular nodes, exclude system groups
                return nodeType !== 'group_success' && nodeType !== 'group_failure';
            }});
            const selectedEdges = cy.edges(':selected');
            const selectedGroups = cy.nodes(':selected').filter(n => {{
                return n.hasClass('custom-group') || 
                       n.data('nodeType') === 'group_success' || 
                       n.data('nodeType') === 'group_failure';
            }});
            
            if (selectedNodes.length === 0 && selectedEdges.length === 0 && selectedGroups.length === 0) {{
                alert('ノード、エッジ、またはグループを選択してください\\n(Ctrl+クリックで複数選択可能)');
                return;
            }}
            
            // Update preview
            const previewDiv = document.getElementById('color-target-preview');
            let previewHtml = '';
            
            if (selectedGroups.length > 0) {{
                previewHtml += `<div><strong>グループ (${{selectedGroups.length}}):</strong></div>`;
                selectedGroups.forEach(g => {{
                    previewHtml += `<div style="margin-left: 10px;">• ${{g.data('label') || g.data('id')}}</div>`;
                }});
            }}
            
            const regularNodes = selectedNodes.filter(n => !n.hasClass('custom-group'));
            if (regularNodes.length > 0) {{
                previewHtml += `<div><strong>ノード (${{regularNodes.length}}):</strong></div>`;
                regularNodes.forEach(n => {{
                    previewHtml += `<div style="margin-left: 10px;">• ${{n.data('id')}}</div>`;
                }});
            }}
            
            if (selectedEdges.length > 0) {{
                previewHtml += `<div><strong>エッジ (${{selectedEdges.length}}):</strong></div>`;
                selectedEdges.forEach(e => {{
                    previewHtml += `<div style="margin-left: 10px;">• ${{e.data('source')}} → ${{e.data('target')}}</div>`;
                }});
            }}
            
            previewDiv.innerHTML = previewHtml;
            
            // Initialize color inputs from first selected element
            const firstNode = regularNodes.length > 0 ? regularNodes[0] : (selectedGroups.length > 0 ? selectedGroups[0] : null);
            const firstEdge = selectedEdges.length > 0 ? selectedEdges[0] : null;
            
            if (firstNode) {{
                const bgColor = rgbToHex(firstNode.style('background-color')) || '#4A90D9';
                const borderColor = rgbToHex(firstNode.style('border-color')) || '#357ABD';
                const textOutline = rgbToHex(firstNode.style('text-outline-color')) || '#000000';
                const textColor = rgbToHex(firstNode.style('color')) || '#FFFFFF';
                
                document.getElementById('color-bg').value = bgColor;
                document.getElementById('color-bg-text').value = bgColor;
                document.getElementById('color-border').value = borderColor;
                document.getElementById('color-border-text').value = borderColor;
                document.getElementById('color-text-outline').value = textOutline;
                document.getElementById('color-text-outline-text').value = textOutline;
                document.getElementById('color-text').value = textColor;
                document.getElementById('color-text-text').value = textColor;
            }} else if (firstEdge) {{
                const lineColor = rgbToHex(firstEdge.style('line-color')) || '#999999';
                document.getElementById('color-bg').value = lineColor;
                document.getElementById('color-bg-text').value = lineColor;
            }}
            
            // Sync color pickers with text inputs
            ['bg', 'border', 'textOutline', 'text'].forEach(type => {{
                const idType = type === 'textOutline' ? 'text-outline' : type;
                const picker = document.getElementById(`color-${{idType}}`);
                const textInput = document.getElementById(`color-${{idType}}-text`);
                
                picker.onchange = () => {{
                    textInput.value = picker.value.toUpperCase();
                }};
                
                textInput.oninput = () => {{
                    const val = textInput.value;
                    if (/^#[0-9A-Fa-f]{{6}}$/.test(val)) {{
                        picker.value = val;
                    }}
                }};
            }});
            
            // Build color palette
            const paletteDiv = document.getElementById('color-palette');
            paletteDiv.innerHTML = '';
            
            colorPalette.forEach(color => {{
                const swatch = document.createElement('div');
                swatch.className = 'color-swatch';
                swatch.style.backgroundColor = color;
                swatch.title = color;
                swatch.onclick = () => {{
                    document.getElementById('color-bg').value = color;
                    document.getElementById('color-bg-text').value = color;
                    applyColorSetting('bg');
                }};
                paletteDiv.appendChild(swatch);
            }});
            
            document.getElementById('color-dialog').style.display = 'block';
            document.getElementById('dialog-overlay').style.display = 'block';
        }}
        
        function applyColorSetting(type) {{
            const selectedNodes = cy.nodes(':selected').filter(n => {{
                const nodeType = n.data('nodeType');
                return nodeType !== 'group_success' && nodeType !== 'group_failure' && !n.hasClass('custom-group');
            }});
            const selectedEdges = cy.edges(':selected');
            const selectedGroups = cy.nodes(':selected').filter(n => {{
                return n.hasClass('custom-group') || 
                       n.data('nodeType') === 'group_success' || 
                       n.data('nodeType') === 'group_failure';
            }});
            
            const idType = type === 'textOutline' ? 'text-outline' : type;
            const color = document.getElementById(`color-${{idType}}-text`).value || 
                         document.getElementById(`color-${{idType}}`).value;
            
            if (!/^#[0-9A-Fa-f]{{6}}$/.test(color)) {{
                alert('有効なカラーコードを入力してください (例: #4A90D9)');
                return;
            }}
            
            // Apply to regular nodes
            selectedNodes.forEach(node => {{
                saveOriginalNodeColors(node);
                switch(type) {{
                    case 'bg':
                        node.style('background-color', color);
                        break;
                    case 'border':
                        node.style('border-color', color);
                        node.style('border-width', 3);
                        break;
                    case 'textOutline':
                        node.style('text-outline-color', color);
                        node.style('text-outline-width', 2);
                        break;
                    case 'text':
                        node.style('color', color);
                        break;
                }}
            }});
            
            // Apply to groups
            selectedGroups.forEach(group => {{
                saveOriginalGroupColors(group);
                switch(type) {{
                    case 'bg':
                        group.style('background-color', color);
                        break;
                    case 'border':
                        group.style('border-color', color);
                        break;
                    case 'textOutline':
                        group.style('text-outline-color', color);
                        group.style('text-outline-width', 2);
                        break;
                    case 'text':
                        group.style('color', color);
                        break;
                }}
            }});
            
            // Apply to edges (only bg and text applicable)
            selectedEdges.forEach(edge => {{
                saveOriginalEdgeColors(edge);
                switch(type) {{
                    case 'bg':
                        edge.style('line-color', color);
                        edge.style('target-arrow-color', color);
                        break;
                    case 'text':
                        edge.style('color', color);
                        break;
                }}
            }});
        }}
        
        function applyAllColors() {{
            ['bg', 'border', 'textOutline', 'text'].forEach(type => {{
                applyColorSetting(type);
            }});
        }}
        
        function saveOriginalNodeColors(node) {{
            if (!node.data('_origColors')) {{
                node.data('_origColors', {{
                    bg: node.style('background-color'),
                    border: node.style('border-color'),
                    borderWidth: node.style('border-width'),
                    textOutline: node.style('text-outline-color'),
                    textOutlineWidth: node.style('text-outline-width'),
                    text: node.style('color'),
                }});
            }}
        }}
        
        function saveOriginalGroupColors(group) {{
            if (!group.data('_origColors')) {{
                group.data('_origColors', {{
                    bg: group.style('background-color'),
                    border: group.style('border-color'),
                    textOutline: group.style('text-outline-color'),
                    textOutlineWidth: group.style('text-outline-width'),
                    text: group.style('color'),
                }});
            }}
        }}
        
        function saveOriginalEdgeColors(edge) {{
            if (!edge.data('_origColors')) {{
                edge.data('_origColors', {{
                    line: edge.style('line-color'),
                    arrow: edge.style('target-arrow-color'),
                    text: edge.style('color'),
                }});
            }}
        }}
        
        function resetSelectedColors() {{
            const selectedNodes = cy.nodes(':selected').filter(n => {{
                const nodeType = n.data('nodeType');
                return nodeType !== 'group_success' && nodeType !== 'group_failure' && !n.hasClass('custom-group');
            }});
            const selectedEdges = cy.edges(':selected');
            const selectedGroups = cy.nodes(':selected').filter(n => {{
                return n.hasClass('custom-group') || 
                       n.data('nodeType') === 'group_success' || 
                       n.data('nodeType') === 'group_failure';
            }});
            
            // Reset node colors
            selectedNodes.forEach(node => {{
                const orig = node.data('_origColors');
                if (orig) {{
                    node.style('background-color', orig.bg);
                    node.style('border-color', orig.border);
                    node.style('border-width', orig.borderWidth);
                    node.style('text-outline-color', orig.textOutline);
                    node.style('text-outline-width', orig.textOutlineWidth);
                    node.style('color', orig.text);
                }}
            }});
            
            // Reset group colors
            selectedGroups.forEach(group => {{
                const orig = group.data('_origColors');
                if (orig) {{
                    group.style('background-color', orig.bg);
                    group.style('border-color', orig.border);
                    group.style('text-outline-color', orig.textOutline);
                    group.style('text-outline-width', orig.textOutlineWidth);
                    group.style('color', orig.text);
                }}
            }});
            
            // Reset edge colors
            selectedEdges.forEach(edge => {{
                const orig = edge.data('_origColors');
                if (orig) {{
                    edge.style('line-color', orig.line);
                    edge.style('target-arrow-color', orig.arrow);
                    edge.style('color', orig.text);
                }}
            }});
        }}
        
        function rgbToHex(rgb) {{
            if (!rgb || rgb.startsWith('#')) return rgb;
            const match = rgb.match(/^rgb\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)$/);
            if (!match) return rgb;
            return '#' + [match[1], match[2], match[3]].map(x => {{
                const hex = parseInt(x).toString(16);
                return hex.length === 1 ? '0' + hex : hex;
            }}).join('').toUpperCase();
        }}
        
        // ===== Custom Group Functions =====
        
        function getRegularNodes() {{
            return cy.nodes().filter(n => {{
                const nodeType = n.data('nodeType');
                return nodeType !== 'group_success' && 
                       nodeType !== 'group_failure' &&
                       !n.hasClass('custom-group') &&
                       !n.hasClass('merged-hidden');
            }});
        }}
        
        function getAllGroups() {{
            const groups = [];
            
            // System groups
            const successGroup = cy.getElementById('_group_success');
            if (successGroup.length > 0) {{
                groups.push({{ id: '_group_success', name: 'SUCCESS', type: 'system' }});
            }}
            
            const failureGroup = cy.getElementById('_group_failure');
            if (failureGroup.length > 0) {{
                groups.push({{ id: '_group_failure', name: 'FAILURE', type: 'system' }});
            }}
            
            // Custom groups
            customGroups.forEach((data, id) => {{
                groups.push({{ id: id, name: data.name, type: 'custom' }});
            }});
            
            return groups;
        }}
        
        function showCreateGroupDialog() {{
            const selectedNodes = cy.nodes(':selected').filter(n => {{
                const nodeType = n.data('nodeType');
                return nodeType !== 'group_success' && 
                       nodeType !== 'group_failure' &&
                       !n.hasClass('custom-group');
            }});
            
            const previewDiv = document.getElementById('create-group-nodes-preview');
            
            if (selectedNodes.length === 0) {{
                previewDiv.innerHTML = '<span style="color: #999;">ノードを選択してください (Ctrl+クリック)</span>';
            }} else {{
                previewDiv.innerHTML = selectedNodes.map(n => `<div>• ${{n.data('id')}}</div>`).join('');
            }}
            
            document.getElementById('new-group-name').value = '';
            document.getElementById('new-group-color').value = '#9C27B0';
            document.getElementById('new-group-color-label').textContent = '#9C27B0';
            
            // Sync color picker with label
            document.getElementById('new-group-color').onchange = function() {{
                document.getElementById('new-group-color-label').textContent = this.value.toUpperCase();
            }};
            
            document.getElementById('create-group-dialog').style.display = 'block';
            document.getElementById('dialog-overlay').style.display = 'block';
        }}
        
        function createNewGroup() {{
            const selectedNodes = cy.nodes(':selected').filter(n => {{
                const nodeType = n.data('nodeType');
                return nodeType !== 'group_success' && 
                       nodeType !== 'group_failure' &&
                       !n.hasClass('custom-group');
            }});
            
            if (selectedNodes.length === 0) {{
                alert('グループに含めるノードを選択してください');
                return;
            }}
            
            const groupName = document.getElementById('new-group-name').value.trim();
            if (!groupName) {{
                alert('グループ名を入力してください');
                return;
            }}
            
            const groupColor = document.getElementById('new-group-color').value;
            const groupId = '_custom_group_' + Date.now();
            
            // Create parent node for the group
            cy.add({{
                group: 'nodes',
                data: {{
                    id: groupId,
                    label: groupName,
                    nodeType: 'custom_group',
                }},
                classes: 'custom-group',
            }});
            
            // Apply color
            const groupNode = cy.getElementById(groupId);
            groupNode.style('background-color', groupColor);
            groupNode.style('border-color', groupColor);
            
            // Move selected nodes into the group
            selectedNodes.forEach(node => {{
                // Store original parent
                node.data('_originalParent', node.data('parent') || null);
                node.move({{ parent: groupId }});
            }});
            
            // Store group info
            customGroups.set(groupId, {{
                name: groupName,
                color: groupColor,
                nodeIds: selectedNodes.map(n => n.data('id')),
            }});
            
            // Refresh layout
            cy.layout({{
                name: 'dagre',
                rankDir: 'TB',
                nodeSep: 80,
                rankSep: 100,
                padding: 50,
                animate: true,
                animationDuration: 300,
            }}).run();
            
            closeDialog('create-group-dialog');
            cy.nodes(':selected').unselect();
        }}
        
        function showAddToGroupDialog() {{
            const selectedNodes = cy.nodes(':selected').filter(n => {{
                const nodeType = n.data('nodeType');
                return nodeType !== 'group_success' && 
                       nodeType !== 'group_failure' &&
                       !n.hasClass('custom-group');
            }});
            
            const previewDiv = document.getElementById('add-to-group-nodes-preview');
            
            if (selectedNodes.length === 0) {{
                previewDiv.innerHTML = '<span style="color: #999;">ノードを選択してください (Ctrl+クリック)</span>';
            }} else {{
                previewDiv.innerHTML = selectedNodes.map(n => `<div>• ${{n.data('id')}}</div>`).join('');
            }}
            
            // Populate group select
            const select = document.getElementById('target-group-select');
            select.innerHTML = '<option value="">-- 選択してください --</option>';
            
            const groups = getAllGroups();
            groups.forEach(g => {{
                const option = document.createElement('option');
                option.value = g.id;
                option.textContent = `${{g.name}} (${{g.type === 'system' ? 'システム' : 'カスタム'}})`;
                select.appendChild(option);
            }});
            
            if (groups.length === 0) {{
                alert('追加先のグループがありません。先にグループを作成してください。');
                return;
            }}
            
            document.getElementById('add-to-group-dialog').style.display = 'block';
            document.getElementById('dialog-overlay').style.display = 'block';
        }}
        
        function addNodesToGroup() {{
            const selectedNodes = cy.nodes(':selected').filter(n => {{
                const nodeType = n.data('nodeType');
                return nodeType !== 'group_success' && 
                       nodeType !== 'group_failure' &&
                       !n.hasClass('custom-group');
            }});
            
            if (selectedNodes.length === 0) {{
                alert('追加するノードを選択してください');
                return;
            }}
            
            const targetGroupId = document.getElementById('target-group-select').value;
            if (!targetGroupId) {{
                alert('追加先グループを選択してください');
                return;
            }}
            
            // Move nodes to the group
            selectedNodes.forEach(node => {{
                // Store original parent if not already stored
                if (!node.data('_originalParent')) {{
                    node.data('_originalParent', node.data('parent') || null);
                }}
                node.move({{ parent: targetGroupId }});
            }});
            
            // Update custom group info if it's a custom group
            if (customGroups.has(targetGroupId)) {{
                const groupData = customGroups.get(targetGroupId);
                selectedNodes.forEach(n => {{
                    if (!groupData.nodeIds.includes(n.data('id'))) {{
                        groupData.nodeIds.push(n.data('id'));
                    }}
                }});
            }}
            
            closeDialog('add-to-group-dialog');
            cy.nodes(':selected').unselect();
        }}
        
        function removeFromGroup() {{
            const selectedNodes = cy.nodes(':selected').filter(n => {{
                const nodeType = n.data('nodeType');
                return nodeType !== 'group_success' && 
                       nodeType !== 'group_failure' &&
                       !n.hasClass('custom-group') &&
                       n.data('parent'); // Must have a parent
            }});
            
            if (selectedNodes.length === 0) {{
                alert('グループに所属しているノードを選択してください');
                return;
            }}
            
            selectedNodes.forEach(node => {{
                const currentParent = node.data('parent');
                
                // Update custom group info
                if (customGroups.has(currentParent)) {{
                    const groupData = customGroups.get(currentParent);
                    groupData.nodeIds = groupData.nodeIds.filter(id => id !== node.data('id'));
                }}
                
                // Remove from parent
                node.move({{ parent: null }});
            }});
            
            // Clean up empty custom groups
            customGroups.forEach((data, id) => {{
                const groupNode = cy.getElementById(id);
                if (groupNode.children().length === 0) {{
                    groupNode.remove();
                    customGroups.delete(id);
                }}
            }});
            
            cy.nodes(':selected').unselect();
        }}
        
        function restoreHidden() {{
            hiddenElements.forEach(el => {{
                el.removeClass('hidden-element');
            }});
            hiddenElements = [];
        }}
        
        function toggleEdgeEditMode() {{
            edgeEditMode = !edgeEditMode;
            const btn = document.getElementById('edgeEditBtn');
            const panel = document.getElementById('edge-edit-panel');
            
            if (edgeEditMode) {{
                btn.textContent = 'エッジ編集: ON';
                btn.classList.add('edit-active');
                panel.style.display = 'block';
                document.getElementById('edge-edit-status').textContent = 'エッジをクリックして選択';
                document.getElementById('edge-edit-form').style.display = 'none';
            }} else {{
                btn.textContent = 'エッジ編集: OFF';
                btn.classList.remove('edit-active');
                panel.style.display = 'none';
                cancelEdgeEdit();
            }}
        }}
        
        function selectEdgeForEdit(edge) {{
            if (selectedEdgeForEdit) {{
                selectedEdgeForEdit.removeClass('edge-editing');
            }}
            
            selectedEdgeForEdit = edge;
            edge.addClass('edge-editing');
            
            // Update panel
            document.getElementById('edge-edit-status').style.display = 'none';
            document.getElementById('edge-edit-form').style.display = 'block';
            document.getElementById('edit-edge-id').textContent = 
                edge.data('source') + ' → ' + edge.data('target');
            document.getElementById('edit-edge-label').textContent = edge.data('label') || '(なし)';
            
            // Populate target select
            const select = document.getElementById('new-target-select');
            select.innerHTML = '';
            
            // Get all non-group nodes
            const allNodes = cy.nodes().filter(n => {{
                const nodeType = n.data('nodeType');
                return nodeType !== 'group_success' && nodeType !== 'group_failure';
            }});
            
            allNodes.forEach(node => {{
                const option = document.createElement('option');
                option.value = node.data('id');
                option.textContent = node.data('id');
                if (node.data('id') === edge.data('target')) {{
                    option.selected = true;
                }}
                select.appendChild(option);
            }});
        }}
        
        function applyEdgeChange() {{
            if (!selectedEdgeForEdit) return;
            
            const newTarget = document.getElementById('new-target-select').value;
            const oldTarget = selectedEdgeForEdit.data('target');
            const oldSource = selectedEdgeForEdit.data('source');
            const oldLabel = selectedEdgeForEdit.data('label');
            const oldId = selectedEdgeForEdit.data('id');
            
            if (newTarget !== oldTarget) {{
                // Save to history for undo
                edgeEditHistory.push({{
                    type: 'change',
                    oldEdge: {{
                        id: oldId,
                        source: oldSource,
                        target: oldTarget,
                        label: oldLabel,
                    }},
                    newEdgeId: oldId + '_modified_' + Date.now(),
                }});
                
                // Create new edge
                const edgeData = {{
                    id: edgeEditHistory[edgeEditHistory.length - 1].newEdgeId,
                    source: oldSource,
                    target: newTarget,
                    label: oldLabel,
                }};
                
                // Remove old edge
                selectedEdgeForEdit.remove();
                
                // Add new edge
                cy.add({{
                    group: 'edges',
                    data: edgeData,
                }});
                
                // Update undo button
                updateUndoButton();
            }}
            
            cancelEdgeEdit();
        }}
        
        function updateUndoButton() {{
            const btn = document.getElementById('undoBtn');
            if (edgeEditHistory.length > 0) {{
                btn.disabled = false;
                btn.textContent = `元に戻す (${{edgeEditHistory.length}})`;
            }} else {{
                btn.disabled = true;
                btn.textContent = '元に戻す';
            }}
        }}
        
        function undoEdgeChange() {{
            if (edgeEditHistory.length === 0) return;
            
            const lastChange = edgeEditHistory.pop();
            
            if (lastChange.type === 'change') {{
                // Remove the new edge
                const newEdge = cy.getElementById(lastChange.newEdgeId);
                if (newEdge.length > 0) {{
                    newEdge.remove();
                }}
                
                // Restore the old edge
                cy.add({{
                    group: 'edges',
                    data: lastChange.oldEdge,
                }});
            }}
            
            updateUndoButton();
        }}
        
        function resetAllEdges() {{
            if (edgeEditHistory.length === 0) {{
                alert('リセットする変更がありません');
                return;
            }}
            
            if (!confirm(`${{edgeEditHistory.length}}件のエッジ変更をリセットしますか？`)) {{
                return;
            }}
            
            // Remove all current edges
            cy.edges().remove();
            
            // Restore all original edges
            originalEdges.forEach(edge => {{
                cy.add({{
                    group: 'edges',
                    data: {{ ...edge.data }},
                }});
            }});
            
            // Clear history
            edgeEditHistory = [];
            updateUndoButton();
            
            // Clear any edge editing state
            cancelEdgeEdit();
        }}
        
        // ===== Node/Edge Add Functions =====
        
        function showAddNodeDialog() {{
            document.getElementById('new-node-id').value = '';
            document.getElementById('new-node-type').value = 'process';
            document.getElementById('new-node-desc').value = '';
            document.getElementById('add-node-dialog').style.display = 'block';
            document.getElementById('dialog-overlay').style.display = 'block';
            document.getElementById('new-node-id').focus();
        }}
        
        function showAddEdgeDialog() {{
            // Populate source and target selects
            const sourceSelect = document.getElementById('new-edge-source');
            const targetSelect = document.getElementById('new-edge-target');
            sourceSelect.innerHTML = '';
            targetSelect.innerHTML = '';
            
            const allNodes = cy.nodes().filter(n => {{
                const nodeType = n.data('nodeType');
                return nodeType !== 'group_success' && nodeType !== 'group_failure';
            }});
            
            allNodes.forEach(node => {{
                const sourceOption = document.createElement('option');
                sourceOption.value = node.data('id');
                sourceOption.textContent = node.data('id');
                sourceSelect.appendChild(sourceOption);
                
                const targetOption = document.createElement('option');
                targetOption.value = node.data('id');
                targetOption.textContent = node.data('id');
                targetSelect.appendChild(targetOption);
            }});
            
            document.getElementById('new-edge-label').value = '';
            document.getElementById('add-edge-dialog').style.display = 'block';
            document.getElementById('dialog-overlay').style.display = 'block';
        }}
        
        function closeDialog(dialogId) {{
            document.getElementById(dialogId).style.display = 'none';
            document.getElementById('dialog-overlay').style.display = 'none';
        }}
        
        function closeAllDialogs() {{
            document.querySelectorAll('.dialog').forEach(d => d.style.display = 'none');
            document.getElementById('dialog-overlay').style.display = 'none';
        }}
        
        function addNode() {{
            const nodeId = document.getElementById('new-node-id').value.trim();
            const nodeType = document.getElementById('new-node-type').value;
            const nodeDesc = document.getElementById('new-node-desc').value.trim();
            
            if (!nodeId) {{
                alert('ノードIDを入力してください');
                return;
            }}
            
            // Check for duplicate
            if (cy.getElementById(nodeId).length > 0) {{
                alert('同じIDのノードが既に存在します');
                return;
            }}
            
            // Determine full node ID and parent based on type
            let fullNodeId = nodeId;
            let parent = null;
            let color = '#6C757D';
            
            if (nodeType === 'success') {{
                if (!nodeId.startsWith('exit.success.')) {{
                    fullNodeId = 'exit.success.' + nodeId;
                }}
                parent = '_group_success';
                color = '#5CB85C';
            }} else if (nodeType === 'failure') {{
                if (!nodeId.startsWith('exit.failure.')) {{
                    fullNodeId = 'exit.failure.' + nodeId;
                }}
                parent = '_group_failure';
                color = '#D9534F';
            }}
            
            // Check again with full ID
            if (cy.getElementById(fullNodeId).length > 0) {{
                alert('同じIDのノードが既に存在します');
                return;
            }}
            
            // Add node
            const nodeData = {{
                id: fullNodeId,
                label: fullNodeId,
                description: nodeDesc,
                nodeType: nodeType,
                color: color,
                fontColor: '#FFFFFF',
            }};
            
            if (parent) {{
                nodeData.parent = parent;
            }}
            
            cy.add({{
                group: 'nodes',
                data: nodeData,
            }});
            
            // Run layout to position new node
            cy.layout({{
                name: 'dagre',
                rankDir: 'TB',
                nodeSep: 80,
                rankSep: 100,
                padding: 50,
                animate: true,
                animationDuration: 300,
            }}).run();
            
            closeDialog('add-node-dialog');
        }}
        
        function addEdge() {{
            const source = document.getElementById('new-edge-source').value;
            const target = document.getElementById('new-edge-target').value;
            const label = document.getElementById('new-edge-label').value.trim();
            
            if (!source || !target) {{
                alert('接続元と接続先を選択してください');
                return;
            }}
            
            if (source === target) {{
                alert('接続元と接続先は異なるノードを選択してください');
                return;
            }}
            
            // Check for duplicate edge
            const existingEdge = cy.edges().filter(e => 
                e.data('source') === source && 
                e.data('target') === target &&
                e.data('label') === label
            );
            
            if (existingEdge.length > 0) {{
                alert('同じ接続のエッジが既に存在します');
                return;
            }}
            
            // Add edge
            const edgeId = `edge_new_${{Date.now()}}`;
            cy.add({{
                group: 'edges',
                data: {{
                    id: edgeId,
                    source: source,
                    target: target,
                    label: label || '',
                }},
            }});
            
            closeDialog('add-edge-dialog');
        }}
        
        // ===== Merge Functions =====
        
        function getSelectableNodes() {{
            return cy.nodes().filter(n => {{
                const nodeType = n.data('nodeType');
                return nodeType !== 'group_success' && 
                       nodeType !== 'group_failure' &&
                       !n.hasClass('merged-hidden');
            }});
        }}
        
        function showMergeSelectedDialog() {{
            const selectedNodes = cy.nodes(':selected').filter(n => {{
                const nodeType = n.data('nodeType');
                return nodeType !== 'group_success' && nodeType !== 'group_failure';
            }});
            
            const listDiv = document.getElementById('selected-nodes-list');
            
            if (selectedNodes.length < 2) {{
                listDiv.innerHTML = '<span style="color: #999;">2つ以上のノードをCtrl+クリックで選択してください</span>';
            }} else {{
                listDiv.innerHTML = selectedNodes.map(n => `<div>• ${{n.data('id')}}</div>`).join('');
            }}
            
            document.getElementById('merge-display-name').value = '';
            document.getElementById('merge-selected-dialog').style.display = 'block';
            document.getElementById('dialog-overlay').style.display = 'block';
        }}
        
        function showMergeChildrenDialog() {{
            document.getElementById('merge-parent-prefix').value = '';
            document.getElementById('merge-children-display-name').value = '';
            document.getElementById('children-preview-list').innerHTML = '<span style="color: #999;">プレフィックスを入力してください</span>';
            
            document.getElementById('merge-children-dialog').style.display = 'block';
            document.getElementById('dialog-overlay').style.display = 'block';
            
            // Add input listener for preview
            document.getElementById('merge-parent-prefix').addEventListener('input', updateChildrenPreview);
        }}
        
        function updateChildrenPreview() {{
            const prefix = document.getElementById('merge-parent-prefix').value.trim();
            const listDiv = document.getElementById('children-preview-list');
            
            if (!prefix) {{
                listDiv.innerHTML = '<span style="color: #999;">プレフィックスを入力してください</span>';
                return;
            }}
            
            const matchingNodes = getSelectableNodes().filter(n => {{
                const nodeId = n.data('id');
                return nodeId.startsWith(prefix + '.') || nodeId === prefix;
            }});
            
            if (matchingNodes.length === 0) {{
                listDiv.innerHTML = '<span style="color: #999;">一致するノードがありません</span>';
            }} else {{
                listDiv.innerHTML = matchingNodes.map(n => `<div>• ${{n.data('id')}}</div>`).join('');
            }}
        }}
        
        function mergeSelectedNodes() {{
            const selectedNodes = cy.nodes(':selected').filter(n => {{
                const nodeType = n.data('nodeType');
                return nodeType !== 'group_success' && nodeType !== 'group_failure';
            }});
            
            if (selectedNodes.length < 2) {{
                alert('2つ以上のノードを選択してください');
                return;
            }}
            
            const displayName = document.getElementById('merge-display-name').value.trim() || 
                               'merged_' + Date.now();
            
            performMerge(selectedNodes, displayName);
            closeDialog('merge-selected-dialog');
        }}
        
        function mergeChildrenNodes() {{
            const prefix = document.getElementById('merge-parent-prefix').value.trim();
            
            if (!prefix) {{
                alert('プレフィックスを入力してください');
                return;
            }}
            
            const matchingNodes = getSelectableNodes().filter(n => {{
                const nodeId = n.data('id');
                return nodeId.startsWith(prefix + '.') || nodeId === prefix;
            }});
            
            if (matchingNodes.length < 2) {{
                alert('2つ以上の一致するノードが必要です');
                return;
            }}
            
            const displayName = document.getElementById('merge-children-display-name').value.trim() || prefix;
            
            performMerge(matchingNodes, displayName);
            closeDialog('merge-children-dialog');
        }}
        
        function performMerge(nodesToMerge, displayName) {{
            const nodeIds = nodesToMerge.map(n => n.data('id'));
            const mergedNodeId = 'merged_' + Date.now();
            
            // Collect all edges connected to these nodes
            const affectedEdges = [];
            const incomingEdges = {{}};  // source -> [edges]
            const outgoingEdges = {{}};  // target -> [edges]
            
            nodesToMerge.forEach(node => {{
                node.connectedEdges().forEach(edge => {{
                    affectedEdges.push({{
                        id: edge.data('id'),
                        source: edge.data('source'),
                        target: edge.data('target'),
                        label: edge.data('label'),
                    }});
                }});
            }});
            
            // Save to history for undo
            mergeHistory.push({{
                mergedNodeId: mergedNodeId,
                originalNodeIds: nodeIds,
                originalEdges: affectedEdges,
                displayName: displayName,
            }});
            
            // Create merged node (position at center of merged nodes)
            let sumX = 0, sumY = 0;
            nodesToMerge.forEach(n => {{
                sumX += n.position('x');
                sumY += n.position('y');
            }});
            const centerX = sumX / nodesToMerge.length;
            const centerY = sumY / nodesToMerge.length;
            
            cy.add({{
                group: 'nodes',
                data: {{
                    id: mergedNodeId,
                    label: displayName,
                    description: `まとめ: ${{nodeIds.join(', ')}}`,
                    nodeType: 'merged',
                    color: '#9C27B0',
                    fontColor: '#FFFFFF',
                    originalNodes: nodeIds,
                }},
                position: {{ x: centerX, y: centerY }},
                classes: 'merged-node',
            }});
            
            // Hide original nodes
            nodesToMerge.forEach(n => n.addClass('merged-hidden'));
            
            // Create new edges with 'Any' label
            const newEdgeSet = new Set();
            
            affectedEdges.forEach(edge => {{
                let newSource = edge.source;
                let newTarget = edge.target;
                
                // If source is one of merged nodes, change to merged node
                if (nodeIds.includes(edge.source)) {{
                    newSource = mergedNodeId;
                }}
                
                // If target is one of merged nodes, change to merged node
                if (nodeIds.includes(edge.target)) {{
                    newTarget = mergedNodeId;
                }}
                
                // Skip self-loops on merged node
                if (newSource === mergedNodeId && newTarget === mergedNodeId) {{
                    return;
                }}
                
                // Create unique key to avoid duplicates
                const edgeKey = `${{newSource}}->${{newTarget}}`;
                if (!newEdgeSet.has(edgeKey)) {{
                    newEdgeSet.add(edgeKey);
                    const newEdgeId = `merged_edge_${{Date.now()}}_${{Math.random().toString(36).substr(2, 9)}}`;
                    
                    // Store original label for this edge connection
                    if (!edgeOriginalLabels.has(edgeKey)) {{
                        edgeOriginalLabels.set(edgeKey, []);
                    }}
                    edgeOriginalLabels.get(edgeKey).push(edge.label || '(unnamed)');
                    
                    cy.add({{
                        group: 'edges',
                        data: {{
                            id: newEdgeId,
                            source: newSource,
                            target: newTarget,
                            label: 'Any',
                            isMergedEdge: true,
                            edgeKey: edgeKey,
                        }},
                    }});
                }} else {{
                    // Add to existing edge's original labels
                    if (edgeOriginalLabels.has(edgeKey)) {{
                        edgeOriginalLabels.get(edgeKey).push(edge.label || '(unnamed)');
                    }}
                }}
            }});
            
            // Hide original edges
            affectedEdges.forEach(edge => {{
                const e = cy.getElementById(edge.id);
                if (e.length > 0) {{
                    e.addClass('merged-hidden');
                }}
            }});
            
            updateMergeUndoButton();
            cy.nodes(':selected').unselect();
        }}
        
        function updateMergeUndoButton() {{
            const btn = document.getElementById('undoMergeBtn');
            if (mergeHistory.length > 0) {{
                btn.disabled = false;
                btn.textContent = `まとめ戻す (${{mergeHistory.length}})`;
            }} else {{
                btn.disabled = true;
                btn.textContent = 'まとめ戻す';
            }}
        }}
        
        function undoMerge() {{
            if (mergeHistory.length === 0) return;
            
            const lastMerge = mergeHistory.pop();
            
            // Remove merged node
            const mergedNode = cy.getElementById(lastMerge.mergedNodeId);
            if (mergedNode.length > 0) {{
                // Remove edges connected to merged node
                mergedNode.connectedEdges().remove();
                mergedNode.remove();
            }}
            
            // Restore original nodes
            lastMerge.originalNodeIds.forEach(nodeId => {{
                const node = cy.getElementById(nodeId);
                if (node.length > 0) {{
                    node.removeClass('merged-hidden');
                }}
            }});
            
            // Restore original edges
            lastMerge.originalEdges.forEach(edge => {{
                const e = cy.getElementById(edge.id);
                if (e.length > 0) {{
                    e.removeClass('merged-hidden');
                }}
            }});
            
            updateMergeUndoButton();
        }}
        
        function resetAllMerges() {{
            if (mergeHistory.length === 0) {{
                alert('リセットするまとめがありません');
                return;
            }}
            
            if (!confirm(`${{mergeHistory.length}}件のまとめをリセットしますか？`)) {{
                return;
            }}
            
            // Undo all merges in reverse order
            while (mergeHistory.length > 0) {{
                undoMerge();
            }}
        }}
        
        function showMergeGroupDialog() {{
            const select = document.getElementById('merge-group-select');
            select.innerHTML = '<option value="">-- 選択してください --</option>';
            
            // Check available groups
            const groups = [];
            
            const successNodes = getSelectableNodes().filter(n => n.data('id').startsWith('exit.success'));
            if (successNodes.length >= 2) {{
                groups.push({{ id: 'success', name: 'SUCCESS', count: successNodes.length }});
            }}
            
            const failureNodes = getSelectableNodes().filter(n => n.data('id').startsWith('exit.failure'));
            if (failureNodes.length >= 2) {{
                groups.push({{ id: 'failure', name: 'FAILURE', count: failureNodes.length }});
            }}
            
            if (groups.length === 0) {{
                alert('まとめ可能なグループがありません（各グループに2つ以上のノードが必要です）');
                return;
            }}
            
            groups.forEach(g => {{
                const option = document.createElement('option');
                option.value = g.id;
                option.textContent = `${{g.name}} (${{g.count}}ノード)`;
                select.appendChild(option);
            }});
            
            document.getElementById('group-nodes-preview').innerHTML = '<span style="color: #999;">グループを選択してください</span>';
            
            // Add change listener
            select.onchange = updateGroupPreview;
            
            document.getElementById('merge-group-dialog').style.display = 'block';
            document.getElementById('dialog-overlay').style.display = 'block';
        }}
        
        function updateGroupPreview() {{
            const groupId = document.getElementById('merge-group-select').value;
            const previewDiv = document.getElementById('group-nodes-preview');
            
            if (!groupId) {{
                previewDiv.innerHTML = '<span style="color: #999;">グループを選択してください</span>';
                return;
            }}
            
            let nodes;
            if (groupId === 'success') {{
                nodes = getSelectableNodes().filter(n => n.data('id').startsWith('exit.success'));
            }} else if (groupId === 'failure') {{
                nodes = getSelectableNodes().filter(n => n.data('id').startsWith('exit.failure'));
            }}
            
            if (nodes && nodes.length > 0) {{
                previewDiv.innerHTML = nodes.map(n => `<div>• ${{n.data('id')}}</div>`).join('');
            }} else {{
                previewDiv.innerHTML = '<span style="color: #999;">対象ノードがありません</span>';
            }}
        }}
        
        function mergeSelectedGroup() {{
            const groupId = document.getElementById('merge-group-select').value;
            
            if (!groupId) {{
                alert('グループを選択してください');
                return;
            }}
            
            let nodes;
            let displayName;
            
            if (groupId === 'success') {{
                nodes = getSelectableNodes().filter(n => n.data('id').startsWith('exit.success'));
                displayName = 'SUCCESS (All)';
            }} else if (groupId === 'failure') {{
                nodes = getSelectableNodes().filter(n => n.data('id').startsWith('exit.failure'));
                displayName = 'FAILURE (All)';
            }}
            
            if (!nodes || nodes.length < 2) {{
                alert('まとめるには2つ以上のノードが必要です');
                return;
            }}
            
            performMerge(nodes, displayName);
            closeDialog('merge-group-dialog');
        }}
        
        function cancelEdgeEdit() {{
            if (selectedEdgeForEdit) {{
                selectedEdgeForEdit.removeClass('edge-editing');
                selectedEdgeForEdit = null;
            }}
            document.getElementById('edge-edit-status').style.display = 'block';
            document.getElementById('edge-edit-status').textContent = 'エッジをクリックして選択';
            document.getElementById('edge-edit-form').style.display = 'none';
        }}
        
        function exportYaml() {{
            // Get current visible edges (excluding hidden)
            const visibleEdges = cy.edges().filter(e => !e.hasClass('hidden-element'));
            const visibleNodes = cy.nodes().filter(n => {{
                const nodeType = n.data('nodeType');
                return nodeType !== 'group_success' && 
                       nodeType !== 'group_failure' && 
                       !n.hasClass('hidden-element');
            }});
            
            // Determine start node (first node that matches original start or first node)
            let startNode = visibleNodes.filter(n => n.data('nodeType') === 'start').first();
            if (startNode.length === 0) {{
                startNode = visibleNodes.first();
            }}
            const startNodeId = startNode.data('id');
            
            // Build nodes structure
            const nodesYaml = [];
            visibleNodes.forEach(node => {{
                const nodeId = node.data('id');
                const desc = node.data('description');
                if (desc) {{
                    nodesYaml.push(`  ${{nodeId}}:`);
                    nodesYaml.push(`    description: "${{desc}}"`);
                }} else {{
                    nodesYaml.push(`  ${{nodeId}}:`);
                }}
            }});
            
            // Build transitions structure
            const transitions = {{}};
            visibleEdges.forEach(edge => {{
                const source = edge.data('source');
                const target = edge.data('target');
                const label = edge.data('label') || 'default';
                
                if (!transitions[source]) {{
                    transitions[source] = {{}};
                }}
                transitions[source][label] = target;
            }});
            
            let transitionsYaml = [];
            Object.keys(transitions).sort().forEach(source => {{
                transitionsYaml.push(`  ${{source}}:`);
                Object.keys(transitions[source]).forEach(label => {{
                    transitionsYaml.push(`    ${{label}}: ${{transitions[source][label]}}`);
                }});
            }});
            
            // Generate YAML content
            const now = new Date();
            const timestamp = now.toISOString().replace(/[-:]/g, '').replace('T', '_').slice(0, 15);
            const filename = `dag_export_${{timestamp}}.yaml`;
            
            const yamlContent = `# DAG YAML Export
# Generated: ${{now.toISOString()}}

start: ${{startNodeId}}

nodes:
${{nodesYaml.join('\\n')}}

transitions:
${{transitionsYaml.join('\\n')}}
`;
            
            // Download file
            const blob = new Blob([yamlContent], {{ type: 'text/yaml' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }}
        
        // Modify edge click handler to support edge editing
        cy.on('tap', 'edge', function(evt) {{
            const edge = evt.target;
            
            // If in edge edit mode, select for editing
            if (edgeEditMode) {{
                selectEdgeForEdit(edge);
                return;
            }}
            
            document.getElementById('info').style.display = 'block';
            document.getElementById('info-title').textContent = 'エッジ情報';
            document.getElementById('info-id').textContent = edge.data('source') + ' → ' + edge.data('target');
            document.getElementById('info-desc').textContent = edge.data('label') || '(なし)';
            
            // Apply effect based on current mode
            if (currentMode) {{
                applyEdgeEffect(edge, currentMode);
            }}
        }});

        function resetLayout() {{
            cy.layout({{
                name: 'dagre',
                rankDir: 'TB',
                nodeSep: 80,
                rankSep: 100,
                padding: 50,
                animate: true,
                animationDuration: 500,
            }}).run();
        }}

        function fitGraph() {{
            cy.fit(50);
        }}

        function toggleLabels() {{
            showFullLabels = !showFullLabels;
            if (showFullLabels) {{
                cy.style().selector('edge').style('font-size', '11px').update();
                cy.style().selector('node').style('text-max-width', '300px').update();
            }} else {{
                cy.style().selector('edge').style('font-size', '10px').update();
                cy.style().selector('node').style('text-max-width', '150px').update();
            }}
        }}
    </script>
</body>
</html>'''
