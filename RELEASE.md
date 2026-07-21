# リリース手順

このドキュメントでは、dev-log-daily の手動リリース手順を説明します。

## 前提条件

- Python 3.11+ がインストール済み
- `build` パッケージがインストール済み（`pip install build`）
- リリース作業用の仮想環境がアクティブ

## 自動リリース（推奨）

GitHub Actions ワークフロー（`.github/workflows/release.yml`）がセットアップされています。
**PR を main ブランチにマージするだけで** 自動的にリリースが作成されます。

### リリースフロー

1. `pyproject.toml` の `version` を更新し、PR を作成
2. PR を main にマージ
3. GitHub Actions が自動で:
   - `pyproject.toml` からバージョンを読み取り
   - 未リリースのバージョンであればタグを作成
   - Wheel とソースアーカイブ（`.tar.gz`）をビルド
   - GitHub Release を作成し、ビルド成果物を添付
   - CHANGELOG から該当バージョンの内容をリリース本文に設定

> **注意**: 既にリリース済みのバージョンが `pyproject.toml` に設定されている場合はスキップされます。新バージョンにするには `pyproject.toml` の `version` を更新してください。

### 手動トリガー

GitHub UI から `workflow_dispatch` を実行して手動でリリースをトリガーすることも可能です。

## 手動リリース手順

自動リリースが利用できない場合は、以下の手順で手動リリースも可能です。

### 1. バージョン更新

```bash
cd /home/takumi/github/DEV-LOG-DAILY
```

`pyproject.toml` の `version` をセマンティックバージョニングに従って更新してください。

```bash
# 例: 0.2.0 → 0.3.0
# pyproject.toml の version = "0.2.0" を編集
```

### 2. CHANGELOG 更新

`CHANGELOG.md` に新しいバージョンの変更点を追記してください。

### 3. ビルド

```bash
# 仮想環境で実施
python -m build
```

**期待される成果物**:
- `dist/dev_log_daily-<version>-py3-none-any.whl`
- `dist/dev_log_daily-<version>.tar.gz`

### 4. ビルド成果物の検証

```bash
# Wheel の内容確認
python -c "
import zipfile
with zipfile.ZipFile('dist/dev_log_daily-<version>-py3-none-any.whl') as z:
    for name in z.namelist():
        print(name)
"

# 新規仮想環境にインストールして動作確認
cd /tmp
python3 -m venv test-release
source test-release/bin/activate
pip install /path/to/dist/dev_log_daily-<version>-py3-none-any.whl

# 基本動作確認
dev-log-daily --help
dev-log-daily init --help
dev-log-daily init --show-paths
dev-log-daily init --guide
```

### 5. Git タグ付けとコミット

```bash
# CHANGELOG とバージョン更新をコミット
git add pyproject.toml CHANGELOG.md
git commit -m "release: v<version>"

# タグ付け
git tag -a v<version> -m "v<version>"
git push origin v<version>
```

### 6. GitHub Releases

1. GitHub リポジトリにアクセス
2. Releases → Draft a new release
3. タグ: `v<version>` を選択
4. リリースタイトル: `v<version>`
5. 説明: CHANGELOG.md の該当バージョンの内容を記述
6. 添付ファイル:
   - `dist/dev_log_daily-<version>-py3-none-any.whl`
   - `dist/dev_log_daily-<version>.tar.gz`
7. 「Publish release」をクリック

## インストール方法（ユーザー向け）

```bash
# pip の場合
pip install https://github.com/DMARU9/DEV-LOG-DAILY/releases/download/v<version>/dev_log_daily-<version>-py3-none-any.whl

# uv の場合
uv tool install https://github.com/DMARU9/DEV-LOG-DAILY/releases/download/v<version>/dev_log_daily-<version>-py3-none-any.whl
```
