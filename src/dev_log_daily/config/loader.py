"""設定ファイルローダー — YAML読み込み・pydanticスキーマ検証・出力ディレクトリ確認."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from dev_log_daily.config.schema import AppConfig


def load_config(config_path: str) -> AppConfig:
    """YAML 設定ファイルを読み込み、pydantic スキーマで検証する.

    Args:
        config_path: YAML 設定ファイルのパス

    Returns:
        検証済みの AppConfig インスタンス

    Raises:
        SystemExit: 設定ファイルが存在しない・読み込めない・検証に失敗した場合（exit code 1）
    """
    config_file = Path(config_path)

    # 設定ファイルの存在確認
    if not config_file.exists():
        print(
            f"ERROR: 設定ファイルが見つかりません: {config_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not config_file.is_file():
        print(
            f"ERROR: 指定されたパスはファイルではありません: {config_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    # YAML 読み込み
    try:
        with open(config_file, encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(
            f"ERROR: YAML パースエラー: {config_path}\n  {e}",
            file=sys.stderr,
        )
        sys.exit(1)
    except OSError as e:
        print(
            f"ERROR: 設定ファイル読み込みエラー: {config_path}\n  {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    if raw_data is None:
        print(
            f"ERROR: 設定ファイルが空です: {config_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    # 旧形式 copilot_chat_dir の検出（廃止済み）
    data_sources = raw_data.get("data_sources") if isinstance(raw_data, dict) else None
    if isinstance(data_sources, dict) and "copilot_chat_dir" in data_sources:
        _print_migration_guidance(config_path)
        sys.exit(1)

    # データソースパスの存在確認（警告のみ、処理は続行）
    path_warnings = _check_data_source_paths(raw_data, config_file)
    for warning in path_warnings:
        print(f"  WARNING: {warning}", file=sys.stderr)

    # LLM設定の全件検証（pydantic検証前に一括チェック）
    llm_errors = _collect_llm_validation_errors(raw_data)
    if llm_errors:
        error_lines = "\n".join(f"  - {e}" for e in llm_errors)
        print(
            f"ERROR: 設定ファイルのLLM設定に誤りがあります:\n{error_lines}",
            file=sys.stderr,
        )
        sys.exit(1)

    # 出力ディレクトリの事前チェック（必須）
    output_dir = _extract_output_directory(raw_data)
    if output_dir:
        output_path = Path(output_dir)
        # 設定ファイルからの相対パスの場合、絶対パスに変換
        if not output_path.is_absolute():
            output_path = (config_file.parent / output_path).resolve()

        if not output_path.exists():
            print(
                f"出力ディレクトリが存在しません: {output_path}",
                file=sys.stderr,
            )
            sys.exit(1)

    # pydantic スキーマ検証
    try:
        config = AppConfig(**raw_data)
    except ValueError as e:
        print(
            f"ERROR: 設定ファイルの検証に失敗しました:\n  {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    return config


def _print_migration_guidance(config_path: str) -> None:
    """旧形式 copilot_chat_dir を検出した場合の移行案内を表示する.

    Args:
        config_path: 設定ファイルのパス（表示用）
    """
    print(
        "ERROR: data_sources.copilot_chat_dir は廃止されました。\n"
        "代わりに data_sources.copilot_chat.workspace_storage_dirs を使用してください。\n"
        "\n"
        "【移行手順】\n"
        f"1. {config_path} の copilot_chat_dir フィールドを削除\n"
        "2. 代わりに以下を追加:\n"
        "   data_sources:\n"
        "     copilot_chat:\n"
        "       workspace_storage_dirs:\n"
        "         - /home/user/.vscode-server/data/User/workspaceStorage\n",
        file=sys.stderr,
    )


def _collect_llm_validation_errors(raw_data: dict | None) -> list[str]:
    """LLM設定のバリデーションエラーを全件収集する.

    pydantic スキーマ検証の前に生データを検査し、LLM設定の
    全エラーを一括で検出する。これによりユーザーは最初のエラーだけでなく
    すべての設定ミスを一度に確認できる。

    Args:
        raw_data: YAML から読み込んだ生データ

    Returns:
        エラーメッセージのリスト（エラーがない場合は空リスト）
    """
    errors: list[str] = []

    if not isinstance(raw_data, dict):
        return errors

    llm = raw_data.get("llm")
    if not isinstance(llm, dict):
        errors.append("llm セクションが指定されていません")
        return errors

    component_names = ("collector", "parser", "enricher", "reporter")
    for name in component_names:
        component = llm.get(name)
        if not isinstance(component, dict):
            errors.append(f"llm.{name} が指定されていません")
            continue

        for field in ("model", "base_url", "api_key"):
            value = component.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"llm.{name}.{field} が指定されていません")

    return errors


def _check_data_source_paths(raw_data: dict | None, config_file: Path) -> list[str]:
    """データソースパスの存在を確認し、警告メッセージのリストを返す.

    設定ファイルに指定された各データソースパス
    （workspace_storage_dirs, git_root_dir, terminal_history_dir）
    が実際に存在するかを確認する。
    存在しない場合は警告メッセージを生成するが、処理は継続する。
    （該当ツールは Collector ノードでスキップされる）

    Args:
        raw_data: YAML から読み込んだ生データ
        config_file: 設定ファイルのパス（相対パス解決用）

    Returns:
        警告メッセージのリスト（警告がない場合は空リスト）
    """
    warnings: list[str] = []

    if not isinstance(raw_data, dict):
        return warnings

    data_sources = raw_data.get("data_sources")
    if not isinstance(data_sources, dict):
        return warnings

    # copilot_chat.workspace_storage_dirs（リスト形式）
    copilot_chat = data_sources.get("copilot_chat")
    if isinstance(copilot_chat, dict):
        ws_dirs = copilot_chat.get("workspace_storage_dirs", [])
        if isinstance(ws_dirs, list):
            for i, d in enumerate(ws_dirs):
                if isinstance(d, str) and d.strip():
                    path = Path(d)
                    if not path.is_absolute():
                        path = (config_file.parent / path).resolve()
                    if not path.exists():
                        warnings.append(f"workspaceStorageディレクトリ[{i}]が存在しません: {path}")

    path_fields = [
        ("git_root_dir", "Gitルートディレクトリ"),
        ("terminal_history_dir", "ターミナル履歴ディレクトリ"),
    ]

    for field, display_name in path_fields:
        value = data_sources.get(field)
        if isinstance(value, str) and value.strip():
            path = Path(value)
            if not path.is_absolute():
                path = (config_file.parent / path).resolve()
            if not path.exists():
                warnings.append(f"{display_name}が存在しません: {path}")

    return warnings


def _extract_output_directory(raw_data: dict | None) -> str | None:
    """生の YAML データから出力ディレクトリを安全に抽出する.

    pydantic 検証前でも出力ディレクトリの存在確認が行えるよう、
    YAML の生データから output.directory の値を取得する。

    Args:
        raw_data: YAML から読み込んだデータ

    Returns:
        出力ディレクトリのパス文字列（取得できない場合は None）
    """
    if not isinstance(raw_data, dict):
        return None
    output = raw_data.get("output")
    if not isinstance(output, dict):
        return None
    directory = output.get("directory")
    if isinstance(directory, str) and directory.strip():
        return directory.strip()
    return None
