# Quickstart: 日報出力フォーマットの大幅リファクタリング

**Phase**: 1 — 検証シナリオと実行手順

**Date**: 2026-07-22

## 前提条件

- 004-project-context-tracking が完了している（project_hints / project_activities の生成が正常動作）
- 仮想環境（`.venv`）がアクティブ
- テストデータが `tests/fixtures/` に存在する

## 検証シナリオ

### Scenario 1: 新フォーマットの完全性検証

**目的**: Reporter が出力する日報が新しいフォーマット仕様に完全に準拠していることを確認する。

**前提条件**:
- `REPORTER_SYSTEM_PROMPT` が新フォーマット指示に書き換わっている
- `_generate_empty_report()` が新フォーマットで出力する

**実行手順**:

```bash
# 仮想環境アクティベート
source .venv/bin/activate

# 単体テスト実行（Reporter）
cd /home/takumi/github/DEV-LOG-DAILY
python -m pytest tests/unit/test_reporter.py -v -k "format" 2>&1
```

**期待される結果**:
- フォーマット関連テストがすべて PASS
- YAML フロントマターの全フィールド（date, tags, type, mood, energy, aliases）が有効な値を持つ
- 見出しレベルが正しい（`#` → `##` → `###` → `####`）
- `📊 プロジェクト別活動サマリー` テーブルが正しい列構成を持つ
- 各プロジェクトセクションのサブセクションが仕様通り出力される

---

### Scenario 2: 空データ時の動作検証

**目的**: 全データソースが空の場合でもエラーなく新フォーマットの日報が生成されることを確認する。

**前提条件**:
- `_generate_empty_report()` が新フォーマットに更新済み

**実行手順**:

```bash
# 単体テスト実行（空データケース）
python -m pytest tests/unit/test_reporter.py -v -k "empty" 2>&1
```

または結合テストで実際に空データを流す:

```bash
python -m pytest tests/integration/test_pipeline.py -v -k "empty" 2>&1
```

**期待される結果**:
- エラーなく日報が生成される
- 出力ファイルが有効な Markdown としてパース可能
- YAML フロントマターが出力されている
- 📋 総合概要が「該当なし」
- 📊 サマリーテーブルがヘッダーのみ（行なし）
- プロジェクトセクションが「該当なし」

---

### Scenario 3: enriched_data report_metadata 検証

**目的**: Enricher の出力に `report_metadata` が正しく含まれることを確認する。

**前提条件**:
- `ENRICHER_SYSTEM_PROMPT` が report_metadata 出力用に更新済み

**実行手順**:

```bash
# Enricher 単体テスト
python -m pytest tests/unit/test_enricher.py -v -k "report_metadata" 2>&1
```

**期待される結果**:
- `enriched_data["report_metadata"]` が存在する
- `report_metadata.mood` が有効な文字列
- `report_metadata.energy` が 1〜5 の整数
- `report_metadata.tags` がリスト形式
- `report_metadata.project_moods` がプロジェクト名をキーとする辞書

---

### Scenario 4: 結合テスト（パイプライン全体）

**目的**: パイプライン全体を通じて新フォーマットの日報が正しく生成されることを確認する。

**実行手順**:

```bash
# 結合テスト（パイプライン全体）
python -m pytest tests/integration/test_pipeline.py -v 2>&1
```

**期待される結果**:
- 全テスト PASS
- 生成された日報の Markdown が新フォーマットに準拠
- 既存のエラーハンドリングが正常動作

---

### Scenario 5: 開発活動フォーマット検証

**目的**: 💻 開発活動の各エントリが正しい種別ラベルとフォーマットで出力されることを確認する。

**実行手順**:

```bash
# Reporter + パーサー結合テスト
python -m pytest tests/integration/ -v -k "activity" 2>&1
```

**期待される結果**:
- 各エントリが `` `種別` 内容 — 関連ファイル: パス / コミット: ハッシュ `` の形式に従う
- 種別は feat/fix/docs/chore のいずれか
- Git データソース由来のエントリにコミットハッシュが含まれる

---

## データモデル参照

詳細なエンティティ定義は以下を参照:

- データモデル全体: [data-model.md](./data-model.md)
- 出力フォーマット仕様: [contracts/report-format.md](./contracts/report-format.md)
- Enricher 拡張契約: [contracts/enricher-to-reporter.md](./contracts/enricher-to-reporter.md)
