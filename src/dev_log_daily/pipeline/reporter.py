"""Reporter ノード — 補完済みデータから Markdown 日報を生成・保存."""

from __future__ import annotations

import logging
from pathlib import Path

from dev_log_daily.config.schema import AppConfig
from dev_log_daily.llm.client import create_llm
from dev_log_daily.state import DailyState
from dev_log_daily.utils.file import write_text

logger = logging.getLogger(__name__)

REPORTER_SYSTEM_PROMPT = """\
あなたは技術学習の記録アナリストであり、開発者の日々の学びを体系化する役割を担います。
Copilot チャットログ、Git コミット履歴、ターミナル操作履歴を解析し、
その日に関わった技術・得た学び・直面した課題を整理した「学習日報」を作成してください。

この日報は週次でのふりかえりやブログ記事の素材として活用されます。
そのため、単なる作業ログではなく「何を学び、どのような知見を得たか」に焦点を当て、
あとから読み返して有益な情報となるよう体系化してください。

日報は以下の Markdown フォーマットに従って出力してください。
各セクションの指示に沿って、データから抽出できる情報を可能な限り具体的に記述してください。
データが存在しないセクションは「該当なし」と記載して構いません。

---

date: YYYY-MM-DD
tags: [DevLogDaily, LangGraph, Python, SpecKit]
type: daily
mood: productive  # データから適切に推測して設定（productive/reflective/frustrated 等）
energy: 4  # データから適切に推測して設定（1-5）
aliases: [デイリー学習レポート YYYY-MM-DD]

---

# デイリー学習レポート - YYYY-MM-DD

## ⏱ タイムトラッキング
（任意：ざっくり時間配分）
データから時間配分が推測できる場合は記述してください。該当しない場合は空欄のままにしてください。

## 📋 概要
その日の開発活動全体を2〜3文で要約してください。
どのような目的を持って、どんな技術領域に取り組んだのかが一目でわかるように記述します。

## 🛠 本日触れた技術・ツール
その日に使用・学習した技術をカテゴリ別に整理してください。
各技術について「何をしたか」「何を学んだか」を簡潔に記述します。

### 言語・フレームワーク
- **技術名**: 使用目的と学んだこと

### ツール・インフラ
- **技術名**: 使用目的と学んだこと

### ライブラリ・API
- **技術名**: 使用目的と学んだこと

### 概念・手法
- **概念名**: どのように触れ、何を理解したか

## 📖 インプット
読んだ記事、見たコード、参考にした資料など、インプットがあれば記載してください。
該当しない場合は「該当なし」と記載して構いません。

## 📚 学習内容
その日新たに得た知識や、理解が深まった事柄を整理します。
後日読み返したときに理解を再現できるよう、具体的に記述してください。

### 新しく学んだこと
- **学習トピック**: 何を学び、どのようなコンテキストで役立ったか
  - キーポイント: 重要なポイントやコード例があれば補足

### 理解を深めたこと
- **学習トピック**: 既存知識からどのように理解が深まったか
  - キーポイント: 新たに得た気づき

## 💻 開発活動
実際に行った開発作業を作業種別に整理します。
Copilot のチャットログ・Git コミット・ターミナル操作から総合的に判断してください。

### 実装・機能追加
- **内容**: 実装した機能や追加したコードの概要
  - 関連ファイル: 変更したファイルパス（判別できる場合）
  - 関連コミット: コミットハッシュ（判別できる場合）

### 修正・改善
- **内容**: 修正したバグや改善した箇所の概要
  - 関連ファイル: 変更したファイルパス
  - 原因: 判別できる場合

### その他の作業（設定変更・ドキュメント整備など）
- **内容**: 作業の概要

## 🚧 発生した問題と解決策
開発中に遭遇したエラー・課題と、その解決に至るプロセスを記録します。
同じ問題に再度直面したときに参照できるよう、原因と解決策を明確にしてください。

### 問題1: （問題の要約）
- **現象**: 発生したエラーや問題の内容
- **推定原因**: なぜ発生したか
- **試した解決策**:
  1. 解決策の説明 → 結果
  2. ...
- **最終的な解決方法**: どのように解決したか
- **ステータス**: 解決済み / 未解決 / 一時対処
- **得られた教訓**: この問題から学んだこと

## 🔄 振り返り
### うまくいったこと
- 具体的に何がうまくいったか、その要因は何か

### 改善したいこと
- うまくいかなかったこと、次回どう改善するか

### 明日に活かしたい知見
- 今日の経験から得た、明日以降に活かせるポイント

## 📌 翌日へのアクション
- [ ] 優先度の高いタスク
- [ ] 継続して取り組むタスク
- [ ] 調査・学習が必要な事項

## 🏷 技術タグ
その日の活動を表す技術キーワードをタグ形式で列挙してください。
週次集計やブログのカテゴリ分けに使用します。

`タグ1` `タグ2` `タグ3` ...

---

全てのセクションで日本語を使用してください。
推測と事実を区別し、推測には「(推測)」と付記してください。
各項目は後日検索しやすいよう、技術キーワードを明示してください。
Frontmatter の mood と energy は収集データから適切に推測して設定してください。
Frontmatter の tags はデフォルト値
（DevLogDaily, LangGraph, Python, SpecKit）に加えて、
その日の活動内容に応じて適宜追加・変更してください。
"""

REPORTER_PROMPT_TEMPLATE = """以下のデータから日報を生成してください。

対象日: {target_date}

## プロジェクト活動データ（主要入力）
{project_activities_text}

## 補助データ

### Copilotチャット
{copilot_chat_data}

### ワークスペースコンテキスト
{workspace_context}

### Gitコミット
{git_commits_data}

### ターミナル履歴
{terminal_logs_data}

## 補完・統合データ
{enriched_data}

上記のデータをもとに、指定されたセクション構成のMarkdown日報を生成してください。
プロジェクト活動データ（project_activities）を主要な情報源として使用し、
他のデータソースは補助的に活用してください。
"""


async def reporter_node(state: DailyState, config: AppConfig) -> DailyState:
    """Reporter ノード: 日報 Markdown を生成しファイルに保存する.

    補完済みデータ（enriched_data）をもとに LLM で Markdown 日報を生成し、
    設定の出力ディレクトリに daily_report_YYYY-MM-DD.md として保存する。

    全データソースが空/存在しない場合は全セクション「該当なし」の日報を生成する。
    同名ファイルは上書きする。

    Args:
        state: 現在の DailyState
        config: アプリケーション設定

    Returns:
        更新された DailyState（daily_report に生成結果を設定）
    """
    target_date = state["target_date"]
    progress_log = state.get("progress_log", [])
    errors = state.get("errors", [])
    llm_config = config.llm.reporter
    output_dir = config.output.directory

    logger.info("[Reporter] 日報生成を開始します...")
    progress_log.append("[Reporter] 日報生成を開始します...")

    # 各データソースの内容を取得
    copilot_data = _format_parsed_data(state, "copilot_chat_parsed", "Copilotチャット")
    git_data = _format_parsed_data(state, "git_commits_parsed", "Gitコミット")
    terminal_data = _format_parsed_data(state, "terminal_logs_parsed", "ターミナル履歴")
    enriched = _format_enriched_data(state.get("enriched_data", {}))
    workspace_context = _format_workspace_context(state.get("copilot_chat_raw", {}))

    # プロジェクト活動データを取得（主要入力）
    project_activities = state.get("project_activities", {})
    project_activities_text = _format_project_activities(project_activities)

    all_empty = not any([copilot_data.strip(), git_data.strip(), terminal_data.strip()])

    if all_empty:
        logger.info("[Reporter] 全データソースが空のため「該当なし」日報を生成")
        progress_log.append("[Reporter] 全データソースが空のため「該当なし」日報を生成")
        report = _generate_empty_report(target_date)
    else:
        # LLM で日報生成
        llm = create_llm(
            model=llm_config.model,
            base_url=llm_config.base_url,
            api_key=llm_config.api_key,
            temperature=0.0,
            timeout=config.timeout_seconds,
            max_tokens=llm_config.max_output_tokens,
        )

        prompt = REPORTER_PROMPT_TEMPLATE.format(
            target_date=target_date,
            project_activities_text=project_activities_text or "（プロジェクト活動データなし）",
            copilot_chat_data=copilot_data or "（データなし）",
            workspace_context=workspace_context or "（データなし）",
            git_commits_data=git_data or "（データなし）",
            terminal_logs_data=terminal_data or "（データなし）",
            enriched_data=enriched or "（データなし）",
        )

        logger.info("[Reporter] LLMによる日報生成中...")
        progress_log.append("[Reporter] LLMによる日報生成中...")

        from dev_log_daily.llm.client import call_llm_with_retry

        messages = [
            {"role": "system", "content": REPORTER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        report = await call_llm_with_retry(llm, messages)

        logger.info("[Reporter] 日報生成が完了しました")
        progress_log.append("[Reporter] 日報生成が完了しました")

    state["daily_report"] = report

    # ファイル保存
    filename = f"daily_report_{target_date}.md"
    output_path = Path(output_dir) / filename

    try:
        write_text(str(output_path), report)
        logger.info("[Reporter] 日報を保存しました: %s", output_path)
        progress_log.append(f"[Reporter] 日報を保存しました: {output_path}")
    except OSError as e:
        logger.error("[Reporter] 日報保存エラー: %s", e)
        progress_log.append(f"[Reporter] 日報保存エラー: {e}")
        errors.append(
            {
                "source": "reporter",
                "stage": "save",
                "error_type": type(e).__name__,
                "message": str(e),
            }
        )

    state["errors"] = errors
    state["progress_log"] = progress_log

    return state


def _format_parsed_data(state: DailyState, field: str, label: str) -> str:
    """DailyState から解析データを文字列形式に整形する."""
    parsed = state.get(field, {})
    if isinstance(parsed, dict):
        summary = parsed.get("summary", "")
        structured = parsed.get("structured_data", {})
        parts = [summary] if summary else []
        if structured:
            parts.append(f"構造化データ: {structured}")
        return "\n".join(parts)
    return ""


def _format_workspace_context(raw_data: dict) -> str:
    """CopilotChat の raw データからワークスペースコンテキストを整形する.

    workspace 名・セッション数・プラットフォーム情報を抽出し、
    日報生成のコンテキストとして提供する。

    Args:
        raw_data: copilot_chat_raw の dict（CollectedLog.to_dict() 出力）

    Returns:
        ワークスペースコンテキストの文字列
    """
    if not raw_data:
        return ""

    workspaces = raw_data.get("workspaces", [])
    if not workspaces:
        return ""

    lines: list[str] = []
    lines.append(f"合計 {len(workspaces)} ワークスペース:")

    for ws in workspaces:
        ws_name = ws.get("workspace_name", "Unknown")
        ws_id = ws.get("workspace_id", "")
        session_count = ws.get("session_count", 0)
        platforms = ws.get("metadata", {}).get("platforms", [])
        platform_str = ", ".join(platforms) if platforms else "不明"

        lines.append(f"- {ws_name} ({ws_id[:8]}...): {session_count} セッション ({platform_str})")

    return "\n".join(lines)


def _format_project_activities(project_activities: dict[str, dict]) -> str:
    """プロジェクト活動データを文字列形式に整形する.

    Args:
        project_activities: プロジェクト名をキーとする ProjectActivity dict

    Returns:
        整形された文字列
    """
    if not project_activities:
        return ""

    lines: list[str] = []
    for project_name, activity in project_activities.items():
        lines.append(f"### {project_name}")
        source_activities = activity.get("source_activities", {})
        time_range = activity.get("time_range", {})
        related_sources = activity.get("related_sources", [])

        if time_range:
            start = time_range.get("start", "")
            end = time_range.get("end", "")
            if start and end:
                lines.append(f"時間範囲: {start} ～ {end}")
            elif start:
                lines.append(f"開始: {start}")

        if source_activities:
            lines.append("データソース別活動:")
            for source, activities_list in source_activities.items():
                for act in activities_list:
                    lines.append(f"  - [{source}] {act}")

        if related_sources:
            lines.append(f"関連ソース: {', '.join(related_sources)}")

        lines.append("")  # 空行

    return "\n".join(lines)


def _format_enriched_data(enriched: dict) -> str:
    """Enriched data を文字列形式に整形する."""
    if not enriched:
        return ""

    parts = []
    if enriched.get("context"):
        parts.append(f"文脈: {enriched['context']}")

    activities = enriched.get("key_activities", [])
    if activities:
        parts.append("主要な開発活動:")
        for act in activities:
            parts.append(f"- {act.get('activity', '')}: {act.get('impact', '')}")

    refs = enriched.get("cross_references", [])
    if refs:
        parts.append("クロスリファレンス:")
        for ref in refs:
            parts.append(f"- {ref.get('topic', '')}: {ref.get('details', '')}")

    return "\n".join(parts)


def _generate_empty_report(target_date: str) -> str:
    """全データ空の場合の日報を生成する."""
    return (
        f"---\n"
        f"date: {target_date}\n"
        f"tags: [DevLogDaily, LangGraph, Python, SpecKit]\n"
        f"type: daily\n"
        f"mood: productive\n"
        f"energy: 4\n"
        f"aliases: [デイリー学習レポート {target_date}]\n"
        f"---\n\n"
        f"# デイリー学習レポート - {target_date}\n\n"
        f"## ⏱ タイムトラッキング\n\n"
        f"## 📋 概要\n"
        f"該当なし\n\n"
        f"## 🛠 本日触れた技術・ツール\n"
        f"該当なし\n\n"
        f"## 📖 インプット\n"
        f"該当なし\n\n"
        f"## 📚 学習内容\n"
        f"該当なし\n\n"
        f"## 💻 開発活動\n"
        f"該当なし\n\n"
        f"## 🚧 発生した問題と解決策\n"
        f"該当なし\n\n"
        f"## 🔄 振り返り\n"
        f"該当なし\n\n"
        f"## 📌 翌日へのアクション\n"
        f"該当なし\n\n"
        f"## 🏷 技術タグ\n"
        f"該当なし\n"
    )
