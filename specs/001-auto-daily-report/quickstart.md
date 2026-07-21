# Quickstart: 開発活動ログ自動収集・日報生成フレームワーク

**Date**: 2026-06-20 | **Feature**: 001-auto-daily-report

---

## 前提条件

- Python 3.11 以上
- llama.cpp サーバーが起動済み（または OpenAI 互換 API エンドポイントが利用可能）
- 以下のデータがローカルに存在すること：
  - GitHub Copilot チャットログ（JSONL ファイル群）
  - Git リポジトリ（指定された親ディレクトリ配下）
  - ターミナル履歴ファイル（`.bash_history` など）

---

## セットアップ

### 1. インストール

```bash
# pip でインストール
pip install dev-log-daily

# または uv でインストール
uv tool install dev-log-daily
```

### 2. 設定ファイルの作成

`config.yml` を作成し、環境に合わせて編集する：

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

timeout_seconds: 600
```

### 3. 出力ディレクトリの確認

```bash
mkdir -p /path/to/output
```

設定ファイルの `output.directory` が存在しない場合、起動時にエラーとなる。

---

## 実行

### 前日の日報を生成

```bash
dev-log-daily --config config.yml
```

### 特定日の日報を生成

```bash
dev-log-daily --config config.yml --date 2026-06-19
```

---

## 検証シナリオ

### シナリオ 1: 全データソースが存在する正常系

```bash
# 実行
dev-log-daily --config config.yml --date 2026-06-19

# 期待結果
# - 標準出力に各ノードの進捗が表示される
# - exit code 0
# - 出力ディレクトリに daily_report_2026-06-19.md が生成される
# - 日報に「📋 概要」「🛠 本日触れた技術・ツール」「📚 学習内容」「💻 開発活動」「🔧 発生した問題と解決策」の全セクションが含まれる
```

### シナリオ 2: 一部のデータソースのみ存在

```bash
# チャットログディレクトリが空の場合でも実行
dev-log-daily --config config.yml --date 2026-06-19

# 期待結果
# - exit code 0
# - 存在するデータソースのみから日報が生成される
# - 欠落したソースは「該当なし」と表示される
```

### シナリオ 3: 対象データが全く存在しない

```bash
dev-log-daily --config config.yml --date 2020-01-01

# 期待結果
# - exit code 0
# - 「対象データがありません」と表示される
# - 全セクション「該当なし」の日報が生成される
```

### シナリオ 4: 設定ファイルの検証

```bash
# 存在しない出力ディレクトリ
dev-log-daily --config config.yml  # output.directory が存在しない場合

# 期待結果
# - exit code 1
# - エラーメッセージ: 「出力ディレクトリが存在しません: /path/to/output」

# LLMモデル未指定
dev-log-daily --config config_missing_llm.yml

# 期待結果
# - exit code 1
# - エラーメッセージ: 「llm.parser.model が指定されていません」
```

### シナリオ 5: 同名ファイルの上書き

```bash
# 1回目
dev-log-daily --config config.yml --date 2026-06-19
# 2回目（同名ファイルが存在）
dev-log-daily --config config.yml --date 2026-06-19

# 期待結果
# - 2回目も正常終了（exit code 0）
# - 日報ファイルが上書きされる
# - 確認プロンプトは表示されない
```

---

## トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| `設定ファイルが見つかりません` | `--config` 未指定 | `--config` で設定ファイルパスを指定する |
| `出力ディレクトリが存在しません` | 出力先ディレクトリ不在 | ディレクトリを作成するか、設定ファイルの `output.directory` を修正 |
| `LLM呼び出しエラー (HTTP 401)` | APIキー不正 | 設定ファイルの `api_key` を確認 |
| `LLM呼び出しエラー (HTTP 503)` + リトライ失敗 | LLMサーバーダウン | llama.cpp サーバーの起動状態を確認 |
| `タイムアウト` | ログファイルが巨大 | `timeout_seconds` を増やすか、ログファイルを分割 |

---

## 開発環境セットアップ

```bash
# リポジトリのクローン
git clone <repo-url>
cd DevLogDaily

# 依存関係のインストール
pip install -e ".[dev]"

# pre-commit フックのインストール
pre-commit install

# テストの実行
pytest

# 型チェック
pyright src/
```
