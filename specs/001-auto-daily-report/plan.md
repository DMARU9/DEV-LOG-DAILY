# Implementation Plan: 開発活動ログ自動収集・日報生成フレームワーク

**Branch**: `001-auto-daily-report` | **Date**: 2026-06-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-auto-daily-report/spec.md`

## Summary

開発者が毎日使用する複数ツール（GitHub Copilotチャット、Gitコミット、ターミナル操作履歴）から活動ログを自動収集し、LLMで構造化・要約してMarkdown形式の日報を自動生成するCLIツール。LangGraph StateGraphによるパイプラインオーケストレーションで収集→解析→補完→生成の4ノードを逐次実行。各コンポーネントは独立したLLMモデルを設定可能で、設定ファイル（YAML）によるカスタマイズをサポートする。

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: LangGraph（状態グラフ管理）, deepagent（自律型エージェント）, llama.cpp（ローカルLLM推論）, langchain-openai（OpenAI互換APIクライアント）, PyYAML（設定ファイル解析）, pydantic（設定スキーマ検証）, click（CLIインターフェース）

**Storage**: ローカルファイルシステム（JSONLチャットログ読み取り、Gitリポジトリ読み取り、ターミナル履歴ファイル読み取り、Markdown日報ファイル書き出し）

**Testing**: pytest（単体テスト・結合テスト）, pytest-asyncio（非同期テスト）, pytest-mock（モック）

**Target Platform**: Linux（主要）、Windows/macOS（クロスプラットフォーム対応）。OSのローカルタイムゾーン設定に依存。

**Project Type**: CLIツール（`dev-log-daily` コマンド）

**Performance Goals**: CLI実行から日報出力完了まで3分以内（SC-001）。ログファイル処理タイムアウトはデフォルト600秒で設定可能。

**Constraints**: オフライン・ローカル優先（外部クラウド送信はデフォルト無効）。全データはローカルファイルシステムに保存。LLM APIキーは設定ファイルに直接記述。

**Scale/Scope**: 単一ユーザー（個人開発者）。単一日付の日報生成のみ。複数日・週次サマリーは範囲外。データソースは内蔵固定の3種類（Copilotチャット、Gitコミット、ターミナル履歴）。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. ツール型アーキテクチャ | ✅ PASS | 各データソース（Copilotチャット、Gitコミット、ターミナル履歴）は内蔵固定のツールとして実装。collect/parseの共通インターフェースに準拠。外部動的ロード・ユーザー追加不可。 |
| II. オフライン・ローカル優先 | ✅ PASS | 全処理がローカル完結。外部サービスへのデータ送信はデフォルト無効（FR-012）。収集ログ・生成日報はローカルファイルシステムに保存（FR-011）。 |
| III. エージェント毎のLLM選択 | ✅ PASS | 各コンポーネント（Collector、Parser、Enricher、Reporter）が独立したLLMモデルを設定ファイルで指定可能（FR-010）。 |
| IV. 設定駆動型 | ✅ PASS | YAML設定ファイルでカスタマイズ可能。スキーマ検証により不正設定を起動時エラー報告（FR-007、FR-009）。 |
| V. 日本語ドキュメント・コメント | ✅ PASS | 全ドキュメント・コードコメントを日本語で統一。 |
| VI. テスト実装の義務付け | ✅ PASS | 全機能に単体テスト・結合テストが必須（FR-014）。各データソースツールに結合テストを実装。 |

**品質ゲート**:
- pre-commit フック: isort, ruff, pyright, trailing-whitespace, pytest がすべて成功すること
- `--no-verify` によるコミット禁止

**Gate Result**: ALL PASS — Continue to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── dev_log_daily/
│   ├── __init__.py
│   ├── main.py              # CLI エントリーポイント（click）
│   ├── agent.py             # LangGraph StateGraph 定義・ノード実装
│   ├── state.py             # DailyState TypedDict 定義
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py          # DataSourceTool 抽象基底クラス（collect/parse）
│   │   ├── copilot_chat.py  # Copilotチャットログ収集・解析
│   │   ├── git_commits.py   # Gitコミット収集・解析
│   │   └── terminal_logs.py # ターミナル履歴収集・解析
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── collector.py     # Collector ノード（並列収集）
│   │   ├── parser.py        # Parser ノード（LLM解析）
│   │   ├── enricher.py      # Enricher ノード（クロスリファレンス・補完）
│   │   └── reporter.py      # Reporter ノード（日報生成・出力）
│   ├── config/
│   │   ├── __init__.py
│   │   ├── schema.py        # pydantic 設定スキーマ定義
│   │   └── loader.py        # YAML設定ファイル読み込み・検証
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py        # LLMクライアント（リトライ・タイムアウト制御）
│   │   └── chunking.py      # トークン分割・要約統合ロジック
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── system.py        # システムプロンプト定義
│   │   └── templates.py     # コンポーネント別プロンプトテンプレート
│   └── utils/
│       ├── __init__.py
│       ├── date.py          # 日付ユーティリティ（タイムゾーン・日付計算）
│       ├── file.py          # ファイルI/Oユーティリティ
│       └── logging.py       # ロギング設定（標準出力・ファイル出力）

tests/
├── __init__.py
├── unit/
│   ├── __init__.py
│   ├── test_config.py       # 設定読み込み・スキーマ検証テスト
│   ├── test_date.py         # 日付ユーティリティテスト
│   ├── test_chunking.py     # トークン分割テスト
│   └── test_llm_client.py   # LLMクライアントテスト
├── integration/
│   ├── __init__.py
│   ├── test_copilot_chat.py # Copilotチャットツール結合テスト
│   ├── test_git_commits.py  # Gitコミットツール結合テスト
│   ├── test_terminal_logs.py# ターミナル履歴ツール結合テスト
│   └── test_pipeline.py     # パイプライン全体結合テスト
└── fixtures/
    ├── sample_chat.jsonl
    ├── sample_git_repo/
    └── sample_terminal.log

pyproject.toml                # プロジェクトメタデータ・依存関係・ツール設定
config.example.yml            # 設定ファイル例
.pre-commit-config.yaml       # pre-commit フック設定
```

**Structure Decision**: 単一CLIプロジェクト構造を採用。`src/dev_log_daily/` 配下に全ソースコードを配置。ツール（tools/）、パイプライン（pipeline/）、設定（config/）、LLM制御（llm/）、プロンプト（prompts/）を機能別に分割。テストは unit/ と integration/ に分離し、fixtures/ にテストデータを配置。

## Complexity Tracking

> Constitution Check に違反は検出されなかったため、本セクションは空とする。
