# Data Model: 複数ワークスペースストレージからのチャットログ収集対応

**Date**: 2026-06-22 | **Feature**: `002-multi-workspace-chat`

## 1. 設定スキーマ拡張

### 1.1 CopilotChatConfig（新設）

`data_sources.copilot_chat` セクションの設定モデル。旧 `copilot_chat_dir` を置き換える。

```python
class CopilotChatConfig(BaseModel):
    """CopilotChat データソース設定 — 複数workspaceStorage対応."""
    workspace_storage_dirs: list[str] = Field(
        ...,
        description="workspaceStorage ベースディレクトリのリスト（絶対パス）",
        min_length=1,
    )
    max_workspaces: int = Field(
        default=50,
        description="処理するワークスペース数の上限",
        ge=1,
        le=1000,
    )
```

**フィールド一覧**:

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| `workspace_storage_dirs` | `list[str]` | ✅ | — | VS Code workspaceStorage への絶対パス。複数指定可能（WSL/Windows 等） |
| `max_workspaces` | `int` | ❌ | `50` | 収集対象とする最大ワークスペース数。超過時は警告表示 |

**検証ルール**:
- `workspace_storage_dirs` は最低 1 つのパスが必要（`min_length=1`）
- 各パスは絶対パスであることを推奨（相対パスは設定ファイルからの相対パスとして解決）
- `max_workspaces` は 1〜1000 の範囲

### 1.2 DataSourceConfig（変更）

```python
class DataSourceConfig(BaseModel):
    """データソースパス設定."""
    # 削除: copilot_chat_dir: str  ← 完全廃止
    # 追加:
    copilot_chat: CopilotChatConfig = Field(
        ...,
        description="CopilotChat データソース設定（複数ワークスペース対応）",
    )
    git_root_dir: str = Field(
        ...,
        description="Gitリポジトリ親ディレクトリ（配下を再帰探索）",
    )
    terminal_history_dir: str = Field(
        ...,
        description="ターミナル履歴ディレクトリ（history_YYYY-MM-DD.jsonl ファイル格納先）",
    )
```

### 1.3 設定例（YAML）

```yaml
data_sources:
  copilot_chat:
    workspace_storage_dirs:
      - /home/takumi/.vscode-server/data/User/workspaceStorage
      - /mnt/c/Users/takumi/AppData/Roaming/Code/User/workspaceStorage
    max_workspaces: 50
  git_root_dir: /home/takumi/github
  terminal_history_dir: /home/takumi/.dev-log-daily/terminal
```

## 2. ワークスペースデータ構造

### 2.1 WorkspaceInfo（収集段階の内部構造）

```python
@dataclass
class WorkspaceInfo:
    """単一ワークスペースの収集情報."""
    workspace_id: str                    # UUID（ディレクトリ名）
    workspace_name: str                  # 表示名（workspace.json から抽出、なければ UUID）
    storage_paths: list[str]             # このWSが存在したベースディレクトリパス
    workspace_metadata: dict             # workspace.json の内容（パース済み）
    sessions: list[dict]                 # 収集したセッションリスト（重複排除済み）
    session_count: int                   # セッション数
    source_platforms: list[str]          # ソースプラットフォーム（"linux", "windows"）
    error: str | None = None             # 収集エラー（任意）
```

**workspace_name 抽出ルール**（優先順位）:
1. `workspace.json` の `workspace.folder` フィールド → パスの basename
2. `workspace.json` の `workspace.workspace` フィールド → ファイル名（拡張子除く）
3. 両方ない場合 → `"Unknown Workspace (<UUID>)"`

### 2.2 WorkspaceDiscoveryResult（探索結果）

```python
@dataclass
class WorkspaceDiscoveryResult:
    """ワークスペース探索結果."""
    workspaces: dict[str, WorkspaceInfo]  # key: UUID
    skipped_uuids: list[str]              # 上限超過でスキップされた UUID
    inaccessible_paths: list[str]         # アクセス不能だったディレクトリパス
    total_workspaces_found: int           # 発見された総ワークスペース数
    total_sessions_collected: int         # 収集された総セッション数
```

## 3. 収集データ構造の拡張

### 3.1 CollectedLog（変更）

`workspaces` フィールドを追加し、既存の `files` は補助情報として維持。

```python
class CollectedLog:
    """収集ログ — collect() の戻り値."""
    def __init__(
        self,
        source: str,
        target_date: str,
        files: list[dict] | None = None,      # 既存: 補助情報として維持
        workspaces: list[dict] | None = None,  # 新設: ワークスペース別グループ化
        error: str | None = None,
        collected_at: str | None = None,
    ):
        ...
```

**workspaces[].dict 形式**:

```python
{
    "workspace_id": "abcdef01-1234-5678-9abc-def012345678",  # UUID
    "workspace_name": "frontend",                              # 表示名
    "sessions": [                                              # セッションリスト（既存の sessions 形式と同じ）
        {
            "session_id": "...",
            "start_time": "...",
            "messages": [...],
            "turn_count": 3,
        }
    ],
    "session_count": 5,
    "metadata": {
        "workspace_json": {"workspace": {"folder": "/home/.../frontend"}},
        "storage_dirs_used": ["/home/.../workspaceStorage"],
        "platforms": ["linux"],
    }
}
```

### 3.2 収集結果全体の形式（collect() 戻り値の to_dict()）

```python
{
    "source": "copilot_chat",
    "target_date": "2026-06-22",
    "files": [...],                              # 補助情報（全ファイル）
    "workspaces": [                               # 新設: ワークスペース別グループ化（主要）
        {
            "workspace_id": "uuid-1",
            "workspace_name": "frontend",
            "sessions": [...],
            "session_count": 3,
            "metadata": {...},
        },
        {
            "workspace_id": "uuid-2",
            "workspace_name": "backend",
            "sessions": [...],
            "session_count": 2,
            "metadata": {...},
        },
    ],
    "error": None,
    "collected_at": "2026-06-22T10:00:00",
}
```

## 4. 解析データ構造の拡張

### 4.1 ParsedData の structured_data（変更）

`structured_data` 内にワークスペース別の解析結果を保持。

```python
{
    "workspaces": {
        "uuid-1": {
            "name": "frontend",
            "sessions": [...],       # LLM 解析済みセッション
            "summary": "frontend プロジェクトでの開発活動の概要...",
        },
        "uuid-2": {
            "name": "backend",
            "sessions": [...],
            "summary": "backend プロジェクトでのAPI実装...",
        },
    },
    "overall_summary": "全体の開発活動の概要...",  # 全ワークスペース統合サマリ
}
```

## 5. 状態遷移

### 5.1 ワークスペース収集フロー

```
START
  │
  ▼
1. Load CopilotChatConfig  ← 設定読み込み（旧形式チェック含む）
  │
  ▼
2. Enumerate base dirs     ← workspace_storage_dirs を順次処理
  │
  ▼
3. Per base dir:
   ├─ 3a. List subdirectories (UUID candidates)
   ├─ 3b. Check dir name is valid UUID
   ├─ 3c. Check transcripts/ or chatSessions/ exists
   └─ 3d. Read workspace.json if exists
  │
  ▼
4. Merge across base dirs  ← 同一UUIDを統合、sessionId重複排除
  │
  ▼
5. Apply max_workspaces    ← 上限超過チェック
  │
  ▼
6. Build CollectedLog      ← workspaces + files を設定
  │
  ▼
END
```

### 5.2 上限超過フロー

```
Total found > max_workspaces?
  │
  ├── Yes:
  │    ├─ Sort UUIDs lexicographically
  │    ├─ Take first max_workspaces
  │    ├─ Log warning: "上限(50)を超えました。5/55 ワークスペースをスキップ"
  │    └─ List skipped UUIDs
  │
  └── No: process all workspaces
```

## 6. エラー処理

| エラー種別 | 動作 | 表示 |
|-----------|------|------|
| ベースディレクトリが存在しない | 警告表示しスキップ、他は継続 | `⚠ /path/not/exist: ディレクトリが存在しません` |
| workspace.json が読めない | デバッグログ記録、UUID フォールバック | 通常表示なし |
| transcripts/chatSessions がない | 情報表示しスキップ | `− UUID-xxx: transcripts なしでスキップ` |
| 上限超過 | 超過数と UUID 一覧を警告 | `⚠ 上限(50)超過: 5/55 ワークスペースをスキップ` |
| 旧形式 copilot_chat_dir 検出 | 移行案内エラー表示して終了 | `ERROR: copilot_chat_dir は廃止されました...` |
