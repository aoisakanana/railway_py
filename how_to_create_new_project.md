# railway-framework を使った新規プロジェクトの作成手順

## 前提条件

- Python 3.10以上がインストールされていること
- uvがインストールされていること

uvがない場合は以下でインストール:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## 手順

### 1. railway-framework をグローバルにインストール

```bash
uv tool install railway-framework
```

これにより `railway` コマンドが使えるようになります。

### 2. プロジェクトを作成

```bash
railway init my-project
```

これにより以下の構造が生成されます:
```
my-project/
├── src/
│   ├── nodes/
│   ├── common/
│   └── settings.py
├── tests/
├── config/
│   └── development.yaml
├── pyproject.toml
├── .env.example
├── .gitignore
└── TUTORIAL.md
```

### 3. プロジェクトディレクトリに移動

```bash
cd my-project
```

### 4. 依存関係をインストール

```bash
uv sync
```

### 5. 環境設定

```bash
cp .env.example .env
```

### 6. Hello Worldを実行

```bash
# サンプルのエントリポイントを作成
railway new entry hello --example

# 実行
uv run railway run hello
```

## 補足: 仮想環境について

uvは自動的に `.venv` ディレクトリに仮想環境を作成・管理します。
手動でアクティベートする必要はありません。`uv run` を使えば自動的に仮想環境内で実行されます。

手動でアクティベートしたい場合:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```
