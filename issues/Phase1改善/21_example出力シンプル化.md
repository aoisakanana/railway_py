# Issue #21: --example 出力のシンプル化

## 優先度: 低

## 概要

`railway new entry --example` の出力が複雑すぎる。チュートリアルでは「Hello, World!」レベルのシンプルな出力を期待しているが、実際には複雑な fetch_data/process_data パイプラインが生成される。

## 対応方法

**Issue #18 の実装により解決**

Issue #18で以下の変更を行うため、本Issueは対応不要:

1. `railway init` がデフォルトでシンプルな `hello.py` を生成
2. TUTORIAL.md は `--example` なしで実行可能に
3. `--with-examples` オプションで複雑な例を生成（上級者向け）

## 状態

**対応不要** - Issue #18 に統合
