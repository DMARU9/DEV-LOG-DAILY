# Implementation Plan: 日報出力フォーマットの大幅リファクタリング

**Branch**: `005-report-format-refactoring` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/005-report-format-refactoring/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

日報の Markdown 出力フォーマットを従来のフラットなカテゴリ別構成からプロジェクト単位の入れ子構造に変更する。
YAML フロントマター、プロジェクト別サマリーテーブル、プロジェクトごとの詳細セクション（学習内容・開発活動・問題解決・振り返り・アクション）、
「その他」セクションを新設する。Enricher の enriched_data に report_metadata（mood/energy/tags）を追加し、
Reporter のシステムプロンプトを全面的に書き換える。パイプライン構造自体は変更しない。

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: LangGraph（StateGraph）, pydantic（設定スキーマ）, aiohttp（LLM クライアント）

**Storage**: ローカルファイルシステム（Markdown ファイル出力）

**Testing**: pytest（単体テスト + 結合テスト）

**Target Platform**: Linux（開発環境）

**Project Type**: CLI ツール（dev-log-daily）

**Performance Goals**: 本リファクタリングでは新たなパフォーマンス要件なし（出力フォーマット変更のみ）

**Constraints**: 
- 004-project-context-tracking の project_activities / enriched_data 構造に依存
- パイプラインのノード構成は変更不可
- 設定ファイル（config.yml）のスキーマは変更不可
- 全データ空の場合でもエラーなく日報を生成する

**Scale/Scope**: 単一ユーザー向け CLI、日次実行

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 憲法原則 | 判定 | 根拠 |
|---------|------|------|
| I. ツール型アーキテクチャ | ✅ 適合 | ツールインターフェースは変更なし。Reporter/Enricher の内部処理のみ拡張 |
| II. オフライン・ローカル優先 | ✅ 適合 | 出力先はローカルファイルシステム。外部サービス依存なし |
| III. エージェント毎のLLM選択 | ✅ 適合 | コンポーネント別 LLM 設定は変更なし |
| IV. 設定駆動型 | ✅ 適合 | FR-007: 設定スキーマ変更なし。新フォーマットはハードコードデフォルト |
| V. 日本語ドキュメント・コメント | ✅ 適合 | 全ドキュメント・プロンプトは日本語 |
| VI. テスト実装の義務付け | ✅ 適合 | FR-008: 単体テスト＋結合テストを義務化 |
| 品質ゲート（仮想環境実行） | ✅ 適合 | テスト実行は `.venv` 内で行う |

**判定**: 全原則に適合。Complexity Tracking は不要。

## Project Structure

### Documentation (this feature)

```text
specs/005-report-format-refactoring/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output — 設計判断の文書化
├── data-model.md        # Phase 1 output — エンティティ定義
├── quickstart.md        # Phase 1 output — 検証シナリオ
├── contracts/           # Phase 1 output — インターフェース契約
│   ├── report-format.md           # Markdown 出力フォーマット仕様
│   └── enricher-to-reporter.md    # enriched_data 拡張契約
├── checklists/
│   └── requirements.md  # Spec 品質チェックリスト
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/dev_log_daily/
├── pipeline/
│   ├── reporter.py      # 🔴 大幅変更: REPORTER_SYSTEM_PROMPT全面書換, _generate_empty_report更新
│   └── enricher.py      # 🟡 変更: ENRICHER_SYSTEM_PROMPTにreport_metadata出力追加
├── prompts/
│   └── templates.py     # 🟢 変更なし（本featureでは直接変更不要）
├── config/
│   └── schema.py        # 🟢 変更なし
└── state.py             # 🟢 変更なし（既存フィールドで対応）

tests/
├── unit/
│   ├── test_reporter.py  # 🔴 更新: 新フォーマット検証テスト追加/既存テスト更新
│   └── test_enricher.py  # 🟡 更新: report_metadata テスト追加
├── integration/
│   ├── test_pipeline.py  # 🟡 更新: パイプライン全体のフォーマット検証
│   └── conftest.py       # 🟢 変更なし
└── fixtures/
    └── sample_chat.jsonl # 🟢 変更なし
```

**Structure Decision**: 単一プロジェクト構造を継続。新規ファイル・ディレクトリの追加はなし。

## Design Artifacts Generated

### Phase 0 — Research

- [research.md](./research.md): 6件の設計判断を文書化。すべての NEEDS CLARIFICATION を解決済み。

### Phase 1 — Design & Contracts

| 成果物 | パス | 説明 |
|--------|------|------|
| Data Model | [data-model.md](./data-model.md) | ReportFormat, Frontmatter, ProjectSummaryTable, ProjectSection, ActivityType, ProblemStatus, ReportMetadata など全エンティティ定義 |
| Contract: Report Format | [contracts/report-format.md](./contracts/report-format.md) | 外部向け Markdown 出力フォーマットの完全仕様 |
| Contract: Enricher→Reporter | [contracts/enricher-to-reporter.md](./contracts/enricher-to-reporter.md) | enriched_data の report_metadata 拡張仕様 |
| Quickstart | [quickstart.md](./quickstart.md) | 5つの検証シナリオ（フォーマット完全性・空データ・report_metadata・結合・活動フォーマット） |
| Agent Context | [.github/copilot-instructions.md](../../.github/copilot-instructions.md) | プラン参照先を 005-report-format-refactoring/plan.md に更新 |

## Complexity Tracking

該当なし（憲法違反なし）。
