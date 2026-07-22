# Contract: Enricher → Reporter（enriched_data 拡張）

**From**: Enricher ノード
**To**: Reporter ノード
**Version**: 2.0.0（report_metadata 拡張）

## 概要

本 contract は 004-project-context-tracking で定義された Enricher→Reporter 間の
enriched_data JSON 構造を拡張し、新フォーマットに必要なメタデータを追加する。
既存フィールド（cross_references, contradictions, completions, context,
key_activities, projects）の構造は変更しない。

## 拡張: report_metadata

`enriched_data` のルートに `report_metadata` キーを追加する。

### JSON スキーマ

```json
{
  "report_metadata": {
    "mood": "productive",
    "energy": 4,
    "tags": ["DevLogDaily", "Python", "LangGraph"],
    "project_moods": {
      "ProjectA": {
        "mood": "frustrated",
        "energy": 3
      },
      "ProjectB": {
        "mood": "productive",
        "energy": 5
      }
    }
  }
}
```

### フィールド定義

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| `mood` | str | MUST | "productive" | 全プロジェクト横断の全体的な mood 推定値。Reporter がフロントマターに使用 |
| `energy` | int (1-5) | MUST | 4 | 全プロジェクト横断の energy 推定値。Reporter がフロントマターに使用 |
| `tags` | list[str] | MUST | ["DevLogDaily"] | フロントマター用タグ候補。デフォルトタグ＋活動内容から抽出。最大10個 |
| `project_moods` | dict[str, object] | SHOULD | {} | プロジェクト単位の mood/energy。キーはプロジェクト名。Reporter が各プロジェクトセクションの文脈として使用 |

### project_moods の値オブジェクト

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| `mood` | str | MUST | "productive" | 当該プロジェクトの mood 推定値 |
| `energy` | int (1-5) | MUST | 4 | 当該プロジェクトの energy 推定値 |

### 完全な enriched_data JSON 構造

```json
{
  "cross_references": [
    {"topic": "トピック名", "sources": ["copilot_chat"], "details": "詳細"}
  ],
  "contradictions": [
    {"topic": "トピック名", "details": "矛盾内容", "resolution": "推定解消方法"}
  ],
  "completions": [
    {"topic": "トピック名", "details": "補完情報", "based_on": "元データ"}
  ],
  "context": "一日の開発活動の全体的な文脈と流れ",
  "key_activities": [
    {"activity": "活動内容", "impact": "影響", "related_sources": ["copilot_chat"]}
  ],
  "projects": {
    "ProjectA": {
      "project_name": "ProjectA",
      "source_activities": {"copilot_chat": ["要約1"]},
      "time_range": {"start": "2026-07-21T09:00:00+09:00", "end": "2026-07-21T12:00:00+09:00"},
      "related_sources": ["copilot_chat", "git_commits"]
    }
  },
  "report_metadata": {
    "mood": "productive",
    "energy": 4,
    "tags": ["DevLogDaily", "Python", "LangGraph"],
    "project_moods": {
      "ProjectA": {"mood": "frustrated", "energy": 3}
    }
  }
}
```

## 変更履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|---------|
| 2.0.0 | 2026-07-22 | report_metadata 拡張を追加（mood, energy, tags, project_moods） |
| 1.0.0 | 2026-07-21 | 初版（004-project-context-tracking で定義） |
