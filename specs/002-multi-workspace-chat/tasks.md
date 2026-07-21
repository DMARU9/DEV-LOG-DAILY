# Tasks: 複数ワークスペースストレージからのチャットログ収集対応

**Input**: Design documents from `specs/002-multi-workspace-chat/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: 単体テスト・結合テストを MUST とする（憲法 VI 準拠）。各 User Story のテストタスクは実装より先に作成し、事前に失敗することを確認する（TDD）。

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: 該当なし — 既存プロジェクトへの機能追加のため、新規セットアップは不要。

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 全 User Story に共通する基盤変更。このフェーズが完了するまでどの User Story も開始不可。

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T001 Add `CopilotChatConfig` pydantic model in `src/dev_log_daily/config/schema.py` (fields: `workspace_storage_dirs: list[str]`, `max_workspaces: int = 50`)
- [X] T002 [P] Replace `copilot_chat_dir` with `copilot_chat: CopilotChatConfig` field in `DataSourceConfig` in `src/dev_log_daily/config/schema.py`; update `AppConfig.validate_all_paths_not_empty` to remove `copilot_chat_dir`
- [X] T003 [P] Add legacy `copilot_chat_dir` detection in `src/dev_log_daily/config/loader.py` that prints migration guidance error and exits with code 1
- [X] T004 Add `workspaces: list[dict]` field to `CollectedLog` in `src/dev_log_daily/tools/base.py`; update `to_dict()` and `is_empty` property; add `workspace_count` property

**Checkpoint**: ✅ Foundation ready — CopilotChatConfig schema, loader detection, and CollectedLog extension complete.

---

## Phase 3: User Story 1 — 複数ワークスペースのチャットログ一括収集 (Priority: P1) 🎯 MVP

**Goal**: ユーザーが指定した workspaceStorage ベースディレクトリ配下の全ワークスペースディレクトリを自動探索し、各ワークスペースのチャットログ（JSONL）を収集する。

**Independent Test**: workspaceStorage ベースディレクトリ（3 つのワークスペースディレクトリを含む）を設定し、日報生成を実行。全ワークスペースのチャットログが収集され、標準出力にワークスペース別の収集結果が表示されることを確認する。

### テスト for User Story 1 ⚠️ MUST（憲法 VI）

> **NOTE**: Write these tests FIRST, ensure they FAIL before implementation

- [X] T005 [P] [US1] Unit test: `CopilotChatConfig` validation (valid config, empty dirs list, invalid max_workspaces) in `tests/unit/test_config.py`
- [X] T006 [P] [US1] Unit test: Legacy `copilot_chat_dir` detection in loader in `tests/unit/test_config.py`
- [X] T007 [P] [US1] Unit test: `CollectedLog` workspaces field — `to_dict()`, `is_empty`, `workspace_count` in `tests/unit/test_base.py`
- [X] T008 [P] [US1] Integration test: Multi-workspace collection from single base dir (3 workspaces with transcripts) in `tests/integration/test_copilot_chat.py`
- [X] T009 [P] [US1] Integration test: Empty workspaceStorage (no valid workspaces) in `tests/integration/test_copilot_chat.py`
- [X] T010 [P] [US1] Integration test: Workspace with missing transcripts/chatSessions is skipped gracefully in `tests/integration/test_copilot_chat.py`
- [X] T011 [P] [US1] Integration test: `max_workspaces` limit enforcement (5 workspaces found, limit 3) in `tests/integration/test_copilot_chat.py`
- [X] T012 [P] [US1] Integration test: Non-existent base dir is warned and skipped in `tests/integration/test_copilot_chat.py`

### 実装 for User Story 1

- [X] T013 [US1] Update `collector_node` in `src/dev_log_daily/pipeline/collector.py` to pass `copilot_chat` config instead of flat `copilot_chat_dir` string to `CopilotChatTool`
- [X] T014 [US1] Implement `_discover_workspaces()` method in `src/dev_log_daily/tools/copilot_chat.py` that enumerates UUID subdirs under each workspace_storage_dir, checks for transcripts/ or chatSessions/ paths, and returns a list of discovered workspace paths
- [X] T015 [P] [US1] Implement dual-path check logic in `src/dev_log_daily/tools/copilot_chat.py`: for each workspace UUID dir, check `GitHub.copilot-chat/transcripts/` (Linux) and `chatSessions/` (Windows); collect JSONL from whichever exists
- [X] T016 [US1] Refactor `CopilotChatTool.collect()` in `src/dev_log_daily/tools/copilot_chat.py` to iterate over discovered workspaces, collect JSONL sessions per workspace, and produce `CollectedLog` with both `files` (legacy) and `workspaces` (new structure)
- [X] T017 [US1] Implement `_log_collection_progress()` in `src/dev_log_daily/tools/copilot_chat.py` for workspace-level logging: `+ name: N sessions found`, `− UUID: transcriptsなしでスキップ`, `⚠ UUID: 上限超過でスキップ`

**Checkpoint**: US1 complete — 単一ベースディレクトリでの複数ワークスペース自動探索と収集が動作。

---

## Phase 4: User Story 2 — ワークスペースの識別と日報でのグルーピング (Priority: P1)

**Goal**: 収集したチャットログをワークスペース単位で識別・グループ化し、workspace.json から人間可読な名前を抽出して日報に出力する。

**Independent Test**: 複数のワークスペースでチャットログを生成し、日報を確認する。各ワークスペースのチャットログが適切に識別・グループ化され、どのプロジェクトの会話かが明確にわかることを確認する。

### テスト for User Story 2 ⚠️ MUST（憲法 VI）

- [X] T018 [P] [US2] Unit test: `_extract_workspace_name()` — workspace.json with folder, workspace file, no json fallback in `tests/unit/test_copilot_chat.py`
- [X] T019 [P] [US2] Unit test: `_read_workspace_json()` — valid JSON, malformed JSON, missing file in `tests/unit/test_copilot_chat.py`
- [X] T020 [P] [US2] Integration test: Workspace metadata in collected output (workspace_id, workspace_name, metadata fields) in `tests/integration/test_copilot_chat.py`
- [X] T021 [P] [US2] Integration test: Workspace grouping — multiple sessions from same workspace are grouped together in `tests/integration/test_copilot_chat.py`

### 実装 for User Story 2

- [X] T022 [P] [US2] Implement `_read_workspace_json()` in `src/dev_log_daily/tools/copilot_chat.py` — parse workspace.json, handle missing/malformed files gracefully with UUID fallback
- [X] T023 [P] [US2] Implement `_extract_workspace_name()` in `src/dev_log_daily/tools/copilot_chat.py` — extract human-readable name from workspace.json using priority: folder → workspace file → UUID fallback with "Unknown Workspace (<UUID>)" format
- [X] T024 [US2] Build workspace metadata dict in `CopilotChatTool.collect()` per discovered workspace: include `workspace_json`, `storage_dirs_used`, `platforms` in `src/dev_log_daily/tools/copilot_chat.py`
- [X] T025 [US2] Implement workspace-grouped session output: sessions are nested under workspace entries in `CollectedLog.workspaces[].sessions` in `src/dev_log_daily/tools/copilot_chat.py`
- [X] T038 [US2] Inject workspace metadata into Reporter prompt in `src/dev_log_daily/pipeline/reporter.py` — add workspace names, session counts, and metadata to the reporter prompt template so workspace context is included in daily report generation

**Checkpoint**: ✅ US1 + US2 complete — ワークスペースの識別・グループ化が動作。workspace.json からの名前抽出、workspace メタデータの構築、Reporter へのコンテキスト注入が完了。

---

## Phase 5: User Story 3 — クロスプラットフォーム対応（WSL + Windows） (Priority: P2)

**Goal**: 複数の workspaceStorage ベースディレクトリ（WSL 用・Windows 用）からの収集をサポートし、同一 UUID のワークスペースを統合、セッションの重複排除を行う。

**Independent Test**: WSL 上のパスと Windows のパスの両方を設定し、日報を生成する。両環境のチャットログが日報に統合され、同一 UUID のワークスペースが重複排除されて 1 つのセクションに表示されることを確認する。

### テスト for User Story 3 ⚠️ MUST（憲法 VI）

- [X] T026 [P] [US3] Integration test: Cross-platform dual-directory collection (two base dirs with disjoint workspaces) in `tests/integration/test_copilot_chat.py`
- [X] T027 [P] [US3] Integration test: UUID-based workspace merging (same UUID in two base dirs → single workspace entry) in `tests/integration/test_copilot_chat.py`
- [X] T028 [P] [US3] Integration test: Session deduplication across platforms (same sessionId appears in both Linux and Windows → kept once) in `tests/integration/test_copilot_chat.py`
- [X] T029 [P] [US3] Integration test: Duplicate base dir paths are deduplicated in `tests/integration/test_copilot_chat.py`
- [X] T030 [P] [US3] Unit test: `_deduplicate_sessions()` — exact sessionId match dedup logic in `tests/unit/test_copilot_chat.py`

### 実装 for User Story 3

- [X] T031 [US3] Implement multi-base-dir iteration in `_discover_workspaces()`: loop over all workspace_storage_dirs, deduplicate same dir paths, accumulate discovered workspaces in `src/dev_log_daily/tools/copilot_chat.py`
- [X] T032 [US3] Implement UUID-based workspace merging: when same UUID is found across multiple base dirs, merge into single `WorkspaceInfo` entry with combined sessions and multi-platform metadata in `src/dev_log_daily/tools/copilot_chat.py`
- [X] T033 [US3] Implement `_deduplicate_sessions()`: global set of seen sessionIds, skip duplicates, log at debug level in `src/dev_log_daily/tools/copilot_chat.py`

**Checkpoint**: ✅ All user stories complete — クロスプラットフォーム統合収集が動作。

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 全 User Story にわたる仕上げ・品質向上

- [X] T034 [P] Update `config.example.yml` to use new `data_sources.copilot_chat.workspace_storage_dirs` format with comments
- [X] T035 [P] Update `tests/integration/conftest.py` — add workspaceStorage fixture factory for multi-workspace test setup (create UUID dirs, workspace.json, transcripts)
- [X] T036 Update `quickstart.md` validation scenarios with actual test commands and expected outputs
- [X] T037 [P] Run full test suite (`uv run pytest`), fix any failures, ensure all tests pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: 即座に開始可能 — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Foundational 完了後に開始 — 他の User Story への依存なし
- **User Story 2 (Phase 4)**: User Story 1 完了後に開始（workspace データ構造が必要）
- **User Story 3 (Phase 5)**: User Story 1 完了後に開始；User Story 2 とは並行可能
- **Polish (Phase 6)**: 全 User Story 完了後に開始

### User Story Dependencies

```
Foundational (T001-T004)
       │
       ▼
  User Story 1 (T005-T017) ─── MVP ─── 単一ベースディレクトリでの複数WS収集
       │
       ├──────────────────────────────┐
       ▼                              ▼
  User Story 2 (T018-T025, T038)    User Story 3 (T026-T033)
  (WS識別・グループ化)           (クロスプラットフォーム統合)
       │                              │
       └──────────────┬───────────────┘
                      ▼
              Polish (T034-T037)
```

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Test infrastructure (fixtures) before test cases
- Core logic before logging/output
- Story complete before moving to next priority

### Parallel Opportunities

- **Foundational**: T002 (schema) and T003 (loader) can run in parallel; both depend on T001 but T001 is small
- **US1 Tests**: T005-T012 all marked [P] — can run in parallel (different test modules/files)
- **US1 Implementation**: T014 (discovery) and T015 (path check) can run partly in parallel; T013 must come first
- **US2 Implementation**: T022 (read workspace.json) and T023 (extract name) can run in parallel
- **US3 Implementation**: All test tasks T026-T030 marked [P] — independent

---

## Parallel Example: User Story 1

```text
Day 1:
  T013 (update collector.py) ─── 15 min
  T014 (discover_workspaces) ─── 45 min
  T015 (dual-path check) ─────── 30 min  ← T014 と並行可能

Day 2:
  T016 (refactor collect()) ──── 60 min  ← T014, T015 が必要
  T017 (logging) ─────────────── 20 min

Tests (T005-T012) ────────────── 並行作成可能
```

## Implementation Strategy

1. **MVP = User Story 1**: 単一ベースディレクトリでの複数ワークスペース自動探索と収集を最優先で実装する。旧形式 `copilot_chat_dir` からの移行パスを含める。
2. **User Story 2 を続けて実装**: ワークスペースの識別とグループ化は US1 の上に自然に構築できる。workspace.json の解析を追加するだけで US1 の収集結果が大幅に価値向上する。
3. **User Story 3 は最後**: クロスプラットフォーム対応は複数ベースディレクトリ間の統合が主な処理であり、US1 の単一ディレクトリ処理が安定してから取り組む。

### リスク軽減

- **workspace.json のフォーマット差異**: テスト用に複数の workspace.json バリエーション（folder 形式、workspace 形式、空、不正 JSON）を fixture として用意する
- **大量ワークスペースのパフォーマンス**: ディレクトリスキャンは `Path.iterdir()` で軽量に行い、上限チェックを早期に実施する
- **重複排除の正確性**: sessionId の完全一致のみに依存し、部分一致や類似度判定は行わない。テストで複数パターンの重複ケースを網羅する
