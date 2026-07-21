# 変更履歴

All notable changes to this project will be documented in this file.

## [0.3.0] - 2026-07-21

### 追加

- **プロジェクト別日報生成**: 日報の「📁 作業プロジェクト」セクションがプロジェクト単位で整理され、全データソースの活動が同一プロジェクトとして統合されて出力される（US1）
  - Parser: Copilot チャットのワークスペース名、Git リポジトリのディレクトリ名、ターミナル cwd のディレクトリ名を `project_hints` として抽出
  - Enricher: `project_hints` をクロスリファレンスし表記ゆれを解決、プロジェクト活動辞書を生成
  - Reporter: プロジェクト活動データを主要入力とし、プロジェクト単位の日報フォーマットで出力
- **ターミナル cwd 情報のプロジェクト紐づけ**: ターミナル操作の cwd/git_branch が LLM 入力に含まれ、プロジェクト分類に使用される（US2）
  - LLM 入力形式を `[{timestamp}] [{cwd}] (branch) $ {command}` に変更
  - cwd が空のエントリは「プロジェクト不明」として扱われる
- **プロジェクト横断的な整合性**: 同一プロジェクト内でデータソース間の時系列関係を分析し、活動の流れが追跡可能に（US3）
- `ParsedData.project_hints` フィールド: `list[dict]` 形式で各 Parser が抽出したプロジェクト名候補を保持
- `DailyState.project_hints` / `project_activities`: パイプライン全体でプロジェクト情報を共有
- 単体テスト: `test_enricher.py`（18件）、`test_reporter.py`（7件）、`test_terminal_logs.py`（5件）
- 結合テスト: `test_pipeline.py` にプロジェクト活動データの結合テスト（3件）

### 変更

- `REPORTER_SYSTEM_PROMPT`: カテゴリ別構成からプロジェクト単位構成に全面書き換え
- `ENRICHER_SYSTEM_PROMPT`: プロジェクトヒント統合手順と `projects` JSON出力スキーマを追加
- `REPORTER_PROMPT_TEMPLATE`: `{project_activities_text}` プレースホルダを追加
- `TerminalLogsTool.parse()`: LLM 入力に cwd/git_branch を追加

## [0.2.0] - 2026-07-03

### 追加

- Wheel 配布対応: `python -m build` で Wheel およびソースアーカイブを生成可能に
- `dev-log-daily init` サブコマンドを追加:
  - `--show-paths`: 同梱スクリプトの絶対パスを表示
  - `--export-post-commit <dir>`: post-commit.sample を指定ディレクトリにコピー
  - `--guide`: ターミナルログ収集のセットアップ手順を表示
- ログ収集スクリプト（`log_terminal.sh`, `post-commit.sample`）をパッケージ内 `scripts/` に内蔵
- パッケージデータ設定（`[tool.setuptools.package-data]`）を追加

### 変更

- CLI エントリポイントを `@click.command` から `@click.group(invoke_without_command=True)` に変更
  - サブコマンドなしの場合は従来通りの日報生成を実行
  - `--config` オプションはサブコマンドなしの場合のみ必須
- ルートディレクトリの `log_terminal.sh` と `post-commit.sample` をパッケージ内に移行

### 開発者向け

- `build>=1.0` を dev 依存関係に追加
- テストフィクスチャ（`tests/fixtures/scripts/`）を追加
- `init` サブコマンドのユニットテストを追加
- パッケージデータアクセスのテストを追加
- Wheel ビルド成果物の検証テストを追加

## [0.1.0] - 2026-06-xx

### 追加

- 初回リリース
- 日報生成パイプラインの基本機能
- CLI エントリポイント（`dev-log-daily`）
- 設定ファイル（YAML）による構成管理
