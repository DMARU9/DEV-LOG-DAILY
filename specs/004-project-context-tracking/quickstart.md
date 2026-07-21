# Quickstart: プロジェクトコンテキスト tracking 機能の検証ガイド

**Feature**: 004-project-context-tracking | **Date**: 2026-07-21

## 前提条件

- dev-log-daily がインストール済み（`pip install -e .` または `uv tool install`）
- 設定ファイル（`config.yml`）が有効
- 前日の開発ログ（Copilot チャット・Git コミット・ターミナル履歴）が存在する

## 検証シナリオ

### シナリオ1: 複数プロジェクトの日報生成（P1）

**目的**: 複数プロジェクトの活動がプロジェクト別に整理されて日報に出力されることを確認する。

**準備**:
- 複数のプロジェクト（例: DevLogDaily, MyApp）で前日に活動がある状態
- 各プロジェクトで Copilot チャット・Git コミット・ターミナル操作が混在していること

**実行**:
```bash
dev-log-daily --config config.yml --date YYYY-MM-DD
```

**期待される結果**:
- 日報に「📁 作業プロジェクト」セクションが存在する
- プロジェクトごとに独立したサブセクション（`### DevLogDaily`, `### MyApp` 等）が設けられている
- 各サブセクションに活動内容・使用技術・学習内容が記載されている
- 同一プロジェクトの Copilot チャット・Git コミット・ターミナル操作が統合されている

**検証方法**:
```bash
# 日報の「📁 作業プロジェクト」セクションに期待するプロジェクト名が含まれているか確認
grep -c "### " output/daily_report_YYYY-MM-DD.md
grep "作業プロジェクト" output/daily_report_YYYY-MM-DD.md
```

---

### シナリオ2: ターミナル cwd のプロジェクト紐づけ（P2）

**目的**: ターミナル操作の cwd 情報が日報のプロジェクト分類に反映されることを確認する。

**準備**:
- ターミナル履歴 JSONL に異なる `cwd` のコマンドが含まれている
- `history_YYYY-MM-DD.jsonl` の各行に `cwd` フィールドが正しく記録されている

**実行**:
```bash
dev-log-daily --config config.yml --date YYYY-MM-DD
```

**期待される結果**:
- cwd が `DevLogDaily` プロジェクト配下のコマンドは DevLogDaily のセクションに分類される
- cwd が `MyApp` プロジェクト配下のコマンドは MyApp のセクションに分類される
- cwd が空のエントリは「プロジェクト不明」として扱われる

**検証方法**:
```bash
# raw データに cwd が含まれていることを確認
python -c "
import json
with open('path/to/history_YYYY-MM-DD.jsonl') as f:
    for line in f:
        data = json.loads(line)
        assert 'cwd' in data, 'cwd field missing'
        print(f'cwd: {data[\"cwd\"]} -> cmd: {data[\"command\"][:50]}')
"
```

---

### シナリオ3: 表記ゆれの統合（P3）

**目的**: Copilot チャットのワークスペース名と Git リポジトリ名が異なっても、同一プロジェクトとして統合されることを確認する。

**準備**:
- Copilot チャットにワークスペース名 `DevLogDaily` のセッションがある
- Git リポジトリ名が `dev-log-daily`（ケース・ハイフン違い）のコミットがある
- ターミナル cwd が `/home/user/github/DevLogDaily` の操作がある

**実行**:
```bash
dev-log-daily --config config.yml --date YYYY-MM-DD
```

**期待される結果**:
- 3つの異なる表記を持つヒントが単一のプロジェクト（例: `DevLogDaily`）として統合される
- 日報の当該プロジェクトセクションに3つのデータソースすべての活動が含まれる
- 統合が推定である場合、「(推測)」と明記される

---

### シナリオ4: 単一プロジェクトのみの日（P1 エッジケース）

**目的**: 単一プロジェクトのみの活動でも正しく表示されることを確認する。

**準備**:
- 1つのプロジェクトのみで活動があった日付を指定

**実行**:
```bash
dev-log-daily --config config.yml --date YYYY-MM-DD
```

**期待される結果**:
- 「📁 作業プロジェクト」セクションに1つのサブセクションのみ表示される
- 「単一プロジェクトのみ」であることが明示される（または1セクションのみで自然に単一と分かる）
- プロジェクトの活動内容は十分に詳細に記載される

---

### シナリオ5: cwd 欠落エントリの取扱い（P2 エッジケース）

**目的**: cwd が空のターミナルエントリが正しく処理されることを確認する。

**準備**:
- `history_YYYY-MM-DD.jsonl` に `cwd` フィールドがないエントリを含める
- または `cwd` が空文字列のエントリを含める

**実行**:
```bash
dev-log-daily --config config.yml --date YYYY-MM-DD
```

**期待される結果**:
- cwd がないエントリは「プロジェクト不明」として分類される
- 日報に「プロジェクト不明の活動があったこと」が明記される
- 他の正常なエントリのプロジェクト分類には影響しない

---

## テスト実行コマンド

### 単体テスト
```bash
# 仮想環境で実行
cd /path/to/dev-log-daily
source .venv/bin/activate

# ParsedData.project_hints のテスト
python -m pytest tests/unit/test_base.py -v -k "project_hints"

# terminal_logs cwd/git_branch 保持のテスト
python -m pytest tests/unit/test_terminal_logs.py -v -k "cwd"

# Enricher project_hints 統合のテスト
python -m pytest tests/unit/test_enricher.py -v
```

### 結合テスト
```bash
# パイプライン全体の結合テスト
python -m pytest tests/integration/test_pipeline.py -v -k "project_activities"
```

### 全テスト
```bash
python -m pytest
```

## 関連ドキュメント

- [データモデル](../data-model.md) — エンティティ定義と状態遷移
- [Parser → Enricher 契約](../contracts/parser-to-enricher.md) — ProjectHint の仕様
- [Enricher → Reporter 契約](../contracts/enricher-to-reporter.md) — ProjectActivity の仕様
- [実装計画](../plan.md) — 実装の全体計画
- [仕様](../spec.md) — 機能要件と成功基準
