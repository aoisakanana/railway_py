"""E2E: 生成コード run()/run_async() の sync/async 4象限テスト (v0.13.25 Issue 01).

codegen が生成する run_async() の開始ノードラッパーが sync ノードを
無条件 await してクラッシュする問題の回帰テスト。

検証方針: 生成コードを実際に実行する挙動テスト（生成文字列への
substring アサーションは実装手段への結合となるため行わない）。
"""
from __future__ import annotations

import asyncio
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from railway.core.dag.codegen import generate_transition_code
from railway.core.dag.parser import load_transition_graph

_SYNC_START = '''
from railway import node
from railway.core.dag.outcome import Outcome


@node
def start(ctx: dict) -> tuple[dict, Outcome]:
    return ctx, Outcome.success("go")
'''

_ASYNC_START = '''
from railway import node
from railway.core.dag.outcome import Outcome


@node
async def start(ctx: dict) -> tuple[dict, Outcome]:
    return ctx, Outcome.success("go")
'''

_SYNC_STEP = '''
from railway import node
from railway.core.dag.outcome import Outcome


@node
def step(ctx: dict) -> tuple[dict, Outcome]:
    return ctx, Outcome.success("done")
'''

_ASYNC_STEP = '''
from railway import node
from railway.core.dag.outcome import Outcome


@node
async def step(ctx: dict) -> tuple[dict, Outcome]:
    return ctx, Outcome.success("done")
'''

_EXIT_DONE = '''
from railway import ExitContract, node


class DoneResult(ExitContract):
    exit_state: str = "success.done"


@node(name="exit.success.done")
def done(ctx) -> DoneResult:
    return DoneResult()
'''

_YAML = '''version: "1.0"
entrypoint: wfq
description: "quadrant test"

nodes:
  start:
    module: nodes.wfq.start
    function: start
    description: "start"
  step:
    module: nodes.wfq.step
    function: step
    description: "step"
  exit:
    success:
      done:
        description: "done"

start: start

transitions:
  start:
    success::go: step
  step:
    success::done: exit.success.done
'''


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _purge_nodes_modules() -> None:
    for name in [m for m in sys.modules if m == "nodes" or m.startswith("nodes.")]:
        del sys.modules[name]


def _build_and_load(tmp_path: Path, tag: str, *, start_async: bool, step_async: bool):
    """tmp_path にプロジェクトを構築し、生成 transitions モジュールをロードする。"""
    src = tmp_path / "src"
    _write(src / "nodes" / "__init__.py", "")
    _write(src / "nodes" / "wfq" / "__init__.py", "")
    _write(src / "nodes" / "wfq" / "start.py", _ASYNC_START if start_async else _SYNC_START)
    _write(src / "nodes" / "wfq" / "step.py", _ASYNC_STEP if step_async else _SYNC_STEP)
    _write(src / "nodes" / "exit" / "__init__.py", "")
    _write(src / "nodes" / "exit" / "success" / "__init__.py", "")
    _write(src / "nodes" / "exit" / "success" / "done.py", _EXIT_DONE)

    yaml_path = tmp_path / "wfq_20260101000000.yml"
    yaml_path.write_text(_YAML)

    graph = load_transition_graph(yaml_path)
    code = generate_transition_code(graph, str(yaml_path))
    gen_path = tmp_path / f"transitions_{tag}.py"
    gen_path.write_text(code)

    sys.path.insert(0, str(src))
    _purge_nodes_modules()
    spec = importlib.util.spec_from_file_location(f"gen_transitions_{tag}", gen_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, gen_path, str(src)


def _cleanup(src_path: str) -> None:
    _purge_nodes_modules()
    if src_path in sys.path:
        sys.path.remove(src_path)


QUADRANTS = [
    ("q1_sync_sync", False, False),
    ("q2_async_async", True, True),
    ("q3_sync_async", False, True),
    ("q4_async_sync", True, False),
]


class TestRunAsyncQuadrants:
    """run_async() は 4 象限すべてで動作する。"""

    @pytest.mark.parametrize("tag,start_async,step_async", QUADRANTS)
    def test_run_async_completes(
        self, tmp_path: Path, tag: str, start_async: bool, step_async: bool
    ) -> None:
        mod, _, src = _build_and_load(
            tmp_path, tag, start_async=start_async, step_async=step_async
        )
        try:
            result = asyncio.run(mod.run_async({}))
            assert result.is_success is True
            assert result.exit_state == "success.done"
        finally:
            _cleanup(src)


class TestRunSyncQuadrant:
    """run()（sync 実行）はケース 1（sync/sync）で従来どおり動作する。

    async ノード象限の run() は dag_runner が await 非対応のため対象外
    （現状維持、Issue 01 のスコープ外）。
    """

    def test_run_sync_start_sync_step(self, tmp_path: Path) -> None:
        mod, _, src = _build_and_load(
            tmp_path, "run_q1", start_async=False, step_async=False
        )
        try:
            result = mod.run({})
            assert result.is_success is True
            assert result.exit_state == "success.done"
        finally:
            _cleanup(src)


class TestGeneratedFileMypy:
    """生成ファイル単体の mypy --check-untyped-defs がエラー 0（BUG-B 回帰）。"""

    def test_generated_file_passes_check_untyped_defs(self, tmp_path: Path) -> None:
        _, gen_path, src = _build_and_load(
            tmp_path, "mypy_check", start_async=False, step_async=False
        )
        _cleanup(src)
        # フレームワーク repo の [tool.mypy]（strict 設定）が cwd から拾われるのを防ぐため
        # 検査条件を config で明示的に固定する（環境非依存）
        config = tmp_path / "mypy_test.ini"
        config.write_text(
            "[mypy]\n"
            "ignore_missing_imports = True\n"
            "check_untyped_defs = True\n"
            f"mypy_path = {tmp_path / 'src'}\n"
        )
        proc = subprocess.run(
            [
                sys.executable, "-m", "mypy",
                "--config-file", str(config),
                "--no-error-summary",
                str(gen_path),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(tmp_path),
        )
        assert proc.returncode == 0, f"mypy errors:\n{proc.stdout}\n{proc.stderr}"
