"""DataSourceTool 抽象基底クラス — collect/parse インターフェース定義."""

from __future__ import annotations

from abc import ABC, abstractmethod

from langchain_openai import ChatOpenAI

from dev_log_daily.config.schema import DataSourceConfig
from dev_log_daily.llm.chunking import DEFAULT_CONTEXT_WINDOW


class CollectedLog:
    """収集ログ — collect() の戻り値として使用するデータクラス."""

    def __init__(
        self,
        source: str,
        target_date: str,
        files: list[dict] | None = None,
        workspaces: list[dict] | None = None,
        error: str | None = None,
        collected_at: str | None = None,
    ) -> None:
        self.source = source
        self.target_date = target_date
        self.files = files or []
        self.workspaces = workspaces or []
        self.error = error
        self.collected_at = collected_at or ""

    def to_dict(self) -> dict:
        """dict 形式に変換する（DailyState 格納用）."""
        return {
            "source": self.source,
            "target_date": self.target_date,
            "files": self.files,
            "workspaces": self.workspaces,
            "error": self.error,
            "collected_at": self.collected_at,
        }

    @property
    def is_empty(self) -> bool:
        """収集結果が空かどうか."""
        return len(self.files) == 0 and len(self.workspaces) == 0

    @property
    def workspace_count(self) -> int:
        """収集されたワークスペース数を返す."""
        return len(self.workspaces)


class ParsedData:
    """解析結果 — parse() の戻り値として使用するデータクラス."""

    def __init__(
        self,
        source: str,
        summary: str = "",
        structured_data: dict | None = None,
        token_count: int = 0,
        chunks_processed: int = 0,
        error: str | None = None,
        project_hints: list[dict] | None = None,
    ) -> None:
        self.source = source
        self.summary = summary
        self.structured_data = structured_data or {}
        self.token_count = token_count
        self.chunks_processed = chunks_processed
        self.error = error
        self.project_hints = project_hints or []

    def to_dict(self) -> dict:
        """dict 形式に変換する（DailyState 格納用）."""
        return {
            "source": self.source,
            "summary": self.summary,
            "structured_data": self.structured_data,
            "token_count": self.token_count,
            "chunks_processed": self.chunks_processed,
            "error": self.error,
            "project_hints": self.project_hints,
        }

    @property
    def is_empty(self) -> bool:
        """解析結果が空（有効なデータを含まない）かどうか."""
        return not self.summary and not self.structured_data


class DataSourceTool(ABC):
    """データソースツールの抽象基底クラス.

    全データソース（Copilotチャット・Gitコミット・ターミナル履歴）は
    このクラスを継承し、collect() と parse() を実装する。
    """

    name: str = ""
    """ツール名（例: copilot_chat, git_commits, terminal_logs）"""

    context_window: int = DEFAULT_CONTEXT_WINDOW
    """チャンク分割時のコンテキストウィンドウサイズ。LLMのmax_input_tokensから設定。"""

    @abstractmethod
    def collect(
        self,
        target_date: str,
        config: DataSourceConfig,
    ) -> CollectedLog:
        """対象日のデータを収集する.

        Args:
            target_date: 対象日（YYYY-MM-DD）
            config: データソース設定

        Returns:
            収集結果（CollectedLog）
        """
        ...

    @abstractmethod
    async def parse(
        self,
        raw: CollectedLog,
        llm: ChatOpenAI,
    ) -> ParsedData:
        """収集したデータを LLM で解析する.

        Args:
            raw: 収集結果
            llm: LLM インスタンス

        Returns:
            解析結果（ParsedData）
        """
        ...
