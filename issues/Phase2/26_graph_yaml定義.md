# Issue #26: graph.yaml定義

**Phase:** 2b | **優先度:** 高 | **依存関係:** #21, #22 | **見積もり:** 3日

## 概要
YAML形式でノード間の依存関係を定義し、グラフベースのワークフロー実行を可能にします。

## 実装内容
- graph.yamlのスキーマ定義
- YAMLパーサーとバリデーター
- グラフ構造への変換
- ノード登録レジストリ

## graph.yaml例
\`\`\`yaml
nodes:
  fetch:
    function: src.nodes.fetch_data.fetch
    depends_on: []
  process:
    function: src.nodes.process.process
    depends_on: [fetch]
  save:
    function: src.nodes.save.save
    depends_on: [process]
\`\`\`

## 完了条件
- [x] YAMLスキーマ定義
- [x] パーサー実装
- [x] バリデーション
- [x] テスト 12個以上
- [x] カバレッジ 90%以上
