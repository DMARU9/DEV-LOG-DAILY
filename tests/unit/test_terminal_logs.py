"""TerminalLogsTool の単体テスト.

cwd/git_branch 抽出、project_hints 生成、エッジケースを検証する。
"""

from __future__ import annotations

from dev_log_daily.tools.base import CollectedLog
from dev_log_daily.tools.terminal_logs import TerminalLogsTool


class TestExtractProjectHints:
    """_extract_project_hints のテスト."""

    def test_extracts_cwd_based_hints(self):
        """cwd からディレクトリ名を抽出して project_hints を生成すること."""
        tool = TerminalLogsTool()
        raw = CollectedLog(
            source="terminal_logs",
            target_date="2026-07-21",
            files=[
                {
                    "path": "/home/user/.local/share/dev-log-daily/history_2026-07-21.jsonl",
                    "entries": [
                        {
                            "timestamp": "2026-07-21T09:00:00",
                            "command": "cd DevLogDaily",
                            "cwd": "/home/takumi/github/DevLogDaily",
                            "git_branch": "main",
                        },
                        {
                            "timestamp": "2026-07-21T09:05:00",
                            "command": "ls",
                            "cwd": "/home/takumi/github/DevLogDaily",
                            "git_branch": "main",
                        },
                        {
                            "timestamp": "2026-07-21T10:00:00",
                            "command": "cd other-project",
                            "cwd": "/home/takumi/github/OtherProject",
                            "git_branch": "feature",
                        },
                    ],
                }
            ],
        )
        hints = tool._extract_project_hints(raw, "テストサマリー")
        # 2つのユニークなディレクトリ名があるはず
        assert len(hints) == 2
        dir_names = {h["candidate_name"] for h in hints}
        assert "DevLogDaily" in dir_names
        assert "OtherProject" in dir_names
        for hint in hints:
            assert hint["source"] == "terminal_logs"
            assert hint["activity_summary"] == "テストサマリー"

    def test_empty_cwd_becomes_unknown(self):
        """cwd が空の場合 candidate_name='プロジェクト不明' になること."""
        tool = TerminalLogsTool()
        raw = CollectedLog(
            source="terminal_logs",
            target_date="2026-07-21",
            files=[
                {
                    "path": "/tmp/history.jsonl",
                    "entries": [
                        {
                            "timestamp": "2026-07-21T09:00:00",
                            "command": "echo test",
                            "cwd": "",
                            "git_branch": "",
                        },
                    ],
                }
            ],
        )
        hints = tool._extract_project_hints(raw, "サマリー")
        assert len(hints) == 1
        assert hints[0]["candidate_name"] == "プロジェクト不明"

    def test_mixed_known_unknown_cwd(self):
        """既知と不明の cwd が混在しても正しく処理されること."""
        tool = TerminalLogsTool()
        raw = CollectedLog(
            source="terminal_logs",
            target_date="2026-07-21",
            files=[
                {
                    "path": "/tmp/history.jsonl",
                    "entries": [
                        {
                            "timestamp": "2026-07-21T09:00:00",
                            "command": "git status",
                            "cwd": "/home/user/ProjectX",
                            "git_branch": "main",
                        },
                        {
                            "timestamp": "2026-07-21T10:00:00",
                            "command": "echo hello",
                            "cwd": "",
                            "git_branch": "",
                        },
                        {
                            "timestamp": "2026-07-21T11:00:00",
                            "command": "npm test",
                            "cwd": "/home/user/ProjectX",
                            "git_branch": "main",
                        },
                    ],
                }
            ],
        )
        hints = tool._extract_project_hints(raw, "サマリー")
        assert len(hints) == 2
        dir_names = {h["candidate_name"] for h in hints}
        assert "ProjectX" in dir_names
        assert "プロジェクト不明" in dir_names

    def test_no_entries(self):
        """エントリがない場合は空リストを返すこと."""
        tool = TerminalLogsTool()
        raw = CollectedLog(
            source="terminal_logs",
            target_date="2026-07-21",
            files=[{"path": "/tmp/empty.jsonl", "entries": []}],
        )
        hints = tool._extract_project_hints(raw, "サマリー")
        assert hints == []

    def test_duplicate_dirs_deduplicated(self):
        """同一ディレクトリ名が重複しないこと."""
        tool = TerminalLogsTool()
        raw = CollectedLog(
            source="terminal_logs",
            target_date="2026-07-21",
            files=[
                {
                    "path": "/tmp/history.jsonl",
                    "entries": [
                        {"timestamp": "t1", "command": "cmd1", "cwd": "/a/Proj", "git_branch": ""},
                        {"timestamp": "t2", "command": "cmd2", "cwd": "/b/Proj", "git_branch": ""},
                    ],
                }
            ],
        )
        hints = tool._extract_project_hints(raw, "サマリー")
        # "/a/Proj" と "/b/Proj" は同じ basename "Proj" → 1つの hint に集約
        assert len(hints) == 1
        assert hints[0]["candidate_name"] == "Proj"
