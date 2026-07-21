# Implementation Plan: パッケージ配布・セットアップ機能

**Branch**: `003-package-distribution-setup` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-package-distribution-setup/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

dev-log-daily を Wheel 形式で配布可能にし、ログ収集スクリプト（`log_terminal.sh`, `post-commit.sample`）をパッケージ内に同梱する。CLI に `dev-log-daily init` サブコマンドを追加し、スクリプトのパス表示・エクスポート・セットアップガイド表示を提供する。ビルドは `python -m build` で手動実行し、GitHub Releases に Wheel を添付して配布する。Wheel インストール時は `site-packages` に配置されるため、一般ユーザー操作によるコード編集は意図されない。

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**:
- click>=8.0（CLI フレームワーク。`@click.group` でサブコマンド化）
- importlib.resources（Python 3.11+ 標準ライブラリ。パッケージデータアクセスに使用）
- build>=1.0（ビルド用、dev 依存関係）
- setuptools>=64.0（既存のビルドシステム。package-data 設定でスクリプトを同梱）

**Storage**: N/A（本機能はパッケージング・配布が主題であり、新しいデータストアは導入しない）

**Testing**: pytest>=8.0, pytest-asyncio>=0.24, pytest-mock>=3.14（dev dependencies）

**Target Platform**: Linux（WSL / VS Code Server）。Windows/macOS は動作確認範囲外。

**Project Type**: CLI ツール（Python Wheel 配布）

**Performance Goals**:
- GitHub Releases からのインストール〜`--help` 表示まで 30 秒以内（SC-001）
- `init --show-paths` の応答 1 秒以内（SC-002）
- `python -m build` によるビルド 30 秒以内（SC-003）

**Constraints**:
- Wheel のみ配布（PyInstaller 等のスタンドアロンバイナリは提供しない）
- 手動リリース（CI 自動化は行わない）
- `init` コマンドは非対話式（すべてフラグで指定）
- 既存の `config.yml` 構造に変更を加えない
- スクリプト内の環境固有設定値（`LOG_ROOT` 等）はユーザー自身が編集する前提
- PyPI 公開は行わず GitHub Releases のみ

**Scale/Scope**: 単一ユーザー向け CLI ツール。単一バージョンの Wheel を GitHub Releases で配布。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 憲法原則 | 評価 | 判定 |
|---------|------|------|
| **I. ツール型アーキテクチャ** | 本機能はデータソースツールではなく、パッケージングと `init` サブコマンドを導入する。`init` は既存 CLI の拡張であり、新たなデータソース抽象化は行わない。 | ✅ PASS |
| **II. オフライン・ローカル優先** | Wheel インストール後の全機能はローカルで完結。`init` コマンドも外部通信不要。ダウンロード行為自体はユーザー操作。 | ✅ PASS |
| **III. エージェント毎のLLM選択** | LLM 設定への変更は一切なし。影響なし。 | ✅ PASS |
| **IV. 設定駆動型** | 設定ファイルへの変更はなし。`init` の各機能は CLI フラグで駆動。 | ✅ PASS |
| **V. 日本語ドキュメント・コメント** | すべてのドキュメント・コードコメントは日本語で記述する。 | ✅ PASS |
| **VI. テスト実装の義務付け** | `init` サブコマンドのユニットテスト、パッケージデータアクセスのテスト、ビルド成果物の検証テストを必須とする。 | ✅ PASS（実装時に担保） |

**判定**: 全ゲート通過。憲法違反なし。Complexity Tracking は不要。

### 再評価（Phase 1 設計後）

| 憲法原則 | 評価 | 判定 |
|---------|------|------|
| **I. ツール型アーキテクチャ** | `init` はデータソースツールではなく CLI 拡張。`ScriptBundle` はパッケージデータでありツールではない。既存の DataSourceTool インターフェースへの影響なし。 | ✅ PASS |
| **II. オフライン・ローカル優先** | `init` 全機能はローカル完結。外部通信不要。 | ✅ PASS |
| **III. エージェント毎のLLM選択** | 影響なし。 | ✅ PASS |
| **IV. 設定駆動型** | `init` は CLI フラグ駆動。config.yml への変更なし。 | ✅ PASS |
| **V. 日本語ドキュメント・コメント** | 全ドキュメント日本語で記述済み。 | ✅ PASS |
| **VI. テスト実装の義務付け** | quickstart.md に検証シナリオ定義済み。実装時に unit/integration テスト必須。 | ✅ PASS |

**判定**: 再評価後も全ゲート通過。憲法違反なし。

## Project Structure

### Documentation (this feature)

```text
specs/003-package-distribution-setup/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── init-command.md  # init サブコマンドの契約定義
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── dev_log_daily/
│   ├── scripts/                  # ★ NEW: ログ収集スクリプト（package-data）
│   │   ├── log_terminal.sh
│   │   └── post-commit.sample
│   ├── __init__.py
│   ├── main.py                   # 変更: @click.command → @click.group に変更し init サブコマンドを追加
│   ├── agent.py
│   ├── state.py
│   ├── config/
│   ├── llm/
│   ├── pipeline/
│   ├── prompts/
│   ├── tools/
│   └── utils/
│
pyproject.toml                     # 変更: package-data 設定追加

tests/
├── unit/
│   ├── test_init_command.py       # ★ NEW: init サブコマンドのテスト
│   └── test_package_data.py       # ★ NEW: パッケージデータアクセスのテスト
├── integration/
│   └── test_build_artifact.py     # ★ NEW: ビルド成果物の検証テスト
└── fixtures/
    └── scripts/                   # ★ NEW: テスト用スクリプトフィクスチャ
```

**Structure Decision**: 既存の単一プロジェクト構成（src/ レイアウト）を維持。`scripts/` ディレクトリを新規追加し、`main.py` を拡張する。新しいモジュールは作成せず、既存のエントリポイントに `init` サブコマンドを追加する。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| （該当なし） | — | — |
