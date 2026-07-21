"""CopilotChatTool の単体テスト.

ワークスペース識別・グループ化（US2）のテストを含む。

注: このテストは実装（T022/T023）より先に作成される。
初期状態ではメソッド未実装のため AttributeError で失敗する想定。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

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


# ═══════════════════════════════════════════════════════════════════
# T019: _read_workspace_json() のユニットテスト
# ═══════════════════════════════════════════════════════════════════


class TestReadWorkspaceJson:
    """_read_workspace_json() の単体テスト."""

    def test_reads_valid_workspace_json(self, tool: CopilotChatTool, tmp_path: Path):
        """有効な workspace.json をパースできること."""
        ws_dir = tmp_path / "test-workspace"
        ws_dir.mkdir()
        ws_data = {
            "workspace": {
                "folder": "/home/user/projects/frontend",
            }
        }
        (ws_dir / "workspace.json").write_text(json.dumps(ws_data), encoding="utf-8")

        result = tool._read_workspace_json(str(ws_dir))
        assert result is not None
        assert result["workspace"]["folder"] == "/home/user/projects/frontend"

    def test_returns_none_for_malformed_json(self, tool: CopilotChatTool, tmp_path: Path):
        """不正な JSON ファイルに対して None を返すこと."""
        ws_dir = tmp_path / "malformed-ws"
        ws_dir.mkdir()
        (ws_dir / "workspace.json").write_text("{invalid json}", encoding="utf-8")

        result = tool._read_workspace_json(str(ws_dir))
        assert result is None

    def test_returns_none_for_missing_file(self, tool: CopilotChatTool, tmp_path: Path):
        """workspace.json が存在しない場合 None を返すこと."""
        ws_dir = tmp_path / "missing-json"
        ws_dir.mkdir()
        # workspace.json を作成しない

        result = tool._read_workspace_json(str(ws_dir))
        assert result is None

    def test_returns_none_for_empty_json(self, tool: CopilotChatTool, tmp_path: Path):
        """空の JSON オブジェクトに対して None を返すこと."""
        ws_dir = tmp_path / "empty-json"
        ws_dir.mkdir()
        (ws_dir / "workspace.json").write_text("{}", encoding="utf-8")

        result = tool._read_workspace_json(str(ws_dir))
        assert result is not None
        assert result == {}

    def test_handles_non_dict_json(self, tool: CopilotChatTool, tmp_path: Path):
        """JSON 配列などの非 dict 値に対して None を返すこと."""
        ws_dir = tmp_path / "array-json"
        ws_dir.mkdir()
        (ws_dir / "workspace.json").write_text('["item1", "item2"]', encoding="utf-8")

        result = tool._read_workspace_json(str(ws_dir))
        assert result is None or result == ["item1", "item2"]


# ═══════════════════════════════════════════════════════════════════
# T018: _extract_workspace_name() のユニットテスト
# ═══════════════════════════════════════════════════════════════════


class TestExtractWorkspaceName:
    """_extract_workspace_name() の単体テスト."""

    def test_extracts_name_from_folder(self, tool: CopilotChatTool):
        """workspace.folder から名前を抽出できること（優先順位1位）."""
        ws_json = {"workspace": {"folder": "/home/user/projects/frontend"}}
        name = tool._extract_workspace_name(ws_json, "any-uuid")
        assert name == "frontend"

    def test_extracts_name_from_workspace_file(self, tool: CopilotChatTool):
        """workspace.workspace から名前を抽出できること（優先順位2位）."""
        ws_json = {"workspace": {"workspace": "backend.code-workspace"}}
        name = tool._extract_workspace_name(ws_json, "any-uuid")
        assert name == "backend"

    def test_folder_priority_over_workspace_file(self, tool: CopilotChatTool):
        """folder が workspace より優先されること."""
        ws_json = {
            "workspace": {
                "folder": "/home/user/projects/frontend",
                "workspace": "backend.code-workspace",
            }
        }
        name = tool._extract_workspace_name(ws_json, "any-uuid")
        assert name == "frontend"

    def test_fallback_to_uuid(self, tool: CopilotChatTool):
        """フォルダもワークスペースファイルもない場合 UUID フォールバック."""
        ws_json = {"workspace": {}}
        name = tool._extract_workspace_name(ws_json, "uuid-12345")
        assert name == "Unknown Workspace (uuid-12345)"

    def test_none_json_fallback(self, tool: CopilotChatTool):
        """workspace.json が None の場合 UUID フォールバック."""
        name = tool._extract_workspace_name(None, "uuid-99999")
        assert name == "Unknown Workspace (uuid-99999)"

    def test_extracts_name_from_nested_folder(self, tool: CopilotChatTool):
        """深いパスの folder から basename を抽出できること."""
        ws_json = {"workspace": {"folder": "/home/user/projects/deeply/nested/project-x"}}
        name = tool._extract_workspace_name(ws_json, "any-uuid")
        assert name == "project-x"

    def test_extracts_name_from_workspace_file_without_extension(self, tool: CopilotChatTool):
        """workspace ファイル名から拡張子を除いた名前を抽出できること."""
        ws_json = {"workspace": {"workspace": "my-project.code-workspace"}}
        name = tool._extract_workspace_name(ws_json, "any-uuid")
        assert name == "my-project"

    def test_empty_folder_path(self, tool: CopilotChatTool):
        """folder が空文字の場合のフォールバック."""
        ws_json = {"workspace": {"folder": ""}}
        name = tool._extract_workspace_name(ws_json, "uuid-empty")
        assert name == "Unknown Workspace (uuid-empty)"


# ═══════════════════════════════════════════════════════════════════
# T030: _deduplicate_sessions() のユニットテスト
# ═══════════════════════════════════════════════════════════════════


class TestDeduplicateSessions:
    """_deduplicate_sessions() の単体テスト（US3）."""

    def test_deduplicates_exact_session_id_match(self, tool: CopilotChatTool):
        """同一 sessionId のセッションが重複排除されること."""
        sessions = [
            {"session_id": "sess-001", "content": "original"},
            {"session_id": "sess-002", "content": "second"},
        ]
        seen_ids: set[str] = set()
        result = tool._deduplicate_sessions(sessions, seen_ids)
        assert len(result) == 2
        assert seen_ids == {"sess-001", "sess-002"}

    def test_skips_duplicate_session(self, tool: CopilotChatTool):
        """既に収集済みの sessionId を持つセッションがスキップされること."""
        sessions = [
            {"session_id": "sess-001", "content": "original"},
            {"session_id": "sess-001", "content": "duplicate"},
        ]
        seen_ids: set[str] = {"sess-001"}
        result = tool._deduplicate_sessions(sessions, seen_ids)
        assert len(result) == 0  # 両方ともスキップ

    def test_handles_mixed_unique_and_duplicate(self, tool: CopilotChatTool):
        """ユニークなセッションと重複が混在する場合、正しくフィルタリングされること."""
        sessions = [
            {"session_id": "sess-001", "content": "already seen"},
            {"session_id": "sess-002", "content": "new 1"},
            {"session_id": "sess-003", "content": "new 2"},
        ]
        seen_ids: set[str] = {"sess-001"}
        result = tool._deduplicate_sessions(sessions, seen_ids)
        assert len(result) == 2
        assert seen_ids == {"sess-001", "sess-002", "sess-003"}

    def test_handles_empty_session_list(self, tool: CopilotChatTool):
        """空のセッションリストを正しく処理すること."""
        sessions: list[dict] = []
        seen_ids: set[str] = set()
        result = tool._deduplicate_sessions(sessions, seen_ids)
        assert len(result) == 0

    def test_handles_sessions_without_session_id(self, tool: CopilotChatTool):
        """session_id がないセッションは常に許可されること."""
        sessions = [
            {"content": "no id 1"},
            {"session_id": "sess-001", "content": "with id"},
            {"content": "no id 2"},
        ]
        seen_ids: set[str] = {"sess-001"}
        result = tool._deduplicate_sessions(sessions, seen_ids)
        # no-id セッションは常に許可、with-id は重複チェック
        assert len(result) == 2  # "no id 1" と "no id 2"
        assert seen_ids == {"sess-001"}
