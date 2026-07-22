# Research: 日報出力フォーマットの大幅リファクタリング

**Phase**: 0 — Technical Context の不確定要素解決と設計判断の文書化

**Date**: 2026-07-22

## Overview

本 feature は日報の Markdown 出力フォーマットを従来のフラットなカテゴリ別構成から
プロジェクト単位の入れ子構造に変更するリファクタリングである。
技術的に未知の領域はなく、既存のパイプライン構造を維持したまま
Reporter / Enricher / Parser の責務を拡張する。

## Decisions

### Decision 1: 新フォーマット構造

- **Decision**: ユーザー提示のフォーマットをほぼそのまま採用する
- **Rationale**: ユーザーが具体的かつ詳細なフォーマットを提示しており、これをベースに
  FR-001 として仕様化済み。変更の余地は小さい
- **Alternatives considered**: カテゴリ別構成の維持（ユーザー要求に反するため却下）

### Decision 2: 活動時間の表現（Clarification Q1）

- **Decision**: 継続時間（duration）を HH:MM 形式で表示する
- **Rationale**: ユーザーによりオプションBが選択された
- **Alternatives considered**: 開始〜終了時刻（A）, 両方（C）

### Decision 3: 「その他」セクションの構造（Clarification Q2）

- **Decision**: 概要・技術・学習（簡易）・開発活動・問題・タグを含む。振り返りとアクションは除外
- **Rationale**: ユーザーによりオプションCが選択された。プロジェクトに紐づかない活動には
  振り返りや翌日アクションは不要
- **Alternatives considered**: プロジェクトと同一構造（A）, 概要・技術・開発・問題・タグのみ（B）,
  概要・開発のみ（D）

### Decision 4: enriched_data への mood/energy/tags 追加（Clarification Q3）

- **Decision**: `report_metadata` サブオブジェクトとして集約（オプションB）
- **Rationale**: ユーザーによりオプションBが選択された。ルートレベルの整理と将来の拡張性を両立
- **JSON 構造**:
  ```json
  {
    "report_metadata": {
      "mood": "productive",
      "energy": 4,
      "tags": ["DevLogDaily", "Python"],
      "project_moods": {
        "ProjectA": {"mood": "productive", "energy": 4}
      }
    }
  }
  ```

### Decision 5: 活動種別の分類方法

- **Decision**: LLM による推論で種別（feat/fix/docs/chore）を付与する。Parser でのハードコード判定は行わない
- **Rationale**: 仕様 Assumptions に記載の通り。LLM の柔軟性を活かし、メンテナンスコストを削減
- **Alternatives considered**: Parser で正規表現ベースの種別判定（既存パーサーへの影響大）

### Decision 6: プロジェクト別振り返り・アクションの生成

- **Decision**: LLM が Enricher 出力（enriched_data）と各データソース解析結果から推論して生成する
- **Rationale**: 新しいデータ構造の追加なしで実現可能。コンテキスト不足時は
  「データ不足のため推論できませんでした」を許容
- **Alternatives considered**: Enricher に振り返り生成専用の出力フィールド追加（過剰設計）

## Key Dependencies

| Dependency | Status | Notes |
|-----------|--------|-------|
| 004-project-context-tracking | ✅ 完了前提 | project_hints / project_activities の生成機能 |
| REPORTER_SYSTEM_PROMPT | 🔄 変更対象 | 全面的書き換え |
| `_generate_empty_report()` | 🔄 変更対象 | 新フォーマット対応 |
| Enricher ENRICHER_SYSTEM_PROMPT | 🔄 変更対象 | report_metadata 出力追加 |
| Parser 各 parse メソッド | 🔄 小幅変更 | ファイルパス・種別抽出の精度向上 |

## Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| LLM が新フォーマット通りに出力しない | High | REPORTER_SYSTEM_PROMPT の詳細な指示 + テストで検証 |
| 既存テストの期待値不一致 | Medium | フォーマット変更に伴うテスト更新を FR-008 で義務化 |
| Enricher の report_metadata が不完全 | Low | デフォルト値フォールバック（mood: productive, energy: 4） |
