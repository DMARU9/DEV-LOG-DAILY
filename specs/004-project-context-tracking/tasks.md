---

description: "Task list for project-context-tracking feature"
---

# Tasks: 日報におけるプロジェクトコンテキストの明確化

**Input**: Design documents from `/specs/004-project-context-tracking/`

**Prerequisites**: [plan.md](./plan.md) (required), [spec.md](./spec.md) (required for user stories), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: Tests are MANDATORY — FR-010 requires unit and integration tests. Constitution Article VI mandates tests for all changes.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Src**: `src/dev_log_daily/`
- **Tests**: `tests/unit/`, `tests/integration/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new dependencies or project initialization needed. All required libraries (LangGraph, langchain-openai, pydantic, click, PyYAML) are already installed.

**Checkpoint**: No setup tasks — skip to Phase 2.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data model changes that MUST be complete before ANY user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T001 Add `project_hints` field (`list[dict]`) to `ParsedData` class in `src/dev_log_daily/tools/base.py`. Include in `__init__` (default `[]`) and `to_dict()` output. Each hint has `{source, candidate_name, activity_summary}` format.
- [ ] T002 [P] Add `project_hints` field (`list[dict]`, default `[]`) and `project_activities` field (`dict[str, dict]`, default `{}`) to `DailyState` TypedDict in `src/dev_log_daily/state.py`
- [ ] T003 [P] Update `initial_state` in `src/dev_log_daily/agent.py` (`run_pipeline` function) to include `project_hints=[]` and `project_activities={}`

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - プロジェクト別に整理された日報の生成 (Priority: P1) 🎯 MVP

**Goal**: 日報の「📁 作業プロジェクト」セクションがプロジェクト単位で整理され、全データソースの活動が同一プロジェクトとして統合されて出力される。

**Independent Test**: 複数プロジェクトの活動データで日報を生成し、「📁 作業プロジェクト」セクションにプロジェクトごとの独立したサブセクションが含まれ、各プロジェクトの活動が統合されて記載されていることを確認する。

### Implementation for User Story 1

- [ ] T004 [P] [US1] Implement `project_hints` extraction in `CopilotChatTool.parse()` in `src/dev_log_daily/tools/copilot_chat.py`. Extract workspace names from `raw.workspaces` and generate hints with `source="copilot_chat"`, `candidate_name` from workspace name, and `activity_summary` from the LLM summary per workspace.
- [ ] T005 [P] [US1] Implement `project_hints` extraction in `GitCommitsTool.parse()` in `src/dev_log_daily/tools/git_commits.py`. Extract repository directory names from `raw.files[].path` and generate hints with `source="git_commits"`, `candidate_name` from the path basename, and `activity_summary` from the LLM summary per repo.
- [ ] T006 [US1] Implement `project_hints` extraction in `TerminalLogsTool.parse()` in `src/dev_log_daily/tools/terminal_logs.py`. Extract cwd directory names from `raw.files[].entries[].cwd` using path basename. Also modify the LLM input format from `[{timestamp}] {command}` to `[{timestamp}] [{cwd}] ({git_branch}) $ {command}` so cwd/git_branch are passed to LLM. Empty cwd → `candidate_name="プロジェクト不明"`.
- [ ] T007 [US1] Enhance Enricher in `src/dev_log_daily/pipeline/enricher.py`:
  - Read all 3 parsers' `project_hints` from DailyState
  - Pass `project_hints` to LLM in `ENRICHER_PROMPT_TEMPLATE`
  - Add project-hint integration instructions to `ENRICHER_SYSTEM_PROMPT` (表記ゆれ解決、統合方法)
  - Enrich the expected JSON output schema with a `"projects"` key containing `dict[str, ProjectActivity]`
  - Parse the new `"projects"` field from LLM JSON output and store in `state["project_activities"]`
  - Handle `candidate_name="プロジェクト不明"` hints: aggregate all unknown-activity entries under a single `"プロジェクト不明"` entry in the project_activities output
  - Handle duplicate project names at different paths: include parent directory in `candidate_name` to disambiguate (e.g., `/work/ProjectA` vs `/personal/ProjectA`)
  - Add project-count logic: if more than 10 projects detected, keep detailed entries for top projects and summarize the rest as a list
  - Include cross-source time-series ordering instructions in `ENRICHER_SYSTEM_PROMPT`: "各プロジェクト内でデータソース間の時系列関係を分析し、活動の流れ（設計→実装→テスト等）が追跡できるように key_activities に time-ordered 情報を含めよ"
  - Require ISO 8601 timestamps for each project's activity time range in JSON output
- [ ] T008 [US1] Rewrite `REPORTER_SYSTEM_PROMPT` in `src/dev_log_daily/prompts/system.py` to the new project-based format:
  - Remove old category-based structure (概要/技術/学習/開発活動/問題)
  - Add new structure: ヘッダー → 📋 概要 → 📁 作業プロジェクト (per-project sections) → 🔄 振り返り → 📌 翌日へのアクション → 🏷 技術タグ
  - Each project section template: project_name, time_range, activity summary, technologies, learnings, problems, achievements
  - For each project section: append "(推測)" to project_name when the project assignment was inferred by LLM (not directly from a workspace name)
  - Include instruction for 10+ project scenario: show major projects in full detail, list the rest as a compact list
- [ ] T009 [US1] Update `REPORTER_PROMPT_TEMPLATE` in `src/dev_log_daily/prompts/templates.py`: Add `{project_activities}` placeholder. Keep existing `{copilot_chat_data}`, `{git_commits_data}`, `{terminal_logs_data}` as supplementary inputs.
- [ ] T010 [US1] Rewrite `reporter_node` in `src/dev_log_daily/pipeline/reporter.py`:
  - Read `state["project_activities"]` as primary input
  - Format `project_activities` dict into a readable text block for the prompt
  - Pass `project_activities_text` + supplementary parsed data to `REPORTER_PROMPT_TEMPLATE`
  - Keep file-saving logic unchanged
  - Handle empty `project_activities` (generate "プロジェクト情報なし" report)
  - Render `"プロジェクト不明"` entries as a dedicated subsection under 📁 作業プロジェクト, with note that cwd was unavailable for these activities
- [ ] T011 [P] [US1] Add unit test for `ParsedData.project_hints` field (init, to_dict, is_empty) in `tests/unit/test_base.py`
- [ ] T012 [US1] Create new `tests/unit/test_enricher.py` with unit tests for Enricher's project_hints integration:
  - Test `_get_parsed_summary` with project_hints present
  - Test `_parse_enriched_json` with project_activities in JSON output
  - Test empty project_hints handling
  - Test LLM JSON parsing with malformed output

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Run `pytest tests/unit/test_base.py -v -k "project_hints"` and `pytest tests/unit/test_enricher.py -v` to verify.

- [ ] T022 [US1] Add unit tests for Reporter project-based format in `tests/unit/test_reporter.py` (new file). Test:
  - `format_project_activities` helper with multi-project dict
  - Empty project_activities handling (output "プロジェクト情報なし")
  - "プロジェクト不明" entry rendering
  - Single-project vs multi-project formatting differences
  - Supplementary parsed data merging with project_activities

---

## Phase 4: User Story 2 - ターミナル操作のプロジェクト情報の可視化 (Priority: P2)

**Goal**: ターミナル操作の cwd/git_branch が日報で正しくプロジェクトに紐づけられ、cwd 不明エントリは「プロジェクト不明」として扱われる。

**Independent Test**: ターミナル履歴に複数プロジェクト＋cwd空エントリがある状態で日報を生成し、各コマンドが正しいプロジェクトに分類され、cwd空エントリが「プロジェクト不明」として扱われることを確認する。

### Implementation for User Story 2

- [ ] T013 [P] [US2] Add unit test for TerminalLogs cwd/git_branch in parse() output in `tests/unit/test_terminal_logs.py`. Verify that `[cwd] (branch) $ command` format is used in LLM input and `project_hints` includes cwd-derived candidate_name.
- [ ] T014 [US2] Verify `project_activities` correctly groups terminal entries by cwd-derived project name. Add unit test for "プロジェクト不明" aggregation (handled in T007) and edge cases with mixed known/unknown cwd entries.

**Checkpoint**: At this point, User Story 2 should be independently verifiable. Run `pytest tests/unit/test_terminal_logs.py -v -k "cwd"` to verify.

---

## Phase 5: User Story 3 - プロジェクト横断的な整合性の確認 (Priority: P3)

**Goal**: 同一プロジェクト内で Copilot チャットでの設計議論 → Git コミットでの実装 → ターミナルでのテスト実行の一連の流れが追跡可能になる。

**Independent Test**: 同一プロジェクトで3データソースすべてに活動がある日のデータで日報を生成し、1つのプロジェクトセクション内で各ソースの活動が時系列的に関連付けられて記載されていることを確認する。

### Implementation for User Story 3

- [ ] T015 [P] [US3] Add unit tests in `tests/unit/test_enricher.py` to verify that Enricher output includes time-ordered key_activities (implementation done in T007). Test that cross-source activities are chronologically ordered within each project entry.
- [ ] T016 [US3] Add unit tests in `tests/unit/test_enricher.py` to verify `time_range` field in Enricher output (implementation done in T007). Test ISO 8601 format compliance and empty time_range handling.
- [ ] T017 [US3] Add integration test in `tests/integration/test_pipeline.py` for project-based report with multi-source traceability. Use fixture data where all 3 sources reference the same project.

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification, documentation, and quality assurance.

- [ ] T018 Run all 5 verification scenarios from `quickstart.md` and confirm they pass. Specifically verify SC-004 (user can understand "which project did what" without additional investigation) by reviewing the generated report.
- [ ] T019 Run full test suite: `python -m pytest` — all tests must pass
- [ ] T020 Code cleanup: ensure all new code has proper docstrings and type hints
- [ ] T021 Update `CHANGELOG.md` with feature summary (日本語)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No tasks — skip
- **Foundational (Phase 2)**: Must complete before any user story
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - **US1 (Phase 3)**: No dependency on other stories — start first
  - **US2 (Phase 4)**: Most terminal changes (cwd format) included in US1 T006. This phase adds US2-specific tests. The "プロジェクト不明" handling is already implemented in T007 (Enricher).
  - **US3 (Phase 5)**: Depends on US1's Enricher/Reporter foundation. Time-range and traceability enhancements build on existing project_activities structure.
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 2 — 🎯 **MVP scope** (only US1 needed for initial release)
- **User Story 2 (P2)**: Can start after Phase 2 — Terminal cwd handling already built in US1 T006. Adds dedicated tests and edge case handling.
- **User Story 3 (P3)**: Depends on US1 Enricher/Reporter — adds time-series tracing enhancement

### Within Each User Story

- Models before services (ParsedData before Parser, DailyState before pipeline nodes)
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 2**: T002 (state.py) and T003 (agent.py) can run in parallel
- **Phase 3**: T004 (CopilotChat hints) and T005 (GitCommits hints) can run in parallel
- **Phase 3**: T011 (test_base), T012 (test_enricher — new file), and T022 (test_reporter — new file) can run in parallel
- **All phases**: Different user stories should NOT be run in parallel (sequential P1→P2→P3 dependency)

---

## Parallel Example: User Story 1

```
Day 1: T001 ─────────────────────────────────────────────
             T004 (CopilotChat hints) ──────────┐
             T005 (GitCommits hints) ───────────┤
             T006 (Terminal hints + cwd) ───────┼── T007 (Enricher) ── T008 (Prompt) ── T009 (Template) ── T010 (Reporter)
                                                T011 (test_base) ──┐
                                                T012 (test_enricher) ── T022 (test_reporter)
```

## Implementation Strategy

**MVP scope**: User Story 1 only (Phase 2 + Phase 3 = 13 tasks: T001–T012 + T022). This delivers the core value of project-grouped daily reports.

**Incremental delivery**:
1. First deliverable: Data model (Phase 2) — 3 tasks, validates approach
2. Second deliverable: US1 MVP (Phase 3) — 10 tasks (T004–T012 + T022), core value delivered
3. Third deliverable: US2 terminal edge cases (Phase 4) — 2 tasks, polish
4. Fourth deliverable: US3 traceability (Phase 5) — 3 tasks (T015–T017), advanced feature
5. Final: Polish (Phase 6) — 4 tasks (T018–T021), quality gate
