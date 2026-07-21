# Implementation Plan: 複数ワークスペースストレージからのチャットログ収集対応

**Branch**: `002-multi-workspace-chat` | **Date**: 2026-06-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-multi-workspace-chat/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

現状の `CopilotChatTool` は単一ディレクトリ（`data_sources.copilot_chat_dir`）から JSONL チャットログを収集している。本機能では、VS Code の workspaceStorage ベースディレクトリをユーザーが複数指定可能にし、その配下の全ワークスペースディレクトリ（UUID 名）を自動探索してチャットログを収集・ワークスペース別にグループ化する。WSL（Linux）と Windows の両プラットフォームのチャットログパスに対応し、同一 UUID のワークスペースは統合する。旧形式 `copilot_chat_dir` は廃止する。

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**:
- langgraph>=0.4.0（パイプラインオーケストレーション）
- langchain-openai>=0.3.0（LLM 接続）
- click>=8.0（CLI）
- pydantic>=2.0（設定スキーマ検証）
- pyyaml>=6.0（YAML 設定読み込み）

**Storage**: ローカルファイルシステム。入力: VS Code workspaceStorage 配下の JSONL ファイル。出力: Markdown 日報ファイル。

**Testing**: pytest + pytest-asyncio + pytest-mock（dev dependencies）

**Target Platform**: Linux（WSL / VS Code Server）および Windows（VS Code Desktop）のクロスプラットフォーム

**Project Type**: CLI ツール

**Performance Goals**: 10 ワークスペースからの収集・解析を 3 分以内に完了（SC-002）

**Constraints**:
- オフライン・ローカル処理（外部サービス不要）
- 設定駆動型（コード変更なしでカスタマイズ可能）
- 1 ワークスペースの障害が他に影響しない（耐障害性）
- デフォルトのワークスペース上限 50（設定変更可能）
- 旧形式設定検出時は移行案内エラーメッセージを表示して終了

**Scale/Scope**: 単一ユーザーの VS Code 開発環境。50 ワークスペース上限。1 日単位の日報生成。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 憲法原則 | 評価 | 判定 |
|---------|------|------|
| **I. ツール型アーキテクチャ** | `CopilotChatTool` を拡張し、複数ワークスペース対応をツール内で実現。新たな抽象化レイヤーは導入せず、既存の collect/parse インターフェースを維持。 | ✅ PASS |
| **II. オフライン・ローカル優先** | 全処理がローカルファイルシステム上で完結。workspaceStorage の JSONL 読み取りのみで外部通信不要。 | ✅ PASS |
| **III. エージェント毎のLLM選択** | 既存の `ComponentLLMConfig` を変更せずそのまま利用。本機能による影響なし。 | ✅ PASS |
| **IV. 設定駆動型** | `data_sources.copilot_chat.workspace_storage_dirs`（リスト型）と `max_workspaces` を新設。既存の `DataSourceConfig` を拡張して対応。旧形式検出はローダー層で処理。 | ✅ PASS |
| **V. 日本語ドキュメント・コメント** | すべての仕様・設計書・コードコメントは日本語で記述する。 | ✅ PASS |
| **VI. テスト実装の義務付け** | 新規ユニットテスト（設定読み込み、ワークスペース探索、重複排除、上限超過処理）および結合テスト（実際のディレクトリ構造を使用）を必須とする。 | ✅ PASS（実装時に担保） |

**判定**: 全ゲート通過。憲法違反なし。Complexity Tracking は不要。

## Project Structure

### Documentation (this feature)

```text
specs/002-multi-workspace-chat/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── config-schema.md # 設定スキーマ契約
│   └── collection-output.md  # 収集出力形式契約
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── dev_log_daily/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── schema.py          # 変更: DataSourceConfig に CopilotChatConfig 追加
│   │   └── loader.py          # 変更: 旧 copilot_chat_dir 検出と移行案内
│   ├── tools/
│   │   ├── base.py            # 変更: CollectedLog に workspaces フィールド追加
│   │   └── copilot_chat.py    # 変更: 複数WS探索・重複排除・グループ化
│   ├── pipeline/
│   │   ├── collector.py       # 変更: ds_config 構築方法の修正
│   │   ├── parser.py          # 変更なし（workspaces データをそのまま渡す）
│   │   ├── enricher.py        # 変更なし
│   │   └── reporter.py        # 変更: ワークスペースメタデータをプロンプトに含める
│   └── state.py               # 変更なし（workspaces は CollectedLog 内部）
│
tests/
├── unit/
│   ├── test_config.py         # 変更: CopilotChatConfig テスト追加
│   └── ... (既存)
├── integration/
│   ├── test_copilot_chat.py   # 変更: 複数WSテスト追加
│   └── ... (既存)
└── fixtures/
    └── ... (既存)
```

**Structure Decision**: 既存の単一プロジェクト構成（src/ レイアウト）を維持。新しいファイルは作らず、既存の `CopilotChatTool`、`DataSourceConfig`、`CollectedLog` を拡張する。設定ローダーに旧形式検出ロジックを追加。
