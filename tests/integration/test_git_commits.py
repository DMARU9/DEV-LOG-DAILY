"""Gitコミットツール結合テスト.

再帰的リポジトリ検出、コミット収集・解析、日付フィルタリングを検証する。

注: このテストはツール実装（T023）より先に作成される。初期状態では
ツールモジュールが未実装のため ImportError で失敗する想定。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# ツールが実装される前は ImportError で失敗する（TDD）
try:
    from dev_log_daily.tools.git_commits import GitCommitsTool

    HAS_TOOL = True
except (ImportError, ModuleNotFoundError):
    HAS_TOOL = False

pytestmark = pytest.mark.skipif(not HAS_TOOL, reason="GitCommitsTool 未実装")


@pytest.fixture
def tool() -> GitCommitsTool:
    """GitCommitsTool のインスタンス."""
    return GitCommitsTool()


class TestGitCommitsCollect:
    """GitCommitsTool.collect() の結合テスト."""

    def test_collect_detects_repos_recursively(
        self,
        tool: GitCommitsTool,
        sample_git_repo: str,
        config_for_tools: dict,
    ):
        """collect() が親ディレクトリ配下の全Gitリポジトリを再帰検出すること."""
        config_for_tools["data_sources"]["git_root_dir"] = sample_git_repo
        result = tool.collect("2026-06-19", config_for_tools["data_sources"])
        assert result is not None
        assert result.source == "git_commits"
        assert result.target_date == "2026-06-19"
        assert not result.is_empty
        assert result.error is None
        # 2つのリポジトリ（project-a, nested/project-b）が検出される
        # 各リポジトリに対象日付のコミットが2件ずつある
        assert len(result.files) >= 2

    def test_collect_filters_commits_by_date(
        self,
        tool: GitCommitsTool,
        sample_git_repo: str,
        config_for_tools: dict,
    ):
        """collect() が対象日付のコミットのみを収集すること."""
        config_for_tools["data_sources"]["git_root_dir"] = sample_git_repo
        result = tool.collect("2026-06-19", config_for_tools["data_sources"])
        assert not result.is_empty
        for file_info in result.files:
            assert "commits" in file_info
            for commit in file_info["commits"]:
                # 各コミットの日付が対象日付であることを確認
                assert "2026-06-19" in commit.get("date", "")

    def test_collect_excludes_other_date_commits(
        self,
        tool: GitCommitsTool,
        sample_git_repo: str,
        config_for_tools: dict,
    ):
        """collect() が異なる日付のコミットを除外すること."""
        config_for_tools["data_sources"]["git_root_dir"] = sample_git_repo
        result = tool.collect("2026-06-19", config_for_tools["data_sources"])
        assert not result.is_empty
        all_commits: list[str] = []
        for file_info in result.files:
            for commit in file_info.get("commits", []):
                all_commits.append(commit.get("message", ""))
        # "Old commit from yesterday" は 2026-06-18 のコミットなので含まれない
        assert "Old commit from yesterday" not in all_commits

    def test_collect_no_git_repos(
        self,
        tool: GitCommitsTool,
        temp_dir: str,
        config_for_tools: dict,
    ):
        """collect() がGitリポジトリ不在のディレクトリに対して空の結果を返すこと."""
        empty_dir = temp_dir + "/no_repos"
        Path(empty_dir).mkdir(parents=True, exist_ok=True)

        config_for_tools["data_sources"]["git_root_dir"] = empty_dir
        result = tool.collect("2026-06-19", config_for_tools["data_sources"])
        assert result is not None
        assert result.is_empty
        assert result.error is None

    def test_collect_nonexistent_directory(
        self,
        tool: GitCommitsTool,
        config_for_tools: dict,
    ):
        """collect() が存在しないディレクトリに対してエラーを返すこと."""
        config_for_tools["data_sources"]["git_root_dir"] = "/nonexistent/path"
        result = tool.collect("2026-06-19", config_for_tools["data_sources"])
        assert result is not None
        assert result.is_empty
        assert result.error is not None

    def test_collect_commit_metadata_complete(
        self,
        tool: GitCommitsTool,
        sample_git_repo: str,
        config_for_tools: dict,
    ):
        """collect() が各コミットの完全なメタデータを収集すること."""
        config_for_tools["data_sources"]["git_root_dir"] = sample_git_repo
        result = tool.collect("2026-06-19", config_for_tools["data_sources"])
        assert not result.is_empty
        for file_info in result.files:
            for commit in file_info.get("commits", []):
                assert "hash" in commit
                assert "message" in commit
                assert "author" in commit
                assert "date" in commit
                assert commit["hash"]  # 空でない
                assert commit["message"]  # 空でない


class TestGitCommitsParse:
    """GitCommitsTool.parse() の結合テスト."""

    @pytest.fixture
    def collected_log(
        self,
        tool: GitCommitsTool,
        sample_git_repo: str,
        config_for_tools: dict,
    ):
        """収集済みログデータ."""
        config_for_tools["data_sources"]["git_root_dir"] = sample_git_repo
        return tool.collect("2026-06-19", config_for_tools["data_sources"])

    @pytest.mark.asyncio
    async def test_parse_returns_structured_summary(
        self,
        tool: GitCommitsTool,
        collected_log,
    ):
        """parse() がLLM解析後に構造化されたサマリーを返すこと."""
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content="解析サマリー: 4件のコミット\n主な変更: プロジェクト初期化、機能追加"
            )
        )

        result = await tool.parse(collected_log, mock_llm)
        assert result is not None
        assert result.source == "git_commits"
        assert result.summary != ""
        assert result.error is None

    @pytest.mark.asyncio
    async def test_parse_empty_log_returns_empty(
        self,
        tool: GitCommitsTool,
    ):
        """parse() が空のログに対して空の解析結果を返すこと."""
        from dev_log_daily.tools.base import CollectedLog

        empty_log = CollectedLog(
            source="git_commits",
            target_date="2026-06-19",
            files=[],
        )
        mock_llm = AsyncMock()

        result = await tool.parse(empty_log, mock_llm)
        assert result.is_empty

    @pytest.mark.asyncio
    async def test_parse_handles_llm_error(
        self,
        tool: GitCommitsTool,
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
