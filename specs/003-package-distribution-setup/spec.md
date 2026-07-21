# Feature Specification: パッケージ配布・セットアップ機能

**Feature Branch**: `003-package-distribution-setup`

**Created**: 2026-07-03

**Status**: Draft

**SPECIFY_FEATURE_DIRECTORY**: `specs/003-package-distribution-setup`

**Input**: User description: "dev-log-daily をパッケージ化し、GitHub Releases に Wheel を添付して配布可能にしたい。Wheel でインストールした場合、コマンド処理のコードは編集できないようにしたい（編集するにはソースからインストールする必要がある）。また、ログ収集用スクリプト（log_terminal.sh, post-commit.sample）をパッケージ内に同梱し、`dev-log-daily init` コマンドでスクリプトの参照・エクスポートができるようにしたい。ターミナルログ収集はインストール時に共通設定として展開し、post-commit サンプルはコマンドの実行体配下などに配置し、プロジェクトごとにユーザーが展開する形を理想とする。"

## Clarifications

### Session 2026-07-03

- **Q**: 配布方式は Wheel のみか、スタンドアロンバイナリも必要か？ → **A**: Wheel のみで十分。スタンドアロンバイナリは現時点では不要。
- **Q**: ログ収集スクリプトのセットアップ方法は？ → **A**: パッケージ内に内蔵し、ユーザーが `dev-log-daily init` コマンドで参照・エクスポートする。インストール時の自動セットアップは不要。
- **Q**: GitHub Actions による自動リリースは必要か？ → **A**: 不要。手動でビルド・リリースする。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Wheel によるパッケージインストール (Priority: P1)

ユーザーは GitHub Releases ページから Wheel ファイルをダウンロードし、`pip install` または `uv tool install` で dev-log-daily をインストールする。インストール後、`dev-log-daily --config config.yml --date YYYY-MM-DD` で日報生成が実行できる。Wheel でインストールされた場合、パッケージ内のコードは `site-packages` に配置されるため、通常のユーザー操作では編集できない。編集が必要な場合はソースコードからインストールする必要がある。

**Why this priority**: 本機能の核心である「配布可能なパッケージ形式の提供」を実現する最小機能。これによりユーザーはソースコードを clone せずともツールを利用できるようになる。

**Independent Test**: GitHub Releases にアップロードされた Wheel をダウンロードし、仮想環境に `pip install` して `dev-log-daily --help` が正常に動作することを確認する。

**Acceptance Scenarios**:

1. **Given** GitHub Releases に Wheel ファイルが添付されている, **When** ユーザーが Wheel をダウンロードして `pip install` する, **Then** `dev-log-daily` コマンドが使用可能になり、`--help` でヘルプが表示される
2. **Given** Wheel からインストールされた環境, **When** ユーザーが `pip show dev-log-daily` を実行する, **Then** 正しいバージョンとメタデータが表示される
3. **Given** Wheel からインストールされた環境, **When** ユーザーが `dev-log-daily --config config.yml --date 2026-07-01` を実行する, **Then** 日報が正常に生成される
4. **Given** `uv tool install` でインストールされた環境, **When** ユーザーが `dev-log-daily` コマンドを実行する, **Then** 隔離環境で正しく動作する

---

### User Story 2 - ログ収集スクリプトのパッケージ内蔵 (Priority: P1)

`log_terminal.sh` と `post-commit.sample` がパッケージ内の `scripts/` ディレクトリに同梱されており、インストール後もパッケージデータとして利用可能である。ユーザーは `dev-log-daily init` コマンドでスクリプトのパスを確認したり、任意のディレクトリにエクスポートしたりできる。

**Why this priority**: ログ収集のセットアップは日報生成の前提条件であり、スクリプトをパッケージと一体化することで「インストール後の導線」を確立する。

**Independent Test**: パッケージをインストール後、`dev-log-daily init --show-paths` でスクリプトのパスが表示され、実際にそのパスにファイルが存在することを確認する。

**Acceptance Scenarios**:

1. **Given** dev-log-daily がインストールされている, **When** ユーザーが `dev-log-daily init --show-paths` を実行する, **Then** `log_terminal.sh` と `post-commit.sample` の絶対パスが表示される
2. **Given** dev-log-daily がインストールされている, **When** ユーザーが `dev-log-daily init --export-post-commit ./my-project/` を実行する, **Then** `post-commit.sample` が指定されたディレクトリにコピーされる
3. **Given** dev-log-daily がインストールされている, **When** ユーザーが `dev-log-daily init --guide` を実行する, **Then** ターミナルログ収集のセットアップ手順（.bashrc への追記方法など）が表示される

---

### User Story 3 - リリースビルドと配布 (Priority: P2)

メンテナーはソースコードから Wheel をビルドし、GitHub Releases に添付して配布する。ビルドは `python -m build` の一発で完了し、生成された Wheel とソースアーカイブをリリースにアップロードする。ビルドは CI ではなく手動で行う。

**Why this priority**: 継続的な配布の基盤となるが、初期リリース後は安定するため P2 とする。

**Independent Test**: `python -m build` を実行し、`dist/` ディレクトリに Wheel（.whl）とソースアーカイブ（.tar.gz）が生成されることを確認する。

**Acceptance Scenarios**:

1. **Given** クリーンなリポジトリのチェックアウト, **When** `python -m build` を実行する, **Then** `dist/dev_log_daily-<version>-py3-none-any.whl` と `dist/dev_log_daily-<version>.tar.gz` が生成される
2. **Given** 生成された Wheel, **When** 内容を確認する, **Then** `scripts/log_terminal.sh` と `scripts/post-commit.sample` がパッケージデータとして含まれている
3. **Given** GitHub Releases のドラフト, **When** Wheel とソースアーカイブを添付して公開する, **Then** リリースページから誰でもダウンロード可能になる

---

### Edge Cases

- Wheel インストール後、`scripts/` ディレクトリが読み取り専用になることはないが、`site-packages` 内のファイルであるため一般的なユーザー操作では編集を意図しない
- `uv tool install` でインストールした場合、ツールは隔離環境に配置されるため、システムの Python 環境に影響を与えない
- `init --export-post-commit` でコピー先のディレクトリが存在しない場合はエラーメッセージを表示する
- スクリプト内の `LOG_ROOT` などの設定値はユーザー自身が編集する必要がある（`init` コマンドは内容を書き換えない）
- パッケージが `pip install -e .`（開発モード）でインストールされている場合、`scripts/` はプロジェクト内の実体パスを指す

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: パッケージは `python -m build` で Wheel（.whl）およびソースアーカイブ（.tar.gz）を生成可能でなければならない（MUST）
- **FR-002**: Wheel には `log_terminal.sh` および `post-commit.sample` がパッケージデータとして含まれていなければならない（MUST）
- **FR-003**: `dev-log-daily` CLI は `init` サブコマンドを提供し、以下の機能を持たなければならない（MUST）
  - `--show-paths`: 同梱スクリプトの絶対パスを一覧表示する
  - `--export-post-commit <dir>`: post-commit.sample を指定ディレクトリにコピーする
  - `--guide`: ターミナルログ収集のセットアップ手順を表示する
- **FR-004**: `init --show-paths` は標準出力に各スクリプトの名称と絶対パスを表示しなければならない（MUST）
- **FR-005**: `init --export-post-commit` は指定ディレクトリが存在しない場合、エラーメッセージを表示して終了しなければならない（MUST）
- **FR-006**: `init --guide` は以下の内容を含むセットアップ手順を表示しなければならない（MUST）
  - `.bashrc` への `source` 追記方法
  - 必要に応じた `LOG_ROOT` などの変数編集箇所の説明
  - post-commit.sample の各 Git リポジトリへの配置方法
- **FR-007**: パッケージデータの読み込みはインストール環境（開発モード / Wheel）の違いに依存せず、同一の方法でスクリプトにアクセスできなければならない（MUST）
- **FR-008**: ビルド設定においてスクリプトファイル群がパッケージデータとして正しく含まれるように構成しなければならない（MUST）
- **FR-009**: パッケージのバージョンはセマンティックバージョニング（MAJOR.MINOR.PATCH）に従い、リリース時に `pyproject.toml` の `version` を更新しなければならない（MUST）
- **FR-010**: Wheel インストール時も `dev-log-daily` エントリポイントは正しく機能し、`--help` で全サブコマンド（`init` 含む）のヘルプが表示されなければならない（MUST）

### Key Entities

- **ScriptBundle**: パッケージ内 `scripts/` ディレクトリに格納されたログ収集用スクリプット群。`log_terminal.sh`（ターミナルログ収集用 bash 関数）と `post-commit.sample`（Git post-commit hook サンプル）から構成される。`importlib.resources` 経由で読み取り専用アクセスされる。
- **InitCommand**: `dev-log-daily init` サブコマンド。ScriptBundle への参照パス表示、ファイルエクスポート、セットアップガイド表示の機能を提供する CLI インターフェース。
- **DistributionWheel**: `python -m build` で生成される Python Wheel ファイル。ScriptBundle を含むパッケージデータが正く同梱され、`pip install` / `uv tool install` でインストール可能。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: GitHub Releases から Wheel をダウンロードし、`pip install` から `dev-log-daily --help` が実行できるまでの時間が 30 秒以内である
- **SC-002**: `dev-log-daily init --show-paths` が実行後 1 秒以内に結果を表示する
- **SC-003**: パッケージのビルド作業が 30 秒以内に完了する
- **SC-004**: `dev-log-daily init --guide` の表示内容を読んだユーザーが、追加の調査なしにターミナルログ収集と post-commit hook のセットアップ手順を理解できる
- **SC-005**: Wheel に含まれるスクリプトファイルが、ビルド元のソースと完全に一致する

## Assumptions

- ユーザーは `pip` または `uv` がインストールされた環境で操作する
- 配布は GitHub Releases 経由とし、PyPI への公開は行わない
- スタンドアロンバイナリ（PyInstaller 等）は提供しない
- `init` コマンドは非対話式とし、すべての操作はフラグで指定する
- スクリプト内の `LOG_ROOT` など環境固有の設定値はユーザー自身が編集することを前提とする
- GitHub Actions による自動リリースは行わず、手動ビルド・アップロードを前提とする
- 対応 OS は Linux（WSL 含む）を第一対象とし、Windows/macOS は動作確認範囲外とする
- 既存の `config.yml` の構造（データソース設定等）に変更は加えない
