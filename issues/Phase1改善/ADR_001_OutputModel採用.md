# ADR-001: Output Model パターンの採用

**日付**: 2026-01-19
**ステータス**: 採用
**決定者**: 開発チーム

---

## コンテキスト

Railway Framework v0.7.0のレビューにおいて、以下の問題が指摘された：

1. **遷移依存**: nodeが直前のnodeの出力形式に依存し、実行順序を変更するとnodeの実装も変更が必要
2. **構造依存**: Context変数案でも、nodeが他nodeの内部データ構造に依存する問題が残存

## 検討した選択肢

### 選択肢A: Context変数アーキテクチャ

```python
@node
def fetch_data(ctx: Context) -> None:
    ctx["fetch_data"] = {"user": get_user(ctx.get_param("user_id"))}

@node
def process_data(ctx: Context) -> None:
    user = ctx["fetch_data"]["user"]  # 構造依存
    ctx["process_data"] = {"processed": transform(user)}
```

**メリット**:
- シンプルなAPI
- 学習コストが低い
- 遷移依存を解消

**デメリット**:
- 構造依存が残る（`ctx["fetch_data"]["user"]`）
- 型安全性がない（Any型）
- IDE補完が効かない
- nodeが純粋関数でない（副作用あり）

### 選択肢B: Output Model パターン

```python
class UsersFetchResult(Contract):
    user: User

@node(output=UsersFetchResult)
def fetch_data() -> UsersFetchResult:
    return UsersFetchResult(user=get_user())

@node(inputs={"data": UsersFetchResult}, output=ProcessResult)
def process_data(data: UsersFetchResult) -> ProcessResult:
    return ProcessResult(processed=transform(data.user))
```

**メリット**:
- 遷移依存を解消
- 構造依存を解消（型契約のみに依存）
- 型安全性（Pydantic + mypy）
- IDE補完が効く
- nodeが純粋関数
- テストが容易（引数渡しのみ）

**デメリット**:
- 学習コストがやや高い
- Contract定義のボイラープレート
- ファイル数が増える

## 決定

**選択肢B: Output Model パターンを採用する**

## 理由

1. **本質的な問題解決**: Context変数案は「遷移依存」のみを解消するが、「構造依存」が残る。Output Modelパターンは両方を解消する。

2. **型安全性**: 現代のPython開発において、型安全性は生産性と保守性に直結する。Pydanticによる実行時検証とmypyによる静的解析は、バグの早期発見に不可欠。

3. **純粋関数**: nodeが純粋関数になることで：
   - テストが容易（モック不要）
   - 理解が容易（副作用なし）
   - 再利用が容易

4. **IDE体験**: 開発者の大半はIDEを使用する。補完・リファクタリング・型チェックが効くことは、開発効率に大きく影響する。

5. **後方互換性**: 旧スタイル（Context直接操作）も引き続きサポートするため、段階的な移行が可能。

6. **学習コストの軽減**: CLIによるContract/Node自動生成で、ボイラープレートの負担を軽減できる。

## 影響

### 変更が必要なもの
- nodeデコレータの拡張
- pipeline関数の改修
- CLI（Contract/Node生成）
- ドキュメント・チュートリアル

### 後方互換性
- 旧スタイルのnodeは非推奨として引き続き動作
- v1.0.0で非推奨警告
- v2.0.0で廃止（検討中）

## 関連Issue
- #01: Output Model基本設計
- #02: Contractベースクラス実装
- #03: nodeデコレータ拡張
- #04: 依存解決とパイプライン改修
- #05: CLI拡張

## 参考
- [旧Context案](./旧Context案/) - 比較検討のため保存
