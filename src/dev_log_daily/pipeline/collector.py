"""Collector ノード — 3データソースを並列実行し収集結果を DailyState に格納."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from dev_log_daily.config.schema import AppConfig
from dev_log_daily.state import DailyState
from dev_log_daily.tools.copilot_chat import CopilotChatTool
from dev_log_daily.tools.git_commits import GitCommitsTool
from dev_log_daily.tools.terminal_logs import TerminalLogsTool

logger = logging.getLogger(__name__)


def collector_node(state: DailyState, config: AppConfig) -> DailyState:
    """Collector ノード: 全データソースを並列収集する.

    3種類のツール（CopilotChat, GitCommits, TerminalLogs）を並列実行し、
    各収集結果を DailyState の *_raw フィールドに格納する。

    個別ツールの障害は他ツールに影響させない。
    全ツール失敗時は state["errors"] にエラー情報を追加する。
    全ツールが空/スキップされた場合は空データのまま後続ノードに渡す。

    Args:
        state: 現在の DailyState
        config: アプリケーション設定（AppConfig）

    Returns:
        更新された DailyState（*_raw フィールドに収集結果を設定）
    """
    target_date = state["target_date"]
    progress_log = state.get("progress_log", [])
    errors = state.get("errors", [])
    data_sources = config.data_sources

    logger.info("[Collector] データ収集を開始します...")
    progress_log.append("[Collector] データ収集を開始します...")

    # ツール設定用 dict
    ds_config: dict = {
        "copilot_chat": {
            "workspace_storage_dirs": data_sources.copilot_chat.workspace_storage_dirs,
            "max_workspaces": data_sources.copilot_chat.max_workspaces,
        },
        "git_root_dir": data_sources.git_root_dir,
        "terminal_history_dir": data_sources.terminal_history_dir,
    }

    # 3ツールのインスタンス作成
    tools = {
        "copilot_chat": CopilotChatTool(),
        "git_commits": GitCommitsTool(),
        "terminal_logs": TerminalLogsTool(),
    }

    results: dict[str, dict] = {}
    has_data = False
    has_error = False

    # ThreadPoolExecutor で collect() を並列実行
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_map = {
            executor.submit(tool.collect, target_date, ds_config): name
            for name, tool in tools.items()
        }

        for future in as_completed(future_map):
            name = future_map[future]
            try:
                collected = future.result()
                results[name] = collected.to_dict()

                if collected.is_empty:
                    logger.info(
                        "[Collector] %s: 対象データなし",
                        _display_name(name),
                    )
                    progress_log.append(f"[Collector] {_display_name(name)}: 対象データなし")
                else:
                    file_count = len(collected.files)
                    logger.info(
                        "[Collector] %s収集完了: %d ファイル/リポジトリ",
                        _display_name(name),
                        file_count,
                    )
                    progress_log.append(
                        f"[Collector] {_display_name(name)}収集完了: {file_count} 件"
                    )
                    has_data = True

            except Exception as e:
                logger.warning(
                    "[Collector] %s収集中にエラー: %s",
                    _display_name(name),
                    e,
                )
                progress_log.append(f"[Collector] {_display_name(name)}収集エラー: {e}")
                errors.append(
                    {
                        "source": name,
                        "stage": "collect",
                        "error_type": type(e).__name__,
                        "message": str(e),
                    }
                )
                results[name] = {
                    "source": name,
                    "target_date": target_date,
                    "files": [],
                    "error": str(e),
                }
                has_error = True

    state["copilot_chat_raw"] = results.get("copilot_chat", {})
    state["git_commits_raw"] = results.get("git_commits", {})
    state["terminal_logs_raw"] = results.get("terminal_logs", {})

    if not has_data and has_error:
        # 全ツールがエラー → 停止
        error_msg = "全データソースの収集に失敗しました"
        logger.error("[Collector] %s", error_msg)
        progress_log.append(f"[Collector] {error_msg}")
        errors.append(
            {
                "source": "collector",
                "stage": "collect",
                "error_type": "AllSourcesFailed",
                "message": error_msg,
            }
        )
    elif not has_data and not has_error:
        # 全ツールが空（エラーなし）→ 後続に空データを渡す
        logger.info("[Collector] 全データソースが空/スキップされました")
        progress_log.append("[Collector] 全データソースが空/スキップされました")
    else:
        logger.info("[Collector] 全データソースの収集が完了しました")
        progress_log.append("[Collector] 全データソースの収集が完了しました")

    state["errors"] = errors
    state["progress_log"] = progress_log

    return state


def _display_name(tool_name: str) -> str:
    """ツール名を表示用に変換する."""
    names = {
        "copilot_chat": "Copilotチャットログ",
        "git_commits": "Gitコミット",
        "terminal_logs": "ターミナル履歴",
    }
    return names.get(tool_name, tool_name)
