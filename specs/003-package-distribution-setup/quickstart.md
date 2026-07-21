# クイックスタート: パッケージ配布・セットアップ機能

**Created**: 2026-07-03 | **Feature**: 003-package-distribution-setup

このドキュメントは、実装後に機能が正しく動作することを検証するためのシナリオを提供します。詳細な実装手順は `tasks.md` を参照してください。

## 前提条件

- Python 3.11+ がインストール済み
- `pip` または `uv` が利用可能
- Git リポジトリのクローン（ビルド検証時）
- 仮想環境（`.venv`）がアクティブ（憲法 品質ゲート 準拠）

## シナリオ 1: Wheel ビルド

### 目的
`python -m build` で Wheel とソースアーカイブが生成され、スクリプトファイルが同梱されていることを確認する。

### コマンド
```bash
# 仮想環境で実施
cd /home/takumi/github/DevLogDaily
source .venv/bin/activate
pip install build

# ビルド
python -m build
```

### 期待される結果
- `dist/dev_log_daily-0.1.0-py3-none-any.whl` が生成される
- `dist/dev_log_daily-0.1.0.tar.gz` が生成される
- Wheel に `scripts/log_terminal.sh` と `scripts/post-commit.sample` が含まれている

### 検証コマンド
```bash
# Wheel の内容確認
unzip -l dist/dev_log_daily-0.1.0-py3-none-any.whl | grep scripts/

# 期待: scripts/log_terminal.sh と scripts/post-commit.sample が表示される
```

---

## シナリオ 2: Wheel インストールと基本動作

### 目的
Wheel からインストールした環境で `dev-log-daily --help` が動作することを確認する。

### コマンド
```bash
# 新規仮想環境に Wheel インストール
cd /tmp
python3 -m venv test-wheel
source test-wheel/bin/activate
pip install /home/takumi/github/DevLogDaily/dist/dev_log_daily-0.1.0-py3-none-any.whl

# 動作確認
dev-log-daily --help
```

### 期待される結果
- `dev-log-daily --help` でヘルプが表示される
- ヘルプに `init` サブコマンドが表示される（例: `Commands: init`）
- `pip show dev-log-daily` で正しいバージョンとメタデータが表示される

### 検証コマンド
```bash
dev-log-daily --help
# 期待: 使用方法とオプション一覧が表示される

dev-log-daily init --help
# 期待: --show-paths, --export-post-commit, --guide のヘルプが表示される

pip show dev-log-daily
# 期待: Name: dev-log-daily, Version: 0.1.0
```

---

## シナリオ 3: init --show-paths

### 目的
`dev-log-daily init --show-paths` でスクリプトの絶対パスが表示されることを確認する。

### コマンド
```bash
dev-log-daily init --show-paths
```

### 期待される結果
- `log_terminal.sh:` と `post-commit.sample:` の行が表示される
- 各パスは実在するファイルを指している
- パスの末尾が `scripts/log_terminal.sh` および `scripts/post-commit.sample` である

### 検証コマンド
```bash
dev-log-daily init --show-paths
# 出力例:
# log_terminal.sh:      /tmp/test-wheel/lib/python3.11/site-packages/dev_log_daily/scripts/log_terminal.sh
# post-commit.sample:   /tmp/test-wheel/lib/python3.11/site-packages/dev_log_daily/scripts/post-commit.sample

# ファイルの実在確認
ls -la $(dev-log-daily init --show-paths 2>/dev/null | awk '{print $2}')
```

---

## シナリオ 4: init --export-post-commit

### 目的
`dev-log-daily init --export-post-commit <dir>` で post-commit.sample が指定ディレクトリにコピーされることを確認する。

### コマンド
```bash
# 正常系
mkdir -p /tmp/test-hooks
dev-log-daily init --export-post-commit /tmp/test-hooks
ls -la /tmp/test-hooks/

# 異常系（ディレクトリが存在しない場合）
dev-log-daily init --export-post-commit /tmp/nonexistent-dir
```

### 期待される結果
- `/tmp/test-hooks/post-commit.sample` が作成される
- 元のファイルと内容が同一である
- 存在しないディレクトリを指定した場合はエラーメッセージが表示され、終了コード 1 で終了する

### 検証コマンド
```bash
# 内容一致確認
diff /tmp/test-hooks/post-commit.sample \
  $(dev-log-daily init --show-paths 2>/dev/null | grep post-commit | awk '{print $2}')

# エラーケースの終了コード確認
dev-log-daily init --export-post-commit /tmp/nonexistent-dir
echo $?  # 期待: 1
```

---

## シナリオ 5: init --guide

### 目的
`dev-log-daily init --guide` でセットアップ手順が表示されることを確認する。

### コマンド
```bash
dev-log-daily init --guide
```

### 期待される結果
- ターミナルログ収集のセットアップ手順（`.bashrc` への `source` 追記方法）が表示される
- post-commit.sample の各 Git リポジトリへの配置方法が表示される
- `LOG_ROOT` などの環境変数の編集箇所が説明される
- 終了コード 0

---

## シナリオ 6: 開発モード（pip install -e .）での動作確認

### 目的
開発モードでも `init` コマンドの全機能が正しく動作することを確認する。

### コマンド
```bash
cd /home/takumi/github/DevLogDaily
source .venv/bin/activate
pip install -e ".[dev]"

dev-log-daily init --show-paths
dev-log-daily init --guide
```

### 期待される結果
- `--show-paths` のパスがプロジェクト内の `src/dev_log_daily/scripts/` を指す
- `--guide` が正常に表示される
- 開発モードと Wheel インストールで同一のコードが動作する

---

## シナリオ 7: uv tool install での動作確認

### 目的
`uv tool install` 経由のインストールでも全機能が動作することを確認する。

### コマンド
```bash
uv tool install /home/takumi/github/DevLogDaily/dist/dev_log_daily-0.1.0-py3-none-any.whl

dev-log-daily init --show-paths
dev-log-daily init --guide
```

### 期待される結果
- `uv` の隔離環境にインストールされる
- 全サブコマンドが正常に動作する
- `pip show dev-log-daily`（システム側）では表示されない

---

## 関連ドキュメント

- [データモデル](./data-model.md): ScriptBundle, InitCommand, DistributionWheel の定義
- [init コマンド契約](./contracts/init-command.md): 各フラグの動作仕様
- [spec.md](./spec.md): 機能仕様と要件一覧
