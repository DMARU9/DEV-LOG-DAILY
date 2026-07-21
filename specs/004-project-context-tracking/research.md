# Research: 日報におけるプロジェクトコンテキストの明確化

**Date**: 2026-07-21 | **Feature**: 004-project-context-tracking | **Plan**: [plan.md](./plan.md)

## 1. ターミナル履歴の cwd/git_branch を LLM に渡すフォーマット

### Decision
ターミナル操作の `parse()` で、各コマンドエントリに `cwd` と `git_branch` を含めたテキストを LLM に渡す。フォーマットは以下の構造とする:

```
[cwd] (branch) $ command
```

### Rationale
- 既存の `CollectorLog.files[].entries[].cwd` と `.git_branch` は collect() で収集済みだが、parse() でテキスト化する際に捨てられている。これを活用する最小変更
- cwd は絶対パスのため、LLM がパスの末尾 2〜3 階層からプロジェクト名を推論できる
- フォーマットを `[cwd]` で明示することで、LLM が「これは実行ディレクトリ情報である」と認識しやすい

### Alternatives considered
- cwd を別フィールドとして構造化データで渡す（プロンプトとは別に system メッセージに入れる） → 変更範囲が大きく、効果に大差なし
- cwd から自動的にプロジェクト名を抽出（Python でパス解析） → プロジェクト名の判定は LLM に委ねる方針に反する。誤判定のリスクが高く、汎用性に欠ける

---

## 2. ParsedData への project_hints フィールド追加方法

### Decision
`ParsedData` クラス（`tools/base.py`）に `project_hints` 属性（`list[dict]`）を追加する。各要素は `{"source": str, "candidate_name": str, "activity_summary": str}` の形式。

### Rationale
- `to_dict()` で DailyState に格納されるため、StateGraph 間で自然に受け渡し可能
- 既存のフィールド（summary, structured_data 等）は互換性を維持
- 各 Parser は自身の parse() の最後で hints を付与するだけでよく、責務が明確

### Alternatives considered
- structured_data 内に含める → 型の一貫性が損なわれる。structured_data はソース固有データ用であり、横断的な project_hints は別フィールドが適切
- 新規のデータクラスを作成せず、text 内にヒントを埋め込む → LLM の抽出精度が不安定。構造化データとして明示する方が信頼性が高い

---

## 3. Enricher での project_hints 統合アプローチ

### Decision
Enricher は既存のクロスリファレンス処理の延長として、各 Parser からの `project_hints` を LLM に渡し、表記ゆれを解決した上で `dict[str, ProjectActivity]` を生成させる。Enricher のシステムプロンプトに以下の指示を追記する:

- 各 Parser から渡された project_hints を分析し、同一プロジェクトを指す候補を統合する
- ワークスペース名（Copilot）・リポジトリパス名（Git）・cwd ディレクトリ名（Terminal）の表記ゆれを解決する
- 統合結果をプロジェクト名をキーとした JSON オブジェクトとして出力する

### Rationale
- 既存の Enricher は LLM による JSON 出力を前提としている（`ENRICHER_SYSTEM_PROMPT` + `ENRICHER_PROMPT_TEMPLATE`）。その拡張として実装可能
- プロジェクトの統合判断は LLM に委ねる方針（FR-009）と合致
- Enricher の責務である「クロスリファレンス」の自然な拡張

### Alternatives considered
- ルールベースの統合（文字列正規化 + レーベンシュタイン距離等） → 設定不要の設計には合致するが、LLM 推論に委ねる方針と矛盾。また、ルールのメンテナンスコストが高い
- Collector 段階で統合 → 各ツールは独立しているべき（憲法第I条）。Collector は収集に専念し、統合は Enricher で行う

---

## 4. 日報フォーマットのプロジェクト単位構成

### Decision
日報の Markdown フォーマットを以下のプロジェクト単位構成に変更する:

```markdown
---
date: YYYY-MM-DD
tags: [...]
type: daily
mood: ...
energy: ...
aliases: [デイリー学習レポート YYYY-MM-DD]
---

# デイリー学習レポート - YYYY-MM-DD

## 📋 概要
（全プロジェクト横断の一日の要約）

## 📁 作業プロジェクト

### ProjectA
- **活動時間**: HH:MM - HH:MM
- **活動内容**: （データソース横断の統合要約）
- **使用技術**: （このプロジェクトで使用した技術・ツール）
- **学習内容**: （このプロジェクトを通じて学んだこと）
- **発生した問題**: （このプロジェクトで発生した問題と解決策）
- **主な成果**: （このプロジェクトでの主な成果・成果物）

### ProjectB
...（同上）
...

## 🔄 振り返り
### うまくいったこと
### 改善したいこと
### 明日に活かしたい知見

## 📌 翌日へのアクション
- [ ] ...

## 🏷 技術タグ
`tag1` `tag2` ...
```

### Rationale
- spec FR-005 で定義されたセクション構成に沿う
- プロジェクトごとに「活動・技術・学習・問題・成果」を完結させることで、読者はプロジェクト単位で情報を消化できる
- プロジェクトを跨ぐ振り返りやアクションは末尾に集約し、重複を避ける

### Alternatives considered
- 従来のカテゴリ別構成を維持し、各セクション内でプロジェクト名を記載 → プロジェクトが増えると情報が分散し、「プロジェクト単位で読む」ことが困難
- プロジェクトセクションのみ追加し、既存セクションは維持 → 情報の重複や矛盾が発生する可能性が高い。プロジェクトセクションに情報を集約し、横断セクション（振り返り等）のみ分離する構成が最適

---

## 5. テスト戦略

### Decision
以下のテストを追加・修正する:

| テスト | 種類 | 内容 |
|--------|------|------|
| `test_base.py` | 単体 | `ParsedData.project_hints` の入出力テスト |
| `test_terminal_logs.py` | 単体 | cwd/git_branch が parse() テキストに含まれることの確認 |
| `test_enricher.py` | 単体 | project_hints 統合のテスト (JSON パース) |
| `test_pipeline.py` | 結合 | プロジェクト単位フォーマットの結合テスト（パイプライン全体） |

### Rationale
- 各変更に対して最低1つのテストを追加する方針
- 結合テストでは実際の JSONL/JSON データを使用し、出力された日報にプロジェクト名が含まれることを確認

### Alternatives considered
- E2E テストのみ → デバッグが困難。変更単位でのテストが必須
- 単体テストのみ → パイプライン全体の連携確認が不十分。結合テストを併用する
