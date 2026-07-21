"""pydantic 設定スキーマ — YAML 設定ファイルの検証・読み込みに使用."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


class LLMConfig(BaseModel):
    """LLM 接続設定."""

    model: str = Field(..., description="モデル名（例: Qwen3.6-35B-A3B）")
    base_url: str = Field(..., description="APIベースURL（例: http://localhost:8080/v1）")
    api_key: str = Field(..., description="APIキー（llama.cpp の場合は not-needed 等）")
    max_input_tokens: int = Field(
        default=131072,
        description="モデルのコンテキストウィンドウサイズ（入力最大トークン数）",
        ge=1024,
    )
    max_output_tokens: int = Field(
        default=16384,
        description="生成応答の最大トークン数",
        ge=256,
    )

    @model_validator(mode="before")
    @classmethod
    def validate_required_fields(cls, data: Any) -> Any:
        """必須フィールドを検証し、日本語エラーメッセージを提供する."""
        if not isinstance(data, dict):
            return data
        for field in ("model", "base_url", "api_key"):
            value = data.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"{field} が指定されていません")
        return data


class ComponentLLMConfig(BaseModel):
    """コンポーネント別 LLM 設定."""

    collector: LLMConfig = Field(..., description="Collector ノード用 LLM")
    parser: LLMConfig = Field(..., description="Parser ノード用 LLM")
    enricher: LLMConfig = Field(..., description="Enricher ノード用 LLM")
    reporter: LLMConfig = Field(..., description="Reporter ノード用 LLM")

    @model_validator(mode="before")
    @classmethod
    def validate_components(cls, data: Any) -> Any:
        """全コンポーネントの存在を検証し、日本語エラーメッセージを提供する."""
        if not isinstance(data, dict):
            return data
        for name in ("collector", "parser", "enricher", "reporter"):
            if name not in data or data.get(name) is None:
                raise ValueError(f"llm.{name} が指定されていません")
        return data


class CopilotChatConfig(BaseModel):
    """CopilotChat データソース設定 — 複数ワークスペースストレージ対応."""

    workspace_storage_dirs: list[str] = Field(
        ...,
        description="workspaceStorage ベースディレクトリのリスト（絶対パス）",
        min_length=1,
    )
    max_workspaces: int = Field(
        default=50,
        description="処理するワークスペース数の上限",
        ge=1,
        le=1000,
    )


class DataSourceConfig(BaseModel):
    """データソースパス設定."""

    copilot_chat: CopilotChatConfig = Field(
        ...,
        description="CopilotChat データソース設定（複数ワークスペース対応）",
    )
    git_root_dir: str = Field(
        ...,
        description="Gitリポジトリ親ディレクトリ（配下を再帰探索）",
    )
    terminal_history_dir: str = Field(
        ...,
        description="ターミナル履歴ディレクトリ（history_YYYY-MM-DD.jsonl ファイル格納先）",
    )


class OutputConfig(BaseModel):
    """出力設定."""

    directory: str = Field(..., description="日報出力ディレクトリ（絶対パス推奨）")

    @model_validator(mode="after")
    def validate_directory_exists(self) -> OutputConfig:
        """出力ディレクトリが存在することを検証する."""
        path = Path(self.directory)
        if not path.exists():
            raise ValueError(f"出力ディレクトリが存在しません: {self.directory}")
        if not path.is_dir():
            raise ValueError(f"出力パスがディレクトリではありません: {self.directory}")
        return self


class AppConfig(BaseModel):
    """アプリケーション設定 — YAML 設定ファイルのルートモデル."""

    llm: ComponentLLMConfig = Field(..., description="コンポーネント別 LLM 設定")
    data_sources: DataSourceConfig = Field(..., description="データソースパス設定")
    output: OutputConfig = Field(..., description="出力設定")
    timeout_seconds: int = Field(
        default=600,
        description="LLMリクエストタイムアウト（秒）。0 の場合はタイムアウトなし（無制限待機）",
        ge=0,
    )

    @model_validator(mode="before")
    @classmethod
    def validate_llm_section(cls, data: Any) -> Any:
        """llm セクションの存在を検証し、日本語エラーメッセージを提供する."""
        if not isinstance(data, dict):
            return data
        if "llm" not in data or data.get("llm") is None:
            raise ValueError("llm セクションが指定されていません")
        return data

    @model_validator(mode="after")
    def validate_all_paths_not_empty(self) -> AppConfig:
        """全パスフィールドが空でないことを検証する."""
        # copilot_chat.workspace_storage_dirs（リスト型）
        ws_dirs = self.data_sources.copilot_chat.workspace_storage_dirs
        if not ws_dirs:
            raise ValueError(
                "data_sources.copilot_chat.workspace_storage_dirs が指定されていません"
            )
        for d in ws_dirs:
            if not d.strip():
                raise ValueError(
                    "data_sources.copilot_chat.workspace_storage_dirs に空文字列が含まれています"
                )

        string_paths = {
            "data_sources.git_root_dir": self.data_sources.git_root_dir,
            "data_sources.terminal_history_dir": self.data_sources.terminal_history_dir,
            "output.directory": self.output.directory,
        }
        for field_name, value in string_paths.items():
            if not value or not value.strip():
                raise ValueError(f"{field_name} が指定されていません")
        return self
