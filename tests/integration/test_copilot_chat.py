"""Copilotチャットツール結合テスト.

JSONLファイルからの収集・解析、日付フィルタリング、空ディレクトリ処理を検証する。

注: このテストはツール実装（T022）より先に作成される。初期状態では
ツールモジュールが未実装のため ImportError で失敗する想定。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# ツールが実装される前は ImportError で失敗する（TDD）
try:
    from dev_log_daily.tools.copilot_chat import CopilotChatTool

    HAS_TOOL = True
except (ImportError, ModuleNotFoundError):
    HAS_TOOL = False

pytestmark = pytest.mark.skipif(not HAS_TOOL, reason="CopilotChatTool 未実装")


@pytest.fixture
def tool() -> CopilotChatTool:
    """CopilotChatTool のインスタンス."""
    return CopilotChatTool()


class TestCopilotChatCollect:
    """CopilotChatTool.collect() の結合テスト."""

    def test_collect_returns_sessions_for_target_date(
        self,
        tool: CopilotChatTool,
        sample_chat_dir: str,
        config_for_tools: dict,
    ):
        """collect() が対象日付のセッションを正しく収集すること."""
        result = tool.collect("2026-06-19", config_for_tools["data_sources"])
        assert result is not None
        assert result.source == "copilot_chat"
        assert result.target_date == "2026-06-19"
        assert not result.is_empty
        assert result.error is None
        # フィクスチャには2026-06-19のセッションが最低2ファイル分存在する
        assert len(result.files) >= 1

    def test_collect_filters_mixed_dates(
        self,
        tool: CopilotChatTool,
        sample_chat_dir: str,
        config_for_tools: dict,
    ):
        """collect() が複数日付混在ファイルから対象日のみをフィルタリングすること."""
        result = tool.collect("2026-06-20", config_for_tools["data_sources"])
        assert result is not None
        # 2026-06-20 のセッションは mixed.jsonl に1件のみ
        assert not result.is_empty

    def test_collect_returns_no_data_for_date_without_sessions(
        self,
        tool: CopilotChatTool,
        sample_chat_dir: str,
        config_for_tools: dict,
    ):
        """collect() がセッションのない日付に対して空の結果を返すこと."""
        result = tool.collect("2025-01-01", config_for_tools["data_sources"])
        assert result is not None
        assert result.is_empty
        assert result.error is None

    def test_collect_empty_directory(
        self,
        tool: CopilotChatTool,
        temp_dir: str,
        config_for_tools: dict,
    ):
        """collect() が空のディレクトリを正しく処理すること."""
        # 空のディレクトリを作成
        empty_dir = Path(temp_dir) / "empty_chats"
        empty_dir.mkdir(parents=True, exist_ok=True)
        config_for_tools["data_sources"]["copilot_chat"] = {
            "workspace_storage_dirs": [str(empty_dir)],
            "max_workspaces": 50,
        }

        result = tool.collect("2026-06-19", config_for_tools["data_sources"])
        assert result is not None
        assert result.is_empty
        assert result.error is None

    def test_collect_nonexistent_directory(
        self,
        tool: CopilotChatTool,
        config_for_tools: dict,
    ):
        """collect() が存在しないディレクトリに対してエラーを返すこと."""
        config_for_tools["data_sources"]["copilot_chat"] = {
            "workspace_storage_dirs": ["/nonexistent/path/that/does/not/exist"],
            "max_workspaces": 50,
        }

        result = tool.collect("2026-06-19", config_for_tools["data_sources"])
        assert result is not None
        assert result.is_empty
        assert result.error is not None  # エラー情報が設定される

    def test_collect_preserves_file_metadata(
        self,
        tool: CopilotChatTool,
        sample_chat_dir: str,
        config_for_tools: dict,
    ):
        """collect() が収集ファイルのメタデータを保持すること."""
        result = tool.collect("2026-06-19", config_for_tools["data_sources"])
        assert not result.is_empty
        for file_info in result.files:
            assert "path" in file_info
            assert "timestamp" in file_info
            assert file_info["source"] == "copilot_chat"


class TestCopilotChatParse:
    """CopilotChatTool.parse() の結合テスト."""

    @pytest.fixture
    def collected_log(self, tool: CopilotChatTool, sample_chat_dir: str, config_for_tools: dict):
        """収集済みログデータ."""
        return tool.collect("2026-06-19", config_for_tools["data_sources"])

    @pytest.mark.asyncio
    async def test_parse_returns_structured_data(
        self,
        tool: CopilotChatTool,
        collected_log,
    ):
        """parse() がLLM解析後に構造化データを返すこと."""
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content="解析サマリー: 3件のチャットセッション\n"
                "トピック: Python非同期処理, FastAPI, Docker Compose"
            )
        )

        result = await tool.parse(collected_log, mock_llm)
        assert result is not None
        assert result.source == "copilot_chat"
        assert result.summary != ""
        assert result.error is None

    @pytest.mark.asyncio
    async def test_parse_empty_log_returns_empty_result(
        self,
        tool: CopilotChatTool,
    ):
        """parse() が空のログに対して空の解析結果を返すこと."""
        from dev_log_daily.tools.base import CollectedLog

        empty_log = CollectedLog(
            source="copilot_chat",
            target_date="2026-06-19",
            files=[],
        )
        mock_llm = AsyncMock()

        result = await tool.parse(empty_log, mock_llm)
        assert result.is_empty

    @pytest.mark.asyncio
    async def test_parse_handles_llm_error(
        self,
        tool: CopilotChatTool,
        collected_log,
    ):
        """parse() がLLMエラー時にエラー情報を設定すること."""
        from dev_log_daily.llm.client import LLMPermanentError

        mock_llm = AsyncMock()
        error = LLMPermanentError("LLM error")
        error.status_code = 400
        mock_llm.ainvoke = AsyncMock(side_effect=error)

        with pytest.raises(LLMPermanentError):
            await tool.parse(collected_log, mock_llm)


# ═══════════════════════════════════════════════════════════════════
# User Story 1: 複数ワークスペースのチャットログ一括収集
# ═══════════════════════════════════════════════════════════════════
#
# 注: これらのテストは _discover_workspaces() と複数WS対応 collect() が
# 実装される前は失敗する（TDD）。実装後は workspace 単位の収集を検証する。


@pytest.fixture
def multi_ws_tool() -> CopilotChatTool:
    """複数WS収集テスト用ツールインスタンス."""
    return CopilotChatTool()


class TestMultiWorkspaceCollection:
    """複数ワークスペースからの収集テスト（US1）."""

    # ── T008 ─────────────────────────────────────────────────────

    def test_collect_from_single_base_dir(
        self,
        multi_ws_tool: CopilotChatTool,
        config_with_workspace_storage: dict,
    ):
        """T008: 単一ベースディレクトリから全ワークスペースのチャットログが収集されること."""
        result = multi_ws_tool.collect("2026-06-22", config_with_workspace_storage["data_sources"])
        assert result is not None
        assert result.source == "copilot_chat"
        assert result.target_date == "2026-06-22"
        # 3つの有効なワークスペース（empty-workspace は transcripts なしでスキップ）
        assert result.workspace_count == 3
        # workspaces にデータがある
        for ws in result.workspaces:
            assert "workspace_id" in ws
            assert "workspace_name" in ws
            assert "sessions" in ws
            assert ws["session_count"] >= 1

    # ── T009 ─────────────────────────────────────────────────────

    def test_collect_empty_workspace_storage(
        self,
        multi_ws_tool: CopilotChatTool,
        temp_dir: str,
    ):
        """T009: 空の workspaceStorage（有効なワークスペースなし）を正しく処理すること."""
        empty_dir = Path(temp_dir) / "empty_storage"
        empty_dir.mkdir(parents=True, exist_ok=True)

        config = {
            "workspace_storage_dirs": [str(empty_dir)],
            "max_workspaces": 50,
        }
        result = multi_ws_tool.collect("2026-06-22", config)
        assert result is not None
        assert result.is_empty
        # エラーまたは空の結果（有効なワークスペースがない）
        assert result.workspace_count == 0

    # ── T010 ─────────────────────────────────────────────────────

    def test_workspace_without_transcripts_is_skipped(
        self,
        multi_ws_tool: CopilotChatTool,
        config_with_workspace_storage: dict,
    ):
        """T010: transcripts/chatSessions がないワークスペースはスキップされること."""
        result = multi_ws_tool.collect("2026-06-22", config_with_workspace_storage["data_sources"])
        # empty-workspace（transcripts なし）はスキップされ、3つのみ収集
        assert result.workspace_count == 3
        # スキップされた empty-workspace が含まれていないことを確認
        ws_ids = [ws["workspace_id"] for ws in result.workspaces]
        assert "empty-workspace" not in ws_ids

    # ── T011 ─────────────────────────────────────────────────────

    def test_max_workspaces_limit_enforced(
        self,
        multi_ws_tool: CopilotChatTool,
        workspace_storage_base_dir: str,
    ):
        """T011: max_workspaces 上限が正しく機能すること（5WS中3まで）."""
        config = {
            "workspace_storage_dirs": [workspace_storage_base_dir],
            "max_workspaces": 3,
        }
        result = multi_ws_tool.collect("2026-06-22", config)
        assert result is not None
        # max_workspaces=3 なので最大3つのワークスペースまで収集
        assert result.workspace_count <= 3

    # ── T012 ─────────────────────────────────────────────────────

    def test_nonexistent_base_dir_warned_and_skipped(
        self,
        multi_ws_tool: CopilotChatTool,
    ):
        """T012: 存在しないベースディレクトリは警告されスキップされること."""
        config = {
            "workspace_storage_dirs": ["/nonexistent/path/that/does/not/exist"],
            "max_workspaces": 50,
        }
        result = multi_ws_tool.collect("2026-06-22", config)
        assert result is not None
        assert result.is_empty
        # エラーが設定されるか、空の結果が返る
        assert result.error is not None or result.workspace_count == 0


# ═══════════════════════════════════════════════════════════════════
# User Story 2: ワークスペースの識別と日報でのグルーピング
# ═══════════════════════════════════════════════════════════════════


class TestWorkspaceIdentification:
    """ワークスペース識別・グループ化のテスト（US2）."""

    # ── T020 ─────────────────────────────────────────────────────

    def test_workspace_metadata_in_collected_output(
        self,
        multi_ws_tool: CopilotChatTool,
        config_with_workspace_storage: dict,
    ):
        """T020: 収集結果にワークスペースメタデータが含まれること."""
        result = multi_ws_tool.collect("2026-06-22", config_with_workspace_storage["data_sources"])
        assert result is not None
        assert result.workspace_count >= 1

        for ws in result.workspaces:
            # workspace_id が UUID 形式であること
            assert "workspace_id" in ws
            assert len(ws["workspace_id"]) > 0

            # workspace_name が人間可読であること（UUID そのままではない）
            assert "workspace_name" in ws
            assert ws["workspace_name"] != ws["workspace_id"]

            # metadata フィールドの存在確認
            assert "metadata" in ws
            meta = ws["metadata"]
            assert "workspace_json" in meta
            assert "storage_dirs_used" in meta
            assert "platforms" in meta
            assert isinstance(meta["storage_dirs_used"], list)
            assert isinstance(meta["platforms"], list)

    # ── T021 ─────────────────────────────────────────────────────

    def test_sessions_grouped_by_workspace(
        self,
        multi_ws_tool: CopilotChatTool,
        config_with_workspace_storage: dict,
    ):
        """T021: 同一ワークスペースの複数セッションがグループ化されること."""
        result = multi_ws_tool.collect("2026-06-22", config_with_workspace_storage["data_sources"])
        assert result is not None
        assert result.workspace_count >= 1

        # 各ワークスペースのセッションが正しくグループ化されている
        total_session_count = 0
        for ws in result.workspaces:
            assert "sessions" in ws
            assert "session_count" in ws
            # session_count が実際の sessions 数と一致すること
            assert ws["session_count"] == len(ws["sessions"])
            total_session_count += ws["session_count"]

        # 全ワークスペースのセッション数の合計が 0 より大きいこと
        assert total_session_count > 0


# ═══════════════════════════════════════════════════════════════════
# User Story 3: クロスプラットフォーム対応（WSL + Windows）
# ═══════════════════════════════════════════════════════════════════


class TestCrossPlatformCollection:
    """クロスプラットフォーム対応のテスト（US3）."""

    # ── T026 ─────────────────────────────────────────────────────

    def test_dual_directory_collection(
        self,
        multi_ws_tool: CopilotChatTool,
        config_with_dual_workspace_storage: dict,
    ):
        """T026: 2つのベースディレクトリから全てのワークスペースが収集されること.

        最初のベース: frontend(uuid-a), backend(uuid-b), docs(uuid-c)
        2番目のベース: frontend(uuid-a, マージ), mobile(uuid-d)
        → uuid-a はマージ、uuid-b, uuid-c, uuid-d は独立 → 合計4WS
        """
        result = multi_ws_tool.collect(
            "2026-06-22", config_with_dual_workspace_storage["data_sources"]
        )
        assert result is not None
        assert result.workspace_count == 4

        # 全てのワークスペース名が存在すること
        ws_ids = {ws["workspace_id"] for ws in result.workspaces}
        assert "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa" in ws_ids
        assert "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb" in ws_ids
        assert "cccccccc-cccc-cccc-cccc-cccccccccccc" in ws_ids
        assert "dddddddd-dddd-dddd-dddd-dddddddddddd" in ws_ids

    # ── T027 ─────────────────────────────────────────────────────

    def test_uuid_based_workspace_merging(
        self,
        multi_ws_tool: CopilotChatTool,
        config_with_dual_workspace_storage: dict,
    ):
        """T027: 同一 UUID のワークスペースが2つのベースディレクトリ間で統合されること.

        uuid-a は最初のベース（linux）と2番目のベース（windows）の両方に存在。
        統合後は1つのエントリになり、両方のプラットフォームとパスが含まれる。
        """
        result = multi_ws_tool.collect(
            "2026-06-22", config_with_dual_workspace_storage["data_sources"]
        )

        # uuid-a が1つのエントリとして統合されていること
        ws_a = None
        for ws in result.workspaces:
            if ws["workspace_id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa":
                ws_a = ws
                break
        assert ws_a is not None, "uuid-a が収集結果に見つかりません"

        # 統合後は2つのプラットフォームが含まれる
        meta = ws_a["metadata"]
        assert "linux" in meta["platforms"], "linux プラットフォームが含まれていること"
        assert "windows" in meta["platforms"], "windows プラットフォームが含まれていること"

        # 2つのストレージディレクトリが含まれる
        assert len(meta["storage_dirs_used"]) >= 1

    # ── T028 ─────────────────────────────────────────────────────

    def test_session_deduplication_across_platforms(
        self,
        multi_ws_tool: CopilotChatTool,
        config_with_dual_workspace_storage: dict,
    ):
        """T028: 同一 sessionId が複数のプラットフォームに存在する場合、重複排除されること.

        uuid-a には最初のベース（linux）と2番目のベース（windows）の両方に
        同一 sessionId "session-aaaaaaaa" が存在。重複排除後は1回のみカウント。
        """
        result = multi_ws_tool.collect(
            "2026-06-22", config_with_dual_workspace_storage["data_sources"]
        )

        # uuid-a のセッションを取得
        ws_a = None
        for ws in result.workspaces:
            if ws["workspace_id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa":
                ws_a = ws
                break
        assert ws_a is not None, "uuid-a が見つかりません"

        # 重複排除後: uuid-a は最初のベースで1セッション + 2番目のベースで1ユニークセッション
        # 最初のベース: session-aaaaaaaa（1つ）
        # 2番目のベース: session-aaaaaaaa（重複→スキップ）, session-aaaaaaaa-other（ユニーク）
        # 合計: 2つのユニークセッション
        assert ws_a["session_count"] == 2, (
            f"期待: 2 セッション (重複排除後), 実際: {ws_a['session_count']}"
        )

        # セッションIDのリストを確認
        session_ids = [s["session_id"] for s in ws_a["sessions"]]
        assert "session-aaaaaaaa" in session_ids
        # session-aaaaaaaa が1回だけ含まれていること（重複排除済み）
        assert session_ids.count("session-aaaaaaaa") == 1

    # ── T029 ─────────────────────────────────────────────────────

    def test_duplicate_base_dir_paths_deduplicated(
        self,
        multi_ws_tool: CopilotChatTool,
        workspace_storage_base_dir: str,
    ):
        """T029: 同一ベースディレクトリパスが重複指定された場合、正しく重複排除されること."""
        # 同じパスを2回指定（copilot_chat ラッパー付き）
        config = {
            "copilot_chat": {
                "workspace_storage_dirs": [
                    workspace_storage_base_dir,
                    workspace_storage_base_dir,  # 重複
                ],
                "max_workspaces": 50,
            },
        }
        result = multi_ws_tool.collect("2026-06-22", config)
        assert result is not None
        # 重複排除後も3つの有効なワークスペースが収集されること
        assert result.workspace_count == 3
        # 重複がないこと
        ws_ids = [ws["workspace_id"] for ws in result.workspaces]
        assert len(ws_ids) == len(set(ws_ids)), "ワークスペースIDに重複があります"
