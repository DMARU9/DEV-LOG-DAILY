# 契約定義: dev-log-daily init コマンド

**Created**: 2026-07-03 | **Feature**: 003-package-distribution-setup

## 概要

`dev-log-daily init` は、パッケージに同梱されたログ収集スクリプトへのアクセスとセットアップ支援を提供する CLI サブコマンド。

## CLI インターフェース

### コマンド構造

```text
dev-log-daily [run] [OPTIONS]          # 日報生成（デフォルト動作）
dev-log-daily init [OPTIONS]            # セットアップ操作
```

### init サブコマンドのフラグ

| フラグ | 型 | 必須 | 説明 |
|-------|-----|------|------|
| `--show-paths` | フラグ | 条件付き | 同梱スクリプトの絶対パスを表示 |
| `--export-post-commit` | 文字列（パス） | 条件付き | post-commit.sample を指定ディレクトリにコピー |
| `--guide` | フラグ | 条件付き | セットアップ手順を表示 |

**排他ルール**: `--show-paths`, `--export-post-commit`, `--guide` は排他的。同時指定時の動作は未定義（実装は click のデフォルト動作に委ねる）。

### 終了コード

| コード | 意味 |
|-------|------|
| 0 | 正常終了 |
| 1 | エラー（指定ディレクトリが存在しない、パッケージデータが見つからない 等） |

## 動作仕様

### --show-paths

**入力**: なし

**出力**: 標準出力に以下の形式で各スクリプトの絶対パスを表示する。

```
log_terminal.sh:      /path/to/site-packages/dev_log_daily/scripts/log_terminal.sh
post-commit.sample:   /path/to/site-packages/dev_log_daily/scripts/post-commit.sample
```

**エラー時**: パッケージデータが取得できない場合、エラーメッセージを stderr に出力し終了コード 1 で終了する。

---

### --export-post-commit <dir>

**入力**: `<dir>` — コピー先ディレクトリの絶対パスまたは相対パス

**処理**:
1. `<dir>` が存在するディレクトリであることを確認
2. `post-commit.sample` の内容を読み取り
3. `<dir>/post-commit.sample` として書き込み

**出力**: 標準出力に以下のメッセージを表示する。

```
post-commit.sample を {dir} にエクスポートしました。
使用するにはファイル名を post-commit にリネームし、実行権限を付与してください:
  mv {dir}/post-commit.sample {dir}/post-commit
  chmod +x {dir}/post-commit
```

**エラー時**:
- `<dir>` が存在しない → `エラー: 指定されたディレクトリが存在しません: {dir}`（終了コード 1）
- 書き込み権限がない → 例外メッセージを表示（終了コード 1）

---

### --guide

**入力**: なし

**出力**: 標準出力に以下のセットアップ手順を表示する。

```
# Dev Log Daily — ログ収集セットアップガイド

## 1. ターミナルログ収集

以下の行を ~/.bashrc に追記してください:

  source /path/to/dev_log_daily/scripts/log_terminal.sh

必要に応じて、log_terminal.sh 内の LOG_ROOT を実際のログ保存先に変更してください。

設定後、シェルを再起動するか以下を実行してください:

  source ~/.bashrc

## 2. Git post-commit hook

日報に Git コミットを含めたいプロジェクトで以下を実行してください:

  dev-log-daily init --export-post-commit /path/to/project/.git/hooks/
  mv /path/to/project/.git/hooks/post-commit.sample /path/to/project/.git/hooks/post-commit
  chmod +x /path/to/project/.git/hooks/post-commit

必要に応じて、post-commit 内の LOG_ROOT を編集してください。
```

## 実装上の注意

- スクリプトの読み取りには `importlib.resources.files("dev_log_daily") / "scripts"` を使用する
- ファイルコピーには `shutil.copy2` を使用し、パーミッションを維持する
- `--export-post-commit` の出力先は `Path.resolve()` で絶対パスに変換してから表示・検証する
- 各フラグの排他チェックは click の `@click.option` の `exclusive` ではなく、Python コード内で明示的に検証する（click 8.x の exclusive は実験的機能のため）
