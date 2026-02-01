# Issue #63: `railway docs --offline` コマンド追加

**優先度**: P2
**依存**: なし
**ブロック**: なし

---

## スコープ外

**本 Issue は v0.13.1 のスコープ外です。v0.13.2 以降で対応予定。**

理由:
- コード生成器修正（v0.13.1 の主目的）と無関係
- 独立した機能追加のため、別バージョンで対応可能
- 優先度 P2（緊急ではない）

---

## 概要

`railway docs` コマンドにオフラインでドキュメントを参照できるオプションを追加する。

## 背景

現在の `railway docs` はブラウザで PyPI を開くだけで、オフライン環境では使用できない。

**現状の問題**:
```bash
railway docs
# → ブラウザで PyPI ページを開く
# → オフラインでは何も表示されない
```

**ユーザーが発見した回避策**:
```bash
cat ~/.local/share/uv/tools/railway-framework/lib/python*/site-packages/railway_framework-*.dist-info/METADATA
```

---

## 提案する改善

```bash
# 既存の動作（デフォルト）
railway docs
# → ブラウザで PyPI を開く

# オフライン参照
railway docs --offline
# → METADATA の README をターミナル出力

# README 部分のみ
railway docs --readme
# → Description 部分のみ出力

# チュートリアル表示
railway docs --tutorial
# → TUTORIAL.md の内容を出力
```

---

## コマンド仕様

| コマンド | 動作 |
|----------|------|
| `railway docs` | ブラウザで PyPI を開く（既存動作） |
| `railway docs --offline` | METADATA 全文をページャーで表示 |
| `railway docs --readme` | Description（README）部分のみ表示 |
| `railway docs --tutorial` | TUTORIAL.md を表示 |

---

## 受け入れ条件

### 機能
- [ ] `--offline` オプションで METADATA を表示
- [ ] `--readme` オプションで README 部分のみ表示
- [ ] `--tutorial` オプションで TUTORIAL.md を表示
- [ ] ページャー（less 等）で長いドキュメントをスクロール可能
- [ ] パッケージが見つからない場合は適切なエラーメッセージ

### TDD・関数型
- [ ] Red → Green → Refactor フェーズに従って実装
- [ ] `extract_description()` は純粋関数
- [ ] 全テスト通過

---

*v0.13.2 以降で対応予定*
