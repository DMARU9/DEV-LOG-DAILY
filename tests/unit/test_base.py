"""CollectedLog / ParsedData / DataSourceTool の単体テスト."""

from dev_log_daily.tools.base import CollectedLog, ParsedData


class TestParsedData:
    """ParsedData のテスト."""

    def test_project_hints_default_empty(self):
        """project_hints がデフォルトで空リストになること."""
        p = ParsedData(source="test")
        assert p.project_hints == []

    def test_project_hints_in_to_dict(self):
        """to_dict() が project_hints を含むこと."""
        p = ParsedData(source="test")
        result = p.to_dict()
        assert "project_hints" in result
        assert result["project_hints"] == []

    def test_project_hints_with_data(self):
        """project_hints にデータを渡すと正しく保持されること."""
        hints = [
            {"source": "copilot_chat", "candidate_name": "ProjectA", "activity_summary": "summary"},
            {"source": "git_commits", "candidate_name": "ProjectB", "activity_summary": "summary2"},
        ]
        p = ParsedData(source="test", project_hints=hints)
        assert len(p.project_hints) == 2
        assert p.project_hints[0]["candidate_name"] == "ProjectA"
        assert p.project_hints[1]["source"] == "git_commits"

    def test_project_hints_to_dict_roundtrip(self):
        """project_hints 付き ParsedData の to_dict が正しい値を持つこと."""
        hints = [
            {
                "source": "copilot_chat",
                "candidate_name": "MyProject",
                "activity_summary": "Did work",
            }
        ]
        p = ParsedData(source="test", project_hints=hints)
        d = p.to_dict()
        assert d["project_hints"] == hints

    def test_project_hints_is_empty_ignored(self):
        """project_hints が is_empty に影響しないこと."""
        p = ParsedData(
            source="test",
            project_hints=[{"source": "t", "candidate_name": "p", "activity_summary": "s"}],
        )
        assert p.is_empty  # summary/structured_data が空のため

    def test_project_hints_none_becomes_empty(self):
        """project_hints=None で空リストに初期化されること."""
        p = ParsedData(source="test", project_hints=None)
        assert p.project_hints == []


class TestCollectedLog:
    """CollectedLog のテスト."""

    def test_to_dict_includes_workspaces(self):
        """to_dict() が workspaces フィールドを含むこと."""
        log = CollectedLog(
            source="copilot_chat",
            target_date="2026-06-22",
            workspaces=[
                {
                    "workspace_id": "uuid-1",
                    "workspace_name": "test-workspace",
                    "sessions": [],
                    "session_count": 0,
                    "metadata": {},
                }
            ],
        )
        result = log.to_dict()
        assert "workspaces" in result
        assert len(result["workspaces"]) == 1
        assert result["workspaces"][0]["workspace_id"] == "uuid-1"

    def test_is_empty_with_workspaces(self):
        """workspaces が空でなければ is_empty が False になること."""
        log = CollectedLog(
            source="copilot_chat",
            target_date="2026-06-22",
            workspaces=[
                {
                    "workspace_id": "uuid-1",
                    "workspace_name": "test",
                    "sessions": [{"session_id": "s1"}],
                    "session_count": 1,
                    "metadata": {},
                }
            ],
        )
        assert not log.is_empty

    def test_is_empty_with_files_only(self):
        """files のみでも is_empty が False になること."""
        log = CollectedLog(
            source="copilot_chat",
            target_date="2026-06-22",
            files=[{"path": "/test.jsonl", "source": "copilot_chat"}],
        )
        assert not log.is_empty

    def test_is_empty_no_data(self):
        """files も workspaces も空なら is_empty が True になること."""
        log = CollectedLog(
            source="copilot_chat",
            target_date="2026-06-22",
        )
        assert log.is_empty

    def test_workspace_count(self):
        """workspace_count が正しい数を返すこと."""
        log = CollectedLog(
            source="copilot_chat",
            target_date="2026-06-22",
            workspaces=[
                {
                    "workspace_id": "uuid-1",
                    "workspace_name": "ws1",
                    "sessions": [],
                    "session_count": 0,
                    "metadata": {},
                },
                {
                    "workspace_id": "uuid-2",
                    "workspace_name": "ws2",
                    "sessions": [],
                    "session_count": 0,
                    "metadata": {},
                },
                {
                    "workspace_id": "uuid-3",
                    "workspace_name": "ws3",
                    "sessions": [],
                    "session_count": 0,
                    "metadata": {},
                },
            ],
        )
        assert log.workspace_count == 3

    def test_workspace_count_zero(self):
        """workspaces がない場合 workspace_count が 0 を返すこと."""
        log = CollectedLog(
            source="copilot_chat",
            target_date="2026-06-22",
        )
        assert log.workspace_count == 0
