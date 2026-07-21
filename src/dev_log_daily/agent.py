"""LangGraph パイプライン — Collector/Parser/Enricher/Reporter を StateGraph で接続."""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph

from dev_log_daily.config.schema import AppConfig
from dev_log_daily.llm.client import create_llm
from dev_log_daily.pipeline.collector import collector_node
from dev_log_daily.pipeline.enricher import enricher_node
from dev_log_daily.pipeline.parser import parser_node
from dev_log_daily.pipeline.reporter import reporter_node
from dev_log_daily.state import DailyState

logger = logging.getLogger(__name__)


def _validate_component_llms(config: AppConfig) -> None:
    """各コンポーネントのLLMインスタンスを生成し、未指定があれば起動時エラーとする.

    設定ファイルの llm.{component} から全コンポーネント（collector/parser/enricher/reporter）
    の LLM インスタンスを生成する。生成に失敗した場合は ValueError を送出する。

    Args:
        config: アプリケーション設定（AppConfig）

    Raises:
        ValueError: いずれかのコンポーネントのLLM設定が不正な場合
    """
    components = {
        "collector": config.llm.collector,
        "parser": config.llm.parser,
        "enricher": config.llm.enricher,
        "reporter": config.llm.reporter,
    }

    for name, llm_config in components.items():
        try:
            create_llm(
                model=llm_config.model,
                base_url=llm_config.base_url,
                api_key=llm_config.api_key,
                max_tokens=llm_config.max_output_tokens,
            )
            logger.debug("[Pipeline] llm.%s のLLMインスタンス生成成功", name)
        except Exception as e:
            raise ValueError(f"llm.{name} のLLMインスタンス生成に失敗しました: {e}") from e


def build_pipeline(config: AppConfig) -> StateGraph:
    """日報生成パイプラインを構築する.

    Collector → Parser → Enricher → Reporter の4ノードを逐次エッジで接続。
    エラー発生時の早期停止分岐を含む。

    パイプライン構築時に全コンポーネントのLLM設定を検証し、
    未指定や不正な設定があれば起動時エラーとする。

    Args:
        config: アプリケーション設定

    Returns:
        構築済みの StateGraph

    Raises:
        ValueError: いずれかのコンポーネントのLLM設定が不正な場合
    """
    # パイプライン構築時に全コンポーネントのLLM設定を検証
    _validate_component_llms(config)

    workflow = StateGraph(DailyState)

    # 同期ノード
    # type: ignore[arg-type] は LangGraph の型推論の制限による
    workflow.add_node("collector", lambda state: collector_node(state, config))  # type: ignore[arg-type]

    # 非同期ノード（LangGraph は async def を正しく認識する）
    async def _run_parser(state: DailyState) -> DailyState:
        return await parser_node(state, config)

    async def _run_enricher(state: DailyState) -> DailyState:
        return await enricher_node(state, config)

    async def _run_reporter(state: DailyState) -> DailyState:
        return await reporter_node(state, config)

    workflow.add_node("parser", _run_parser)  # type: ignore[arg-type]
    workflow.add_node("enricher", _run_enricher)  # type: ignore[arg-type]
    workflow.add_node("reporter", _run_reporter)  # type: ignore[arg-type]

    # エントリポイント設定
    workflow.set_entry_point("collector")

    # 条件付きエッジ: Collector → Parser または終了（全ソース収集失敗時）
    workflow.add_conditional_edges(
        "collector",
        lambda state: _check_collector_errors(state),
        {
            "continue": "parser",
            "all_failed": "__end__",
        },
    )

    # 条件付きエッジ: Parser → Enricher または終了（LLM永続エラー時）
    workflow.add_conditional_edges(
        "parser",
        lambda state: _check_parser_errors(state),
        {
            "continue": "enricher",
            "permanent_error": "__end__",
        },
    )

    # 条件付きエッジ: Enricher → Reporter または終了（LLMエラー時）
    workflow.add_conditional_edges(
        "enricher",
        lambda state: _check_enricher_errors(state),
        {
            "continue": "reporter",
            "error": "__end__",
        },
    )

    return workflow


async def run_pipeline(config: AppConfig, target_date: str) -> dict:
    """パイプラインを実行する.

    Args:
        config: アプリケーション設定
        target_date: 対象日（YYYY-MM-DD）

    Returns:
        パイプライン実行結果（最終 DailyState）
    """

    # 初期状態
    initial_state: DailyState = {
        "target_date": target_date,
        "copilot_chat_raw": {},
        "git_commits_raw": {},
        "terminal_logs_raw": {},
        "copilot_chat_parsed": {},
        "git_commits_parsed": {},
        "terminal_logs_parsed": {},
        "project_hints": [],
        "project_activities": {},
        "enriched_data": {},
        "daily_report": "",
        "errors": [],
        "progress_log": [],
    }

    workflow = build_pipeline(config)
    app = workflow.compile()

    # LangGraph の非同期ノード対応: ainvoke で非同期実行
    result = await app.ainvoke(initial_state)

    return result


def _check_collector_errors(state: DailyState) -> str:
    """Collector ノードの結果を評価し、次ノードまたは停止を判定する.

    Returns:
        "continue": 次のノードに進む
        "all_failed": 全ソース収集失敗により停止
    """
    errors = state.get("errors", [])

    # 全ソース収集失敗をチェック
    collector_errors = [
        e for e in errors if e.get("source") == "collector" and e.get("stage") == "collect"
    ]
    has_all_failed = any(e.get("error_type") == "AllSourcesFailed" for e in collector_errors)

    if has_all_failed:
        logger.warning("[Pipeline] 全データソース収集失敗のため停止します")
        return "all_failed"
    return "continue"


def _check_parser_errors(state: DailyState) -> str:
    """Parser ノードの結果を評価し、次ノードまたは停止を判定する.

    Returns:
        "continue": 次のノードに進む
        "permanent_error": LLM永続エラーにより停止
    """
    errors = state.get("errors", [])

    # LLM 関連エラーをチェック
    from dev_log_daily.llm.client import LLMPermanentError

    parser_errors = [e for e in errors if e.get("stage") == "parse"]
    has_permanent = any(e.get("error_type") == LLMPermanentError.__name__ for e in parser_errors)

    if has_permanent:
        logger.warning("[Pipeline] LLM永続エラーのため停止します")
        return "permanent_error"
    return "continue"


def _check_enricher_errors(state: DailyState) -> str:
    """Enricher ノードの結果を評価し、次ノードまたは停止を判定する.

    Enricher で LLM エラーが発生した場合はパイプラインを停止する。
    収集・解析済みのデータは保持されるが、日報生成までは進めない。

    Returns:
        "continue": 通常通り Reporter に進む
        "error": LLMエラーにより停止
    """
    errors = state.get("errors", [])
    enricher_errors = [e for e in errors if e.get("stage") == "enrich"]

    if enricher_errors:
        logger.warning("[Pipeline] Enricher LLMエラーのため停止します")
        return "error"
    return "continue"
