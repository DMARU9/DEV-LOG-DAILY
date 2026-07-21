"""DailyState TypedDict — パイプライン全ノードで共有される状態定義."""

from typing import TypedDict


class DailyState(TypedDict):
    """LangGraph パイプライン全体で共有される状態.

    各ノード（Collector → Parser → Enricher → Reporter）が
    この状態を介してデータを受け渡す。
    """

    # 日報対象日（YYYY-MM-DD 形式）
    target_date: str

    # --- 収集結果（Collector ノード出力 / *_raw） ---
    copilot_chat_raw: dict
    """Copilotチャット収集結果（ファイルリスト等の dict）. 未収集時は {}."""
    git_commits_raw: dict
    """Gitコミット収集結果. 未収集時は {}."""
    terminal_logs_raw: dict
    """ターミナル履歴収集結果. 未収集時は {}."""

    # --- 解析結果（Parser ノード出力 / *_parsed） ---
    copilot_chat_parsed: dict
    """Copilotチャット解析結果. 未解析時は {}."""
    git_commits_parsed: dict
    """Gitコミット解析結果. 未解析時は {}."""
    terminal_logs_parsed: dict
    """ターミナル履歴解析結果. 未解析時は {}."""

    # --- プロジェクトヒント（Parser ノード出力） ---
    project_hints: list[dict]
    """全 Parser から収集された ProjectHint のリスト.
    各 hint は {source, candidate_name, activity_summary} 形式. 未収集時は [].

    Parser ノード完了後に設定される。Enricher が project_activities 生成の
    入力として使用する。"""

    # --- プロジェクト活動（Enricher ノード出力） ---
    project_activities: dict[str, dict]
    """Enricher が正規化したプロジェクト活動辞書.
    キーはプロジェクト名、値は ProjectActivity の dict 表現. 未処理時は {}.

    Reporter が日報生成の主要入力として使用する。"""

    # --- 補完結果（Enricher ノード出力） ---
    enriched_data: dict
    """Enricher によるクロスリファレンス・補完結果. 未処理時は {}."""

    # --- 最終出力（Reporter ノード出力） ---
    daily_report: str
    """生成された日報の完全な Markdown テキスト. 未生成時は ''."""

    # --- エラー・進捗管理 ---
    errors: list[dict]
    """パイプライン実行中に発生したエラーのリスト.

    各エントリは {source, stage, error_type, message} の形式.
    """
    progress_log: list[str]
    """各ノードの進捗ログメッセージ（標準出力用）."""
