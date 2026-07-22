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
Copilot チャットログ、Git コミット履歴、ターミナル操作履歴、プロジェクト活動データを解析し、
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

## 📋 総合概要
その日の開発活動全体を2〜3文で要約してください。
どのような目的を持って、どんな技術領域に取り組んだのかが一目でわかるように記述します。
プロジェクト活動データ（project_activities）を主要な情報源として活用してください。
データがない場合は「該当なし」と記載してください。

## 📊 プロジェクト別活動サマリー
以下の Markdown テーブル形式で、プロジェクトごとの活動を一覧表示してください。

| プロジェクト | 活動時間 | 主な活動内容 | 関連データソース |
|------------|---------|-------------|----------------|
| プロジェクトA | 03:15 | 〜の実装、〜の調査 | Copilot, Git, Terminal |

- 活動時間は継続時間（duration）を HH:MM 形式で表示
- データがない場合: テーブルヘッダーのみ出力（行なし）
- ヘッダー行とセパレータ行は常に出力

## プロジェクト詳細セクション

プロジェクトごとに `## プロジェクト名` の見出しでセクションを作成してください（見出しレベルは `##`）。
プロジェクトに紐づかない活動は `## その他` セクションに集約してください。

### 📋 概要
プロジェクトでの活動を2〜5文で要約。

### 🛠 触れた技術・ツール
- **技術名**: 使用目的と学んだこと

### 📖 インプット
読んだ記事、見たコード、参考資料。該当なしの場合は「該当なし」。

### 📚 学習内容
#### 新しく学んだこと
- **学習トピック**: 内容
  - キーポイント: 補足

#### 理解を深めたこと
（該当データがない場合、このサブセクションは省略可）
- **学習トピック**: 内容
  - キーポイント: 補足

### 💻 開発活動
- `feat` ユーザー認証機能を実装 — 関連ファイル: src/auth.py / コミット: abc1234
- `fix` ログイン時のクラッシュを修正 — 関連ファイル: src/auth.py / コミット: def5678
- `docs` API仕様書を更新 — 関連ファイル: docs/api.md
- `chore` 依存パッケージを更新 — 関連ファイル: package.json

### 🚧 発生した問題と解決策
（該当データがない場合、セクションごと省略可）
- **問題**: 要約 → **原因**: 原因 → **解決**: 解決方法（`解決済`）
- **問題**: 要約 → **原因**: 原因 → **解決**: 解決方法（`未解決`）

### 🔄 振り返り
（該当データがない場合、セクションごと省略可）
#### うまくいったこと
- 具体的な内容

#### 改善したいこと
- 具体的な内容

#### 明日に活かしたい知見
- 具体的な内容

### 📌 翌日へのアクション
（該当データがない場合、セクションごと省略可）
- [ ] 優先度の高いタスク
- [ ] 継続して取り組むタスク

### 🏷 技術タグ
`タグ1` `タグ2` `タグ3`

---

全てのセクションで日本語を使用してください。
プロジェクト活動データ（project_activities）が主要な入力です。
これを中心に日報を構成し、他のデータソース（Copilotチャット・Gitコミット・
ターミナル履歴）は補助的な情報として使用してください。
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

### report_metadata（フロントマター情報）
{report_metadata}

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
    enriched_data = state.get("enriched_data", {})
    enriched = _format_enriched_data(enriched_data)
    report_metadata = _format_report_metadata(enriched_data.get("report_metadata", {}))
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
            report_metadata=report_metadata or "（report_metadataなし）",
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

    # report_metadata を LLM コンテキストとして整形
    metadata = enriched.get("report_metadata", {})
    if metadata:
        parts.append("report_metadata:")
        if metadata.get("mood"):
            parts.append(f"  全体的な気分: {metadata['mood']}")
        if metadata.get("energy"):
            parts.append(f"  全体的なエネルギー: {metadata['energy']}/5")
        if metadata.get("tags"):
            parts.append(f"  タグ候補: {', '.join(metadata['tags'])}")
        project_moods = metadata.get("project_moods", {})
        if project_moods:
            parts.append("  プロジェクト別気分:")
            for proj, moods in project_moods.items():
                parts.append(f"    - {proj}: mood={moods.get('mood', '')}, energy={moods.get('energy', '')}/5")

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


def _format_report_metadata(metadata: dict) -> str:
    """report_metadata を LLM コンテキスト用文字列に整形する.

    Args:
        metadata: report_metadata dict（mood, energy, tags, project_moods）

    Returns:
        整形された文字列
    """
    if not metadata:
        return ""

    lines = []
    if metadata.get("mood"):
        lines.append(f"推定気分: {metadata['mood']}")
    if metadata.get("energy"):
        lines.append(f"推定エネルギー: {metadata['energy']}/5")
    if metadata.get("tags"):
        lines.append(f"タグ候補: {', '.join(metadata['tags'])}")

    project_moods = metadata.get("project_moods", {})
    if project_moods:
        lines.append("プロジェクト別気分:")
        for proj, moods in project_moods.items():
            lines.append(
                f"  - {proj}: mood={moods.get('mood', '')}, "
                f"energy={moods.get('energy', '')}/5"
            )

    return "\n".join(lines)


def _generate_empty_report(target_date: str) -> str:
    """全データ空の場合の日報を生成する（新フォーマット）."""
    return (
        f"---\n"
        f"date: {target_date}\n"
        f"tags: [DevLogDaily]\n"
        f"type: daily\n"
        f"mood: productive\n"
        f"energy: 4\n"
        f"aliases: [デイリー学習レポート {target_date}]\n"
        f"---\n\n"
        f"# デイリー学習レポート - {target_date}\n\n"
        f"## 📋 総合概要\n"
        f"該当なし\n\n"
        f"## 📊 プロジェクト別活動サマリー\n"
        f"| プロジェクト | 活動時間 | 主な活動内容 | 関連データソース |\n"
        f"|------------|---------|-------------|----------------|\n"
        f"\n"
        f"## プロジェクト\n"
        f"該当なし\n"
    )
