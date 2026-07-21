"""ターミナル履歴ツール結合テスト.

日付ごとのJSONL履歴ファイル読み込み・解析、日付フィルタリング、
巨大ファイル分割処理、ディレクトリ不在処理を検証する。
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# ツールが実装される前は ImportError で失敗する（TDD）
try:
    from dev_log_daily.tools.terminal_logs import TerminalLogsTool

    HAS_TOOL = True
except (ImportError, ModuleNotFoundError):
    HAS_TOOL = False

pytestmark = pytest.mark.skipif(not HAS_TOOL, reason="TerminalLogsTool 未実装")


@pytest.fixture
def tool() -> TerminalLogsTool:
    """TerminalLogsTool のインスタンス."""
    return TerminalLogsTool()


class TestTerminalLogsCollect:
    """TerminalLogsTool.collect() の結合テスト."""

    def test_collect_reads_terminal_history(
        self,
        tool: TerminalLogsTool,
        sample_terminal_dir: str,
        config_for_tools: dict,
    ):
        """collect() がターミナル履歴ディレクトリからJSONLを読み込むこと."""
        config_for_tools["data_sources"]["terminal_history_dir"] = sample_terminal_dir
        result = tool.collect("2026-06-19", config_for_tools["data_sources"])
        assert result is not None
        assert result.source == "terminal_logs"
        assert result.target_date == "2026-06-19"
        assert not result.is_empty
        assert result.error is None

    def test_collect_filters_commands_by_date(
        self,
        tool: TerminalLogsTool,
        sample_terminal_dir: str,
        config_for_tools: dict,
    ):
        """collect() が対象日付のコマンドのみをフィルタリングすること."""
        config_for_tools["data_sources"]["terminal_history_dir"] = sample_terminal_dir
        result = tool.collect("2026-06-19", config_for_tools["data_sources"])
        assert not result.is_empty
        for file_info in result.files:
            for entry in file_info.get("entries", []):
                assert "2026-06-19" in entry.get("timestamp", "")

    def test_collect_excludes_other_dates(
        self,
        tool: TerminalLogsTool,
        sample_terminal_dir: str,
        config_for_tools: dict,
    ):
        """collect() が異なる日付のコマンドを除外すること。

        異なる日付のJSONLファイルからは収集せず、指定日のファイルのみを
        読み込むことを確認する。
        """
        config_for_tools["data_sources"]["terminal_history_dir"] = sample_terminal_dir
        # 2026-06-18 のデータのみを収集
        result = tool.collect("2026-06-18", config_for_tools["data_sources"])
        assert not result.is_empty
        commands: list[str] = []
        for file_info in result.files:
            for entry in file_info.get("entries", []):
                commands.append(entry.get("command", ""))
        # 2026-06-18 のコマンドのみが含まれる
        assert "npm install" in commands
        # 2026-06-19 のコマンドは含まれない
        assert "docker compose up -d" not in commands

    def test_collect_returns_no_data_for_date_without_commands(
        self,
        tool: TerminalLogsTool,
        sample_terminal_dir: str,
        config_for_tools: dict,
    ):
        """collect() がファイルのない日付に対して空の結果を返すこと."""
        config_for_tools["data_sources"]["terminal_history_dir"] = sample_terminal_dir
        result = tool.collect("2025-01-01", config_for_tools["data_sources"])
        assert result.is_empty
        assert result.error is None

    def test_collect_missing_directory(
        self,
        tool: TerminalLogsTool,
        config_for_tools: dict,
    ):
        """collect() が存在しないディレクトリに対してエラーを返すこと."""
        config_for_tools["data_sources"]["terminal_history_dir"] = "/nonexistent/directory"
        result = tool.collect("2026-06-19", config_for_tools["data_sources"])
        assert result is not None
        assert result.is_empty
        assert result.error is not None

    def test_collect_empty_file(
        self,
        tool: TerminalLogsTool,
        temp_dir: str,
        config_for_tools: dict,
    ):
        """collect() が空のJSONLファイルを正しく処理すること."""
        history_dir = Path(temp_dir) / "terminal_history"
        history_dir.mkdir(parents=True, exist_ok=True)
        (history_dir / "history_2026-06-19.jsonl").write_text("", encoding="utf-8")
        config_for_tools["data_sources"]["terminal_history_dir"] = str(history_dir)

        result = tool.collect("2026-06-19", config_for_tools["data_sources"])
        assert result.is_empty
        assert result.error is None

    def test_collect_large_file_chunking(
        self,
        tool: TerminalLogsTool,
        temp_dir: str,
        config_for_tools: dict,
    ):
        """collect() が巨大なJSONLファイルを処理できること.

        大量のエントリを含むファイルを作成し、適切に収集されることを確認する。
        """
        history_dir = Path(temp_dir) / "terminal_history"
        history_dir.mkdir(parents=True, exist_ok=True)

        lines = []
        for i in range(1000):
            entry = {
                "timestamp": f"2026-06-19T{i // 60:02d}:{i % 60:02d}:00+09:00",
                "command": f"command_{i}: git status",
                "exit_code": 0,
                "cwd": "/home/user/project",
                "git_branch": "main",
            }
            lines.append(json.dumps(entry, ensure_ascii=False))
        (history_dir / "history_2026-06-19.jsonl").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

        config_for_tools["data_sources"]["terminal_history_dir"] = str(history_dir)
        result = tool.collect("2026-06-19", config_for_tools["data_sources"])
        assert not result.is_empty
        # 大量エントリが含まれていることを確認
        total_entries = sum(len(file_info.get("entries", [])) for file_info in result.files)
        assert total_entries == 1000

    def test_collect_metadata_includes_entry_details(
        self,
        tool: TerminalLogsTool,
        sample_terminal_dir: str,
        config_for_tools: dict,
    ):
        """collect() が各エントリにコマンド・タイムスタンプ等を含むこと."""
        config_for_tools["data_sources"]["terminal_history_dir"] = sample_terminal_dir
        result = tool.collect("2026-06-19", config_for_tools["data_sources"])
        assert not result.is_empty
        for file_info in result.files:
            for entry in file_info.get("entries", []):
                assert "command" in entry
                assert "timestamp" in entry
                assert "exit_code" in entry
                assert "cwd" in entry
                assert entry["command"]  # 空でない
                assert entry["timestamp"]  # 空でない


class TestTerminalLogsParse:
    """TerminalLogsTool.parse() の結合テスト."""

    @pytest.fixture
    def collected_log(
        self,
        tool: TerminalLogsTool,
        sample_terminal_dir: str,
        config_for_tools: dict,
    ):
        """収集済みログデータ."""
        config_for_tools["data_sources"]["terminal_history_dir"] = sample_terminal_dir
        return tool.collect("2026-06-19", config_for_tools["data_sources"])

    @pytest.mark.asyncio
    async def test_parse_returns_structured_summary(
        self,
        tool: TerminalLogsTool,
        collected_log,
    ):
        """parse() がLLM解析後に構造化されたサマリーを返すこと."""
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content="解析サマリー: 10件のコマンド\n"
                "主な操作: git操作、Python仮想環境セットアップ、Docker操作"
            )
        )

        result = await tool.parse(collected_log, mock_llm)
        assert result is not None
        assert result.source == "terminal_logs"
        assert result.summary != ""
        assert result.error is None

    @pytest.mark.asyncio
    async def test_parse_empty_log_returns_empty(
        self,
        tool: TerminalLogsTool,
    ):
        """parse() が空のログに対して空の解析結果を返すこと."""
        from dev_log_daily.tools.base import CollectedLog

        empty_log = CollectedLog(
            source="terminal_logs",
            target_date="2026-06-19",
            files=[],
        )
        mock_llm = AsyncMock()

        result = await tool.parse(empty_log, mock_llm)
        assert result.is_empty

    @pytest.mark.asyncio
    async def test_parse_handles_llm_error(
        self,
        tool: TerminalLogsTool,
        collected_log,
    ):
        """parse() がLLMエラー時にエラーを伝播すること."""
        from dev_log_daily.llm.client import LLMPermanentError

        mock_llm = AsyncMock()
        error = LLMPermanentError("LLM error")
        error.status_code = 400
        mock_llm.ainvoke = AsyncMock(side_effect=error)

        with pytest.raises(LLMPermanentError):
            await tool.parse(collected_log, mock_llm)
