"""Enricher ノードの単体テスト.

project_hints 統合、JSON パース、空データ処理を検証する。
"""

from __future__ import annotations

from dev_log_daily.pipeline.enricher import (
    _collect_project_hints,
    _format_project_hints,
    _get_parsed_summary,
    _parse_enriched_json,
)
from dev_log_daily.state import DailyState


class TestGetParsedSummary:
    """_get_parsed_summary のテスト."""

    def test_with_summary(self):
        """サマリーが存在する場合に正しく取得できること."""
        state: DailyState = {
            "target_date": "2026-07-21",
            "copilot_chat_raw": {},
            "git_commits_raw": {},
            "terminal_logs_raw": {},
            "copilot_chat_parsed": {"summary": "テストサマリー", "source": "copilot_chat"},
            "git_commits_parsed": {},
            "terminal_logs_parsed": {},
            "project_hints": [],
            "project_activities": {},
            "enriched_data": {},
            "daily_report": "",
            "errors": [],
            "progress_log": [],
        }
        result = _get_parsed_summary(state, "copilot_chat_parsed")
        assert result == "テストサマリー"

    def test_without_summary(self):
        """サマリーが存在しない場合に空文字を返すこと."""
        state: DailyState = {
            "target_date": "2026-07-21",
            "copilot_chat_raw": {},
            "git_commits_raw": {},
            "terminal_logs_raw": {},
            "copilot_chat_parsed": {"source": "copilot_chat"},
            "git_commits_parsed": {},
            "terminal_logs_parsed": {},
            "project_hints": [],
            "project_activities": {},
            "enriched_data": {},
            "daily_report": "",
            "errors": [],
            "progress_log": [],
        }
        result = _get_parsed_summary(state, "copilot_chat_parsed")
        assert result == ""

    def test_empty_dict(self):
        """空の dict の場合に空文字を返すこと."""
        result = _get_parsed_summary({}, "copilot_chat_parsed")
        assert result == ""


class TestCollectProjectHints:
    """_collect_project_hints のテスト."""

    def test_collects_all_sources(self):
        """全データソースから project_hints を収集できること."""
        state: DailyState = {
            "target_date": "2026-07-21",
            "copilot_chat_raw": {},
            "git_commits_raw": {},
            "terminal_logs_raw": {},
            "copilot_chat_parsed": {
                "source": "copilot_chat",
                "project_hints": [
                    {
                        "source": "copilot_chat",
                        "candidate_name": "ProjA",
                        "activity_summary": "summary",
                    }
                ],
            },
            "git_commits_parsed": {
                "source": "git_commits",
                "project_hints": [
                    {
                        "source": "git_commits",
                        "candidate_name": "ProjB",
                        "activity_summary": "summary",
                    }
                ],
            },
            "terminal_logs_parsed": {
                "source": "terminal_logs",
                "project_hints": [
                    {
                        "source": "terminal_logs",
                        "candidate_name": "ProjC",
                        "activity_summary": "summary",
                    }
                ],
            },
            "project_hints": [],
            "project_activities": {},
            "enriched_data": {},
            "daily_report": "",
            "errors": [],
            "progress_log": [],
        }
        hints = _collect_project_hints(state)
        assert len(hints) == 3
        sources = {h["source"] for h in hints}
        assert sources == {"copilot_chat", "git_commits", "terminal_logs"}

    def test_empty_hints(self):
        """project_hints が空の場合は空リストを返すこと."""
        state: DailyState = {
            "target_date": "2026-07-21",
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
        hints = _collect_project_hints(state)
        assert hints == []

    def test_missing_field(self):
        """project_hints フィールドがないパース結果は無視されること."""
        state: DailyState = {
            "target_date": "2026-07-21",
            "copilot_chat_raw": {},
            "git_commits_raw": {},
            "terminal_logs_raw": {},
            "copilot_chat_parsed": {"source": "copilot_chat", "summary": "test"},
            "git_commits_parsed": {},
            "terminal_logs_parsed": {},
            "project_hints": [],
            "project_activities": {},
            "enriched_data": {},
            "daily_report": "",
            "errors": [],
            "progress_log": [],
        }
        hints = _collect_project_hints(state)
        assert hints == []


class TestFormatProjectHints:
    """_format_project_hints のテスト."""

    def test_formats_hints(self):
        """プロジェクトヒントが正しくフォーマットされること."""
        hints = [
            {
                "source": "copilot_chat",
                "candidate_name": "ProjA",
                "activity_summary": "Doing something",
            },
        ]
        result = _format_project_hints(hints)
        assert "ProjA" in result
        assert "copilot_chat" in result

    def test_empty_hints(self):
        """空リストの場合は空文字を返すこと."""
        assert _format_project_hints([]) == ""


class TestParseEnrichedJson:
    """_parse_enriched_json のテスト."""

    def test_parse_with_projects(self):
        """projects フィールドを含む JSON をパースできること."""
        json_str = """{
            "cross_references": [],
            "contradictions": [],
            "completions": [],
            "context": "test context",
            "key_activities": [],
            "projects": {
                "MyProject": {
                    "project_name": "MyProject",
                    "source_activities": {
                        "copilot_chat": ["did something"]
                    },
                    "time_range": {
                        "start": "2026-07-21T09:00:00+09:00",
                        "end": "2026-07-21T18:00:00+09:00"
                    },
                    "related_sources": ["copilot_chat"]
                }
            }
        }"""
        result = _parse_enriched_json(json_str)
        assert "projects" in result
        assert "MyProject" in result["projects"]
        assert result["projects"]["MyProject"]["project_name"] == "MyProject"

    def test_parse_malformed_json(self):
        """不正な JSON でもエラーにならず defaults を返すこと."""
        result = _parse_enriched_json("not json at all")
        assert "projects" in result
        assert result["projects"] == {}

    def test_parse_codeblock_json(self):
        """コードブロックで囲まれた JSON をパースできること."""
        json_str = '```json\n{"projects": {}}\n```'
        result = _parse_enriched_json(json_str)
        assert "projects" in result

    def test_parse_mixed_text_json(self):
        """余分なテキストと JSON が混在していてもパースできること."""
        json_str = 'Here is the result:\n\n{"context": "test", "projects": {}}\n\nEnd.'
        result = _parse_enriched_json(json_str)
        assert result.get("context") == "test"

    def test_parse_empty_projects(self):
        """projects が空の場合でも正しくパースされること."""
        json_str = '{"projects": {}}'
        result = _parse_enriched_json(json_str)
        assert result["projects"] == {}

    def test_key_activities_time_ordered(self):
        """key_activities に time-ordered 情報が含まれていることをパースできること."""
        json_str = """{
            "key_activities": [
                {"activity": "設計議論(09:00)", "impact": "アーキテクチャ決定",
                 "related_sources": ["copilot_chat"]},
                {"activity": "実装作業(10:30)", "impact": "コード作成",
                 "related_sources": ["git_commits"]},
                {"activity": "テスト実行(14:00)", "impact": "動作確認",
                 "related_sources": ["terminal_logs"]}
            ],
            "projects": {}
        }"""
        result = _parse_enriched_json(json_str)
        assert "key_activities" in result
        assert len(result["key_activities"]) == 3
        # 時系列順に並んでいることを確認
        assert "09:00" in result["key_activities"][0]["activity"]
        assert "10:30" in result["key_activities"][1]["activity"]
        assert "14:00" in result["key_activities"][2]["activity"]

    def test_key_activities_cross_source(self):
        """複数ソースにまたがる key_activities がパースできること."""
        json_str = """{
            "key_activities": [
                {"activity": "設計", "impact": "設計書作成",
                 "related_sources": ["copilot_chat", "terminal_logs"]}
            ],
            "projects": {}
        }"""
        result = _parse_enriched_json(json_str)
        assert len(result["key_activities"]) == 1
        assert "copilot_chat" in result["key_activities"][0]["related_sources"]
        assert "terminal_logs" in result["key_activities"][0]["related_sources"]

    def test_time_range_iso8601(self):
        """time_range が ISO 8601 形式でパースできること."""
        json_str = """{
            "projects": {
                "TestProj": {
                    "project_name": "TestProj",
                    "source_activities": {},
                    "time_range": {
                        "start": "2026-07-21T09:00:00+09:00",
                        "end": "2026-07-21T18:00:00+09:00"
                    },
                    "related_sources": []
                }
            }
        }"""
        result = _parse_enriched_json(json_str)
        assert "projects" in result
        proj = result["projects"]["TestProj"]
        assert proj["time_range"]["start"] == "2026-07-21T09:00:00+09:00"
        assert proj["time_range"]["end"] == "2026-07-21T18:00:00+09:00"

    def test_time_range_empty(self):
        """time_range が空の場合でも正しくパースされること."""
        json_str = """{
            "projects": {
                "NoTimeProj": {
                    "project_name": "NoTimeProj",
                    "source_activities": {},
                    "time_range": {},
                    "related_sources": []
                }
            }
        }"""
        result = _parse_enriched_json(json_str)
        assert result["projects"]["NoTimeProj"]["time_range"] == {}

    def test_time_range_partial(self):
        """time_range が start のみの場合でもパースできること."""
        json_str = """{
            "projects": {
                "PartialProj": {
                    "project_name": "PartialProj",
                    "source_activities": {},
                    "time_range": {"start": "2026-07-21T10:00:00+09:00"},
                    "related_sources": []
                }
            }
        }"""
        result = _parse_enriched_json(json_str)
        assert (
            result["projects"]["PartialProj"]["time_range"]["start"] == "2026-07-21T10:00:00+09:00"
        )
