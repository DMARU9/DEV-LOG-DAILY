"""Copilotチャットツール — JSONLチャットログの収集・解析・圧縮.

JSONLチャットログディレクトリから対象日のセッションを収集（collect）、
レコードタイプに応じて構造化データに圧縮し、LLMで解析（parse）する。

## 圧縮方針

元のJSONLは数百行ありますが、以下の情報を抽出して圧縮:

1. セッションメタデータ: sessionId, startTime, copilotVersion, vscodeVersion
2. ユーザーメッセージ: content（質問・指示）
3. AI応答: reasoningText（推論）, toolRequests（ツール呼び出し）, content（回答）
4. ターン数: turn_start/turn_end からカウント

除外する情報:
- id, timestamp, parentId などの細かいメタデータ（一部）
- assistant.turn_start/turn_end イベント（カウントのみ保持）
- tool.execution_start/completion イベント
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_openai import ChatOpenAI

from dev_log_daily.config.schema import DataSourceConfig
from dev_log_daily.tools.base import CollectedLog, DataSourceTool, ParsedData
from dev_log_daily.utils.file import find_files, read_text

logger = logging.getLogger(__name__)


class CopilotChatTool(DataSourceTool):
    """Copilotチャットログツール.

    JSONL 形式のチャットログファイルを収集し、レコードタイプに応じて
    構造化データに圧縮した上で LLM で解析する。
    """

    name: str = "copilot_chat"

    def collect(
        self,
        target_date: str,
        config: DataSourceConfig | dict[str, Any],
    ) -> CollectedLog:
        """JSONLチャットログディレクトリから対象日のセッションを収集・圧縮する.

        複数ワークスペースストレージ対応:
        - workspace_storage_dirs で指定された各ベースディレクトリ配下の
          UUID サブディレクトリを自動探索
        - 各ワークスペースの Linux/Windows 両パスを確認し JSONL を収集
        - セッションID ベースの重複排除
        - max_workspaces 上限を遵守

        Args:
            target_date: 対象日（YYYY-MM-DD）
            config: データソース設定（DataSourceConfig または dict）

        Returns:
            収集結果（CollectedLog） — files（全ファイル）と workspaces（WS別）を併用
        """
        # === config から workspace_storage_dirs と max_workspaces を抽出 ===
        if isinstance(config, dict):
            copilot_chat_cfg = config.get("copilot_chat", {}) or {}
            ws_dirs = copilot_chat_cfg.get("workspace_storage_dirs", [])
            max_workspaces = copilot_chat_cfg.get("max_workspaces", 50)
            # 旧形式フォールバック
            if not ws_dirs:
                old_dir = config.get("copilot_chat_dir", "")
                ws_dirs = [old_dir] if old_dir else []
        else:
            ws_dirs = config.copilot_chat.workspace_storage_dirs
            max_workspaces = config.copilot_chat.max_workspaces

        if not ws_dirs:
            logger.warning("workspace_storage_dirs が指定されていません")
            return CollectedLog(
                source=self.name,
                target_date=target_date,
                files=[],
                error="workspace_storage_dirs が指定されていません",
            )

        # === ワークスペース探索 ===
        discovered, skipped_uuids = self._discover_workspaces(ws_dirs, max_workspaces)

        if not discovered:
            # --- レガシーフォールバック: フラットなディレクトリからの収集 ---
            return self._collect_flat(target_date, ws_dirs)

        # === 新パス: ワークスペース別収集 ===
        all_files: list[dict] = []
        workspace_entries: list[dict] = []
        total_original_size = 0
        total_compressed_size = 0
        all_session_ids: set[str] = set()

        for ws in discovered:
            ws_id = ws["workspace_id"]
            transcript_paths = [Path(p) for p in ws["transcript_paths"]]
            ws_sessions: list[dict] = []

            for transcript_dir in transcript_paths:
                jsonl_files = sorted(transcript_dir.glob("*.jsonl"))
                for file_path in jsonl_files:
                    try:
                        content = read_text(str(file_path))
                    except Exception as e:
                        logger.warning("ファイル読み込みエラー: %s: %s", file_path, e)
                        continue

                    sessions = self._parse_jsonl(content, target_date)
                    if not sessions:
                        continue

                    # 重複排除と圧縮率計算
                    original_size = len(content.encode("utf-8"))
                    compressed_json = json.dumps(sessions, ensure_ascii=False, default=str)
                    compressed_size = len(compressed_json.encode("utf-8"))
                    ratio = (compressed_size * 100 // original_size) if original_size > 0 else 0
                    total_original_size += original_size
                    total_compressed_size += compressed_size

                    # セッションID重複排除（T033）
                    deduped_sessions = self._deduplicate_sessions(sessions, all_session_ids)
                    ws_sessions.extend(deduped_sessions)

                    all_files.append(
                        {
                            "path": str(file_path),
                            "source": self.name,
                            "timestamp": datetime.now().isoformat(),
                            "sessions": deduped_sessions,
                            "session_count": len(deduped_sessions),
                            "compression": {
                                "original_bytes": original_size,
                                "compressed_bytes": compressed_size,
                                "ratio_pct": ratio,
                                "saved_pct": 100 - ratio,
                            },
                        }
                    )

            if ws_sessions:
                workspace_entries.append(
                    {
                        "workspace_id": ws_id,
                        "workspace_name": ws["workspace_name"],
                        "sessions": ws_sessions,
                        "session_count": len(ws_sessions),
                        "metadata": {
                            "workspace_json": ws.get("workspace_json"),
                            "storage_dirs_used": ws.get("storage_paths", []),
                            "platforms": ws.get("platforms", []),
                        },
                    }
                )

        # === 収集ログ ===
        self._log_collection_progress(
            discovered,
            skipped_uuids,
            max_workspaces,
            workspace_entries,
            total_original_size,
            total_compressed_size,
        )

        return CollectedLog(
            source=self.name,
            target_date=target_date,
            files=all_files,
            workspaces=workspace_entries,
        )

    def _collect_flat(
        self,
        target_date: str,
        ws_dirs: list[str],
    ) -> CollectedLog:
        """レガシー: フラットなディレクトリから JSONL を収集する.

        ワークスペース構造がないディレクトリ（旧来の単一ディレクトリ）から
        後方互換用に JSONL を収集する。workspaces は空リストとする。

        Args:
            target_date: 対象日（YYYY-MM-DD）
            ws_dirs: ワークスペースディレクトリのリスト（先頭のみ使用）

        Returns:
            収集結果（CollectedLog）
        """
        chat_dir = Path(ws_dirs[0])

        if not chat_dir.exists():
            logger.warning("チャットログディレクトリが存在しません: %s", chat_dir)
            return CollectedLog(
                source=self.name,
                target_date=target_date,
                files=[],
                error=f"チャットログディレクトリが存在しません: {chat_dir}",
            )

        if not chat_dir.is_dir():
            logger.warning("指定されたパスはディレクトリではありません: %s", chat_dir)
            return CollectedLog(
                source=self.name,
                target_date=target_date,
                files=[],
                error=f"指定されたパスはディレクトリではありません: {chat_dir}",
            )

        jsonl_files = find_files(chat_dir, pattern="*.jsonl")
        if not jsonl_files:
            logger.info("チャットログディレクトリに JSONL ファイルがありません: %s", chat_dir)
            return CollectedLog(
                source=self.name,
                target_date=target_date,
                files=[],
            )

        collected_files: list[dict] = []
        total_original_size = 0
        total_compressed_size = 0

        for file_path in jsonl_files:
            try:
                content = read_text(str(file_path))
            except Exception as e:
                logger.warning("ファイル読み込みエラー: %s: %s", file_path, e)
                continue

            sessions = self._parse_jsonl(content, target_date)
            if not sessions:
                continue

            original_size = len(content.encode("utf-8"))
            compressed_json = json.dumps(sessions, ensure_ascii=False, default=str)
            compressed_size = len(compressed_json.encode("utf-8"))
            ratio = (compressed_size * 100 // original_size) if original_size > 0 else 0
            total_original_size += original_size
            total_compressed_size += compressed_size

            collected_files.append(
                {
                    "path": str(file_path),
                    "source": self.name,
                    "timestamp": datetime.now().isoformat(),
                    "sessions": sessions,
                    "session_count": len(sessions),
                    "compression": {
                        "original_bytes": original_size,
                        "compressed_bytes": compressed_size,
                        "ratio_pct": ratio,
                        "saved_pct": 100 - ratio,
                    },
                }
            )

        total_session_count = sum(f.get("session_count", 0) for f in collected_files)

        if total_original_size > 0:
            overall_ratio = total_compressed_size * 100 // total_original_size
            logger.info(
                "Copilotチャット収集完了: %d ファイル, %d セッション "
                "(圧縮: %s → %s bytes, %d%%削減)",
                len(collected_files),
                total_session_count,
                f"{total_original_size:,}",
                f"{total_compressed_size:,}",
                100 - overall_ratio,
            )
        else:
            logger.info(
                "Copilotチャット収集完了: %d ファイル, %d セッション",
                len(collected_files),
                total_session_count,
            )

        return CollectedLog(
            source=self.name,
            target_date=target_date,
            files=collected_files,
        )

    # ── ワークスペース識別 ──────────────────────────────────────────

    def _read_workspace_json(self, workspace_dir: str) -> dict | None:
        """workspace.json を読み込んでパースする.

        Args:
            workspace_dir: ワークスペースディレクトリの絶対パス

        Returns:
            パース済みの dict、または読み込みエラー時は None
        """
        ws_path = Path(workspace_dir) / "workspace.json"
        if not ws_path.is_file():
            logger.debug("workspace.json が存在しません: %s", ws_path)
            return None

        try:
            content = ws_path.read_text(encoding="utf-8")
            data = json.loads(content)
            if not isinstance(data, dict):
                logger.debug("workspace.json が dict ではありません: %s", type(data).__name__)
                return None
            return data
        except json.JSONDecodeError as e:
            logger.warning("workspace.json のパースエラー: %s: %s", ws_path, e)
            return None
        except (OSError, PermissionError) as e:
            logger.warning("workspace.json の読み込みエラー: %s: %s", ws_path, e)
            return None

    def _extract_workspace_name(
        self,
        workspace_json: dict | None,
        workspace_id: str,
    ) -> str:
        """workspace.json から人間可読なワークスペース名を抽出する.

        優先順位:
        1. workspace.folder フィールド → パスの basename
        2. workspace.workspace フィールド → ファイル名（拡張子除く）
        3. フォールバック → "Unknown Workspace (<UUID>)"

        Args:
            workspace_json: workspace.json のパース済み内容（None 可）
            workspace_id: ワークスペース UUID（フォールバック用）

        Returns:
            抽出されたワークスペース名
        """
        if workspace_json is None:
            return f"Unknown Workspace ({workspace_id})"

        ws = workspace_json.get("workspace", {})
        if not isinstance(ws, dict):
            return f"Unknown Workspace ({workspace_id})"

        # 優先順位1: workspace.folder
        folder = ws.get("folder", "")
        if folder and isinstance(folder, str) and folder.strip():
            return Path(folder.strip()).name

        # 優先順位2: workspace.workspace
        workspace_file = ws.get("workspace", "")
        if workspace_file and isinstance(workspace_file, str) and workspace_file.strip():
            name = Path(workspace_file.strip()).stem  # 拡張子除去
            if name:
                return name

        # フォールバック
        return f"Unknown Workspace ({workspace_id})"

    # ── セッション重複排除 ──────────────────────────────────────────

    def _deduplicate_sessions(
        self,
        sessions: list[dict],
        seen_ids: set[str],
    ) -> list[dict]:
        """セッションIDベースで重複排除を行う.

        既に収集済みの sessionId を持つセッションをスキップする。
        session_id がないセッションは常に許可される。

        Args:
            sessions: 重複排除対象のセッションリスト
            seen_ids: 既に収集済みの sessionId 集合（更新される）

        Returns:
            重複排除後のセッションリスト
        """
        deduped: list[dict] = []
        for s in sessions:
            sid = s.get("session_id", "")
            if sid and sid in seen_ids:
                logger.debug("重複セッションをスキップ: sessionId=%s", sid)
                continue
            if sid:
                seen_ids.add(sid)
            deduped.append(s)
        return deduped

    # ── ワークスペース探索 ───────────────────────────────────────────

    def _discover_workspaces(
        self,
        ws_dirs: list[str],
        max_workspaces: int,
    ) -> tuple[list[dict], list[str]]:
        """全ベースディレクトリ配下のワークスペースを探索する（UUID 統合対応）.

        各 workspace_storage_dir を走査し、UUID サブディレクトリを列挙。
        各サブディレクトリ内の Linux/Windows 両パスを確認し、有効な
        ワークスペース情報を返す。

        複数ベースディレクトリ間で同一 UUID のワークスペースは統合する（T032）。
        transcript_paths、platforms、storage_paths をマージし、表示名は
        最初に見つかった workspace.json の情報を優先する。

        Args:
            ws_dirs: workspaceStorage ベースディレクトリのリスト
            max_workspaces: 処理する最大ワークスペース数

        Returns:
            (discovered_workspaces, skipped_uuids)
            discovered_workspaces: 発見されたワークスペース情報のリスト（UUID統合済み）
            skipped_uuids: 上限超過でスキップされた UUID のリスト
        """
        # UUID → workspace_info のマップ（統合用）
        workspace_map: dict[str, dict] = {}
        skipped: list[str] = []
        # 上限チェック用のカウンター（ユニークWS数のみカウント）
        unique_ws_count = 0

        # 同一パスの重複排除（T029）
        seen_dirs: set[str] = set()
        unique_dirs: list[str] = []
        for d in ws_dirs:
            try:
                resolved = str(Path(d).resolve())
            except OSError:
                resolved = d
            if resolved not in seen_dirs:
                seen_dirs.add(resolved)
                unique_dirs.append(d)

        for base_dir_str in unique_dirs:
            if unique_ws_count >= max_workspaces:
                break

            base_dir = Path(base_dir_str)
            if not base_dir.is_dir():
                logger.warning("workspaceStorageディレクトリが存在しません: %s", base_dir)
                continue

            # サブディレクトリを走査
            for child in sorted(base_dir.iterdir()):
                if not child.is_dir():
                    continue

                workspace_id = child.name

                # すでに発見済みの UUID は上限カウントに含めない
                is_new_workspace = workspace_id not in workspace_map
                if is_new_workspace and unique_ws_count >= max_workspaces:
                    skipped.append(str(child.name))
                    continue

                # T015: dual-path check — Linux と Windows 両方のパスを確認
                linux_path = child / "GitHub.copilot-chat" / "transcripts"
                windows_path = child / "chatSessions"

                found_paths: list[Path] = []
                platforms: list[str] = []

                if linux_path.is_dir():
                    found_paths.append(linux_path)
                    platforms.append("linux")
                if windows_path.is_dir():
                    found_paths.append(windows_path)
                    platforms.append("windows")

                if not found_paths:
                    logger.debug(
                        "ワークスペース %s: transcripts/chatSessions なしでスキップ",
                        workspace_id,
                    )
                    continue

                if workspace_id in workspace_map:
                    # ── T032: UUID 統合 — 既存エントリにマージ ──
                    existing = workspace_map[workspace_id]
                    existing["transcript_paths"].extend(str(p) for p in found_paths)
                    for plat in platforms:
                        if plat not in existing["platforms"]:
                            existing["platforms"].append(plat)
                    if base_dir_str not in existing["storage_paths"]:
                        existing["storage_paths"].append(base_dir_str)
                else:
                    # ── 新規 UUID ──
                    ws_json = self._read_workspace_json(str(child))
                    ws_name = self._extract_workspace_name(ws_json, workspace_id)

                    workspace_map[workspace_id] = {
                        "workspace_id": workspace_id,
                        "workspace_name": ws_name,
                        "workspace_json": ws_json,
                        "storage_paths": [base_dir_str],
                        "transcript_paths": [str(p) for p in found_paths],
                        "platforms": platforms,
                    }
                    unique_ws_count += 1

        discovered = list(workspace_map.values())
        return discovered, skipped

    # ── 収集進捗ログ ────────────────────────────────────────────────

    def _log_collection_progress(
        self,
        discovered: list[dict],
        skipped_uuids: list[str],
        max_workspaces: int,
        workspace_entries: list[dict],
        total_original_size: int,
        total_compressed_size: int,
    ) -> None:
        """ワークスペース単位の収集進捗を標準出力にログ出力する.

        Args:
            discovered: 発見された全ワークスペース情報
            skipped_uuids: 上限超過でスキップされた UUID リスト
            workspace_entries: 実際に収集されたワークスペースエントリ
            max_workspaces: 上限値（表示用）
            total_original_size: 合計元サイズ
            total_compressed_size: 合計圧縮後サイズ
        """
        log_lines: list[str] = []

        # 収集成功ワークスペース
        collected_ws = {ws["workspace_id"] for ws in workspace_entries}
        for ws in discovered:
            ws_id = ws["workspace_id"]
            if ws_id in collected_ws:
                ws_entry = next(w for w in workspace_entries if w["workspace_id"] == ws_id)
                count = ws_entry["session_count"]
                platforms = "+".join(ws.get("platforms", []))
                log_lines.append(
                    f"+ {ws.get('workspace_name', ws_id)}: {count} sessions found ({platforms})"
                )
            elif ws_id in skipped_uuids:
                log_lines.append(f"⚠ {ws_id}: 上限超過でスキップ (max_workspaces={max_workspaces})")
            else:
                log_lines.append(f"− {ws_id}: transcripts/chatSessions なしでスキップ")

        for log in log_lines:
            logger.info("[CopilotChat] %s", log)

        # 全体集計
        total_collected = len(workspace_entries)
        total_discovered = len(discovered)
        total_sessions = sum(ws["session_count"] for ws in workspace_entries)

        if total_collected > 0:
            if total_original_size > 0:
                overall_ratio = total_compressed_size * 100 // total_original_size
                logger.info(
                    "Copilotチャット収集完了: 合計 %d/%d ワークスペース "
                    "から %d セッション (圧縮: %d%%削減)",
                    total_collected,
                    total_discovered,
                    total_sessions,
                    100 - overall_ratio,
                )
            else:
                logger.info(
                    "Copilotチャット収集完了: 合計 %d/%d ワークスペース から %d セッション",
                    total_collected,
                    total_discovered,
                    total_sessions,
                )
        else:
            logger.info("Copilotチャット収集完了: 有効なワークスペースが見つかりませんでした")

    def _parse_jsonl(self, content: str, target_date: str) -> list[dict]:
        """JSONL をレコードタイプに応じてパースし、対象日付のセッションを抽出・圧縮する.

        session.start / user.message / assistant.message / turn_start/end の
        各レコードタイプを解析し、不要なメタデータを除外して構造化データに圧縮する。

        Args:
            content: JSONL ファイルの内容
            target_date: 対象日（YYYY-MM-DD）

        Returns:
            圧縮されたセッションデータのリスト
        """
        raw_records: list[dict] = []
        for line_num, line in enumerate(content.split("\n"), 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                # 対象日付のレコードのみ抽出
                ts = record.get("timestamp", "")
                if ts.startswith(target_date):
                    record["_line"] = line_num
                    raw_records.append(record)
            except json.JSONDecodeError:
                logger.warning("JSONL パースエラー (行 %d): スキップします", line_num)
                continue

        if not raw_records:
            return []

        # レコードを時系列に処理してセッションを構築
        sessions: list[dict] = []
        current_session: dict | None = None
        current_turn_count = 0
        current_turn_active = False
        messages: list[dict] = []

        for record in raw_records:
            record_type = record.get("type", "")

            if record_type == "session.start":
                # 前のセッションを確定
                if current_session is not None:
                    current_session["turn_count"] = current_turn_count
                    current_session["messages"] = messages
                    # メッセージ内容を圧縮（各メッセージのcontent/reasoningを200文字に制限）
                    current_session["messages"] = self._truncate_messages(messages)
                    sessions.append(current_session)

                # 新しいセッションを開始
                data = record.get("data", {})
                current_session = {
                    "session_id": data.get("sessionId", ""),
                    "start_time": data.get("startTime", ""),
                    "copilot_version": data.get("copilotVersion", ""),
                    "vscode_version": data.get("vscodeVersion", ""),
                }
                current_turn_count = 0
                current_turn_active = False
                messages = []

            elif record_type == "user.message":
                content_text = record.get("data", {}).get("content", "")
                if content_text:
                    messages.append(
                        {
                            "role": "user",
                            "content": content_text,
                        }
                    )

            elif record_type == "assistant.message":
                data = record.get("data", {})
                reasoning_text = data.get("reasoningText", "")
                tool_requests = data.get("toolRequests", [])
                content_text = data.get("content", "")

                msg_entry: dict = {"role": "assistant"}

                if reasoning_text:
                    msg_entry["reasoning"] = reasoning_text
                if tool_requests:
                    tools_used = []
                    for tr in tool_requests:
                        args_raw = tr.get("arguments", {})
                        if isinstance(args_raw, str):
                            try:
                                args_raw = json.loads(args_raw)
                            except json.JSONDecodeError:
                                args_raw = {"raw": args_raw}
                        tools_used.append(
                            {
                                "name": tr.get("name", ""),
                                "arguments": args_raw,
                            }
                        )
                    msg_entry["tools_called"] = tools_used
                if content_text and content_text.strip():
                    msg_entry["content"] = content_text

                messages.append(msg_entry)

            elif record_type == "assistant.turn_start":
                current_turn_active = True

            elif record_type == "assistant.turn_end":
                if current_turn_active:
                    current_turn_count += 1
                    current_turn_active = False

        # 最後のセッションを確定
        if current_session is not None:
            current_session["turn_count"] = current_turn_count
            current_session["messages"] = self._truncate_messages(messages)
            sessions.append(current_session)

        return sessions

    def _truncate_messages(self, messages: list[dict], max_length: int = 500) -> list[dict]:
        """メッセージ内容を指定文字数に制限して圧縮する.

        Args:
            messages: メッセージリスト
            max_length: 各フィールドの最大文字数

        Returns:
            圧縮されたメッセージリスト
        """
        truncated = []
        for msg in messages:
            entry: dict = {"role": msg["role"]}
            for field in ("content", "reasoning"):
                val = msg.get(field, "")
                if val:
                    entry[field] = (val[:max_length] + "...") if len(val) > max_length else val
            tools = msg.get("tools_called", [])
            if tools:
                entry["tools_called"] = [
                    {
                        "name": t["name"],
                        "arguments": self._truncate_dict(t.get("arguments", {}), max_length=150),
                    }
                    for t in tools
                ]
            truncated.append(entry)
        return truncated

    def _truncate_dict(self, d: dict, max_length: int = 150) -> dict:
        """辞書の各値を指定文字数に制限する."""
        result = {}
        for k, v in d.items():
            if isinstance(v, str) and len(v) > max_length:
                result[k] = v[:max_length] + "..."
            elif isinstance(v, dict):
                result[k] = self._truncate_dict(v, max_length)
            else:
                result[k] = v
        return result

    def _format_sessions_for_llm(self, files: list[dict]) -> str:
        """圧縮されたセッションデータを LLM 入力用のテキストに変換する.

        compress_chatlog.py の要約フォーマットと同様の形式で出力する。

        Args:
            files: 収集ファイル情報のリスト

        Returns:
            LLM に入力するテキスト
        """
        all_lines: list[str] = []

        for file_info in files:
            for session in file_info.get("sessions", []):
                lines = []
                start_time = session.get("start_time", "N/A")
                lines.append("=== Copilot Chat Session ===")
                lines.append(f"Session: {session.get('session_id', 'N/A')}")
                lines.append(f"Start: {start_time}")
                lines.append(f"Turns: {session.get('turn_count', 0)}")
                if session.get("copilot_version"):
                    lines.append(f"Copilot: {session['copilot_version']}")
                if session.get("vscode_version"):
                    lines.append(f"VS Code: {session['vscode_version']}")
                lines.append("")

                for msg in session.get("messages", []):
                    role = msg["role"].upper()
                    if role == "USER":
                        content = msg.get("content", "")
                        lines.append("[USER]")
                        lines.append(f"  {content}")
                    elif role == "ASSISTANT":
                        reasoning = msg.get("reasoning", "")
                        tools = msg.get("tools_called", [])
                        content = msg.get("content", "")
                        lines.append("[ASSISTANT]")
                        if reasoning:
                            lines.append(f"  reasoning: {reasoning}")
                        if tools:
                            for t in tools:
                                args_str = json.dumps(t.get("arguments", {}), ensure_ascii=False)
                                lines.append(f"  -> {t['name']}({args_str})")
                        if content:
                            lines.append(f"  {content}")
                    lines.append("")

                all_lines.append("\n".join(lines))

        return "\n---\n\n".join(all_lines) if all_lines else ""

    def _extract_project_hints(self, raw: CollectedLog, analysis: str) -> list[dict]:
        """収集結果からプロジェクトヒントを抽出する.

        各ワークスペースの名前を candidate_name とし、LLM 解析結果のサマリーを
        activity_summary として格納した ProjectHint リストを生成する。

        Args:
            raw: 収集結果（CollectedLog）
            analysis: LLM による解析結果サマリー

        Returns:
            プロジェクトヒントのリスト
        """
        hints: list[dict] = []
        for ws in raw.workspaces:
            ws_name = ws.get("workspace_name", "")
            if ws_name:
                hints.append(
                    {
                        "source": "copilot_chat",
                        "candidate_name": ws_name,
                        "activity_summary": analysis,
                    }
                )
        if not hints and raw.files:
            # ワークスペース情報がない場合はファイルパスから推測
            hints.append(
                {
                    "source": "copilot_chat",
                    "candidate_name": "copilot_chat",
                    "activity_summary": analysis,
                }
            )
        return hints

    async def parse(
        self,
        raw: CollectedLog,
        llm: ChatOpenAI,
    ) -> ParsedData:
        """収集・圧縮したチャットログを LLM で解析する.

        Args:
            raw: 収集結果（CollectedLog）
            llm: LLM インスタンス

        Returns:
            解析結果（ParsedData）
        """
        if raw.is_empty:
            logger.info("Copilotチャットログが空のため解析をスキップします")
            return ParsedData(source=self.name)

        # 圧縮済みセッションデータを LLM 入力用テキストに変換
        text = self._format_sessions_for_llm(raw.files)

        if not text.strip():
            logger.info("Copilotチャットログが空のため解析をスキップします")
            return ParsedData(source=self.name)

        from dev_log_daily.llm.chunking import estimate_tokens, process_with_chunking
        from dev_log_daily.prompts.system import COLLECTOR_SYSTEM_PROMPT
        from dev_log_daily.prompts.templates import (
            COLLECTOR_COPILOT_CHAT_PROMPT,
            REDUCE_SUMMARIES_PROMPT,
        )

        estimated_tokens = estimate_tokens(text)

        map_prompt = COLLECTOR_COPILOT_CHAT_PROMPT.format(
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

        # 圧縮統計を構造化データに含める
        total_original = sum(f.get("compression", {}).get("original_bytes", 0) for f in raw.files)
        total_compressed = sum(
            f.get("compression", {}).get("compressed_bytes", 0) for f in raw.files
        )

        # プロジェクトヒント抽出
        project_hints = self._extract_project_hints(raw, analysis)

        return ParsedData(
            source=self.name,
            summary=analysis,
            chunks_processed=chunks_processed,
            structured_data={
                "file_count": len(raw.files),
                "session_count": sum(f.get("session_count", 0) for f in raw.files),
                "compression": {
                    "original_bytes": total_original,
                    "compressed_bytes": total_compressed,
                    "saved_pct": (100 - total_compressed * 100 // total_original)
                    if total_original > 0
                    else 0,
                },
            },
            token_count=estimated_tokens,
            project_hints=project_hints,
        )
