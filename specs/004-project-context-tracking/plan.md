# Implementation Plan: 日報におけるプロジェクトコンテキストの明確化

**Branch**: `004-project-context-tracking` | **Date**: 2026-07-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-project-context-tracking/spec.md`

## Summary

日報の「どのプロジェクトに対する作業か」を明確にするため、3つのデータソース（Copilot チャット・Git コミット・ターミナル履歴）からプロジェクト名のヒントを抽出し、Enricher で統合してプロジェクト単位の日報を生成する。Parser で抽出した `project_hints` を Enricher がクロスリファレンスして正規化された `dict[str, ProjectActivity]` を生成し、Reporter はこれを主要入力としてプロジェクト単位の日報フォーマットで出力する。日報全体の構成をカテゴリ別からプロジェクト単位に変更する。

## Technical Context

**Language/Version**: Python 3.11+（既存プロジェクトと同一）

**Primary Dependencies**:
- 既存: LangGraph, langchain-openai, pydantic, click, PyYAML
- 新規導入: なし（既存の依存関係のみで実装可能）
- 変更方針: terminal_logs の parse() で cwd/git_branch を LLM に渡す（テキストフォーマット変更のみ）

**Storage**: ローカルファイルシステム。変更なし。出力ファイル名は従来通り `daily_report_YYYY-MM-DD.md` を上書き保存。

**Testing**: pytest, pytest-asyncio, pytest-mock（既存構成を拡張）

**Target Platform**: Linux（Windows/macOS は既存と同様のクロスプラットフォーム対応）

**Project Type**: CLIツール（`dev-log-daily` コマンド）— 変更なし

**Performance Goals**: CLI実行から日報出力完了まで3分以内（既存 SC-001 を維持）。プロジェクトヒント抽出・統合による追加処理時間は 10秒以内に収める。

**Constraints**:
- ユーザーにプロジェクト名を意識させない設計（設定不要）
- 既存パイプラインのノード構成を変更しない
- DailyState の既存フィールド互換性を維持
- 表記ゆれ解決は LLM 推論のみに依存（設定機構なし）

**Scale/Scope**: 単一ユーザー（個人開発者）。単一日付の日報生成。データソースは内蔵固定。プロジェクト名の手動マッピングは提供しない。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. ツール型アーキテクチャ | ✅ PASS | 各データソースツールの Parser に `project_hints` 抽出を追加するが、ツールのインターフェース（collect/parse）は不変。外部からの動的ロードやユーザー追加は不可。 |
| II. オフライン・ローカル優先 | ✅ PASS | 全処理がローカル完結。新たな外部依存なし。LLM の推論による表記ゆれ解決もローカル LLM で完結。 |
| III. エージェント毎のLLM選択 | ✅ PASS | コンポーネント別 LLM 設定に変更なし。Enricher は既存の LLM 設定をそのまま使用。 |
| IV. 設定駆動型 | ✅ PASS | 新たな設定項目は追加しない。プロジェクト名解決にユーザー設定を必要としない設計（FR-009 決定事項）。 |
| V. 日本語ドキュメント・コメント | ✅ PASS | 全ドキュメント・コードコメントを日本語で統一（変更なし）。 |
| VI. テスト実装の義務付け | ✅ PASS | Parser、Enricher、Reporter への変更に対応するテストを追加する（FR-010）。 |

**品質ゲート**:
- pre-commit フック: isort, ruff, pyright, trailing-whitespace, pytest がすべて成功すること
- `--no-verify` によるコミット禁止

**Gate Result**: ALL PASS — Continue to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/004-project-context-tracking/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

既存プロジェクト構造に機能追加のみ行う。新規ファイルは一切作成せず、以下の既存ファイルを修正する:

```text
src/dev_log_daily/
├── state.py                    # [修正] DailyState に project_hints / project_activities フィールド追加
├── tools/
│   ├── base.py                 # [修正] ParsedData に project_hints フィールド追加
│   ├── copilot_chat.py         # [修正] parse() でワークスペース名を project_hints に含める
│   ├── git_commits.py          # [修正] parse() でリポジトリパス名を project_hints に含める
│   └── terminal_logs.py        # [修正] parse() で cwd/git_branch を LLM 入力に含め、project_hints に cwd ディレクトリ名を含める
├── pipeline/
│   ├── enricher.py             # [修正] project_hints をクロスリファレンスして project_activities 辞書を生成
│   └── reporter.py             # [修正] プロジェクト単位フォーマットに変更（システムプロンプト・テンプレート全面書き換え）
├── prompts/
│   ├── system.py               # [修正] REPORTER_SYSTEM_PROMPT をプロジェクト単位フォーマットに変更
│   └── templates.py            # [修正] REPORTER_PROMPT_TEMPLATE に project_activities を渡すよう変更

tests/
├── unit/
│   ├── test_base.py            # [修正] ParsedData.project_hints のテスト追加
│   ├── test_terminal_logs.py   # [修正] cwd/git_branch 保持のテスト追加
│   └── test_enricher.py        # [新規] project_hints 統合のテスト追加
└── integration/
    └── test_pipeline.py        # [修正] プロジェクト単位フォーマットの結合テスト追加
```

**Structure Decision**: 新規ファイルを一切作成しない方針。全変更は「既存ファイルの修正」で完結する。これは本機能が既存パイプラインの拡張であり、アーキテクチャ変更を伴わないため。

## Complexity Tracking

> Constitution Check に違反は検出されなかったため、本セクションは空とする。
