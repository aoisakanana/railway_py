# Issue #08: TUTORIAL.md 更新

## 概要

Phase2（#01-#06）で実装されるバージョン管理機能を `TUTORIAL.md` に反映する。
ユーザーが**実際に手を動かして恩恵を体験できる**Step 9を追加する。

## 現状

現在のTUTORIAL.mdは以下の構成:
- Step 1-7: 基本機能（Contract, Node, TDD, IDE補完, typed_pipeline, リファクタリング）
- Step 8: エラーハンドリング
- FAQ, Next Steps, Troubleshooting

Phase2の機能が未掲載:
- `.railway/project.yaml`（バージョン追跡）
- `railway update`（マイグレーション）
- `railway backup`（バックアップ・ロールバック）

## 設計方針

### 体験設計の原則

1. **恩恵ファースト**: 「何ができるか」ではなく「何が嬉しいか」から始める
2. **ハンズオン**: 読むだけでなく、実際にコマンドを実行する
3. **失敗→成功**: 問題を先に見せてから解決策を体験
4. **所要時間明記**: 各Stepに時間目安を記載

### 追加するStep

```
Step 9: バージョン管理 - 安全なアップグレード体験（5分）
```

**コンセプト**: フレームワークのバージョンアップ時に、プロジェクトが安全に追従できることを体験

## 目標: Step 9の内容

### Step 9: バージョン管理 - 安全なアップグレード体験（5分）

Railway Framework は**プロジェクトのバージョンを追跡**し、安全なアップグレードを支援します。

#### 9.1 現状を確認

まず、プロジェクトのバージョン情報を確認します:

```bash
cat .railway/project.yaml
```

**出力例:**
```yaml
railway:
  version: "0.10.0"
  created_at: "2026-01-23T10:30:00+09:00"
  updated_at: "2026-01-23T10:30:00+09:00"

project:
  name: "my_project"

compatibility:
  min_version: "0.10.0"
```

**ポイント:**
- `railway init` 時に自動生成される
- チーム全員で同じバージョン情報を共有（Git管理対象）

---

#### 9.2 体験: バージョン不一致の警告

将来、railway-framework がアップグレードされた状況をシミュレートします。

**シナリオ**: v0.11.0 にアップグレード後、新しいノードを追加しようとする

```bash
# バージョン情報を一時的に古くする（シミュレーション用）
# 注意: 本番では手動編集は不要です
```

実際の開発では、以下のような警告が表示されます:

```
$ railway new node my_new_node

⚠️  バージョン不一致を検出
    プロジェクト: 0.10.0
    現在:         0.11.0

    マイナーバージョンが異なります。
    テンプレートが更新されている可能性があります。

    [c] 続行 / [u] 'railway update' を実行 / [a] 中止
```

**なぜ重要か:**
- **チームの不整合防止**: 古いテンプレートと新しいテンプレートの混在を防ぐ
- **意図しない変更の防止**: 警告なしに新形式が適用されることを防ぐ

---

#### 9.3 体験: railway update でマイグレーション

`railway update` でプロジェクトを最新バージョンに更新できます:

```bash
railway update --dry-run
```

**出力例:**
```
🔍 プロジェクトを分析中...

   プロジェクト名:      my_project
   現在のバージョン:    0.10.0
   ターゲットバージョン: 0.11.0

📋 適用される変更:

   [設定更新]
   ~ config/development.yaml
     - 新規キー: railway.new_feature

[dry-run] 実際の変更は行われませんでした。
実行するには: railway update
```

**ポイント:**
- `--dry-run` で事前に変更内容を確認できる
- ユーザーコード（`src/nodes/*`）は**変更されない**

実際に更新を適用:

```bash
railway update
```

**出力例:**
```
...
続行しますか? [y/N]: y

💾 バックアップ作成: .railway/backups/0.10.0_20260123_103000/

✅ 更新完了
   バックアップ: .railway/backups/0.10.0_20260123_103000/
   新バージョン: 0.11.0
```

---

#### 9.4 体験: バックアップから復元

問題が発生した場合は、簡単に元に戻せます:

```bash
# バックアップ一覧を確認
railway backup list
```

**出力例:**
```
利用可能なバックアップ:
  [1] 0.10.0_20260123_103000  たった今   15KB
```

```bash
# 復元
railway backup restore
```

**出力例:**
```
どのバックアップに戻しますか? [1]: 1

0.10.0_20260123_103000 に戻しますか? [y/N]: y

✅ ロールバック完了: 0.10.0
   復元ファイル数: 3
```

---

#### 9.5 恩恵のまとめ

| 従来の問題 | Railway の解決策 |
|-----------|------------------|
| バージョン不明でチームが混乱 | `.railway/project.yaml` で明示 |
| 手動マイグレーションが面倒 | `railway update` で自動化 |
| 失敗したら戻せない | 自動バックアップ + `railway backup restore` |
| 変更内容が分からない | `--dry-run` で事前確認 |

**設計思想:**

- **安全第一**: 更新前に自動バックアップ
- **透明性**: 何が変更されるか事前表示
- **ユーザーコード不変更**: `src/nodes/*` は絶対に変更しない

🎉 **これでバージョンアップも安心！** 次のステップに進みましょう。

---

## 実装

### 1. `railway/cli/init.py` の `_create_tutorial_md` 関数を修正

#### 関数型パラダイム: コンテンツ生成の分離

```python
# 純粋関数: Step 9 のコンテンツを生成
def _generate_step_9_content(project_name: str, version: str) -> str:
    """Step 9（バージョン管理）のコンテンツを生成する純粋関数。

    Args:
        project_name: プロジェクト名
        version: railway-framework バージョン

    Returns:
        Step 9 のMarkdownコンテンツ
    """
    return f'''
## Step 9: バージョン管理 - 安全なアップグレード体験（5分）
... (テンプレート内容、{project_name} と {version} を埋め込み)
'''

# _create_tutorial_md 関数内で呼び出し
def _create_tutorial_md(project_path: Path, project_name: str) -> None:
    from railway import __version__

    step_9 = _generate_step_9_content(project_name, __version__)
    # ... 既存のコンテンツに step_9 を追加
```

#### 追加位置

Step 8（エラーハンドリング）の後、FAQ の前に Step 9 を追加:

```python
## Step 8: エラーハンドリング（実践）
...
---

## Step 9: バージョン管理（5分）  ← 追加

... (Step 9 の内容)

---

## よくある質問 (FAQ)
```

#### 追加するコード

```python
# _create_tutorial_md 関数内の content に追加

STEP_9_CONTENT = '''
## Step 9: バージョン管理 - 安全なアップグレード体験（5分）

Railway Framework は**プロジェクトのバージョンを追跡**し、安全なアップグレードを支援します。

### 9.1 現状を確認

プロジェクトのバージョン情報を確認します:

```bash
cat .railway/project.yaml
```

**出力例:**
```yaml
railway:
  version: "{version}"
  created_at: "2026-01-23T10:30:00+09:00"
  updated_at: "2026-01-23T10:30:00+09:00"

project:
  name: "{project_name}"

compatibility:
  min_version: "{version}"
```

**ポイント:**
- `railway init` 時に自動生成される
- チーム全員で同じバージョン情報を共有（Git管理対象）

---

### 9.2 バージョン不一致の警告

フレームワークがアップグレードされた後に `railway new` を実行すると:

```
$ railway new node my_new_node

⚠️  バージョン不一致を検出
    プロジェクト: 0.10.0
    現在:         0.11.0

    [c] 続行 / [u] 'railway update' を実行 / [a] 中止
```

**なぜ重要か:**
- 古いテンプレートと新しいテンプレートの混在を防ぐ
- チーム内の不整合を防止

---

### 9.3 railway update でマイグレーション

プロジェクトを最新バージョンに更新:

```bash
# まず変更内容をプレビュー
railway update --dry-run

# 実際に更新
railway update
```

**ポイント:**
- `--dry-run` で事前確認
- 更新前に自動バックアップ
- ユーザーコード（`src/nodes/*`）は変更されない

---

### 9.4 バックアップから復元

問題が発生した場合は簡単に復元:

```bash
# 一覧表示
railway backup list

# 復元
railway backup restore
```

---

### 9.5 恩恵のまとめ

| 問題 | Railway の解決策 |
|------|------------------|
| バージョン不明 | `.railway/project.yaml` で明示 |
| 手動マイグレーション | `railway update` で自動化 |
| 失敗時のリカバリ | 自動バックアップ + 復元 |
| 変更内容不明 | `--dry-run` で事前確認 |

🎉 **これでバージョンアップも安心！**
'''
```

### 2. 「学べること」セクションに追加

```python
# 既存
- typed_pipeline による依存関係の自動解決

# 追加
- バージョン管理と安全なアップグレード
```

### 3. 「学んだこと」セクション（次のステップ）に追加

```python
# 既存
- **on_step でデバッグ/監査**

# 追加
- **バージョン管理** (`railway update`, `railway backup`)
```

### 4. FAQに追加

```python
### Q: 既存プロジェクトにバージョン情報を追加するには？

```bash
railway update --init
```

これにより `.railway/project.yaml` が作成され、バージョン追跡が開始されます。

### Q: バージョン不一致の警告を無視して続行できる？

`--force` オプションで警告をスキップできます:

```bash
railway new node my_node --force
```

ただし、チーム開発では推奨しません。`railway update` で先にプロジェクトを更新してください。
```

## テスト

### 追加するテストファイル

`tests/unit/cli/test_tutorial_version_management.py`:

```python
"""Tests for TUTORIAL.md version management section."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestTutorialVersionManagementSection:
    """Test that TUTORIAL includes version management content."""

    def test_tutorial_has_step_9(self):
        """TUTORIAL should have Step 9 for version management."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                assert "Step 9" in content
                assert "バージョン管理" in content
            finally:
                os.chdir(original_cwd)

    def test_tutorial_mentions_railway_update(self):
        """TUTORIAL should explain railway update command."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                assert "railway update" in content
                assert "--dry-run" in content
            finally:
                os.chdir(original_cwd)

    def test_tutorial_mentions_railway_backup(self):
        """TUTORIAL should explain railway backup command."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                assert "railway backup" in content
                assert "restore" in content.lower()
            finally:
                os.chdir(original_cwd)

    def test_tutorial_explains_project_yaml(self):
        """TUTORIAL should explain .railway/project.yaml."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                assert ".railway/project.yaml" in content or "project.yaml" in content
            finally:
                os.chdir(original_cwd)

    def test_tutorial_shows_benefits_table(self):
        """TUTORIAL should show benefits of version management."""
        from railway.cli.main import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner.invoke(app, ["init", "test_project"])

                tutorial_md = Path(tmpdir) / "test_project" / "TUTORIAL.md"
                content = tutorial_md.read_text()

                # Should have a comparison table
                assert "Railway の解決策" in content or "解決" in content
            finally:
                os.chdir(original_cwd)
```

### 確認項目

- [ ] Step 9 が Step 8 の後、FAQ の前に配置されている
- [ ] `cat .railway/project.yaml` のコマンド例がある
- [ ] `railway update --dry-run` のコマンド例がある
- [ ] `railway backup list` / `restore` のコマンド例がある
- [ ] 恩恵のまとめ表がある
- [ ] 「学べること」に「バージョン管理」が追加されている
- [ ] 「学んだこと」に「バージョン管理」が追加されている
- [ ] FAQ に関連する質問が追加されている

## 依存関係

- #01 プロジェクトバージョン記録（`.railway/project.yaml` 生成）
- #02 バージョン互換性チェック（警告メッセージの文言）
- #03 railway updateコマンド基本実装（コマンドインターフェース）
- #04 マイグレーション戦略設計（変更の概念：ファイル追加/更新/削除）
- #05 バックアップ・ロールバック機能（バックアップコマンド）
- #06 Dry-runモード実装（`--dry-run` オプション）

**Note**: `railway init` 時に `.railway/project.yaml` を生成する #01 の完了後に実装可能。

## 優先度

**低** - 機能実装完了後のドキュメント作業

## 補足: 体験設計のポイント

### なぜこの構成にしたか

1. **9.1 現状確認**: まず「何が生成されているか」を見せる（驚き）
2. **9.2 警告体験**: 問題のシナリオを提示（共感）
3. **9.3 解決策**: `railway update` で解決（納得）
4. **9.4 安心感**: バックアップ・復元で安心（信頼）
5. **9.5 まとめ**: 恩恵を表で整理（記憶）

### シンプルさの維持

- コマンドは最小限（`update`, `backup list`, `backup restore`）
- オプションは代表的なもののみ（`--dry-run`, `--init`）
- 詳細はREADMEやドキュメントに委ねる
