"""Reporter ノードの単体テスト.

project_activities フォーマット、空データ処理、プロジェクト不明エントリを検証する。
"""

from __future__ import annotations

from dev_log_daily.pipeline.reporter import _format_project_activities


class TestFormatProjectActivities:
    """_format_project_activities のテスト."""

    def test_single_project(self):
        """単一プロジェクトの活動データが正しくフォーマットされること."""
        activities = {
            "DevLogDaily": {
                "project_name": "DevLogDaily",
                "source_activities": {
                    "copilot_chat": ["asyncioの使い方を学習"],
                    "git_commits": ["READMEを更新"],
                },
                "time_range": {
                    "start": "2026-07-21T09:00:00+09:00",
                    "end": "2026-07-21T12:00:00+09:00",
                },
                "related_sources": ["copilot_chat", "git_commits"],
            }
        }
        result = _format_project_activities(activities)
        assert "DevLogDaily" in result
        assert "asyncioの使い方を学習" in result
        assert "READMEを更新" in result
        assert "2026-07-21T09:00:00+09:00" in result
        assert "copilot_chat" in result
        assert "git_commits" in result

    def test_multi_project(self):
        """複数プロジェクトの活動データが正しくフォーマットされること."""
        activities = {
            "ProjectA": {
                "project_name": "ProjectA",
                "source_activities": {
                    "copilot_chat": ["設計レビュー"],
                },
                "time_range": {},
                "related_sources": ["copilot_chat"],
            },
            "ProjectB": {
                "project_name": "ProjectB",
                "source_activities": {
                    "git_commits": ["バグ修正"],
                },
                "time_range": {},
                "related_sources": ["git_commits"],
            },
        }
        result = _format_project_activities(activities)
        assert "ProjectA" in result
        assert "ProjectB" in result
        # 両プロジェクトが含まれていること
        assert result.index("ProjectA") < result.index("ProjectB") or result.index(
            "ProjectB"
        ) < result.index("ProjectA")

    def test_empty_project_activities(self):
        """空の project_activities は空文字を返すこと."""
        assert _format_project_activities({}) == ""

    def test_no_time_range(self):
        """time_range がない場合でもエラーにならないこと."""
        activities = {
            "TestProj": {
                "project_name": "TestProj",
                "source_activities": {
                    "terminal_logs": ["テスト実行"],
                },
                "time_range": {},
                "related_sources": ["terminal_logs"],
            }
        }
        result = _format_project_activities(activities)
        assert "TestProj" in result
        assert "テスト実行" in result

    def test_no_source_activities(self):
        """source_activities が空でもエラーにならないこと."""
        activities = {
            "EmptyProj": {
                "project_name": "EmptyProj",
                "source_activities": {},
                "time_range": {},
                "related_sources": [],
            }
        }
        result = _format_project_activities(activities)
        assert "EmptyProj" in result

    def test_unknown_project_rendering(self):
        """'プロジェクト不明' エントリが通常のプロジェクトと同様にフォーマットされること."""
        activities = {
            "プロジェクト不明": {
                "project_name": "プロジェクト不明",
                "source_activities": {
                    "terminal_logs": ["cwd不明のコマンド実行"],
                },
                "time_range": {},
                "related_sources": ["terminal_logs"],
            }
        }
        result = _format_project_activities(activities)
        assert "プロジェクト不明" in result
        assert "cwd不明のコマンド実行" in result

    def test_single_vs_multi_formatting(self):
        """単一プロジェクトと複数プロジェクトで同様のフォーマットが適用されること."""
        single = {
            "Proj": {
                "project_name": "Proj",
                "source_activities": {"copilot_chat": ["act"]},
                "time_range": {},
                "related_sources": ["copilot_chat"],
            }
        }
        multi = {
            "ProjA": {
                "project_name": "ProjA",
                "source_activities": {"copilot_chat": ["actA"]},
                "time_range": {},
                "related_sources": ["copilot_chat"],
            },
            "ProjB": {
                "project_name": "ProjB",
                "source_activities": {"git_commits": ["actB"]},
                "time_range": {},
                "related_sources": ["git_commits"],
            },
        }
        single_result = _format_project_activities(single)
        multi_result = _format_project_activities(multi)
        # 両方ともプロジェクト名を含む
        assert "Proj" in single_result
        assert "ProjA" in multi_result
        assert "ProjB" in multi_result
