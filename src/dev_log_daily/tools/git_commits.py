"""Gitコミットツール — Gitリポジトリのコミット収集・解析.

設定の git_root_dir 配下を再帰探索し全Gitリポジトリの対象日コミットを収集（collect）、
LLMでコミットメッセージを解析（parse）する。
"""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_openai import ChatOpenAI

from dev_log_daily.config.schema import DataSourceConfig
from dev_log_daily.tools.base import CollectedLog, DataSourceTool, ParsedData

logger = logging.getLogger(__name__)


class GitCommitsTool(DataSourceTool):
    """Gitコミットツール.

    指定された親ディレクトリ配下の全 Git リポジトリを再帰検出し、
    対象日付のコミットを収集する。LLM でコミットメッセージを解析する。
    """

    name: str = "git_commits"

    def collect(
        self,
        target_date: str,
        config: DataSourceConfig | dict[str, Any],
    ) -> CollectedLog:
        """Gitリポジトリ親ディレクトリ配下を再帰探索し、対象日のコミットを収集する.

        Args:
            target_date: 対象日（YYYY-MM-DD）
            config: データソース設定

        Returns:
            収集結果（CollectedLog）
        """
        git_root_str = (
            config.get("git_root_dir") if isinstance(config, dict) else config.git_root_dir
        )
        git_root = Path(git_root_str or "")

        if not git_root.exists():
            logger.warning("Git親ディレクトリが存在しません: %s", git_root)
            return CollectedLog(
                source=self.name,
                target_date=target_date,
                files=[],
                error=f"Git親ディレクトリが存在しません: {git_root}",
            )

        if not git_root.is_dir():
            logger.warning("指定されたパスはディレクトリではありません: %s", git_root)
            return CollectedLog(
                source=self.name,
                target_date=target_date,
                files=[],
                error=f"指定されたパスはディレクトリではありません: {git_root}",
            )

        # Git リポジトリを再帰検出
        git_dirs = self._find_git_repos(git_root)
        if not git_dirs:
            logger.info("Gitリポジトリが見つかりませんでした: %s", git_root)
            return CollectedLog(
                source=self.name,
                target_date=target_date,
                files=[],
            )

        collected_files: list[dict] = []
        for repo_dir in git_dirs:
            commits = self._get_commits_for_date(repo_dir, target_date)
            if commits:
                collected_files.append(
                    {
                        "path": str(repo_dir),
                        "source": self.name,
                        "timestamp": datetime.now().isoformat(),
                        "commits": commits,
                        "commit_count": len(commits),
                    }
                )

        logger.info(
            "Gitコミット収集完了: %d リポジトリ, %d コミット",
            len(collected_files),
            sum(f.get("commit_count", 0) for f in collected_files),
        )

        return CollectedLog(
            source=self.name,
            target_date=target_date,
            files=collected_files,
        )

    def _find_git_repos(self, root_dir: Path) -> list[Path]:
        """指定ディレクトリ配下の Git リポジトリを再帰検出する.

        .git ディレクトリの存在で Git リポジトリを判定する。

        Args:
            root_dir: 検索起点ディレクトリ

        Returns:
            Git リポジトリのルートディレクトリのリスト
        """
        repos: list[Path] = []

        # ルート自体がリポジトリの場合
        if (root_dir / ".git").is_dir():
            repos.append(root_dir)

        # サブディレクトリを再帰検索（深さ制限: 5）
        try:
            for level in range(1, 6):
                # glob で depth 指定して検索
                pattern = "*/" * level + ".git"
                for git_dir in root_dir.glob(pattern):
                    if git_dir.is_dir():
                        repos.append(git_dir.parent)
        except PermissionError as e:
            logger.warning("ディレクトリ検索中に権限エラー: %s", e)

        # 重複除去とソート
        return sorted(set(repos))

    def _get_commits_for_date(self, repo_path: Path, target_date: str) -> list[dict]:
        """指定されたリポジトリから対象日付のコミットを取得する.

        Args:
            repo_path: Git リポジトリのパス
            target_date: 対象日（YYYY-MM-DD）

        Returns:
            コミット情報のリスト
        """
        git_cmd = ["git", "-C", str(repo_path)]

        # リポジトリが有効か確認
        try:
            subprocess.run(
                [*git_cmd, "rev-parse", "--git-dir"],
                capture_output=True,
                check=True,
                timeout=10,
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return []

        # 対象日付のコミットを取得
        # --after と --before で日付範囲を指定（システムローカルタイムゾーンを使用）
        from dev_log_daily.utils.date import get_system_timezone

        local_tz = get_system_timezone()
        offset_minutes = int(local_tz.utcoffset(None).total_seconds() / 60)  # type: ignore[union-attr]
        offset_hours = offset_minutes // 60
        offset_mins = abs(offset_minutes) % 60
        sign = "+" if offset_hours >= 0 else "-"
        tz_str = f"{sign}{abs(offset_hours):02d}:{offset_mins:02d}"
        since = f"{target_date}T00:00:00{tz_str}"
        until = f"{target_date}T23:59:59{tz_str}"

        try:
            result = subprocess.run(
                [
                    *git_cmd,
                    "log",
                    "--all",
                    f"--after={since}",
                    f"--before={until}",
                    "--format=%H|||%an|||%ai|||%s",
                    "--no-merges",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.warning("Gitコミット取得エラー (%s): %s", repo_path, e)
            return []

        commits: list[dict] = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("|||", 3)
            if len(parts) >= 4:
                commit_hash, author, date_str, message = parts
                commits.append(
                    {
                        "hash": commit_hash.strip(),
                        "author": author.strip(),
                        "date": date_str.strip(),
                        "message": message.strip(),
                    }
                )

        return commits

    def _extract_project_hints(self, raw: CollectedLog, analysis: str) -> list[dict]:
        """収集結果からプロジェクトヒントを抽出する.

        各リポジトリのパス basename を candidate_name とし、LLM 解析結果の
        サマリーを activity_summary として格納した ProjectHint リストを生成する。

        Args:
            raw: 収集結果（CollectedLog）
            analysis: LLM による解析結果サマリー

        Returns:
            プロジェクトヒントのリスト
        """
        from pathlib import Path

        hints: list[dict] = []
        seen_repos: set[str] = set()
        for file_info in raw.files:
            repo_path = file_info.get("path", "")
            if repo_path:
                repo_name = Path(repo_path).name
                if repo_name and repo_name not in seen_repos:
                    seen_repos.add(repo_name)
                    hints.append(
                        {
                            "source": "git_commits",
                            "candidate_name": repo_name,
                            "activity_summary": analysis,
                        }
                    )
        return hints

    async def parse(
        self,
        raw: CollectedLog,
        llm: ChatOpenAI,
    ) -> ParsedData:
        """収集したコミットログを LLM で解析する.

        Args:
            raw: 収集結果（CollectedLog）
            llm: LLM インスタンス

        Returns:
            解析結果（ParsedData）
        """
        if raw.is_empty:
            logger.info("Gitコミットログが空のため解析をスキップします")
            return ParsedData(source=self.name)

        text_parts: list[str] = []
        for file_info in raw.files:
            repo_path = file_info.get("path", "")
            commits = file_info.get("commits", [])
            for commit in commits:
                entry = (
                    f"リポジトリ: {repo_path}\n"
                    f"ハッシュ: {commit.get('hash', '')}\n"
                    f"作者: {commit.get('author', '')}\n"
                    f"日時: {commit.get('date', '')}\n"
                    f"メッセージ: {commit.get('message', '')}\n"
                )
                text_parts.append(entry)

        text = "\n---\n".join(text_parts)

        from dev_log_daily.llm.chunking import estimate_tokens, process_with_chunking
        from dev_log_daily.prompts.system import COLLECTOR_SYSTEM_PROMPT
        from dev_log_daily.prompts.templates import (
            COLLECTOR_GIT_COMMITS_PROMPT,
            REDUCE_SUMMARIES_PROMPT,
        )

        estimated_tokens = estimate_tokens(text)

        map_prompt = COLLECTOR_GIT_COMMITS_PROMPT.format(
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
                "repo_count": len(raw.files),
                "commit_count": sum(f.get("commit_count", 0) for f in raw.files),
            },
            token_count=estimated_tokens,
            project_hints=project_hints,
        )
