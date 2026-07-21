# Contract: 収集出力形式（CollectedLog / ParsedData）

**Version**: 2.0.0 | **Date**: 2026-06-22 | **Feature**: `002-multi-workspace-chat`

**Change from v1**: `CollectedLog` に `workspaces` フィールドを追加。`ParsedData.structured_data` に `workspaces` キーを追加。

## CollectedLog（collect() 出力）

```python
{
    "source": "copilot_chat",
    "target_date": "2026-06-22",
    "files": [                     # 補助情報: 全収集ファイルのリスト
        {
            "path": "/path/to/file.jsonl",
            "source": "copilot_chat",
            "timestamp": "2026-06-22T10:00:00",
            "sessions": [...],     # このファイルのセッション（Collector内部で圧縮済み）
            "session_count": 3,
            "compression": {
                "original_bytes": 12345,
                "compressed_bytes": 2345,
                "ratio_pct": 19,
                "saved_pct": 81,
            }
        }
    ],
    "workspaces": [                # 新設: ワークスペース別グループ化（主要データ）
        {
            "workspace_id": "abcdef01-1234-5678-9abc-def012345678",
            "workspace_name": "frontend",
            "sessions": [
                {
                    "session_id": "session-uuid-1",
                    "start_time": "2026-06-22T09:00:00Z",
                    "messages": [
                        {"role": "user", "content": "質問..."},
                        {"role": "assistant", "content": "回答..."}
                    ],
                    "turn_count": 3,
                }
            ],
            "session_count": 5,
            "metadata": {
                "workspace_json": {                     # workspace.json の内容
                    "workspace": {
                        "folder": "/home/user/projects/frontend"
                    }
                },
                "storage_dirs_used": [                  # このWSが存在したベースディレクトリ
                    "/home/user/.vscode-server/data/User/workspaceStorage"
                ],
                "platforms": ["linux"],                  # チャットログが取得されたプラットフォーム
            }
        }
    ],
    "error": None,
    "collected_at": "2026-06-22T10:00:00",
}
```

### workspaces[] 要素の契約

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `workspace_id` | `string` | ✅ | UUIDv4（ディレクトリ名）。ワークスペースの一次識別子。 |
| `workspace_name` | `string` | ✅ | 人間可読な表示名。workspace.json から抽出、なければ "Unknown Workspace (<UUID>)"。 |
| `sessions` | `array[object]` | ✅ | 収集されたチャットセッションのリスト（重複排除済み）。空配列可。 |
| `session_count` | `int` | ✅ | セッション数。 |
| `metadata.workspace_json` | `object` or `null` | ❌ | workspace.json のパース済み内容。読めなかった場合は null。 |
| `metadata.storage_dirs_used` | `array[string]` | ✅ | このワークスペースが検出されたベースディレクトリパス。 |
| `metadata.platforms` | `array[string]` | ✅ | チャットログが収集されたプラットフォーム（"linux" または "windows"）。 |

### 空の収集結果

有効なワークスペースが 1 つも見つからなかった場合：

```python
{
    "source": "copilot_chat",
    "target_date": "2026-06-22",
    "files": [],
    "workspaces": [],        # 空のリスト
    "error": "チャットログが見つかりませんでした: 有効なワークスペースがありません",
    "collected_at": "2026-06-22T10:00:00",
}
```

## ParsedData（parse() 出力）

```python
{
    "source": "copilot_chat",
    "summary": "全体の開発活動の概要...",
    "structured_data": {
        "workspaces": {                       # 新設: ワークスペース別解析結果
            "uuid-1": {
                "name": "frontend",
                "sessions": [                  # 各セッションのLLM解析結果
                    {
                        "session_id": "...",
                        "topics": ["React", "TypeScript"],
                        "key_points": ["要点1", "要点2"],
                        "problems_faced": ["問題点"],
                    }
                ],
                "summary": "frontend プロジェクトでの開発活動..."
            },
            "uuid-2": {
                "name": "backend",
                "sessions": [...],
                "summary": "backend プロジェクトでのAPI実装..."
            }
        },
        "overall_summary": "全ワークスペースを統合した一日の開発活動の概要..."
    },
    "token_count": 1500,
    "chunks_processed": 2,
    "error": None,
}
```

## DailyState 格納時の形式

`DailyState` の `copilot_chat_raw` / `copilot_chat_parsed` には上記の `to_dict()` 出力をそのまま格納する。

```python
state["copilot_chat_raw"] = {
    "source": "copilot_chat",
    "target_date": "...",
    "files": [...],
    "workspaces": [...],       # 新設
    "error": None,
    "collected_at": "...",
}
```

## 旧形式からの移行注意点

- `copilot_chat_raw["files"]` は後方互換性のために維持されるが、日報生成では `copilot_chat_raw["workspaces"]` を優先して使用する
- `copilot_chat_parsed["structured_data"]["workspaces"]` が存在する場合はそれを優先、存在しない場合は従来のフラットな解析結果をフォールバックとして使用する
