# Issue #33: WebUI基本実装

**Phase:** 2c
**優先度:** 中
**依存関係:** #31 (Mermaid図生成), #32 (メトリクス収集)
**見積もり:** 5日

---

## 概要

FastAPI ベースの Web UI を実装し、グラフの可視化とメトリクスの表示を行います。
ワークフローの理解とデバッグを視覚的にサポートします。

---

## TDD実装手順

### Step 1: WebUI のテスト (Red)

```python
# tests/unit/webui/test_api.py
"""Tests for WebUI API."""
import pytest
from fastapi.testclient import TestClient


class TestWebUIAPI:
    """Test WebUI API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from railway.webui.app import app
        return TestClient(app)

    def test_get_root(self, client):
        """Should return UI homepage."""
        response = client.get("/")
        assert response.status_code == 200
        assert "Railway Framework" in response.text

    def test_get_graph_list(self, client):
        """Should list available graphs."""
        response = client.get("/api/graphs")
        assert response.status_code == 200
        data = response.json()
        assert "graphs" in data
        assert isinstance(data["graphs"], list)

    def test_get_graph_diagram(self, client, tmp_path):
        """Should return Mermaid diagram."""
        # Create test graph
        graph_file = tmp_path / "test_graph.yaml"
        graph_file.write_text("""
nodes:
  - name: test
    type: source
""")

        response = client.get(f"/api/graph/diagram?path={graph_file}")
        assert response.status_code == 200
        data = response.json()
        assert "mermaid" in data
        assert "test[test]" in data["mermaid"]

    def test_get_metrics(self, client):
        """Should return metrics data."""
        response = client.get("/api/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "pipelines" in data

    def test_get_node_metrics(self, client):
        """Should return specific node metrics."""
        response = client.get("/api/metrics/node/test_node")
        assert response.status_code == 200
        data = response.json()
        assert "execution_count" in data
```

```bash
# 実行して失敗を確認 (Red)
pytest tests/unit/webui/test_api.py -v
# Expected: FAILED (WebUI app not implemented)
```

---

### Step 2: WebUI の実装 (Green)

```python
# railway/webui/__init__.py
"""Web UI module."""

from .app import app

__all__ = ["app"]


# railway/webui/app.py
"""FastAPI application for Railway WebUI."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional

from railway.visualization.mermaid import MermaidGenerator
from railway.core.graph import load_graph_from_yaml
from railway.metrics import get_global_collector

app = FastAPI(
    title="Railway Framework WebUI",
    description="Visual interface for Railway workflows",
    version="0.1.0"
)

# Setup templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Render homepage."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "Railway Framework"}
    )


@app.get("/api/graphs")
async def list_graphs():
    """
    List available workflow graphs.

    Returns:
        JSON with list of graph files
    """
    # Scan for graph.yaml files in current directory and subdirectories
    graphs = []
    for graph_file in Path.cwd().rglob("graph.yaml"):
        graphs.append({
            "name": graph_file.parent.name,
            "path": str(graph_file),
        })

    return {"graphs": graphs}


@app.get("/api/graph/diagram")
async def get_graph_diagram(path: str):
    """
    Get Mermaid diagram for a graph.

    Args:
        path: Path to graph.yaml file

    Returns:
        JSON with Mermaid diagram and stats
    """
    try:
        graph = load_graph_from_yaml(path)
        generator = MermaidGenerator(style=True)
        result = generator.generate_with_metadata(graph)

        return {
            "mermaid": result["mermaid"],
            "stats": result["stats"],
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Graph file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics")
async def get_all_metrics():
    """
    Get all collected metrics.

    Returns:
        JSON with nodes and pipeline metrics
    """
    collector = get_global_collector()
    import json
    metrics = json.loads(collector.export_json())
    return metrics


@app.get("/api/metrics/node/{node_name}")
async def get_node_metrics(node_name: str):
    """
    Get metrics for a specific node.

    Args:
        node_name: Name of the node

    Returns:
        JSON with node metrics
    """
    collector = get_global_collector()
    metrics = collector.get_metrics(node_name)

    if metrics["execution_count"] == 0:
        raise HTTPException(status_code=404, detail="Node not found or has no metrics")

    return metrics


@app.get("/api/metrics/pipeline/{pipeline_name}")
async def get_pipeline_metrics(pipeline_name: str):
    """
    Get metrics for a specific pipeline.

    Args:
        pipeline_name: Name of the pipeline

    Returns:
        JSON with pipeline metrics
    """
    collector = get_global_collector()
    metrics = collector.get_pipeline_metrics(pipeline_name)

    if metrics["execution_count"] == 0:
        raise HTTPException(status_code=404, detail="Pipeline not found or has no metrics")

    return metrics


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "railway-webui"}


# railway/webui/templates/index.html
"""HTML template for WebUI."""
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Railway Framework - WebUI</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #4caf50;
            padding-bottom: 10px;
        }
        .graph-list {
            margin-top: 20px;
        }
        .graph-item {
            padding: 15px;
            margin: 10px 0;
            background: #f9f9f9;
            border-left: 4px solid #2196f3;
            cursor: pointer;
        }
        .graph-item:hover {
            background: #e3f2fd;
        }
        .mermaid-container {
            margin-top: 30px;
            padding: 20px;
            background: #fafafa;
            border-radius: 4px;
        }
        .metrics {
            margin-top: 30px;
        }
        .metric-card {
            display: inline-block;
            padding: 20px;
            margin: 10px;
            background: #fff;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12);
            min-width: 200px;
        }
        .metric-value {
            font-size: 32px;
            font-weight: bold;
            color: #2196f3;
        }
        .metric-label {
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚂 Railway Framework WebUI</h1>

        <div class="metrics">
            <h2>Metrics Overview</h2>
            <div id="metrics-container"></div>
        </div>

        <div class="graph-list">
            <h2>Available Workflows</h2>
            <div id="graphs-container"></div>
        </div>

        <div class="mermaid-container" id="diagram-container" style="display:none;">
            <h2>Workflow Diagram</h2>
            <div class="mermaid" id="mermaid-diagram"></div>
        </div>
    </div>

    <script>
        mermaid.initialize({ startOnLoad: true });

        // Load metrics
        fetch('/api/metrics')
            .then(r => r.json())
            .then(data => {
                const container = document.getElementById('metrics-container');
                const nodeCount = Object.keys(data.nodes || {}).length;
                const pipelineCount = Object.keys(data.pipelines || {}).length;

                container.innerHTML = `
                    <div class="metric-card">
                        <div class="metric-value">${nodeCount}</div>
                        <div class="metric-label">Nodes Executed</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${pipelineCount}</div>
                        <div class="metric-label">Pipelines Run</div>
                    </div>
                `;
            });

        // Load graph list
        fetch('/api/graphs')
            .then(r => r.json())
            .then(data => {
                const container = document.getElementById('graphs-container');
                if (data.graphs.length === 0) {
                    container.innerHTML = '<p>No workflow graphs found.</p>';
                    return;
                }

                container.innerHTML = data.graphs.map(g => `
                    <div class="graph-item" onclick="loadGraph('${g.path}')">
                        <strong>${g.name}</strong><br>
                        <small>${g.path}</small>
                    </div>
                `).join('');
            });

        function loadGraph(path) {
            fetch(`/api/graph/diagram?path=${encodeURIComponent(path)}`)
                .then(r => r.json())
                .then(data => {
                    const container = document.getElementById('diagram-container');
                    const diagram = document.getElementById('mermaid-diagram');
                    diagram.textContent = data.mermaid;
                    container.style.display = 'block';
                    mermaid.init(undefined, diagram);
                });
        }
    </script>
</body>
</html>
"""


# railway/cli/webui.py
"""WebUI CLI command."""

import typer
import uvicorn
from loguru import logger

app = typer.Typer(help="WebUI commands")


@app.command()
def start(
    host: str = typer.Option("127.0.0.1", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
):
    """
    Start the Railway WebUI server.

    Example:
        railway webui start --port 8000
    """
    logger.info(f"Starting Railway WebUI on http://{host}:{port}")

    uvicorn.run(
        "railway.webui.app:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    app()
```

```bash
# 実行して成功を確認 (Green)
pytest tests/unit/webui/test_api.py -v
# Expected: PASSED
```

---

## 完了条件

- [ ] FastAPI アプリケーション実装
- [ ] グラフ一覧API
- [ ] Mermaid 図生成API
- [ ] メトリクス表示API
- [ ] HTML テンプレート
- [ ] `railway webui start` コマンド
- [ ] テスト (8テスト以上)
- [ ] テストカバレッジ 90%以上
- [ ] ドキュメント更新

---

## 画面構成

1. **ダッシュボード**: メトリクス概要
2. **ワークフロー一覧**: 利用可能なグラフ
3. **グラフ可視化**: Mermaid図の表示
4. **メトリクス詳細**: ノード/パイプライン別

---

## 関連Issue

- Issue #31: Mermaid図生成
- Issue #32: メトリクス収集
- Issue #34: リアルタイム実行モニタリング

---

## 使用技術

- **Backend**: FastAPI, Uvicorn
- **Frontend**: Vanilla JS, Mermaid.js
- **Styling**: CSS3
