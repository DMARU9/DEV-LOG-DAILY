# データモデル: パッケージ配布・セットアップ機能

**Created**: 2026-07-03 | **Feature**: 003-package-distribution-setup

## エンティティ一覧

### ScriptBundle

パッケージ内 `scripts/` ディレクトリに格納されたログ収集用スクリプト群。

| 項目 | 値 |
|------|-----|
| **格納場所** | `dev_log_daily/scripts/`（パッケージデータ） |
| **アクセス手段** | `importlib.resources.files("dev_log_daily") / "scripts"` |
| **インストール形態** | Wheel 内に同梱、`pip install -e .` 時はプロジェクトの実体パス |

**構成ファイル**:

| ファイル | 役割 | ユーザー操作 |
|---------|------|------------|
| `log_terminal.sh` | ターミナルコマンド履歴を JSONL に記録する bash 関数。`.bashrc` で `source` して使用 | `.bashrc` に `source` 追記、必要に応じて `LOG_ROOT` を編集 |
| `post-commit.sample` | Git コミット時に commit メタデータと diff を JSONL/.patch として保存する post-commit hook | 各 Git リポジトリの `.git/hooks/post-commit` にコピーして使用 |

**制約**:
- ScriptBundle は読み取り専用（ユーザーが直接編集する想定はしない）
- スクリプト内の環境依存設定値（`LOG_ROOT` など）はユーザーがコピー後に編集する
- パッケージ更新時に ScriptBundle も更新される可能性がある（上書き注意）

---

### InitCommand

`dev-log-daily init` サブコマンド。ScriptBundle への操作を提供する CLI インターフェース。

| 項目 | 値 |
|------|-----|
| **親コマンド** | `dev-log-daily`（`@click.group`） |
| **モード** | 非対話式（フラグベース） |
| **オペレーション** | show-paths / export-post-commit / guide |

**提供機能**:

| フラグ | 引数 | 動作 |
|-------|------|------|
| `--show-paths` | なし | 同梱スクリプトの絶対パスを一覧表示 |
| `--export-post-commit` | `<dir>`（必須） | `post-commit.sample` を指定ディレクトリにコピー |
| `--guide` | なし | ターミナルログ収集のセットアップ手順を標準出力に表示 |

**フラグ間の関係**:
- `--show-paths`, `--export-post-commit`, `--guide` は排他的（同時指定不可）
- いずれのフラグも指定されていない場合は `--help` 相当の使用方法を表示する
- `--export-post-commit` で指定ディレクトリが存在しない場合はエラー終了

**エラー状態**:
- パッケージデータが見つからない（破損等）→ エラーメッセージを表示して終了
- コピー先ディレクトリが存在しない → エラーメッセージを表示して終了
- 排他的フラグを同時指定 → 最後に指定されたフラグを優先（click のデフォルト動作）

---

### DistributionWheel

`python -m build` で生成される Python Wheel ファイル。

| 項目 | 値 |
|------|-----|
| **ファイル名** | `dev_log_daily-<version>-py3-none-any.whl` |
| **生成コマンド** | `python -m build` |
| **生成先** | `dist/` ディレクトリ |
| **同時生成** | `dev_log_daily-<version>.tar.gz`（ソースアーカイブ） |

**Wheel に含まれるもの**:
- コンパイル済み Python モジュール（`.pyc` に非ず、`.py` のまま）
- `scripts/log_terminal.sh`
- `scripts/post-commit.sample`
- パッケージメタデータ（METADATA, RECORD, WHEEL, entry_points.txt）

**Wheel に含まれないもの**:
- テストコード（`tests/`）
- 設定ファイルサンプル（`config.example.yml`）
- ドキュメント類（`README.md` は含む場合あり）
- `.specify/` ディレクトリ
- `tmp/` ディレクトリ

**配布チャネル**: GitHub Releases（手動アップロード）

---

## 状態遷移

本機能はデータパイプラインではなくパッケージ配布機能のため、従来のような状態遷移図は不要。以下はユーザー操作の流れである。

```text
[ユーザー]
   │
   ├── 1. GitHub Releases から Wheel をダウンロード
   │
   ├── 2. pip install dev_log_daily-*.whl
   │     └─ site-packages に配置 + エントリポイント登録
   │
   ├── 3. dev-log-daily init --guide       # セットアップ手順を確認
   │
   ├── 4. .bashrc に log_terminal.sh を source
   │
   ├── 5. dev-log-daily init --export-post-commit ./my-project/.git/hooks/
   │     └─ post-commit.sample をコピー → hooks/post-commit にリネーム
   │
   └── 6. dev-log-daily --config config.yml --date YYYY-MM-DD
         └─ 日報生成（既存機能）
```

## バリデーションルール

| 対象 | ルール |
|------|--------|
| ScriptBundle の存在 | パッケージインストール後、`importlib.resources.files()` で各スクリプトが存在すること |
| コピー先ディレクトリ | `init --export-post-commit <dir>` の `<dir>` は存在するディレクトリでなければならない |
| 排他フラグ | `--show-paths`, `--export-post-commit`, `--guide` は同時に指定できない |
| Wheel の完全性 | Wheel 内のスクリプトがソースと一致すること |
