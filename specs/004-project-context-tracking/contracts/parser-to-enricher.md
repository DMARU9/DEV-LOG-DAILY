# 内部データ契約: Parser → Enricher （ProjectHint）

**Feature**: 004-project-context-tracking | **Date**: 2026-07-21

## 概要

各 Parser は収集データの解析結果に `project_hints` フィールドを含め、Enricher がプロジェクト単位の統合を行えるようにする。

## 契約

```python
@dataclass
class ProjectHint:
    """Parser から Enricher に渡されるプロジェクト名の生ヒント."""
    source: str                        # データソース種別: "copilot_chat" | "git_commits" | "terminal_logs"
    candidate_name: str                # プロジェクト名候補（空文字列不可）
    activity_summary: str              # 当該プロジェクトでの活動要約
```

## ParsedData への追加フィールド

```python
@dataclass
class ParsedData:
    # ... 既存フィールド（変更なし） ...
    project_hints: list[dict] = field(default_factory=list)
    # 各要素: {"source": str, "candidate_name": str, "activity_summary": str}

    def to_dict(self) -> dict:
        # 既存のキー + "project_hints" を含める
        ...
```

## 各 Parser の抽出ルール

| Parser | candidate_name の抽出元 | 備考 |
|--------|------------------------|------|
| CopilotChat | `workspace[].workspace_name` | workspace.json から抽出された名前 |
| GitCommits | `files[].path` の basename | リポジトリパスの末尾ディレクトリ名 |
| TerminalLogs | `entries[].cwd` の basename | cwd パスの末尾ディレクトリ名。空の場合は `"プロジェクト不明"` |

## activity_summary の生成

各 Parser の LLM 解析結果（summary）から、プロジェクトに関連する活動内容を抽出する。
Copilot チャットの場合はワークスペース単位、Git の場合はリポジトリ単位、ターミナルの場合は cwd 単位で要約する。

## エラー処理

- `candidate_name` が空文字列の hint は Enricher が無視する
- 全 Parser の hints が空の場合、Enricher は `project_activities` を空辞書とする
- 活動要約が空の hint は統合時にそのまま空として扱う（削除しない）
