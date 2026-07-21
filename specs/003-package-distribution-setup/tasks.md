# Tasks: パッケージ配布・セットアップ機能

**Input**: Design documents from `specs/003-package-distribution-setup/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/init-command.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root

---

## Phase 1: Setup — パッケージ内スクリプト配置

**Purpose**: ログ収集スクリプトをパッケージ内に移動し、ビルド設定を構成する

- [X] T001 Create `src/dev_log_daily/scripts/` directory and copy `log_terminal.sh`, `post-commit.sample` from project root into it
- [X] T002 [P] Add `[tool.setuptools.package-data] "dev_log_daily" = ["scripts/*"]` to `pyproject.toml` for Wheel inclusion

**Checkpoint**: Setup complete — scripts are inside the package and package-data is configured

---

## Phase 2: Foundational — CLI 基盤 + パッケージ設定

**Purpose**: `init` サブコマンドを追加するための CLI 基盤整備とビルド依存の追加

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Refactor `src/dev_log_daily/main.py`: change `@click.command` to `@click.group(invoke_without_command=True)` and wrap existing logic as default invocation
- [X] T004 [P] Add `build>=1.0` to `[project.optional-dependencies.dev]` in `pyproject.toml`
- [X] T020 [P] Create test fixtures: `tests/fixtures/scripts/log_terminal.sh` and `tests/fixtures/scripts/post-commit.sample` for unit test use

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 — Wheel によるパッケージインストール (Priority: P1) 🎯 MVP

**Goal**: ユーザーが Wheel をインストールし、`dev-log-daily --help` が動作する状態を作る

**Independent Test**: 新規仮想環境に Wheel を `pip install` し、`dev-log-daily --help` が正常に表示されることを確認する

### Tests for User Story 1 (test-first) ⚠️

- [X] T021 [US1] Write `tests/integration/test_build_artifact.py` with Wheel build and content verification — MUST FAIL before implementation

### Implementation for User Story 1

- [X] T005 [P] [US1] Build wheel with `python -m build` and verify `scripts/log_terminal.sh` and `scripts/post-commit.sample` are included in the wheel
- [X] T006 [US1] Test wheel installation in a clean venv: `pip install dist/dev_log_daily-*.whl` and verify `dev-log-daily --help` works (see `quickstart.md` Scenario 1-2)

**Checkpoint**: At this point, User Story 1 should be fully functional — Wheel can be built, installed, and the command works

---

## Phase 4: User Story 2 — ログ収集スクリプトのパッケージ内蔵 + init コマンド (Priority: P1)

**Goal**: `dev-log-daily init` サブコマンドを実装し、スクリプトのパス表示・エクスポート・セットアップガイドを提供する

**Independent Test**: `dev-log-daily init --show-paths` で `log_terminal.sh` と `post-commit.sample` の絶対パスが表示され、実在するファイルを指していることを確認する

### Tests for User Story 2 (test-first) ⚠️

- [X] T022 [P] [US2] Write `tests/unit/test_init_command.py` with init subcommand flag behavior tests (--show-paths, --export-post-commit, --guide, flag exclusivity) — MUST FAIL before implementation
- [X] T023 [P] [US2] Write `tests/unit/test_package_data.py` with importlib.resources path resolution and file existence tests — MUST FAIL before implementation

### Implementation for User Story 2

- [X] T007 [US2] Implement script path resolution using `importlib.resources.files("dev_log_daily") / "scripts"` as a helper function in `src/dev_log_daily/main.py` (scripts/ is pure package-data, no __init__.py)
- [X] T008 [US2] Register `init` subcommand group under `main` with mutually exclusive `--show-paths`, `--export-post-commit`, `--guide` flags in `src/dev_log_daily/main.py`
- [X] T009 [P] [US2] Implement `--show-paths` in `src/dev_log_daily/main.py`: display absolute paths of `log_terminal.sh` and `post-commit.sample` (SC-002: 応答1秒以内を確認)
- [X] T010 [P] [US2] Implement `--export-post-commit <dir>` in `src/dev_log_daily/main.py`: copy `post-commit.sample` to specified directory with validation
- [X] T011 [P] [US2] Implement `--guide` in `src/dev_log_daily/main.py`: print setup instructions for terminal log and git hook
- [X] T012 [US2] Add flag exclusivity validation: show error and exit code 1 if multiple flags are specified in `src/dev_log_daily/main.py`

**Checkpoint**: At this point, User Story 2 should be fully functional — all three init flags work correctly

---

## Phase 5: User Story 3 — リリースビルドと配布 (Priority: P2)

**Goal**: バージョン更新とリリース手順を文書化し、手動リリースを可能にする

**Independent Test**: `python -m build` を実行し、`dist/` に Wheel とソースアーカイブが生成されることを確認する

### Implementation for User Story 3

- [X] T013 [US3] Update `version` in `pyproject.toml` (e.g., `0.2.0`) and create/update `CHANGELOG.md` with release notes (日本語で記述、憲法準拠)
- [X] T014 [US3] Create `RELEASE.md` in repository root documenting manual release procedure (build → tag → GitHub Releases upload)
- [X] T015 [US3] Perform full release dry-run: build (SC-003: 30秒以内に完了), install in clean venv, run `init --show-paths`, verify script files match source (SC-005), verify all features

**Checkpoint**: Release process documented and validated

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 残りのドキュメント更新とクリーンアップ

- [X] T016 [P] Update `README.md`: add "Wheel からのインストール" section and update installation instructions
- [X] T017 [P] Remove root-level `log_terminal.sh` and `post-commit.sample` (scripts are now inside the package); add migration note in changelog
- [X] T019 Run validation scenarios from `specs/003-package-distribution-setup/quickstart.md` Scenarios 1–7 and confirm all pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (P1)**: Depends on Foundational — scripts in package, build configured
- **User Story 2 (P1)**: Depends on Foundational + can proceed in parallel with US1 (different concerns: US1 = packaging, US2 = CLI)
- **User Story 3 (P2)**: Depends on US1 (needs working wheel) and US2 (needs init command verified)
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

```
Phase 1 (Setup)
   └── Phase 2 (Foundational)
          ├── Phase 3: US1 (P1) — Wheel Distribution
          ├── Phase 4: US2 (P1) — Init Command
          │     └── Both US1 and US2 feed into...
          └── Phase 5: US3 (P2) — Release Process
                  └── Phase 6: Polish
```

- **US1 (P1) → US3 (P2)**: US3 requires US1 to be complete (wheel build + install verification)
- **US2 (P1)**: Independent from US1 — only needs Foundational (click group refactoring)
- **US3 (P2)**: Requires both US1 (working wheel) and US2 (init verified) for a complete release

### Parallel Opportunities

- **Phase 1**: T001 and T002 are independent and can run in parallel
- **Phase 2**: T003, T004, and T020 are independent and can run in parallel
- **Phase 3→4**: US1 and US2 can proceed in parallel once Phase 2 completes (different files: `pyproject.toml` + build vs `main.py`)
- **Within US2**: T009, T010, T011 (three init flags) can run in parallel after T007 and T008
- **Within US2 tests**: T022 and T023 can run in parallel
- **Phase 6**: All Polish tasks marked [P] can run in parallel

### Test Strategy

- **Test-first approach**: Tests in each US (T021, T022, T023) MUST be written and FAIL before implementation begins
- **Phase 2 (T020)**: Test fixture scripts must exist before US2 unit tests can reference them
- **T019 (Polish)**: Full validation from quickstart.md serves as end-to-end acceptance testing

### Implementation Strategy

1. **MVP (Phase 1+2+3)**: Wheel がビルドできて `pip install` でコマンドが動く状態 — US1 完了
2. **Incremental (Phase 4)**: `init` サブコマンドの全機能追加 — US2 完了
3. **Release (Phase 5+6)**: リリース手順の文書化と最終調整 — US3 + Polish 完了
