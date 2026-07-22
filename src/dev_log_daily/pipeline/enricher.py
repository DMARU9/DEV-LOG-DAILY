"""Enricher ノード — 解析結果のクロスリファレンス・矛盾検出・補完."""

from __future__ import annotations

import logging

from dev_log_daily.config.schema import AppConfig
from dev_log_daily.llm.client import create_llm
from dev_log_daily.state import DailyState

logger = logging.getLogger(__name__)

ENRICHER_SYSTEM_PROMPT = """あなたは日報生成パイプラインの Enricher です。
与えられた複数のデータソース（Copilotチャットログ、Gitコミット、ターミナル履歴）の
解析結果をクロスリファレンスし、以下の処理を行ってください：

これらの処理結果は後続の Reporter が「デイリー学習レポート」を生成するための
入力として使用されます。日報の各セクション（技術・ツール、学習内容、開発活動、
問題と解決策等）に必要な情報が過不足なく連携されるよう、以下の処理を実施してください：

1. **クロスリファレンス**: 各ソース間で共通するトピック・プロジェクトを特定し、
   関連付けを行う（例：Copilotチャットで議論した内容が実際にGitコミットや
   ターミナル操作として現れているか）
2. **矛盾点検出**: 同じトピックで異なる情報がある場合、矛盾点としてマークする
3. **欠落情報の補完**: あるソースにしかない情報を他のソースの文脈で補足する
4. **コンテキスト付与**: 各開発活動に、なぜその作業を行ったかの文脈を付与する
5. **プロジェクト統合**: 各データソースから抽出されたプロジェクトヒントを
   クロスリファレンスして表記ゆれを解決し、プロジェクト単位の活動情報を生成する

### プロジェクト統合手順

1. 各データソースのプロジェクトヒント（project_hints）の candidate_name を比較し、
   同じプロジェクトを指すものを統合する（表記ゆれ解決: "DevLogDaily" = "dev-log-daily"）
2. 統合後の各プロジェクトについて、全データソースでの活動を集約する
3. 各プロジェクト内でデータソース間の時系列関係を分析し、活動の流れ
   （設計→実装→テスト等）が追跡できるように key_activities に time-ordered 情報を含めよ
4. プロジェクト名の重複（異なるパスに同名フォルダ）を検出した場合、
    candidate_name に親ディレクトリを含めて区別せよ（例: /work/ProjectA vs /personal/ProjectA）
5. 10プロジェクトを超える場合は、主要プロジェクトのみ詳細を保持し、
   残りは一覧として要約せよ
6. "プロジェクト不明" のヒントは単一のエントリに集約せよ

出力は以下の JSON 形式で返してください：
{
  "cross_references": [
    {"topic": "トピック名", "sources": ["copilot_chat", "git_commits",
     "terminal_logs"], "details": "関連性の説明"}
  ],
  "contradictions": [
    {"topic": "トピック名", "details": "矛盾内容",
     "resolution": "推定される解消方法"}
  ],
  "completions": [
    {"topic": "トピック名", "details": "補完情報", "based_on": "元データ"}
  ],
  "context": "一日の開発活動の全体的な文脈と流れの説明。"
  " 日報の「概要」セクションの素材となるよう記述",
  "key_activities": [
    {"activity": "活動内容", "impact": "影響や成果",
     "related_sources": ["関連ソース"]}
  ],
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
  },
  "projects": {
    "ProjectName": {
      "project_name": "正規化されたプロジェクト名",
      "source_activities": {
        "copilot_chat": ["活動要約1", "活動要約2"],
        "git_commits": ["活動要約1"],
        "terminal_logs": ["活動要約1"]
      },
      "time_range": {
        "start": "2026-07-21T09:00:00+09:00",
        "end": "2026-07-21T18:00:00+09:00"
      },
      "related_sources": ["copilot_chat", "git_commits", "terminal_logs"]
    }
  }
}

"projects" キーの各値は ProjectActivity オブジェクトです。
time_range.start/end は ISO 8601 形式で記述してください。
活動がないプロジェクトは projects に含めないでください。
"""

ENRICHER_PROMPT_TEMPLATE = """以下のデータソース解析結果をクロスリファレンスし、
JSON形式で補完・統合してください。

これらのデータは後続の Reporter が「デイリー学習レポート」を生成するために使用されます。
日報の各セクション（� 概要、🛠 触れた技術・ツール、📚 学習内容、💻 開発活動、
🚧 発生した問題と解決策、🔄 振り返り等）に必要な情報を過不足なく抽出できるよう、
以下の観点でデータを構造化・補完してください。

対象日: {target_date}

## Copilotチャット解析結果
{copilot_chat_summary}

## Gitコミット解析結果
{git_commits_summary}

## ターミナル履歴解析結果
{terminal_logs_summary}

## プロジェクトヒント（全データソース）
{project_hints_text}

上記の解析結果とプロジェクトヒントを統合し、統一された JSON 形式で出力してください。
プロジェクトヒントの candidate_name の表記ゆれを解決し、同一プロジェクトを統合した上で
"projects" フィールドにプロジェクト単位の活動情報を生成してください。

また、全データソースの内容から以下の report_metadata を推定し、出力 JSON の
"report_metadata" フィールドに含めてください：
- mood: 一日の全体的な気分を表す文字列（productive / reflective / frustrated 等）
- energy: 一日の全体的なエネルギー量を 1〜5 の整数で推定
- tags: フロントマター用タグ候補（DevLogDaily を含む最大10個のリスト）
- project_moods: プロジェクトごとの mood/energy（キーはプロジェクト名）
"""


async def enricher_node(state: DailyState, config: AppConfig) -> DailyState:
    """Enricher ノード: 解析結果をクロスリファレンス・補完する.

    各データソースの解析結果（*_parsed）を統合し、クロスリファレンス・
    矛盾点検出・欠落情報補完・コンテキスト付与を実施する。
    また、全データソースの project_hints を統合して project_activities を生成する。

    LLMエラー時は errors に記録し、enriched_data は空のまま後続に渡す。

    Args:
        state: 現在の DailyState
        config: アプリケーション設定

    Returns:
        更新された DailyState（enriched_data + project_activities を設定）
    """
    target_date = state["target_date"]
    progress_log = state.get("progress_log", [])
    errors = state.get("errors", [])
    llm_config = config.llm.enricher

    logger.info("[Enricher] データ補完を開始します...")
    progress_log.append("[Enricher] データ補完を開始します...")

    # 各解析結果のサマリーを取得
    copilot_summary = _get_parsed_summary(state, "copilot_chat_parsed")
    git_summary = _get_parsed_summary(state, "git_commits_parsed")
    terminal_summary = _get_parsed_summary(state, "terminal_logs_parsed")

    # プロジェクトヒントを全データソースから収集
    project_hints = _collect_project_hints(state)
    project_hints_text = _format_project_hints(project_hints)

    # すべて空の場合はスキップ
    if not copilot_summary and not git_summary and not terminal_summary:
        logger.info("[Enricher] 全データソースが空のためスキップ")
        progress_log.append("[Enricher] 全データソースが空のためスキップ")
        state["enriched_data"] = {
            "cross_references": [],
            "contradictions": [],
            "completions": [],
            "context": "",
            "key_activities": [],
            "projects": {},
            "report_metadata": {
                "mood": "productive",
                "energy": 4,
                "tags": ["DevLogDaily"],
                "project_moods": {},
            },
            "note": "全データソースが空のため補完処理をスキップしました",
        }
        state["project_activities"] = {}
        state["progress_log"] = progress_log
        return state

    # LLM インスタンス生成
    llm = create_llm(
        model=llm_config.model,
        base_url=llm_config.base_url,
        api_key=llm_config.api_key,
        temperature=0.0,
        timeout=config.timeout_seconds,
        max_tokens=llm_config.max_output_tokens,
    )

    prompt = ENRICHER_PROMPT_TEMPLATE.format(
        target_date=target_date,
        copilot_chat_summary=copilot_summary or "（データなし）",
        git_commits_summary=git_summary or "（データなし）",
        terminal_logs_summary=terminal_summary or "（データなし）",
        project_hints_text=project_hints_text or "（プロジェクトヒントなし）",
    )

    logger.info("[Enricher] LLMによるクロスリファレンス処理中...")
    progress_log.append("[Enricher] LLMによるクロスリファレンス処理中...")

    from dev_log_daily.llm.client import call_llm_with_retry

    messages = [
        {"role": "system", "content": ENRICHER_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    result = await call_llm_with_retry(llm, messages)

    # JSON パースを試みる
    enriched = _parse_enriched_json(result)

    # project_activities を enriched から抽出
    project_activities = enriched.get("projects", {})
    state["project_activities"] = project_activities

    state["enriched_data"] = enriched
    logger.info("[Enricher] データ補完が完了しました（%d プロジェクト）", len(project_activities))
    progress_log.append(
        f"[Enricher] データ補完が完了しました（{len(project_activities)} プロジェクト）"
    )

    state["errors"] = errors
    state["progress_log"] = progress_log

    return state


def _get_parsed_summary(state: DailyState, field: str) -> str:
    """DailyState から指定フィールドの解析サマリーを取得する."""
    parsed = state.get(field, {})
    if isinstance(parsed, dict):
        return parsed.get("summary", "")
    return ""


def _collect_project_hints(state: DailyState) -> list[dict]:
    """全データソースのパース結果から project_hints を収集する.

    Args:
        state: 現在の DailyState

    Returns:
        全データソースの project_hints を統合したリスト
    """
    hints: list[dict] = []
    for field in ("copilot_chat_parsed", "git_commits_parsed", "terminal_logs_parsed"):
        parsed = state.get(field, {})
        if isinstance(parsed, dict):
            field_hints = parsed.get("project_hints", [])
            hints.extend(field_hints)
    return hints


def _format_project_hints(hints: list[dict]) -> str:
    """プロジェクトヒントのリストを LLM 入力用の文字列に整形する.

    Args:
        hints: プロジェクトヒントのリスト

    Returns:
        整形された文字列
    """
    if not hints:
        return ""
    lines: list[str] = ["### プロジェクトヒント一覧"]
    for hint in hints:
        source = hint.get("source", "不明")
        candidate = hint.get("candidate_name", "不明")
        summary = hint.get("activity_summary", "")
        summary_preview = (summary[:100] + "...") if len(summary) > 100 else summary
        lines.append(f"- [{source}] {candidate}: {summary_preview}")
    return "\n".join(lines)


def _parse_enriched_json(result: str) -> dict:
    """LLM の出力から JSON をパースする.

    Args:
        result: LLM の出力文字列

    Returns:
        パース済みの enriched_data dict
    """
    import json
    import re

    # JSON コードブロックを探す
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", result, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = result

    # 中括弧で囲まれた部分を抽出
    brace_match = re.search(r"\{.*\}", json_str, re.DOTALL)
    if brace_match:
        json_str = brace_match.group(0)

    try:
        parsed = json.loads(json_str)
        # report_metadata がなければデフォルト値を設定
        if "report_metadata" not in parsed:
            parsed["report_metadata"] = {
                "mood": "productive",
                "energy": 4,
                "tags": ["DevLogDaily"],
                "project_moods": {},
            }
        return parsed
    except json.JSONDecodeError:
        # JSON パース失敗時はテキストをそのまま格納
        return {
            "cross_references": [],
            "contradictions": [],
            "completions": [],
            "context": "",
            "key_activities": [],
            "projects": {},
            "report_metadata": {
                "mood": "productive",
                "energy": 4,
                "tags": ["DevLogDaily"],
                "project_moods": {},
            },
            "raw_output": result,
        }
