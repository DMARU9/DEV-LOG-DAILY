# 技術調査レポート: パッケージ配布・セットアップ機能

**Created**: 2026-07-03 | **Feature**: 003-package-distribution-setup

## 調査項目

### 1. パッケージデータアクセス方法（importlib.resources）

**課題**: 同梱した `scripts/` 内のファイルに、インストール環境（開発モード / Wheel）によらず同一の API でアクセスする必要がある。

**評価した選択肢**:

| 方式 | バージョン要件 | 開発モード対応 | Wheel対応 | 推奨 |
|------|--------------|---------------|----------|------|
| `importlib.resources.files()` | Python 3.9+ | ✅ 実体パスを返す | ✅ パッケージ内パスを返す | ⭐ **採用** |
| `importlib.resources.read_text()` | Python 3.9+ | ✅ | ✅ | バイナリファイルに非対応 |
| `pkg_resources.resource_filename()` | サードパーティ | ✅ | ✅ | 非推奨（setuptools 非推奨化） |

**決定**: `importlib.resources.files()` を採用する。

**根拠**:
- Python 3.11+ がプロジェクト要件のため、`files()` API を問題なく使用可能
- パスオブジェクトを返すため、ファイルコピー・開封・存在確認が柔軟に行える
- `importlib.resources.as_file()` と組み合わせることで、一時ファイル展開も可能
- `pkg_resources` は setuptools で非推奨化されており、新規コードでの使用を避けるべき

**使用例**:

```python
import importlib.resources

# スクリプトディレクトリのパスを取得
script_dir = importlib.resources.files("dev_log_daily") / "scripts"

# 特定のスクリプトのパスを取得
post_commit_path = script_dir / "post-commit.sample"

# ファイル内容を文字列として読み取り
content = (script_dir / "log_terminal.sh").read_text(encoding="utf-8")
```

**注意点**:
- Wheel インストール時は `files()` が返すパスは `site-packages` 内の実パスを指す
- 開発モード（`pip install -e .`）時はプロジェクト内の実体パスを指す
- いずれの環境でも同一コードで動作する

---

### 2. Click サブコマンド構成

**課題**: 現在 `@click.command` 単体のエントリポイントを、`@click.group` に変更して `init` サブコマンドを追加する必要がある。

**評価した選択肢**:

| 方式 | 特徴 | 推奨 |
|------|------|------|
| `@click.group()` で main をグループ化 | 既存の引数（--config, --date）をグループレベルまたはサブコマンドレベルに配置 | ⭐ **採用** |
| `main` を別ファイルに分割 | 可読性は向上するが、変更範囲が大きい | 非推奨（現状維持優先） |
| argparse に乗り換え | 既存コードの全面的な書き換えが必要 | 非推奨 |

**決定**: `@click.group(invoke_without_command=True)` パターンを採用する。

**根拠**:
- 既存の `@click.command` を `@click.group` に変更し、従来の `--config --date` は `dev-log-daily run` サブコマンドまたは `dev-log-daily` 直下のデフォルト動作とする
- `invoke_without_command=True` とすることで、引数なしで `dev-log-daily` と実行された場合に従来の日報生成処理（デフォルト動作）を実行できる
- `dev-log-daily init --show-paths` のように `init` サブコマンドを追加する

**CLI 構造**:

```
dev-log-daily [OPTIONS]               # 既存の日報生成（デフォルト動作）
dev-log-daily init --show-paths       # スクリプトパス表示
dev-log-daily init --export-post-commit DIR  # post-commit エクスポート
dev-log-daily init --guide            # セットアップガイド表示
dev-log-daily --help                  # 全コマンドのヘルプ
dev-log-daily init --help             # init サブコマンドのヘルプ
```

**移行パス**:
1. `main()` 関数を `@click.group` に変更
2. 既存のロジックを `run` サブコマンドとして分離するか、グループ直下に `@click.command` として保持
3. `init` サブコマンドを `@main.command()` として追加（別ファイルでも可）

---

### 3. パッケージデータ構成（setuptools）

**課題**: ビルド時に `scripts/` ディレクトリ内のファイルを Wheel に含める必要がある。

**評価した選択肢**:

| 方式 | 設定箇所 | 特徴 | 推奨 |
|------|---------|------|------|
| `[tool.setuptools.package-data]` | pyproject.toml | モダンな設定方法。パッケージ相対パスで指定 | ⭐ **採用** |
| `include_package_data` + `MANIFEST.in` | pyproject.toml + MANIFEST.in | 2箇所管理になる。`package-data` で十分 | 非推奨 |
| `[options.package_data]` | setup.cfg | ini 形式。既存プロジェクトは pyproject.toml 統一 | 非推奨 |

**決定**: `[tool.setuptools.package-data]` を pyproject.toml に追加する。

**根拠**:
- 既存の pyproject.toml ベースの設定と一貫性がある
- 1 行の追加で完了し、最小限の変更で済む
- `MANIFEST.in` は sdist 向けの設定であり、Wheel に含めるには別途 `package-data` が必要。本プロジェクトでは Wheel 配布が主目的のため `package-data` 単独で十分

**設定内容**:

```toml
[tool.setuptools.package-data]
"dev_log_daily" = ["scripts/*"]
```

**確認方法**:

```bash
# Wheel の内容を確認
python -m build
unzip -l dist/dev_log_daily-*.whl | grep scripts/
```
