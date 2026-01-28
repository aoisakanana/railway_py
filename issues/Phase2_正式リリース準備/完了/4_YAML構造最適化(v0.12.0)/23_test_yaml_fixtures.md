# Issue #23: テスト用 YAML フィクスチャ作成

**Phase:** 2
**優先度:** 高
**依存関係:** なし（最初に着手）
**見積もり:** 0.25日

---

## 概要

Issue #24-30 の実装に先立ち、テスト用の YAML フィクスチャを作成する。
TDD で実装を進めるため、テストデータが最初に必要。

---

## 作成場所

```
tests/fixtures/transition_graphs/
├── exit_node/
│   ├── basic_exit.yml           # 基本的な終端ノード
│   ├── nested_exit.yml          # ネストした終端ノード
│   ├── deep_nested_exit.yml     # 深いネストの終端ノード
│   ├── auto_resolve.yml         # module/function 自動解決
│   ├── explicit_override.yml    # 明示的な module/function 指定
│   ├── custom_exit_code.yml     # カスタム終了コード
│   └── multiple_exits.yml       # 複数の終端ノード
└── invalid/
    └── invalid_exit_path.yml    # 不正な終端パス
```

**Note:** 後方互換性は不要のため、legacy/ ディレクトリは作成しない。

---

## フィクスチャ定義

### 1. basic_exit.yml

最小限の終端ノード構造。TDD の基本テストケース。

```yaml
version: "1.0"
entrypoint: basic_exit_test
description: "基本的な終端ノードテスト"

# 開始ノードを最初に明示（分かりやすさのため）
start: initialize

nodes:
  # 通常ノード
  initialize:
    description: "初期化ノード"

  # 終端ノード（nodes.exit 配下）
  exit:
    success:
      done:
        description: "正常終了"
    failure:
      error:
        description: "異常終了"

transitions:
  initialize:
    success::done: exit.success.done
    failure::error: exit.failure.error
```

**Note:** `start` フィールドはノード名と紛らわしいため、開始ノードには `initialize` のような明確な名前を推奨。

### 2. nested_exit.yml

同一カテゴリ内に複数の終端。

```yaml
version: "1.0"
entrypoint: nested_exit_test
description: "ネストした終端ノードテスト"

nodes:
  process:
    description: "処理ノード"

  exit:
    success:
      done:
        description: "正常終了"
      skipped:
        description: "スキップ終了"
    failure:
      timeout:
        description: "タイムアウト"
      validation:
        description: "バリデーションエラー"

start: process

transitions:
  process:
    success::done: exit.success.done
    success::skipped: exit.success.skipped
    failure::timeout: exit.failure.timeout
    failure::validation: exit.failure.validation
```

### 3. deep_nested_exit.yml

3階層以上の深いネスト。エラーの詳細分類に使用。

```yaml
version: "1.0"
entrypoint: deep_nested_exit_test
description: "深いネストの終端ノードテスト"

nodes:
  start:
    description: "開始"

  exit:
    success:
      done:
        description: "正常終了"

    failure:
      ssh:
        handshake:
          description: "SSHハンドシェイク失敗"
        authentication:
          description: "SSH認証失敗"
        unknown_host:
          description: "不明なホスト"
      api:
        request:
          bad_format:
            description: "リクエスト形式エラー"
          dns:
            description: "DNS解決失敗"
        response:
          timeout:
            description: "レスポンスタイムアウト"
          parse_error:
            description: "レスポンスパースエラー"

start: start

transitions:
  start:
    success::done: exit.success.done
    failure::ssh_handshake: exit.failure.ssh.handshake
    failure::ssh_auth: exit.failure.ssh.authentication
    failure::api_dns: exit.failure.api.request.dns
    failure::api_timeout: exit.failure.api.response.timeout
```

### 4. auto_resolve.yml

module/function の自動解決テスト。

```yaml
version: "1.0"
entrypoint: auto_resolve_test
description: "module/function 自動解決テスト"

nodes:
  # module/function 省略 → 自動解決
  start_process:
    description: "開始ノード"

  validate_input:
    description: "入力検証"

  exit:
    success:
      done:
        description: "正常終了"

start: start_process

transitions:
  start_process:
    success::done: validate_input

  validate_input:
    success::done: exit.success.done
```

### 5. explicit_override.yml

明示的な module/function 指定が自動解決より優先されることを検証。

```yaml
version: "1.0"
entrypoint: explicit_override_test
description: "明示的な module/function 指定テスト"

nodes:
  # module のみ明示
  process:
    module: custom.module.path
    description: "カスタムモジュール"

  exit:
    success:
      # function を明示（キー名と異なる）
      session_check:
        module: nodes.exit.handlers
        function: notify_and_exit
        description: "セッションチェック後終了"

start: process

transitions:
  process:
    success::done: exit.success.session_check
```

### 6. custom_exit_code.yml

カスタム終了コードのテスト。

```yaml
version: "1.0"
entrypoint: custom_exit_code_test
description: "カスタム終了コードテスト"

nodes:
  start:
    description: "開始"

  exit:
    success:
      done:
        description: "正常終了"
        # exit_code 省略 → 0

    failure:
      error:
        description: "異常終了"
        # exit_code 省略 → 1

    warning:
      low_disk:
        description: "ディスク容量警告"
        exit_code: 2

      high_memory:
        description: "メモリ使用量警告"
        exit_code: 3

start: start

transitions:
  start:
    success::done: exit.success.done
    warning::low_disk: exit.warning.low_disk
    warning::high_memory: exit.warning.high_memory
    failure::error: exit.failure.error
```

### 7. multiple_exits.yml

複数の終端ノードを持つ現実的なワークフロー。

```yaml
version: "1.0"
entrypoint: multiple_exits_test
description: "複数終端ノードテスト"

nodes:
  fetch_data:
    description: "データ取得"

  validate:
    description: "検証"

  transform:
    description: "変換"

  save:
    description: "保存"

  exit:
    success:
      complete:
        description: "完全成功"
      partial:
        description: "部分成功"
      dry_run:
        description: "ドライラン完了"

    failure:
      fetch:
        description: "取得失敗"
      validation:
        description: "検証失敗"
      transform:
        description: "変換失敗"
      save:
        description: "保存失敗"

start: fetch_data

transitions:
  fetch_data:
    success::done: validate
    failure::error: exit.failure.fetch

  validate:
    success::done: transform
    success::skip: exit.success.dry_run
    failure::error: exit.failure.validation

  transform:
    success::done: save
    success::partial: save
    failure::error: exit.failure.transform

  save:
    success::done: exit.success.complete
    success::partial: exit.success.partial
    failure::error: exit.failure.save
```

---

## エラーケースフィクスチャ

### invalid/invalid_exit_path.yml

遷移先が存在しない終端パスを参照。バリデーションエラーのテスト。

```yaml
version: "1.0"
entrypoint: invalid_exit_path_test
description: "不正な終端パステスト"

nodes:
  start:
    description: "開始"

  exit:
    success:
      done:
        description: "正常終了"

start: start

transitions:
  start:
    success::done: exit.success.nonexistent  # ← 存在しない
```

---

## 実装手順

### Step 1: ディレクトリ作成

```bash
mkdir -p tests/fixtures/transition_graphs/exit_node
mkdir -p tests/fixtures/transition_graphs/invalid
```

### Step 2: YAML ファイル作成

上記の定義に従って各ファイルを作成。

### Step 3: フィクスチャ読み込みヘルパー追加

```python
# tests/conftest.py に追加

import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "transition_graphs"


@pytest.fixture
def exit_node_fixtures() -> Path:
    """終端ノードテスト用フィクスチャディレクトリ。"""
    return FIXTURES_DIR / "exit_node"


@pytest.fixture
def invalid_fixtures() -> Path:
    """無効な YAML テスト用フィクスチャディレクトリ。"""
    return FIXTURES_DIR / "invalid"


def load_fixture(fixture_dir: Path, name: str) -> Path:
    """フィクスチャファイルのパスを取得（純粋関数）。

    Args:
        fixture_dir: フィクスチャディレクトリ
        name: ファイル名

    Returns:
        フィクスチャファイルのパス

    Raises:
        FileNotFoundError: ファイルが存在しない場合
    """
    path = fixture_dir / name
    if not path.exists():
        raise FileNotFoundError(f"Fixture not found: {path}")
    return path
```

### Step 4: YAML 構文検証

```bash
# yamllint で構文チェック
yamllint tests/fixtures/transition_graphs/exit_node/*.yml
yamllint tests/fixtures/transition_graphs/invalid/*.yml
```

---

## 完了条件

- [ ] `tests/fixtures/transition_graphs/exit_node/` 配下に 7 ファイル作成
- [ ] `tests/fixtures/transition_graphs/invalid/` 配下に 1 ファイル作成
- [ ] conftest.py にフィクスチャヘルパー追加
- [ ] 各 YAML が構文的に正しい（YAML lint 通過）

---

## 関連 Issue

- Issue #24-30: すべての実装 Issue がこのフィクスチャを使用
- [000_YAML構造変更実装計画.md](./000_YAML構造変更実装計画.md)
