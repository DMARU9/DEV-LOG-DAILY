# DevLogDaily

開発者の日々の学びと活動を、Copilot/Git/ターミナルログから自動で構造化・日報化するCLIツール。

**LangGraph StateGraph** によるパイプラインオーケストレーションで、収集 → 解析 → 補完 → 生成 の4ノードを逐次実行。各コンポーネントは独立したLLMモデルを設定可能。

---

## 特徴

- **🤖 自動収集**: GitHub Copilotチャットログ、Gitコミット、ターミナル操作履歴から自動収集
- **🧠 LLM解析**: 収集データをLLMで構造化・要約・カテゴリ抽出
- **📝 Markdown日報**: 「概要」「使用技術」「学習内容」「開発活動」「問題と解決策」の5セクションで出力
- **⚙️ 設定駆動**: YAML設定ファイルで各コンポーネントのLLMモデルを個別に指定可能
- **🔒 ローカル完結**: 全処理がローカルで完結。外部送信はデフォルト無効

---

## インストール

### Wheel からのインストール（推奨）

GitHub Releases から Wheel をダウンロードしてインストールします。

```bash
# pip の場合（ローカルファイルから）
pip install dev_log_daily-<version>-py3-none-any.whl

# pip の場合（GitHub Releases から直接）
pip install https://github.com/DMARU9/DEV-LOG-DAILY/releases/download/v<version>/dev_log_daily-<version>-py3-none-any.whl

# uv の場合（ローカルファイルから）
uv tool install dev_log_daily-<version>-py3-none-any.whl

# uv の場合（GitHub Releases から直接）
uv tool install https://github.com/DMARU9/DEV-LOG-DAILY/releases/download/v<version>/dev_log_daily-<version>-py3-none-any.whl
```

インストール後、コマンドが使用可能になります:

```bash
dev-log-daily --help
dev-log-daily init --help
```

### 開発環境セットアップ（ソースから）

```bash
# リポジトリのクローン
git clone git@github.com:DMARU9/DEV-LOG-DAILY.git
cd DEV-LOG-DAILY

# 仮想環境の作成
python3 -m venv .venv
source .venv/bin/activate

# 依存関係のインストール
pip install -e ".[dev]"

# pre-commit フックのインストール
pre-commit install
```

---

## 設定

`config.yml` を作成し、環境に合わせて編集します。

```yaml
llm:
  collector:
    model: Qwen3.6-35B-A3B
    base_url: http://localhost:8080/v1
    api_key: not-needed
  parser:
    model: Qwen3.6-35B-A3B
    base_url: http://localhost:8080/v1
    api_key: not-needed
  enricher:
    model: Qwen3.6-35B-A3B
    base_url: http://localhost:8080/v1
    api_key: not-needed
  reporter:
    model: Qwen3.6-35B-A3B
    base_url: http://localhost:8080/v1
    api_key: not-needed

data_sources:
  copilot_chat_dir: /path/to/copilot/transcripts
  git_root_dir: /path/to/git/repos/parent
  terminal_history_file: /home/user/.bash_history

output:
  directory: /path/to/output

timeout_seconds: 0  # 0=無制限待機（ローカルLLM推奨）
```

### 設定項目

| 項目 | 必須 | 説明 |
|------|------|------|
| `llm.collector` | ✅ | データ収集ツール用LLM |
| `llm.parser` | ✅ | データ解析用LLM |
| `llm.enricher` | ✅ | クロスリファレンス・補完用LLM |
| `llm.reporter` | ✅ | 日報生成用LLM |
| `data_sources.copilot_chat_dir` | ✅ | Copilotチャットログディレクトリ |
| `data_sources.git_root_dir` | ✅ | Gitリポジトリ親ディレクトリ |
| `data_sources.terminal_history_file` | ✅ | ターミナル履歴ファイル |
| `output.directory` | ✅ | 日報出力ディレクトリ |
| `timeout_seconds` | ❌ | LLMリクエストタイムアウト（秒）。0で無制限待機（デフォルト: 600） |

---

## 実行方法

### 前日の日報を生成

```bash
dev-log-daily --config config.yml
```

### 特定日の日報を生成

```bash
dev-log-daily --config config.yml --date 2026-06-19
```

### 出力例

```text
============================================================
Dev Log Daily - 日報生成パイプライン
============================================================
対象日: 2026-06-19

[Collector] データ収集を開始します...
[Collector] Copilotチャットログ収集完了: 5件のセッション
[Collector] Gitコミット収集完了: 3件のコミット
[Collector] ターミナル履歴収集完了: 150行
[Collector] 全データソースの収集が完了しました

[Parser] データ解析を開始します...
[Parser] Copilotチャットログ解析完了 (1500 tokens)
[Parser] Gitコミット解析完了 (800 tokens)
[Parser] ターミナル履歴解析完了 (600 tokens)
[Parser] 全データソースの解析が完了しました

[Enricher] クロスリファレンス・補完を開始します...
[Enricher] クロスリファレンス・補完完了 (400 tokens)

[Reporter] 日報を生成中...
[Reporter] 日報生成完了 (2500 tokens)

============================================================
日報生成完了！
出力先: /path/to/output/daily_report_2026-06-19.md
============================================================
```

### 生成される日報

```markdown
# デイリー学習レポート - 2026-06-19

## 📋 概要
（2〜3文の開発活動要約）

## 🛠 本日触れた技術・ツール
- **カテゴリ名**
  - 技術名: 何をしたか・何を学んだか

## 📚 学習内容
- **トピック**: 説明

## 💻 開発活動
- **プロジェクト名**
  - 作業内容

## 🔧 発生した問題と解決策
- **問題**: 説明
  - 解決策: 説明
```

---

## 終了コード

| コード | 意味 |
|--------|------|
| `0` | 正常終了（日報生成成功 / 対象データなし） |
| `1` | 起動時エラー（設定ファイル未指定・不正・出力ディレクトリ不在） |
| `2` | LLMエラー（LLM永続エラー・全リトライ失敗） |
| `3` | 全データソース収集失敗 |

---

## ログ収集のセットアップ

`dev-log-daily init` コマンドで、パッケージに同梱されたセットアップ手順やスクリプトを利用できます。

### セットアップガイドの表示

```bash
dev-log-daily init --guide
```

ターミナルログ収集と Git post-commit hook のセットアップ手順が表示されます。

### スクリプトのパス確認

```bash
dev-log-daily init --show-paths
```

### post-commit sample のエクスポート

```bash
dev-log-daily init --export-post-commit /path/to/project/.git/hooks/
mv /path/to/project/.git/hooks/post-commit.sample /path/to/project/.git/hooks/post-commit
chmod +x /path/to/project/.git/hooks/post-commit
```

### ログ出力先構造

```
ログ出力先ディレクトリ
├── terminal/{project}/history_YYYY-MM-DD.jsonl   # コマンド履歴
├── git/{project}/commits.jsonl                    # commit メタデータ
└── diff/{project}/{commit}.patch                  # commit 差分
```

---

## トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| `設定ファイルが見つかりません` | `--config` 未指定 | `--config` で設定ファイルパスを指定 |
| `出力ディレクトリが存在しません` | 出力先ディレクトリ不在 | ディレクトリを作成するか設定を修正 |
| `LLM呼び出しエラー (HTTP 401)` | APIキー不正 | 設定ファイルの `api_key` を確認 |
| `LLM呼び出しエラー (HTTP 503)` + リトライ失敗 | LLMサーバーダウン | LLMサーバーの起動状態を確認 |
| `タイムアウト` | ローカルLLMが遅い / ログが巨大 | `timeout_seconds` を増やす、または 0 で無制限待機 |

---

## 開発

### テストの実行

```bash
# 全テスト
pytest

# 単体テストのみ
pytest tests/unit/

# 結合テストのみ
pytest tests/integration/

# カバレッジレポート
pytest --cov=src/dev_log_daily
```

### 型チェック

```bash
pyright src/
```

### コード整形・lint

```bash
# isort（インポート順）
isort src/ tests/

# ruff（linter）
ruff check src/ tests/

# 自動修正
ruff check --fix src/ tests/
```

---

## プロジェクト構成

```
src/dev_log_daily/
├── main.py              # CLI エントリポイント（click）
├── agent.py             # LangGraph StateGraph 定義・パイプライン構築
├── state.py             # DailyState TypedDict 定義
├── tools/               # データソースツール（収集・解析）
│   ├── base.py          # DataSourceTool 抽象基底クラス
│   ├── copilot_chat.py  # Copilotチャットログ収集・解析
│   ├── git_commits.py   # Gitコミット収集・解析
│   └── terminal_logs.py # ターミナル履歴収集・解析
├── pipeline/            # パイプラインノード
│   ├── collector.py     # Collector ノード（並列収集）
│   ├── parser.py        # Parser ノード（LLM解析）
│   ├── enricher.py      # Enricher ノード（クロスリファレンス）
│   └── reporter.py      # Reporter ノード（日報生成）
├── config/              # 設定管理
│   ├── schema.py        # pydantic 設定スキーマ
│   └── loader.py        # YAML設定ファイル読み込み・検証
├── llm/                 # LLM制御
│   ├── client.py        # LLMクライアント（リトライ・タイムアウト）
│   └── chunking.py      # トークン分割・Map-Reduce要約
├── prompts/             # プロンプト管理
│   ├── system.py        # システムプロンプト
│   └── templates.py     # コンポーネント別テンプレート
└── utils/               # ユーティリティ
    ├── date.py          # 日付計算
    ├── file.py          # ファイルI/O
    └── logging.py       # ロギング設定
```

