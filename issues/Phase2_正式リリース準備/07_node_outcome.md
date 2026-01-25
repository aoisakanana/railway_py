# Issue #07: 状態Enum基底クラス

**Phase:** 2a
**優先度:** 中
**依存関係:** #04
**見積もり:** 0.5日

---

## 概要

ノードが返す状態を表現するための基底クラス `NodeOutcome` を実装する。
コード生成時にこの基底クラスを継承した状態Enumが生成される。

---

## 設計原則

### 型安全な状態表現

```python
# 生成されるEnum（NodeOutcomeを継承）
class Top2State(NodeOutcome):
    FETCH_ALERT_SUCCESS_DONE = "fetch_alert::success::done"
    FETCH_ALERT_FAILURE_HTTP = "fetch_alert::failure::http"
```

### 状態の構造

```
{node_name}::{outcome_type}::{detail}

例:
- fetch_alert::success::done
- fetch_alert::failure::http
- check_session::success::exist
- check_session::success::not_exist
```

---

## TDD実装手順

### Step 1: Red（テストを書く）

```python
# tests/unit/core/dag/test_state.py
"""Tests for NodeOutcome base class."""
import pytest
from enum import Enum


class TestNodeOutcome:
    """Test NodeOutcome base class."""

    def test_create_outcome_enum(self):
        """Should create an Enum subclass of NodeOutcome."""
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            SUCCESS = "my_node::success::done"
            FAILURE = "my_node::failure::error"

        assert issubclass(MyState, Enum)
        assert issubclass(MyState, NodeOutcome)
        assert MyState.SUCCESS.value == "my_node::success::done"

    def test_outcome_is_string_enum(self):
        """NodeOutcome should be a string enum."""
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            SUCCESS = "node::success"

        assert isinstance(MyState.SUCCESS, str)
        assert MyState.SUCCESS == "node::success"

    def test_outcome_node_name(self):
        """Should extract node name from outcome."""
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            FETCH_SUCCESS = "fetch_data::success::done"
            FETCH_FAILURE = "fetch_data::failure::http"

        assert MyState.FETCH_SUCCESS.node_name == "fetch_data"
        assert MyState.FETCH_FAILURE.node_name == "fetch_data"

    def test_outcome_type(self):
        """Should extract outcome type (success/failure)."""
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            OK = "node::success::done"
            ERR = "node::failure::error"

        assert MyState.OK.outcome_type == "success"
        assert MyState.ERR.outcome_type == "failure"
        assert MyState.OK.is_success is True
        assert MyState.ERR.is_success is False
        assert MyState.OK.is_failure is False
        assert MyState.ERR.is_failure is True

    def test_outcome_detail(self):
        """Should extract detail from outcome."""
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            SUCCESS_EXIST = "check::success::exist"
            SUCCESS_NOT_EXIST = "check::success::not_exist"

        assert MyState.SUCCESS_EXIST.detail == "exist"
        assert MyState.SUCCESS_NOT_EXIST.detail == "not_exist"

    def test_outcome_hashable(self):
        """NodeOutcome should be hashable."""
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            A = "node::success::a"
            B = "node::success::b"

        state_set = {MyState.A, MyState.B}
        assert MyState.A in state_set
        assert len(state_set) == 2

    def test_outcome_comparison(self):
        """Should support equality comparison."""
        from railway.core.dag.state import NodeOutcome

        class MyState(NodeOutcome):
            A = "node::success::a"

        assert MyState.A == "node::success::a"
        assert MyState.A == MyState.A


class TestExitOutcome:
    """Test ExitOutcome base class."""

    def test_create_exit_enum(self):
        """Should create an Enum subclass of ExitOutcome."""
        from railway.core.dag.state import ExitOutcome

        class MyExit(ExitOutcome):
            SUCCESS = "exit::green::resolved"
            ERROR = "exit::red::error"

        assert issubclass(MyExit, Enum)
        assert MyExit.SUCCESS.value == "exit::green::resolved"

    def test_exit_color(self):
        """Should extract exit color."""
        from railway.core.dag.state import ExitOutcome

        class MyExit(ExitOutcome):
            GREEN = "exit::green::done"
            RED = "exit::red::failed"

        assert MyExit.GREEN.color == "green"
        assert MyExit.RED.color == "red"

    def test_exit_is_success(self):
        """Should determine if exit is successful."""
        from railway.core.dag.state import ExitOutcome

        class MyExit(ExitOutcome):
            GREEN = "exit::green::done"
            RED = "exit::red::failed"

        assert MyExit.GREEN.is_success is True
        assert MyExit.RED.is_success is False

    def test_exit_name(self):
        """Should extract exit name."""
        from railway.core.dag.state import ExitOutcome

        class MyExit(ExitOutcome):
            RESOLVED = "exit::green::resolved"

        assert MyExit.RESOLVED.exit_name == "resolved"


class TestStateHelpers:
    """Test helper functions for state creation."""

    def test_make_success_state(self):
        """Should create a success state string."""
        from railway.core.dag.state import make_state

        state = make_state("fetch_data", "success", "done")
        assert state == "fetch_data::success::done"

    def test_make_failure_state(self):
        """Should create a failure state string."""
        from railway.core.dag.state import make_state

        state = make_state("fetch_data", "failure", "http_error")
        assert state == "fetch_data::failure::http_error"

    def test_make_exit_state(self):
        """Should create an exit state string."""
        from railway.core.dag.state import make_exit

        exit_state = make_exit("green", "resolved")
        assert exit_state == "exit::green::resolved"

    def test_parse_state(self):
        """Should parse a state string into components."""
        from railway.core.dag.state import parse_state

        node, outcome, detail = parse_state("fetch_data::success::done")
        assert node == "fetch_data"
        assert outcome == "success"
        assert detail == "done"

    def test_parse_state_invalid(self):
        """Should raise error for invalid state format."""
        from railway.core.dag.state import parse_state, StateFormatError

        with pytest.raises(StateFormatError):
            parse_state("invalid_format")

        with pytest.raises(StateFormatError):
            parse_state("only::two")
```

```bash
pytest tests/unit/core/dag/test_state.py -v
# Expected: FAILED (ImportError)
```

### Step 2: Green（最小限の実装）

```python
# railway/core/dag/state.py
"""
State and outcome types for DAG nodes.

Provides base classes for node states and exit outcomes,
along with helper functions for state manipulation.
"""
from __future__ import annotations

from enum import Enum
from typing import Tuple


class StateFormatError(ValueError):
    """Error when state format is invalid."""
    pass


class NodeOutcome(str, Enum):
    """
    Base class for node outcome enums.

    Subclasses represent the possible states a node can return.
    The value format is: {node_name}::{outcome_type}::{detail}

    Example:
        class FetchAlertState(NodeOutcome):
            SUCCESS_DONE = "fetch_alert::success::done"
            FAILURE_HTTP = "fetch_alert::failure::http"
    """

    @property
    def node_name(self) -> str:
        """Extract the node name from the state value."""
        parts = self.value.split("::")
        return parts[0] if len(parts) >= 1 else ""

    @property
    def outcome_type(self) -> str:
        """Extract the outcome type (success/failure)."""
        parts = self.value.split("::")
        return parts[1] if len(parts) >= 2 else ""

    @property
    def detail(self) -> str:
        """Extract the detail part of the state."""
        parts = self.value.split("::")
        return parts[2] if len(parts) >= 3 else ""

    @property
    def is_success(self) -> bool:
        """Check if this is a success outcome."""
        return self.outcome_type == "success"

    @property
    def is_failure(self) -> bool:
        """Check if this is a failure outcome."""
        return self.outcome_type == "failure"


class ExitOutcome(str, Enum):
    """
    Base class for exit outcome enums.

    The value format is: exit::{color}::{name}
    Color is typically 'green' (success) or 'red' (failure).

    Example:
        class WorkflowExit(ExitOutcome):
            SUCCESS = "exit::green::resolved"
            ERROR = "exit::red::unhandled"
    """

    @property
    def color(self) -> str:
        """Extract the exit color (green/red)."""
        parts = self.value.split("::")
        return parts[1] if len(parts) >= 2 else ""

    @property
    def exit_name(self) -> str:
        """Extract the exit name."""
        parts = self.value.split("::")
        return parts[2] if len(parts) >= 3 else ""

    @property
    def is_success(self) -> bool:
        """Check if this is a successful exit."""
        return self.color == "green"


def make_state(node_name: str, outcome_type: str, detail: str) -> str:
    """
    Create a state string from components.

    Args:
        node_name: Name of the node
        outcome_type: 'success' or 'failure'
        detail: Specific detail (e.g., 'done', 'http_error')

    Returns:
        Formatted state string
    """
    return f"{node_name}::{outcome_type}::{detail}"


def make_exit(color: str, name: str) -> str:
    """
    Create an exit state string.

    Args:
        color: 'green' or 'red'
        name: Exit name (e.g., 'resolved', 'error')

    Returns:
        Formatted exit string
    """
    return f"exit::{color}::{name}"


def parse_state(state: str) -> Tuple[str, str, str]:
    """
    Parse a state string into components.

    Args:
        state: State string in format {node}::{outcome}::{detail}

    Returns:
        Tuple of (node_name, outcome_type, detail)

    Raises:
        StateFormatError: If format is invalid
    """
    parts = state.split("::")
    if len(parts) != 3:
        raise StateFormatError(
            f"状態文字列の形式が不正です: '{state}' "
            "(期待: 'node::outcome::detail')"
        )
    return parts[0], parts[1], parts[2]


def parse_exit(exit_state: str) -> Tuple[str, str]:
    """
    Parse an exit state string.

    Args:
        exit_state: Exit string in format exit::{color}::{name}

    Returns:
        Tuple of (color, name)

    Raises:
        StateFormatError: If format is invalid
    """
    parts = exit_state.split("::")
    if len(parts) != 3 or parts[0] != "exit":
        raise StateFormatError(
            f"終了状態の形式が不正です: '{exit_state}' "
            "(期待: 'exit::color::name')"
        )
    return parts[1], parts[2]
```

```bash
pytest tests/unit/core/dag/test_state.py -v
# Expected: PASSED
```

### Step 3: Refactor

- 状態文字列のバリデーション強化
- カスタム状態形式のサポート検討

---

## 完了条件

- [ ] `NodeOutcome` が `str, Enum` を継承
- [ ] `node_name`, `outcome_type`, `detail` プロパティ
- [ ] `is_success`, `is_failure` プロパティ
- [ ] `ExitOutcome` が `str, Enum` を継承
- [ ] `color`, `exit_name`, `is_success` プロパティ
- [ ] `make_state()`, `make_exit()` ヘルパー関数
- [ ] `parse_state()`, `parse_exit()` パーサー関数
- [ ] テストカバレッジ90%以上

---

## 次のIssue

- #08: コード生成器実装
