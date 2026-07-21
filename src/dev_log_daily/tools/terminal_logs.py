"""ターミナル履歴ツール — ターミナル操作履歴の収集・解析.

ターミナル履歴ディレクトリから対象日のJSONLファイルを収集（collect）、
LLMで操作内容を解析（parse）する。設定可能なタイムアウト（デフォルト600秒）を適用。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_openai import ChatOpenAI

from dev_log_daily.config.schema import DataSourceConfig
from dev_log_daily.tools.base import CollectedLog, DataSourceTool, ParsedData
from dev_log_daily.utils.file import find_files, read_text

logger = logging.getLogger(__name__)


class TerminalLogsTool(DataSourceTool):
    """ターミナル履歴ツール.

    ターミナル履歴ディレクトリ内の日付JSONLファイルから対象日の
    コマンド履歴を収集・解析する。巨大ファイルは分割処理される。
    """

    name: str = "terminal_logs"

    def collect(
        self,
        target_date: str,
        config: DataSourceConfig | dict[str, Any],
    ) -> CollectedLog:
        """ターミナル履歴ディレクトリから対象日のJSONLファイルを収集する.

        Args:
            target_date: 対象日（YYYY-MM-DD）
            config: データソース設定

        Returns:
            収集結果（CollectedLog）
        """
        history_dir_str = (
            config.get("terminal_history_dir")
            if isinstance(config, dict)
            else config.terminal_history_dir
        )
        history_dir = Path(history_dir_str or "")

        if not history_dir.exists():
            logger.warning("ターミナル履歴ディレクトリが存在しません: %s", history_dir)
            return CollectedLog(
                source=self.name,
                target_date=target_date,
                files=[],
                error=f"ターミナル履歴ディレクトリが存在しません: {history_dir}",
            )

        if not history_dir.is_dir():
            logger.warning("指定されたパスはディレクトリではありません: %s", history_dir)
            return CollectedLog(
                source=self.name,
                target_date=target_date,
                files=[],
                error=f"指定されたパスはディレクトリではありません: {history_dir}",
            )

        # 再帰的に history_YYYY-MM-DD.jsonl を検索
        target_filename = f"history_{target_date}.jsonl"
        matching_files = find_files(history_dir, pattern=f"**/{target_filename}")

        if not matching_files:
            logger.info(
                "対象日の履歴ファイルが見つかりません: %s (in %s)", target_filename, history_dir
            )
            return CollectedLog(
                source=self.name,
                target_date=target_date,
                files=[],
            )

        collected_files: list[dict] = []
        total_entries = 0

        for file_path in matching_files:
            try:
                content = read_text(str(file_path))
            except Exception as e:
                logger.warning("履歴ファイル読み込みエラー: %s: %s", file_path, e)
                continue

            if not content.strip():
                logger.info("空の履歴ファイルをスキップ: %s", file_path)
                continue

            entries = self._parse_jsonl(content, target_date)
            if not entries:
                continue

            collected_files.append(
                {
                    "path": str(file_path),
                    "source": self.name,
                    "timestamp": datetime.now().isoformat(),
                    "entries": entries,
                    "entry_count": len(entries),
                    "total_lines": len(content.split("\n")),
                }
            )
            total_entries += len(entries)

        logger.info(
            "ターミナル履歴収集完了: %d ファイル, %d エントリ (対象: %s)",
            len(collected_files),
            total_entries,
            target_date,
        )

        return CollectedLog(
            source=self.name,
            target_date=target_date,
            files=collected_files,
        )

    def _parse_jsonl(self, content: str, target_date: str) -> list[dict]:
        """JSONL 形式の履歴をパースし、対象日付のエントリを抽出する.

        Args:
            content: 履歴ファイルの内容（JSONL）
            target_date: 対象日（YYYY-MM-DD）

        Returns:
            対象日付のエントリのリスト
        """
        entries: list[dict] = []
        for line_num, line in enumerate(content.split("\n"), 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                timestamp = data.get("timestamp", "")
                if timestamp.startswith(target_date):
                    entries.append(
                        {
                            "line": line_num,
                            "timestamp": timestamp,
                            "command": data.get("command", ""),
                            "exit_code": data.get("exit_code"),
                            "cwd": data.get("cwd", ""),
                            "git_branch": data.get("git_branch", ""),
                        }
                    )
            except json.JSONDecodeError:
                logger.warning("JSONL パースエラー (行 %d): スキップします", line_num)
                continue
        return entries

    def _extract_project_hints(self, raw: CollectedLog, analysis: str) -> list[dict]:
        """収集結果からプロジェクトヒントを抽出する.

        各エントリの cwd ディレクトリ名を candidate_name とし、LLM 解析結果の
        サマリーを activity_summary として格納した ProjectHint リストを生成する。
        cwd が空のエントリは candidate_name="プロジェクト不明" として扱う。

        Args:
            raw: 収集結果（CollectedLog）
            analysis: LLM による解析結果サマリー

        Returns:
            プロジェクトヒントのリスト
        """
        from pathlib import Path

        hints: list[dict] = []
        seen_dirs: set[str] = set()
        for file_info in raw.files:
            entries = file_info.get("entries", [])
            for entry in entries:
                cwd = entry.get("cwd", "")
                if cwd:
                    dir_name = Path(cwd).name
                else:
                    dir_name = "プロジェクト不明"
                if dir_name not in seen_dirs:
                    seen_dirs.add(dir_name)
                    hints.append(
                        {
                            "source": "terminal_logs",
                            "candidate_name": dir_name,
                            "activity_summary": analysis,
                        }
                    )
        return hints

    async def parse(
        self,
        raw: CollectedLog,
        llm: ChatOpenAI,
    ) -> ParsedData:
        """収集したターミナル履歴を LLM で解析する.

        Args:
            raw: 収集結果（CollectedLog）
            llm: LLM インスタンス

        Returns:
            解析結果（ParsedData）
        """
        if raw.is_empty:
            logger.info("ターミナル履歴が空のため解析をスキップします")
            return ParsedData(source=self.name)

        text_parts: list[str] = []
        for file_info in raw.files:
            entries = file_info.get("entries", [])
            for entry in entries:
                timestamp = entry.get("timestamp", "")
                command = entry.get("command", "")
                cwd = entry.get("cwd", "")
                git_branch = entry.get("git_branch", "")
                # cwd/git_branch を LLM 入力に含める
                if cwd or git_branch:
                    cwd_str = cwd if cwd else "（不明）"
                    branch_str = git_branch if git_branch else "（なし）"
                    text_parts.append(f"[{timestamp}] [{cwd_str}] ({branch_str}) $ {command}")
                else:
                    text_parts.append(f"[{timestamp}] {command}")

        text = "\n".join(text_parts)

        from dev_log_daily.llm.chunking import estimate_tokens, process_with_chunking
        from dev_log_daily.prompts.system import COLLECTOR_SYSTEM_PROMPT
        from dev_log_daily.prompts.templates import (
            COLLECTOR_TERMINAL_LOGS_PROMPT,
            REDUCE_SUMMARIES_PROMPT,
        )

        estimated_tokens = estimate_tokens(text)

        map_prompt = COLLECTOR_TERMINAL_LOGS_PROMPT.format(
            target_date=raw.target_date,
            text="{text}",
        )

        analysis, chunks_processed = await process_with_chunking(
            llm=llm,
            text=text,
            system_prompt=COLLECTOR_SYSTEM_PROMPT,
            map_prompt_template=map_prompt,
            reduce_prompt_template=REDUCE_SUMMARIES_PROMPT,
            context_window=self.context_window,
        )

        # プロジェクトヒント抽出
        project_hints = self._extract_project_hints(raw, analysis)

        return ParsedData(
            source=self.name,
            summary=analysis,
            chunks_processed=chunks_processed,
            structured_data={
                "file_count": len(raw.files),
                "entry_count": sum(f.get("entry_count", 0) for f in raw.files),
            },
            token_count=estimated_tokens,
            project_hints=project_hints,
        )
