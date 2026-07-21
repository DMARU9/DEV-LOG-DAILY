"""Parser ノード — 各データソースの収集結果を LLM 解析し *_parsed に格納."""

from __future__ import annotations

import logging

from dev_log_daily.config.schema import AppConfig
from dev_log_daily.llm.client import create_llm
from dev_log_daily.state import DailyState
from dev_log_daily.tools.base import CollectedLog
from dev_log_daily.tools.copilot_chat import CopilotChatTool
from dev_log_daily.tools.git_commits import GitCommitsTool
from dev_log_daily.tools.terminal_logs import TerminalLogsTool

logger = logging.getLogger(__name__)


async def parser_node(state: DailyState, config: AppConfig) -> DailyState:
    """Parser ノード: 収集結果を LLM で解析する.

    各データソースの収集結果（*_raw）を対応するツールの parse() で
    LLM 解析し、結果を *_parsed フィールドに格納する。

    トークン制限超過時は分割要約（Map-Reduce）を適用する。
    LLM永続エラー時は errors に記録し後続ノードで判断する。

    Args:
        state: 現在の DailyState
        config: アプリケーション設定

    Returns:
        更新された DailyState（*_parsed フィールドに解析結果を設定）
    """
    target_date = state["target_date"]
    progress_log = state.get("progress_log", [])
    errors = state.get("errors", [])
    llm_config = config.llm.parser

    logger.info("[Parser] データ解析を開始します...")
    progress_log.append("[Parser] データ解析を開始します...")

    # LLM インスタンス生成
    llm = create_llm(
        model=llm_config.model,
        base_url=llm_config.base_url,
        api_key=llm_config.api_key,
        temperature=0.0,
        timeout=config.timeout_seconds,
        max_tokens=llm_config.max_output_tokens,
    )

    # 各データソースの raw データを CollectedLog に復元
    # ツールインスタンスに context_window を設定（チャンク分割用）
    copilot_tool = CopilotChatTool()
    copilot_tool.context_window = llm_config.max_input_tokens
    git_tool = GitCommitsTool()
    git_tool.context_window = llm_config.max_input_tokens
    terminal_tool = TerminalLogsTool()
    terminal_tool.context_window = llm_config.max_input_tokens

    raw_data_sources = {
        "copilot_chat": (copilot_tool, state.get("copilot_chat_raw", {})),
        "git_commits": (git_tool, state.get("git_commits_raw", {})),
        "terminal_logs": (terminal_tool, state.get("terminal_logs_raw", {})),
    }

    async def parse_single(
        tool_name: str,
        tool: CopilotChatTool | GitCommitsTool | TerminalLogsTool,
        raw_dict: dict,
    ) -> tuple[str, dict]:
        """単一ツールの収集結果を解析する."""
        display_name = _display_name(tool_name)

        if not raw_dict or not raw_dict.get("files"):
            logger.info("[Parser] %s: データがないためスキップ", display_name)
            progress_log.append(f"[Parser] {display_name}: データがないためスキップ")
            return tool_name, {}

        # エラーが設定されている場合はスキップ
        if raw_dict.get("error"):
            logger.info(
                "[Parser] %s: 収集エラーのためスキップ: %s",
                display_name,
                raw_dict["error"],
            )
            progress_log.append(f"[Parser] {display_name}: 収集エラーのためスキップ")
            return tool_name, {}

        collected_log = CollectedLog(
            source=tool_name,
            target_date=target_date,
            files=raw_dict.get("files", []),
            error=raw_dict.get("error"),
        )

        try:
            logger.info("[Parser] %s解析中...", display_name)
            progress_log.append(f"[Parser] {display_name}解析中...")
            parsed = await tool.parse(collected_log, llm)
            logger.info("[Parser] %s解析完了", display_name)
            progress_log.append(f"[Parser] {display_name}解析完了")
            return tool_name, parsed.to_dict()
        except Exception as e:
            logger.warning("[Parser] %s解析エラー: %s", display_name, e)
            progress_log.append(f"[Parser] {display_name}解析エラー: {e}")
            errors.append(
                {
                    "source": tool_name,
                    "stage": "parse",
                    "error_type": type(e).__name__,
                    "message": str(e),
                }
            )
            return tool_name, {"source": tool_name, "error": str(e)}

    # 逐次実行（単一LLMサーバーへの同時リクエストによるタイムアウトを防止）
    for name, (tool, raw_dict) in raw_data_sources.items():
        result = await parse_single(name, tool, raw_dict)
        parsed_name, parsed_dict = result
        if parsed_name == "copilot_chat":
            state["copilot_chat_parsed"] = parsed_dict
        elif parsed_name == "git_commits":
            state["git_commits_parsed"] = parsed_dict
        elif parsed_name == "terminal_logs":
            state["terminal_logs_parsed"] = parsed_dict

    state["errors"] = errors
    state["progress_log"] = progress_log

    logger.info("[Parser] データ解析が完了しました")
    progress_log.append("[Parser] データ解析が完了しました")

    return state


def _display_name(tool_name: str) -> str:
    """ツール名を表示用に変換する."""
    names = {
        "copilot_chat": "Copilotチャットログ",
        "git_commits": "Gitコミット",
        "terminal_logs": "ターミナル履歴",
    }
    return names.get(tool_name, tool_name)
