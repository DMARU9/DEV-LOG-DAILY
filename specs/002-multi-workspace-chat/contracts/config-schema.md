# Contract: 設定ファイルスキーマ（複数ワークスペース対応）

**Version**: 2.0.0 | **Date**: 2026-06-22 | **Feature**: `002-multi-workspace-chat`

**Change from v1**: `data_sources.copilot_chat_dir` を廃止し、`data_sources.copilot_chat.workspace_storage_dirs` に置き換え。

## YAML 設定ファイル形式

```yaml
llm:
  collector:
    model: "<モデル名>"
    base_url: "<APIベースURL>"
    api_key: "<APIキー>"
    max_input_tokens: 131072
    max_output_tokens: 16384
  parser:
    # ... (同上)
  enricher:
    # ... (同上)
  reporter:
    # ... (同上)

data_sources:
  copilot_chat:
    workspace_storage_dirs:
      - "<絶対パス1>"
      - "<絶対パス2>"
    max_workspaces: 50        # オプション、デフォルト 50
  git_root_dir: "<絶対パス>"
  terminal_history_dir: "<絶対パス>"

output:
  directory: "<絶対パス>"

timeout_seconds: 120
```

## data_sources.copilot_chat セクション

| フィールド | 型 | 必須 | デフォルト | 制約 | 説明 |
|-----------|-----|------|-----------|------|------|
| `workspace_storage_dirs` | `array[str]` | ✅ | — | 最小 1 要素、各要素は空文字不可 | VS Code の workspaceStorage ディレクトリへの絶対パス。複数指定可。 |
| `max_workspaces` | `int` | ❌ | `50` | 1〜1000 | 収集する最大ワークスペース数。超過分は警告表示してスキップ。 |

## 廃止されたフィールド

### ❌ data_sources.copilot_chat_dir（v1 で使用）

本バージョンでは完全に廃止。設定ファイルにこのフィールドが存在する場合、以下のメッセージを表示して終了する：

```
ERROR: data_sources.copilot_chat_dir は廃止されました。
代わりに data_sources.copilot_chat.workspace_storage_dirs を使用してください。

【移行手順】
1. 設定ファイルの copilot_chat_dir フィールドを削除
2. 代わりに以下を追加:
   data_sources:
     copilot_chat:
       workspace_storage_dirs:
         - /home/user/.vscode-server/data/User/workspaceStorage
```

## 検証ルール

1. `workspace_storage_dirs` は最低 1 つのパスを指定必須
2. 各パスの実在確認は実行時（collect 時）に行い、存在しないパスは警告表示してスキップ
3. `max_workspaces` が指定されない場合のデフォルト値は 50
4. `max_workspaces` に 1 未満または 1000 超過の値が指定された場合は pydantic 検証エラー
5. 旧形式 `data_sources.copilot_chat_dir` が検出された場合は設定ローダーが検出し、移行案内を表示して終了コード 1 で終了
6. 新旧両方の形式が同時に指定された場合も、旧形式検出としてエラー終了（移行を促す）
