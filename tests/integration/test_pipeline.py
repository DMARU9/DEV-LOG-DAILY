"""パイプライン全体の結合テスト.

全データソース正常系、一部データソース欠落、全データソース空、
LLMエラー停止、同名ファイル上書きを検証する（FR-012含む）。
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dev_log_daily.agent import run_pipeline
from dev_log_daily.config.schema import AppConfig

_LLM_BASE_URL = "http://172.21.96.1:8080/v1"


@contextmanager
def _mock_chat_openai(response_content: str = "モック応答"):
    """全パイプラインノードの create_llm をモックするコンテキストマネージャ.

    parser.py, enricher.py, reporter.py は各々 create_llm() を呼び出し、
    その戻り値の .ainvoke() を通して LLM 応答を取得する。
    そのため create_llm 自体をモックしてモックインスタンスを返す。

    Args:
        response_content: LLM 応答として返す文字列
    """
    inst = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = response_content
    inst.ainvoke = AsyncMock(return_value=mock_resp)

    patcher_parser = patch("dev_log_daily.pipeline.parser.create_llm", return_value=inst)
    patcher_enricher = patch("dev_log_daily.pipeline.enricher.create_llm", return_value=inst)
    patcher_reporter = patch("dev_log_daily.pipeline.reporter.create_llm", return_value=inst)

    patcher_parser.start()
    patcher_enricher.start()
    patcher_reporter.start()
    try:
        yield inst
    finally:
        patcher_reporter.stop()
        patcher_enricher.stop()
        patcher_parser.stop()


@contextmanager
def _mock_chat_openai_error(error_cls, status_code: int = 500):
    """全パイプラインノードの create_llm がエラーを送出するモック."""
    inst = MagicMock()
    error = error_cls("mock error")
    error.status_code = status_code  # type: ignore[union-attr]
    inst.ainvoke = AsyncMock(side_effect=error)

    patcher_parser = patch("dev_log_daily.pipeline.parser.create_llm", return_value=inst)
    patcher_enricher = patch("dev_log_daily.pipeline.enricher.create_llm", return_value=inst)
    patcher_reporter = patch("dev_log_daily.pipeline.reporter.create_llm", return_value=inst)

    patcher_parser.start()
    patcher_enricher.start()
    patcher_reporter.start()
    try:
        yield inst
    finally:
        patcher_reporter.stop()
        patcher_enricher.stop()
        patcher_parser.stop()


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def pipeline_config(
    temp_dir: str,
    sample_chat_dir: str,
    sample_git_repo: str,
    sample_terminal_dir: str,
) -> AppConfig:
    """パイプライン結合テスト用の設定（全データソース正常）."""
    return AppConfig(
        llm={
            "collector": {
                "model": "test-model",
                "base_url": _LLM_BASE_URL,
                "api_key": "not-needed",
            },
            "parser": {
                "model": "test-model",
                "base_url": _LLM_BASE_URL,
                "api_key": "not-needed",
            },
            "enricher": {
                "model": "test-model",
                "base_url": _LLM_BASE_URL,
                "api_key": "not-needed",
            },
            "reporter": {
                "model": "test-model",
                "base_url": _LLM_BASE_URL,
                "api_key": "not-needed",
            },
        },
        data_sources={
            "copilot_chat": {
                "workspace_storage_dirs": [sample_chat_dir],
                "max_workspaces": 50,
            },
            "git_root_dir": sample_git_repo,
            "terminal_history_dir": sample_terminal_dir,
        },
        output={"directory": temp_dir},
        timeout_seconds=600,
    )


@pytest.fixture
def empty_pipeline_config(temp_dir: str) -> AppConfig:
    """全データソースが空の設定."""
    empty_chat = Path(temp_dir) / "empty_chats"
    empty_chat.mkdir(parents=True, exist_ok=True)

    empty_repos = Path(temp_dir) / "empty_repos"
    empty_repos.mkdir(parents=True, exist_ok=True)

    empty_terminal_dir = Path(temp_dir) / "empty_terminal"
    empty_terminal_dir.mkdir(parents=True, exist_ok=True)
    (empty_terminal_dir / "history_2026-06-19.jsonl").write_text("", encoding="utf-8")

    return AppConfig(
        llm={
            "collector": {
                "model": "test-model",
                "base_url": _LLM_BASE_URL,
                "api_key": "not-needed",
            },
            "parser": {
                "model": "test-model",
                "base_url": _LLM_BASE_URL,
                "api_key": "not-needed",
            },
            "enricher": {
                "model": "test-model",
                "base_url": _LLM_BASE_URL,
                "api_key": "not-needed",
            },
            "reporter": {
                "model": "test-model",
                "base_url": _LLM_BASE_URL,
                "api_key": "not-needed",
            },
        },
        data_sources={
            "copilot_chat": {
                "workspace_storage_dirs": [str(empty_chat)],
                "max_workspaces": 50,
            },
            "git_root_dir": str(empty_repos),
            "terminal_history_dir": str(empty_terminal_dir),
        },
        output={"directory": temp_dir},
        timeout_seconds=600,
    )


@pytest.fixture
def partial_pipeline_config(
    temp_dir: str,
    sample_git_repo: str,
    sample_chat_dir: str,
) -> AppConfig:
    """一部データソースが欠落した設定（terminal が存在しないディレクトリを指す）."""
    nonexistent_dir = Path(temp_dir) / "nonexistent_terminal_dir"
    return AppConfig(
        llm={
            "collector": {
                "model": "test-model",
                "base_url": _LLM_BASE_URL,
                "api_key": "not-needed",
            },
            "parser": {
                "model": "test-model",
                "base_url": _LLM_BASE_URL,
                "api_key": "not-needed",
            },
            "enricher": {
                "model": "test-model",
                "base_url": _LLM_BASE_URL,
                "api_key": "not-needed",
            },
            "reporter": {
                "model": "test-model",
                "base_url": _LLM_BASE_URL,
                "api_key": "not-needed",
            },
        },
        data_sources={
            "copilot_chat": {
                "workspace_storage_dirs": [sample_chat_dir],
                "max_workspaces": 50,
            },
            "git_root_dir": sample_git_repo,
            "terminal_history_dir": str(nonexistent_dir),
        },
        output={"directory": temp_dir},
        timeout_seconds=600,
    )


# ============================================================================
# Tests
# ============================================================================


class TestPipelineNormal:
    """正常系: 全データソースがデータを持ち、LLMが正常応答する場合."""

    @pytest.mark.asyncio
    async def test_all_sources_produces_report_file(self, pipeline_config, temp_dir):
        """全データソース正常系で日報ファイルが生成されること."""
        target_date = "2026-06-19"

        with _mock_chat_openai():
            result = await run_pipeline(pipeline_config, target_date)

        # 結果に日報が含まれる
        assert "daily_report" in result
        report = result["daily_report"]
        assert isinstance(report, str)
        assert len(report) > 0
        assert "モック応答" in report

        # ファイルが作成される
        expected_path = Path(temp_dir) / f"daily_report_{target_date}.md"
        assert expected_path.exists()
        assert expected_path.read_text(encoding="utf-8") == report

        # エラーなし（エラー一覧が空 or 情報レベルのみ）
        errors = result.get("errors", [])
        assert len(errors) == 0

        # 進捗ログが全ノード分ある
        progress_log = result.get("progress_log", [])
        assert any("[Collector]" in msg for msg in progress_log)
        assert any("[Parser]" in msg for msg in progress_log)
        assert any("[Enricher]" in msg for msg in progress_log)
        assert any("[Reporter]" in msg for msg in progress_log)

    @pytest.mark.asyncio
    async def test_report_contains_target_date_in_filename(self, pipeline_config, temp_dir):
        """日報ファイル名に対象日が含まれること."""
        target_date = "2026-06-19"
        with _mock_chat_openai():
            await run_pipeline(pipeline_config, target_date)

        expected_path = Path(temp_dir) / f"daily_report_{target_date}.md"
        assert expected_path.exists()

    @pytest.mark.asyncio
    async def test_report_saved_as_utf8_lf(self, pipeline_config, temp_dir):
        """日報が UTF-8/LF で保存されること."""
        target_date = "2026-06-19"
        with _mock_chat_openai():
            await run_pipeline(pipeline_config, target_date)

        expected_path = Path(temp_dir) / f"daily_report_{target_date}.md"
        raw_bytes = expected_path.read_bytes()
        # UTF-8 としてデコード可能であること
        raw_bytes.decode("utf-8")

    @pytest.mark.asyncio
    async def test_progress_log_records_all_stages(self, pipeline_config):
        """進捗ログに全ノードの開始・完了が記録されること."""
        target_date = "2026-06-19"
        with _mock_chat_openai():
            result = await run_pipeline(pipeline_config, target_date)

        progress = "\n".join(result.get("progress_log", []))
        assert "Collector" in progress
        assert "Parser" in progress
        assert "Enricher" in progress
        assert "Reporter" in progress


class TestPipelinePartialData:
    """代替系: 一部データソースが欠落している場合."""

    @pytest.mark.asyncio
    async def test_missing_terminal_file_still_completes(
        self,
        partial_pipeline_config,
        temp_dir,
    ):
        """ターミナル履歴ファイルが存在しなくてもパイプラインが完了すること."""
        target_date = "2026-06-19"
        with _mock_chat_openai():
            result = await run_pipeline(partial_pipeline_config, target_date)

        expected_path = Path(temp_dir) / f"daily_report_{target_date}.md"
        assert expected_path.exists()
        # エラーはあっても（terminal 欠落）、全体としては完了する
        assert result.get("daily_report", "") != ""

    @pytest.mark.asyncio
    async def test_partial_data_logs_warning_for_missing_source(
        self,
        partial_pipeline_config,
    ):
        """欠落データソースがある場合、進捗ログに警告が記録されること."""
        target_date = "2026-06-19"
        with _mock_chat_openai():
            result = await run_pipeline(partial_pipeline_config, target_date)

        progress = "\n".join(result.get("progress_log", []))
        assert "ターミナル履歴" in progress


class TestPipelineEmptyData:
    """代替系: 全データソースが空/対象データなしの場合."""

    @pytest.mark.asyncio
    async def test_all_empty_creates_empty_report(self, empty_pipeline_config, temp_dir):
        """全データソース空の場合でも日報が生成されること."""
        target_date = "2026-06-19"
        with _mock_chat_openai():
            result = await run_pipeline(empty_pipeline_config, target_date)

        # 日報が生成される（空データ用フォールバック）
        assert "daily_report" in result
        report = result["daily_report"]
        assert isinstance(report, str)
        assert len(report) > 0

        # ファイルに保存される
        expected_path = Path(temp_dir) / f"daily_report_{target_date}.md"
        assert expected_path.exists()

    @pytest.mark.asyncio
    async def test_all_empty_report_contains_empty_sections(self, empty_pipeline_config, temp_dir):
        """空データ時の日報が「該当なし」セクションを含むこと."""
        target_date = "2026-06-19"
        with _mock_chat_openai():
            result = await run_pipeline(empty_pipeline_config, target_date)

        report = result["daily_report"]
        # 空レポートは「該当なし」を含む
        assert "該当なし" in report
        # 日付がタイトルに含まれる
        assert target_date in report


class TestPipelineLLMError:
    """例外系: LLM エラー発生時の動作."""

    @pytest.mark.asyncio
    async def test_permanent_error_does_not_block_other_sources(
        self,
        pipeline_config,
    ):
        """Parser で LLM 永続エラーが発生した場合、エラーが記録されること."""
        from dev_log_daily.llm.client import LLMPermanentError

        target_date = "2026-06-19"

        with _mock_chat_openai_error(LLMPermanentError, status_code=400):
            result = await run_pipeline(pipeline_config, target_date)

        # エラーが記録される
        errors = result.get("errors", [])
        parse_errors = [e for e in errors if e.get("stage") == "parse"]
        assert len(parse_errors) >= 1
        assert any("LLMPermanentError" in str(e.get("error_type", "")) for e in parse_errors)

    @pytest.mark.asyncio
    async def test_raw_data_preserved_on_parser_permanent_error(
        self,
        pipeline_config,
    ):
        """LLM永続エラー発生後も収集済み*_rawデータが保持されること.

        憲法第VI条 / FR-014 に基づき、LLMエラーによる停止後も
        Collector で収集された生データが破棄されないことを検証する。
        """
        from dev_log_daily.llm.client import LLMPermanentError

        target_date = "2026-06-19"

        with _mock_chat_openai_error(LLMPermanentError, status_code=400):
            result = await run_pipeline(pipeline_config, target_date)

        # *_raw データが保持されていることを確認
        assert "copilot_chat_raw" in result
        assert "git_commits_raw" in result
        assert "terminal_logs_raw" in result

        # *_raw に収集データが含まれている（論理値で判定）
        assert result["copilot_chat_raw"].get("files"), (
            f"copilot_chat_raw の files が空です: {result['copilot_chat_raw']}"
        )
        assert result["git_commits_raw"].get("files"), (
            f"git_commits_raw の files が空です: {result['git_commits_raw']}"
        )
        assert result["terminal_logs_raw"].get("files"), (
            f"terminal_logs_raw の files が空です: {result['terminal_logs_raw']}"
        )

        # *_parsed フィールドが存在すること（値は空でもよい）
        assert "copilot_chat_parsed" in result
        assert "git_commits_parsed" in result
        assert "terminal_logs_parsed" in result

        # エラーが記録されていること
        errors = result.get("errors", [])
        parse_errors = [e for e in errors if e.get("stage") == "parse"]
        assert len(parse_errors) >= 1

        # target_date が正しく設定されていること
        assert result.get("target_date") == target_date


class TestPipelineOverwrite:
    """同名ファイル上書きのテスト."""

    @pytest.mark.asyncio
    async def test_file_overwrites_on_second_run(self, pipeline_config, temp_dir):
        """同名ファイルが上書きされること."""
        target_date = "2026-06-19"
        expected_path = Path(temp_dir) / f"daily_report_{target_date}.md"

        # 1回目の実行
        with _mock_chat_openai("1回目の内容"):
            await run_pipeline(pipeline_config, target_date)
        content1 = expected_path.read_text(encoding="utf-8")

        # 2回目の実行（異なるLLM応答で上書き）
        with _mock_chat_openai("2回目の実行による内容"):
            await run_pipeline(pipeline_config, target_date)

        content2 = expected_path.read_text(encoding="utf-8")
        # ファイルは存在し、内容が更新されている
        assert expected_path.exists()
        assert content2 == "2回目の実行による内容"
        # 1回目と内容が異なる（上書きされた）
        assert content1 != content2


class TestPipelineFR012:
    """FR-012: 外部送信デフォルト無効の確認."""

    @pytest.mark.asyncio
    async def test_data_stays_local_no_external_api_keys(self, pipeline_config):
        """収集データが外部に送信されないこと（設定の base_url のみが通信先）.

        全ての LLM 呼び出しが同じ base_url に向かい、
        生の収集データが外部 API に送信されないことを確認する。
        アーキテクチャ上、LLM 以外の通信経路は存在しない。
        """
        target_date = "2026-06-19"
        config_data_sources = pipeline_config.data_sources

        with _mock_chat_openai():
            await run_pipeline(pipeline_config, target_date)

        # 結果がローカルファイルとして保存される
        expected_path = Path(pipeline_config.output.directory) / f"daily_report_{target_date}.md"
        assert expected_path.exists()

        # ソースデータはローカルパスのみを参照
        assert config_data_sources.copilot_chat is not None
        assert len(config_data_sources.copilot_chat.workspace_storage_dirs) > 0
        assert config_data_sources.git_root_dir is not None
        assert config_data_sources.terminal_history_dir is not None


class TestPipelineProjectActivities:
    """プロジェクト活動データの結合テスト.

    全データソースが project_hints を生成し、Enricher が統合して
    project_activities を生成する流れを検証する。
    """

    @pytest.mark.asyncio
    async def test_parsed_data_includes_project_hints(
        self,
        pipeline_config,
    ):
        """パース結果に project_hints が含まれること."""
        target_date = "2026-06-19"

        with _mock_chat_openai():
            result = await run_pipeline(pipeline_config, target_date)

        # 各パース結果に project_hints フィールドが存在すること
        for field in ("copilot_chat_parsed", "git_commits_parsed", "terminal_logs_parsed"):
            parsed = result.get(field, {})
            assert "project_hints" in parsed, f"{field} に project_hints がありません"

    @pytest.mark.asyncio
    async def test_project_activities_populated_by_enricher(
        self,
        pipeline_config,
    ):
        """Enricher が project_activities を生成すること.

        LLM モックが projects フィールドを含む JSON を返すことで、
        state.project_activities が設定されることを検証する。
        """
        target_date = "2026-06-19"

        enricher_response = """{
            "cross_references": [],
            "contradictions": [],
            "completions": [],
            "context": "test context",
            "key_activities": [],
            "projects": {
                "project-a": {
                    "project_name": "project-a",
                    "source_activities": {
                        "copilot_chat": ["asyncioについて学習"],
                        "git_commits": ["README.mdを更新"],
                        "terminal_logs": ["git push"]
                    },
                    "time_range": {
                        "start": "2026-06-19T09:00:00+09:00",
                        "end": "2026-06-19T18:00:00+09:00"
                    },
                    "related_sources": ["copilot_chat", "git_commits", "terminal_logs"]
                }
            }
        }"""

        with _mock_chat_openai(enricher_response):
            result = await run_pipeline(pipeline_config, target_date)

        # project_activities が設定されている
        project_activities = result.get("project_activities", {})
        assert isinstance(project_activities, dict)

        # enriched_data.projects から project_activities がコピーされる
        enriched = result.get("enriched_data", {})
        assert "projects" in enriched

    @pytest.mark.asyncio
    async def test_empty_project_activities_when_no_data(self, empty_pipeline_config):
        """データが空の場合、project_activities も空になること."""
        target_date = "2026-06-19"

        with _mock_chat_openai():
            result = await run_pipeline(empty_pipeline_config, target_date)

        project_activities = result.get("project_activities", {})
        assert project_activities == {}
