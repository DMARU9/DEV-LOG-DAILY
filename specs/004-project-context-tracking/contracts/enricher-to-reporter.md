# 内部データ契約: Enricher → Reporter （ProjectActivity）

**Feature**: 004-project-context-tracking | **Date**: 2026-07-21

## 概要

Enricher は全 Parser の `project_hints` を統合・正規化し、`dict[str, ProjectActivity]` 形式のプロジェクト活動辞書を生成する。Reporter はこれを主要入力としてプロジェクト単位の日報を生成する。

## 契約

```python
@dataclass
class ProjectActivity:
    """Enricher が生成する正規化済みプロジェクト情報."""
    project_name: str                        # 正規化されたプロジェクト名（LLM により統一）
    source_activities: dict[str, list[str]]  # ソース種別 → 活動要約リスト
    time_range: dict                         # {"start": "ISO8601", "end": "ISO8601"} または空
    related_sources: list[str]               # 活動確認済みソース種別リスト
```

### source_activities のキー

| キー | 値の型 | 内容 |
|------|--------|------|
| `"copilot_chat"` | `list[str]` | このプロジェクトに関する Copilot チャットの活動要約 |
| `"git_commits"` | `list[str]` | このプロジェクトに関する Git コミットの活動要約 |
| `"terminal_logs"` | `list[str]` | このプロジェクトで実行されたターミナル操作の要約 |

## DailyState への格納形式

```python
class DailyState(TypedDict):
    # ... 既存フィールド（変更なし） ...
    project_hints: list[dict]        # Parser 出力の生ヒント
    project_activities: dict[str, dict]  # Enricher 出力の正規化辞書
```

## Reporter での利用

Reporter は `state["project_activities"]` を主要入力とし、従来の各ソース別 parsed データ（`copilot_chat_parsed` 等）は補助情報として併用する。

```python
# Reporter ノード内での使用イメージ
project_activities = state.get("project_activities", {})
# project_activities = {"DevLogDaily": {project_name, source_activities, ...}, ...}
```

## エラー処理

- `project_activities` が空辞書の場合 → Reporter は「プロジェクト情報なし」として日報を生成
- プロジェクト名が 100 文字を超える場合 → Enricher が truncate する（プロンプトで指示）
- プロジェクト数が 20 を超える場合 → Enricher が主要プロジェクトのみ詳細を残す
