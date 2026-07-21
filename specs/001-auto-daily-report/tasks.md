# Tasks: 開発活動ログ自動収集・日報生成フレームワーク

**Input**: Design documents from `/specs/001-auto-daily-report/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: 憲法第VI条および FR-014 により、全機能に単体テスト・結合テストが必須。

**Organization**: タスクはユーザーストーリー別に編成。各ストーリーは独立して実装・テスト可能。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 並列実行可能（異なるファイル、依存なし）
- **[Story]**: 対象ユーザーストーリー（US1, US2）
- 説明に必ずファイルパスを含める

---

## Phase 1: Setup（プロジェクト初期化）

**Purpose**: プロジェクト構造の作成と基本設定

- [X] T001 プロジェクトディレクトリ構造を作成し、全 `__init__.py` を配置する（`src/dev_log_daily/`、`src/dev_log_daily/tools/`、`src/dev_log_daily/pipeline/`、`src/dev_log_daily/config/`、`src/dev_log_daily/llm/`、`src/dev_log_daily/prompts/`、`src/dev_log_daily/utils/`、`tests/`、`tests/unit/`、`tests/integration/`、`tests/fixtures/`）
- [X] T002 [P] `pyproject.toml` を作成し、全依存関係（langgraph, deepagents, langchain-openai, click, pydantic, PyYAML, pytest, pytest-asyncio, pytest-mock）と `[project.scripts]` エントリポイント `dev-log-daily` を定義する
- [X] T003 [P] `.pre-commit-config.yaml` を作成し、isort, ruff, pyright, trailing-whitespace, pytest の各フックを設定する
- [X] T004 [P] `config.example.yml` を作成し、全LLMコンポーネント・データソースパス・出力設定・タイムアウトのサンプル値を記載する

---

## Phase 2: Foundational（基盤インフラ）

**Purpose**: 全ユーザーストーリーが依存するコアインフラ。このフェーズ完了前にユーザーストーリー実装は開始不可。

**⚠️ CRITICAL**: このフェーズが完了するまでユーザーストーリー作業は開始できない。

- [X] T005 [P] `DailyState` TypedDict を実装する（`src/dev_log_daily/state.py`）— 全ノード共有状態フィールド（target_date, *_raw, *_parsed, enriched_data, daily_report, errors, progress_log）を定義
- [X] T006 [P] pydantic 設定スキーマを実装する（`src/dev_log_daily/config/schema.py`）— `LLMConfig`, `ComponentLLMConfig`, `DataSourceConfig`, `OutputConfig`, `AppConfig` の全モデルとバリデーションルール（全LLM必須、output.directory 存在確認、全パス必須）
- [X] T007 設定ファイルローダーを実装する（`src/dev_log_daily/config/loader.py`）— YAMLファイル読み込み、pydanticスキーマ検証、出力ディレクトリ存在確認。CLIオプション `--config` 未指定時・出力ディレクトリ不在時は起動エラー（exit code 1）
- [X] T008 [P] 日付ユーティリティを実装する（`src/dev_log_daily/utils/date.py`）— ローカルタイムゾーンに基づく前日計算、`YYYY-MM-DD` 形式の日付文字列処理
- [X] T009 [P] ファイルI/Oユーティリティを実装する（`src/dev_log_daily/utils/file.py`）— UTF-8/LF でのファイル読み書き、ディレクトリ存在確認、再帰的ファイル検索
- [X] T010 [P] ロギング設定を実装する（`src/dev_log_daily/utils/logging.py`）— 標準出力への進捗表示用ロガー、ファイル出力用詳細ロガー
- [X] T011 [P] LLMクライアントを実装する（`src/dev_log_daily/llm/client.py`）— `langchain-openai` の `ChatOpenAI` を使用。エラー種別に応じたリトライ戦略（永続エラー 400/401/403 即時停止、一時的エラー 429/5xx 指数バックオフ最大3回）
- [X] T012 [P] トークン分割・要約統合ロジックを実装する（`src/dev_log_daily/llm/chunking.py`）— テキストのチャンク分割、各チャンクのLLM要約、中間要約の統合（Map-Reduce パターン）
- [X] T013 [P] `DataSourceTool` 抽象基底クラスを実装する（`src/dev_log_daily/tools/base.py`）— `collect(target_date, config) -> CollectedLog` および `parse(raw, llm) -> ParsedData` インターフェース定義
- [X] T014 [P] システムプロンプトを実装する（`src/dev_log_daily/prompts/system.py`）— 共通システムプロンプト（日本語、Markdown形式、セクション構造の指示）を定義
- [X] T015 [P] コンポーネント別プロンプトテンプレートを実装する（`src/dev_log_daily/prompts/templates.py`）— Collector/Parser/Enricher/Reporter 各ノード用のプロンプトテンプレートを定義
- [X] T016 [P] 日付ユーティリティの単体テストを作成する（`tests/unit/test_date.py`）— 前日計算、タイムゾーン境界、日付フォーマット検証
- [X] T017 [P] トークン分割の単体テストを作成する（`tests/unit/test_chunking.py`）— チャンク分割、トークン数推定、Map-Reduce統合
- [X] T018 [P] 設定読み込み・スキーマ検証の単体テストを作成する（`tests/unit/test_config.py`）— 有効/無効なYAMLの検証、必須項目欠落時のエラー検出、出力ディレクトリ不在時のエラー検出

**Checkpoint**: 基盤完了 — ユーザーストーリーの実装を開始可能

---

## Phase 3: User Story 1 — 日次レポートの自動生成 (Priority: P1) 🎯 MVP

**Goal**: CLI コマンド `dev-log-daily --config <PATH>` を実行すると、前日の Copilotチャット・Gitコミット・ターミナル履歴から Markdown 日報を自動生成し、指定出力先に保存する。

**Independent Test**: `dev-log-daily --config config.yml` を実行し、出力ディレクトリに `daily_report_YYYY-MM-DD.md` が生成され、全セクション（概要、使用技術、学習内容、開発活動、問題と解決策）が含まれることを確認する。

### Tests for User Story 1

> **NOTE: テストを先に作成し、実装前に失敗することを確認する**

- [X] T019 [P] [US1] Copilotチャットツール結合テストを作成する（`tests/integration/test_copilot_chat.py`）— JSONLファイルからの収集・解析、日付フィルタリング（複数日混在データのフィルタリング含む）、空ディレクトリ処理
- [X] T020 [P] [US1] Gitコミットツール結合テストを作成する（`tests/integration/test_git_commits.py`）— 再帰的リポジトリ検出、コミット収集・解析、日付フィルタリング
- [X] T021 [P] [US1] ターミナル履歴ツール結合テストを作成する（`tests/integration/test_terminal_logs.py`）— 履歴ファイル読み込み・解析、日付フィルタリング、巨大ファイル分割処理

### Implementation for User Story 1

- [X] T022 [P] [US1] Copilotチャットツールを実装する（`src/dev_log_daily/tools/copilot_chat.py`）— JSONLチャットログディレクトリから対象日のセッションを収集（`collect`）、LLMでチャット内容を解析・圧縮（`parse`）
- [X] T023 [P] [US1] Gitコミットツールを実装する（`src/dev_log_daily/tools/git_commits.py`）— 設定の `git_root_dir` 配下を再帰探索し全Gitリポジトリの対象日コミットを収集（`collect`）、LLMでコミットメッセージを解析（`parse`）
- [X] T024 [P] [US1] ターミナル履歴ツールを実装する（`src/dev_log_daily/tools/terminal_logs.py`）— ターミナル履歴ファイルから対象日のコマンド行を収集（`collect`）、LLMで操作内容を解析（`parse`）。設定可能なタイムアウト（デフォルト600秒）を適用
- [X] T025 [US1] Collector ノードを実装する（`src/dev_log_daily/pipeline/collector.py`）— 3ツールを並列実行し `DailyState` の `*_raw` フィールドに収集結果を格納。個別ツール障害は他ツールに影響させず、全ツール失敗時は exit code 3 で停止。全ツールが空/スキップされた場合は後続ノードに空データを渡し、最終的に exit code 0「対象データがありません」で正常終了する
- [X] T026 [US1] Parser ノードを実装する（`src/dev_log_daily/pipeline/parser.py`）— 各ツールの収集結果をLLM解析し `*_parsed` フィールドに格納。トークン制限超過時は分割要約を適用。LLM永続エラー時は exit code 2 で停止
- [X] T027 [US1] Enricher ノードを実装する（`src/dev_log_daily/pipeline/enricher.py`）— 解析結果のクロスリファレンス、矛盾点検出、欠落情報の補完、コンテキスト付与を実行し `enriched_data` に格納。LLMエラー時は他ノードと同様にリトライ・停止
- [X] T028 [US1] Reporter ノードを実装する（`src/dev_log_daily/pipeline/reporter.py`）— 補完済みデータから日報Markdownを生成し `daily_report` に格納。出力セクションは spec.md に従い「概要」「使用技術」「学習内容」「開発活動」「発生した問題と解決策」の5セクションを必須とする。全データソースが空/存在しない場合は全セクション「該当なし」の日報を生成し exit code 0 で正常終了。ファイル名 `daily_report_YYYY-MM-DD.md` で出力。同名ファイルは上書き。UTF-8/LF で保存
- [X] T029 [US1] LangGraph StateGraph パイプラインを組み立てる（`src/dev_log_daily/agent.py`）— Collector → Parser → Enricher → Reporter の4ノードを逐次エッジで接続。entry_point を collector に設定。`add_conditional_edges` でエラー発生時の早期停止分岐を実装（全ソース収集失敗 → exit code 3、LLM永続エラー/リトライ失敗 → exit code 2）。各ノードの進捗ログを `progress_log` に記録
- [X] T030 [US1] CLI エントリポイントを実装する（`src/dev_log_daily/main.py`）— `click` で `--config`（必須）、`--date`（オプション、デフォルト前日）を受け付け。設定ロード→StateGraph実行→結果出力のフロー。標準出力に各ノードの開始・終了・エラーを表示（contracts/cli.md のフォーマットに準拠）。exit code は contracts/cli.md に従い `sys.exit()` で返す（0: 正常/対象データなし、1: 起動時エラー、2: LLMエラー、3: 全ソース収集失敗
- [X] T031 [US1] パイプラインノードの単体テストを作成する（`tests/unit/test_llm_client.py`）— LLMクライアントのリトライ戦略（一時的エラー最大3回、永続エラー即時停止）、タイムアウト処理
- [X] T032 [US1] パイプライン全体の結合テストを作成する（`tests/integration/test_pipeline.py`）— 全データソース正常系、一部データソース欠落、全データソース空、LLMエラー停止、同名ファイル上書き、外部サービスへのデータ送信がないことの確認（FR-012）

**Checkpoint**: この時点で User Story 1 は完全に機能し、独立してテスト可能。MVP 達成。

---

## Phase 4: User Story 2 — 設定ファイルによるカスタマイズ (Priority: P2)

**Goal**: YAML設定ファイルを通じて各コンポーネントのLLMモデルや出力設定をコード変更なしにカスタマイズ可能。不正な設定は起動時に具体的なエラーメッセージで報告される。

**Independent Test**: 設定ファイルのLLMモデルを変更して再実行し、変更が反映されることを確認。不正な設定でエラーメッセージが表示されることを確認。

### Tests for User Story 2

- [X] T033 [P] [US2] 設定検証エラーメッセージの単体テストを作成する（`tests/unit/test_config.py` に追加）— コンポーネント別LLM未指定時のエラー、出力ディレクトリ不在時のエラー、設定ファイル不在時のエラー、不正なYAML構文のエラー

### Implementation for User Story 2

- [X] T034 [P] [US2] 設定スキーマのエラーメッセージを日本語で詳細化する（`src/dev_log_daily/config/schema.py` 修正）— 各バリデーションエラーに「llm.parser.model が指定されていません」「出力ディレクトリが存在しません: {path}」等の具体的メッセージを追加
- [X] T035 [US2] 設定ローダーのエラーハンドリングを強化する（`src/dev_log_daily/config/loader.py` 修正）— データソースディレクトリ/ファイルが存在しない場合は警告を出力し、該当ツールをスキップ（収集失敗として扱い他ツールに影響させない）。コンポーネント別LLM未指定の全件検出と一括エラー報告
- [X] T036 [US2] コンポーネント別LLMモデル割り当てを検証する（`src/dev_log_daily/agent.py` 修正）— 設定ファイルの `llm.{component}` から各ノードのLLMインスタンスを生成し、未指定コンポーネントがあれば起動時エラー

**Checkpoint**: この時点で User Stories 1 と 2 が両方とも独立して機能する

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: 全ユーザーストーリーにまたがる品質向上

- [X] T037 [P] テストフィクスチャを整備する（`tests/fixtures/`）— `sample_chat.jsonl`（Copilotチャットログサンプル）、`sample_terminal.log`（ターミナル履歴サンプル）に加え、結合テスト用 `tests/integration/conftest.py` に動的フィクスチャ（`sample_git_repo/`, `sample_chat_dir`, `sample_terminal_file`, `config_for_tools`）を実装
- [X] T038 quickstart.md の全検証シナリオを手動実行し、期待通りの動作を確認する — SC-001（CLI実行〜日報出力完了まで3分以内）の時間計測、SC-002（日報が元ログの主要開発活動をカバーしていること）の目視確認を含む
- [X] T039 [P] `README.md` を更新し、インストール手順・設定方法・実行例・トラブルシューティングを記載する
- [X] T040 pre-commit フック（isort, ruff, pyright, trailing-whitespace, pytest）が全ファイルで成功することを確認し、必要に応じて修正する
- [X] T041 エラー発生時の部分データ保持を確認する — LLMエラー停止後も `*_raw`/`*_parsed` フィールドのデータが破棄されていないことを結合テストで検証

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 依存なし — 即時開始可能
- **Foundational (Phase 2)**: Phase 1 完了後に開始 — 全ユーザーストーリーをブロック
- **User Stories (Phase 3-4)**: Phase 2 完了後に開始可能
  - US1 (P1) → US2 (P2) の順で逐次実装（US2 は US1 の設定機構に依存）
- **Polish (Phase 5)**: Phase 3-4 完了後に開始

### User Story Dependencies

- **User Story 1 (P1)**: Phase 2 完了後開始可能。他ストーリーに依存しない
- **User Story 2 (P2)**: Phase 2 および US1 の設定ローダー（T007）に依存。US1 完了後に開始

### Within Each User Story

- テスト（T019-T021, T033）を先に作成し、実装前に失敗を確認
- データソースツール（T022-T024）→ パイプラインノード（T025-T028）→ エージェント（T029）→ CLI（T030）の順
- ツール間は並列実装可能（[P] マーク）
- ノード間は Collector → Parser → Enricher → Reporter の順次依存

### Parallel Opportunities

- Phase 1: T002, T003, T004 は並列実行可能
- Phase 2: T005, T006, T008-T018 は広範に並列実行可能（T007 のみ T006 に依存）
- Phase 3 テスト: T019, T020, T021 は並列実行可能
- Phase 3 ツール実装: T022, T023, T024 は並列実行可能
- Phase 3 ノード実装: T025 → T026 → T027 → T028 は逐次
- Phase 4: T033, T034 は並列実行可能
- Phase 5: T037, T039 は並列実行可能

---

## Parallel Example: User Story 1

```bash
# テストを並列作成（実装前にFAILを確認）:
Task T019: "Copilotチャットツール結合テスト in tests/integration/test_copilot_chat.py"
Task T020: "Gitコミットツール結合テスト in tests/integration/test_git_commits.py"
Task T021: "ターミナル履歴ツール結合テスト in tests/integration/test_terminal_logs.py"

# ツール実装を並列実行:
Task T022: "Copilotチャットツール in src/dev_log_daily/tools/copilot_chat.py"
Task T023: "Gitコミットツール in src/dev_log_daily/tools/git_commits.py"
Task T024: "ターミナル履歴ツール in src/dev_log_daily/tools/terminal_logs.py"

# ノード実装は逐次（順序依存あり）:
Task T025 → T026 → T027 → T028 → T029 → T030
```

---

## Implementation Strategy

### MVP First (User Story 1 のみ)

1. Phase 1: Setup 完了
2. Phase 2: Foundational 完了（基盤インフラ）
3. Phase 3: US1 実装 → **MVP リリース可能**
4. Phase 4: US2（設定カスタマイズ）でUX向上
5. Phase 5: 品質仕上げ

### Incremental Delivery

- **Iteration 1**: Setup + Foundational → 土台完成（テスト実行可能な状態）
- **Iteration 2**: US1（日報自動生成） → コア機能完成、MVPリリース
- **Iteration 3**: US2（設定カスタマイズ） → カスタマイズ性向上
- **Iteration 4**: Polish → 本番品質

---

## Phase 6: Convergence

**Purpose**: `/speckit.converge` によるコードベースと spec/plan/tasks の乖離修正。

- [X] T042 [CRITICAL] Enricher ノードで LLM エラー発生時にパイプラインを停止する（例外を捕捉せず伝播させる） per Spec:Enricher障害時動作 (contradicts) — `src/dev_log_daily/pipeline/enricher.py:140-148` の try/except を削除し、`call_llm_with_retry` からの例外を上位ノードに伝播させる
- [X] T043 [CRITICAL] Reporter ノードで LLM エラー発生時にパイプラインを停止する（`_generate_error_report` へのフォールバックを廃止） per Spec:LLM永続エラー即時停止 (contradicts) — `src/dev_log_daily/pipeline/reporter.py:128-139` の try/except を削除し、LLM 呼び出し失敗時は例外を伝播させる。エラーレポート生成ロジック `_generate_error_report` は削除
- [X] T044 [CRITICAL] Enricher → Reporter 間に条件付きエッジを追加し、Enricher エラー時にパイプラインを停止する per T029/plan:条件付きエッジ (contradicts) — `src/dev_log_daily/agent.py:117` の `add_edge("enricher", "reporter")` を `add_conditional_edges` に置き換え、`_check_enricher_errors` 関数の docstring とロジックを「エラー時停止」に修正し、条件付きエッジに接続する
- [X] T045 [HIGH] CLIのデフォルト日付計算をシステムローカルタイムゾーンに修正する per FR-001/Edge Cases:タイムゾーン判定 (partial) — `src/dev_log_daily/main.py:18` の `_get_default_date()` を `timezone(timedelta(hours=9))` 固定から `utils/date.py` の `get_previous_date()` を使用するよう修正
- [X] T046 [HIGH] Gitコミットツールの日付範囲をシステムローカルタイムゾーンに修正する per FR-001/Edge Cases:タイムゾーン判定 (partial) — `src/dev_log_daily/tools/git_commits.py:161-162` の `since`/`until` を `+09:00` 固定からローカルタイムゾーンの UTC オフセットを動的計算するよう修正
- [X] T047 [MEDIUM] 未使用のプロンプト定義を整理する per plan:prompts/ (unrequested) — `src/dev_log_daily/prompts/templates.py` の PARSER_PROMPT, ENRICHER_PROMPT, REPORTER_PROMPT（パイプラインノードで未使用）を削除し、ノード実装内のインラインプロンプトと統合するか、逆にノード側を templates.py 参照に切り替える
- [X] T048 [MEDIUM] `ParsedData.chunks_processed` にチャンク分割数を反映させる per plan:chunking (partial) — `src/dev_log_daily/llm/chunking.py` の `process_with_chunking()` で分割数を返し、各ツールの `parse()` メソッドで `ParsedData.chunks_processed` に設定する
- [X] T049 [MEDIUM] 未使用依存 `deepagents` を pyproject.toml から削除する per plan:dependencies (unrequested) — `pyproject.toml` の `dependencies` から `deepagents` を削除
- [X] T050 [MEDIUM] `terminal_history_dir` と data-model.md の `terminal_history_file` の整合を取る per data-model.md:DataSourceConfig (partial) — `config.example.yml` のコメントを更新し、data-model.md のフィールド名を実装に合わせて `terminal_history_dir` に修正する（dir 指定が実際的）
