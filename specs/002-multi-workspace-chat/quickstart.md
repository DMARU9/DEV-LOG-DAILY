# Quickstart: 複数ワークスペースストレージからのチャットログ収集対応

**Date**: 2026-06-22 | **Feature**: `002-multi-workspace-chat`

---

## 前提条件

- Python 3.11 以上
- llama.cpp サーバー起動済み（または OpenAI 互換 API エンドポイント利用可能）
- VS Code の workspaceStorage ディレクトリが存在すること（以下のいずれかまたは両方）：
  - **Linux（WSL/VS Code Server）**: `~/.vscode-server/data/User/workspaceStorage/`
  - **Windows（VS Code Desktop）**: `~/AppData/Roaming/Code/User/workspaceStorage/`

---

## セットアップ

### 1. 設定ファイルの作成

`config.yml` を作成し、`data_sources.copilot_chat` セクションを設定する：

```yaml
llm:
  collector:
    model: Qwen3.6-35B-A3B
    base_url: http://localhost:8080/v1
    api_key: not-needed
  parser:
    model: Qwen3.6-35B-A3B
    base_url: http://localhost:8080/v1
    api_key: not-needed
  enricher:
    model: Qwen3.6-35B-A3B
    base_url: http://localhost:8080/v1
    api_key: not-needed
  reporter:
    model: Qwen3.6-35B-A3B
    base_url: http://localhost:8080/v1
    api_key: not-needed

data_sources:
  copilot_chat:
    workspace_storage_dirs:
      - /home/takumi/.vscode-server/data/User/workspaceStorage
      - /mnt/c/Users/takumi/AppData/Roaming/Code/User/workspaceStorage
    max_workspaces: 50
  git_root_dir: /home/takumi/github
  terminal_history_dir: /home/takumi/.dev-log-daily/terminal

output:
  directory: /path/to/output

timeout_seconds: 120
```

> **注意**: 旧形式 `data_sources.copilot_chat_dir` は使用しないこと。使用した場合は移行案内エラーで終了する。

詳細な設定スキーマは [contracts/config-schema.md](./contracts/config-schema.md) を参照。

---

## 実行

### 前日の日報を生成

```bash
dev-log-daily --config config.yml
```

### 特定日の日報を生成

```bash
dev-log-daily --config config.yml --date 2026-06-22
```

---

## 検証シナリオ

### シナリオ 1: 複数ワークスペースのチャットログ一括収集（P1）

**目的**: 3 つ以上のワークスペースが存在する環境で、全ワークスペースのチャットログが収集されることを確認する。

**準備**:
```bash
# テスト用の workspaceStorage ディレクトリ構造を作成
mkdir -p /tmp/test-ws-storage/{uuid-a,uuid-b,uuid-c}/GitHub.copilot-chat/transcripts/

# 各ワークスペースにダミーの JSONL ファイルを配置
# （実際のテストでは tests/fixtures/ のサンプルデータを使用可）
```

**設定ファイル**:
```yaml
data_sources:
  copilot_chat:
    workspace_storage_dirs:
      - /tmp/test-ws-storage
```

**実行**:
```bash
dev-log-daily --config test-config.yml --date 2026-06-22
```

**期待結果**:
- 3 つのワークスペースすべてのチャットログが収集される
- 標準出力に各ワークスペースの収集結果が表示される（例: `+ frontend: 5 sessions found`）
- 日報内にワークスペース別のセクションが出力される

### シナリオ 2: 空の workspaceStorage（P1）

**目的**: workspaceStorage 配下に有効なワークスペースがない場合の動作を確認する。

**準備**:
```bash
mkdir -p /tmp/empty-ws-storage
```

**実行**:
```bash
dev-log-daily --config empty-config.yml --date 2026-06-22
```

**期待結果**:
- `チャットログが見つかりませんでした: 有効なワークスペースがありません` と表示される
- exit code 0（他データソースの処理は継続）
- 日報の Copilot チャットセクションは空

### シナリオ 3: 一部ワークスペースに transcripts がない（P1）

**準備**:
```bash
# uuid-a のみ transcripts あり、uuid-b は transcripts なし
mkdir -p /tmp/partial-ws-storage/{uuid-a,uuid-b}
mkdir -p /tmp/partial-ws-storage/uuid-a/GitHub.copilot-chat/transcripts/
```

**期待結果**:
- uuid-a は正常収集される
- uuid-b は `− uuid-b: transcripts なしでスキップ` と表示される
- 他のワークスペースの収集に影響なし

### シナリオ 4: クロスプラットフォーム統合（P2）

**目的**: WSL と Windows 両方のベースディレクトリを指定し、同一 UUID のワークスペースが統合されることを確認する。

**設定**:
```yaml
data_sources:
  copilot_chat:
    workspace_storage_dirs:
      - /tmp/wsl-ws-storage
      - /tmp/windows-ws-storage
```

**準備**:
```bash
# WSL側: uuid-a に transcripts あり
mkdir -p /tmp/wsl-ws-storage/uuid-a/GitHub.copilot-chat/transcripts/
echo '{"type":"session.start","data":{"sessionId":"sess-1","startTime":"2026-06-22T09:00:00Z"}}' > /tmp/wsl-ws-storage/uuid-a/GitHub.copilot-chat/transcripts/chat.jsonl

# Windows側: 同一 uuid-a に chatSessions あり（別セッション）
mkdir -p /tmp/windows-ws-storage/uuid-a/chatSessions/
echo '{"type":"session.start","data":{"sessionId":"sess-2","startTime":"2026-06-22T10:00:00Z"}}' > /tmp/windows-ws-storage/uuid-a/chatSessions/chat.jsonl
```

**期待結果**:
- uuid-a は 1 つのワークスペースとして統合される
- 2 つのセッション（sess-1, sess-2）が含まれる
- `platforms` は `["linux", "windows"]`

### シナリオ 5: 上限超過の警告（P3）

**準備**: 6 つのワークスペースがある環境で `max_workspaces: 3` を設定。

**期待結果**:
- 3 つのワークスペースのみ処理される
- `⚠ 上限(3)超過: 3/6 ワークスペースをスキップ` と警告表示される
- スキップされた UUID 一覧が表示される

### シナリオ 6: 旧形式設定の検出

**設定**:
```yaml
data_sources:
  copilot_chat_dir: /old/path  # 旧形式
```

**期待結果**:
- `ERROR: data_sources.copilot_chat_dir は廃止されました...` と表示される
- exit code 1 で終了
- 移行手順が案内される

---

## テスト実行

```bash
cd /home/takumi/github/DevLogDaily
source .venv/bin/activate

# 全テスト実行
uv run pytest
```

### 各検証シナリオに対応するテスト

各シナリオには対応する自動テストが存在する。テストファースト（TDD）で開発され、実装前に失敗することを確認済み。

#### シナリオ 1: 複数ワークスペースのチャットログ一括収集

```bash
# 単体テスト: CopilotChatConfig のバリデーション
uv run pytest tests/unit/test_config.py::TestCopilotChatConfig -v

# 単体テスト: CollectedLog workspaces フィールド
uv run pytest tests/unit/test_base.py::TestCollectedLog -v

# 結合テスト: 単一ベースディレクトリからの収集（3 ワークスペース）
uv run pytest tests/integration/test_copilot_chat.py::TestMultiWorkspaceCollection::test_collect_from_single_base_dir -v
```

**期待出力**:
```text
tests/integration/test_copilot_chat.py::TestMultiWorkspaceCollection::test_collect_from_single_base_dir ✓  (3 workspaces collected, 3 sessions found)
```

#### シナリオ 2: 空の workspaceStorage

```bash
uv run pytest tests/integration/test_copilot_chat.py::TestMultiWorkspaceCollection::test_collect_empty_workspace_storage -v
```

**期待出力**:
```text
tests/integration/test_copilot_chat.py::TestMultiWorkspaceCollection::test_collect_empty_workspace_storage ✓  (0 sessions, error message returned)
```

#### シナリオ 3: transcripts なしのワークスペースをスキップ

```bash
uv run pytest tests/integration/test_copilot_chat.py::TestMultiWorkspaceCollection::test_workspace_without_transcripts_is_skipped -v
```

**期待出力**:
```text
tests/integration/test_copilot_chat.py::TestMultiWorkspaceCollection::test_workspace_without_transcripts_is_skipped ✓  (empty-workspace skipped, others collected)
```

#### シナリオ 4: クロスプラットフォーム統合

```bash
# 結合テスト: 二重ディレクトリ収集
uv run pytest tests/integration/test_copilot_chat.py::TestCrossPlatform::test_dual_directory_collection -v

# 結合テスト: UUID ベースのマージ
uv run pytest tests/integration/test_copilot_chat.py::TestCrossPlatform::test_uuid_based_workspace_merging -v

# 結合テスト: セッション重複排除
uv run pytest tests/integration/test_copilot_chat.py::TestCrossPlatform::test_session_deduplication_across_platforms -v
```

**期待出力**:
```text
tests/integration/test_copilot_chat.py::TestCrossPlatform::test_dual_directory_collection ✓  (workspaces from both dirs collected)
tests/integration/test_copilot_chat.py::TestCrossPlatform::test_uuid_based_workspace_merging ✓  (same UUID merged into single entry)
tests/integration/test_copilot_chat.py::TestCrossPlatform::test_session_deduplication_across_platforms ✓  (duplicate sessionId removed)
```

#### シナリオ 5: 上限超過の警告

```bash
uv run pytest tests/integration/test_copilot_chat.py::TestMultiWorkspaceCollection::test_max_workspaces_limit_enforced -v
```

**期待出力**:
```text
tests/integration/test_copilot_chat.py::TestMultiWorkspaceCollection::test_max_workspaces_limit_enforced ✓  (limit=3, 5 found, 3 processed, 2 skipped)
```

#### シナリオ 6: 旧形式設定の検出

```bash
uv run pytest tests/unit/test_config.py::TestCopilotChatConfig::test_legacy_copilot_chat_dir_detected -v
```

**期待出力**:
```text
tests/unit/test_config.py::TestCopilotChatConfig::test_legacy_copilot_chat_dir_detected ✓  (migration error raised)
```

### ワークスペース識別のテスト（US2）

```bash
# workspace.json 読み取り
uv run pytest tests/unit/test_copilot_chat.py::TestReadWorkspaceJson -v

# ワークスペース名抽出（folder / workspace file / UUID fallback）
uv run pytest tests/unit/test_copilot_chat.py::TestExtractWorkspaceName -v

# 結合テスト: ワークスペースメタデータ
uv run pytest tests/integration/test_copilot_chat.py::TestWorkspaceGrouping::test_workspace_metadata_in_collected_output -v

# 結合テスト: ワークスペース別グループ化
uv run pytest tests/integration/test_copilot_chat.py::TestWorkspaceGrouping::test_sessions_grouped_by_workspace -v
```

### 重複排除のテスト

```bash
uv run pytest tests/unit/test_copilot_chat.py::TestDeduplicateSessions -v
```

詳細なデータ構造の契約は [contracts/collection-output.md](./contracts/collection-output.md) を参照。
