"""Reporter ノードの単体テスト.

project_activities フォーマット、空データ処理、プロジェクト不明エントリを検証する。
加えて新フォーマットの空日報生成、report_metadata 整形、フロントマター検証を含む。
"""

from __future__ import annotations

from dev_log_daily.pipeline.reporter import (
    _format_enriched_data,
    _format_project_activities,
    _format_report_metadata,
    _generate_empty_report,
)


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


class TestEmptyReportNewFormat:
    """_generate_empty_report の新フォーマット検証 (FR-003)."""

    def test_empty_report_has_yaml_frontmatter(self):
        """空日報が YAML フロントマターを含むこと."""
        report = _generate_empty_report("2026-07-22")
        assert report.startswith("---\n")
        assert "date: 2026-07-22" in report
        assert "tags: [DevLogDaily]" in report
        assert "type: daily" in report
        assert "mood: productive" in report
        assert "energy: 4" in report
        assert "aliases: [デイリー学習レポート 2026-07-22]" in report
        assert "\n---\n" in report

    def test_empty_report_has_new_title(self):
        """空日報が新フォーマットのタイトルを含むこと."""
        report = _generate_empty_report("2026-07-22")
        assert "# デイリー学習レポート - 2026-07-22" in report

    def test_empty_report_has_overall_summary(self):
        """空日報が「📋 総合概要」セクションを含むこと."""
        report = _generate_empty_report("2026-07-22")
        assert "## 📋 総合概要" in report
        assert "該当なし" in report

    def test_empty_report_has_summary_table(self):
        """空日報が「📊 プロジェクト別活動サマリー」テーブルを含むこと."""
        report = _generate_empty_report("2026-07-22")
        assert "## 📊 プロジェクト別活動サマリー" in report
        assert "| プロジェクト | 活動時間 | 主な活動内容 | 関連データソース |" in report
        assert "|------------|---------|-------------|----------------|" in report

    def test_empty_report_has_project_section(self):
        """空日報が「プロジェクト」セクション（該当なし）を含むこと."""
        report = _generate_empty_report("2026-07-22")
        assert "## プロジェクト" in report
        assert "該当なし" in report

    def test_empty_report_omits_old_sections(self):
        """空日報が旧フォーマットのセクションを含まないこと."""
        report = _generate_empty_report("2026-07-22")
        assert "## ⏱ タイムトラッキング" not in report
        assert "## 🛠 本日触れた技術・ツール" not in report
        assert "## 🛠 触れた技術・ツール" not in report
        assert "## 💻 開発活動" not in report
        assert "## 🏷 技術タグ" not in report

    def test_empty_report_different_date(self):
        """異なる日付で正しく空日報が生成されること."""
        report = _generate_empty_report("2026-07-15")
        assert "date: 2026-07-15" in report
        assert "# デイリー学習レポート - 2026-07-15" in report


class TestFormatEnrichedDataWithMetadata:
    """_format_enriched_data の report_metadata 対応テスト."""

    def test_format_with_report_metadata(self):
        """report_metadata を含む enriched_data が正しく整形されること."""
        enriched = {
            "context": "今日は主にバグ修正に取り組んだ",
            "report_metadata": {
                "mood": "frustrated",
                "energy": 3,
                "tags": ["DevLogDaily", "bugfix"],
                "project_moods": {
                    "ProjectA": {"mood": "frustrated", "energy": 3},
                },
            },
            "key_activities": [],
            "cross_references": [],
        }
        result = _format_enriched_data(enriched)
        assert "文脈" in result
        assert "report_metadata" in result
        assert "frustrated" in result
        assert "3" in result
        assert "DevLogDaily, bugfix" in result
        assert "ProjectA" in result

    def test_format_without_report_metadata(self):
        """report_metadata がない enriched_data でもエラーにならないこと."""
        enriched = {
            "context": "テスト",
            "key_activities": [],
            "cross_references": [],
        }
        result = _format_enriched_data(enriched)
        assert "文脈: テスト" in result

    def test_format_with_empty_report_metadata(self):
        """空の report_metadata でもエラーにならないこと."""
        enriched = {
            "context": "テスト",
            "report_metadata": {},
            "key_activities": [],
            "cross_references": [],
        }
        result = _format_enriched_data(enriched)
        assert "文脈: テスト" in result

    def test_format_with_key_activities_and_metadata(self):
        """key_activities と report_metadata の両方が正しく整形されること."""
        enriched = {
            "report_metadata": {
                "mood": "productive",
                "energy": 4,
                "tags": ["DevLogDaily"],
                "project_moods": {},
            },
            "key_activities": [
                {"activity": "実装作業", "impact": "コード作成"},
            ],
            "cross_references": [],
        }
        result = _format_enriched_data(enriched)
        assert "productive" in result
        assert "実装作業" in result

    def test_format_with_project_moods(self):
        """project_moods が正しく整形されること."""
        enriched = {
            "report_metadata": {
                "mood": "productive",
                "energy": 4,
                "tags": ["DevLogDaily"],
                "project_moods": {
                    "ProjectA": {"mood": "frustrated", "energy": 3},
                    "ProjectB": {"mood": "productive", "energy": 5},
                },
            },
            "key_activities": [],
            "cross_references": [],
        }
        result = _format_enriched_data(enriched)
        assert "ProjectA" in result
        assert "ProjectB" in result
        assert "frustrated" in result
        assert "productive" in result


class TestFormatReportMetadata:
    """_format_report_metadata のテスト."""

    def test_format_full_metadata(self):
        """完全な report_metadata が正しく整形されること."""
        metadata = {
            "mood": "productive",
            "energy": 4,
            "tags": ["DevLogDaily", "Python"],
            "project_moods": {
                "MyProject": {"mood": "reflective", "energy": 3},
            },
        }
        result = _format_report_metadata(metadata)
        assert "推定気分: productive" in result
        assert "推定エネルギー: 4/5" in result
        assert "DevLogDaily, Python" in result
        assert "MyProject" in result
        assert "reflective" in result

    def test_format_empty_metadata(self):
        """空の metadata は空文字を返すこと."""
        assert _format_report_metadata({}) == ""

    def test_format_minimal_metadata(self):
        """必要最小限の metadata が正しく整形されること."""
        metadata = {
            "mood": "productive",
            "energy": 4,
            "tags": ["DevLogDaily"],
            "project_moods": {},
        }
        result = _format_report_metadata(metadata)
        assert "推定気分: productive" in result
        assert "推定エネルギー: 4/5" in result
        assert "DevLogDaily" in result
        assert "プロジェクト別気分" not in result
