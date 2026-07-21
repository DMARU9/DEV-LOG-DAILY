"""結合テスト用の共通フィクスチャ.

テスト用の一時ディレクトリ・サンプルデータ・Gitリポジトリなどを提供する。
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """テスト用の一時ディレクトリを作成する.

    Yields:
        一時ディレクトリの絶対パス文字列
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_chat_dir(temp_dir: str) -> str:
    """サンプルCopilotチャットログディレクトリを作成する.

    実際のCopilot JSONL形式（session.start / user.message / assistant.message /
    turn_start / turn_end）に準拠したトランスクリプトを作成する。

    Args:
        temp_dir: テスト用一時ディレクトリ

    Returns:
        チャットログディレクトリの絶対パス
    """
    chat_dir = Path(temp_dir) / "copilot_chats"
    chat_dir.mkdir(parents=True, exist_ok=True)

    # 2026-06-19 のセッションを含むファイル
    date19_lines = []
    # セッション s001（セッション開始 → ユーザー質問 → AI回答 → ターン終了）
    date19_lines.append(
        '{"type":"session.start","data":{"sessionId":"s001","version":1,'
        '"producer":"copilot-agent","copilotVersion":"0.53.0",'
        '"vscodeVersion":"1.125.0","startTime":"2026-06-19T09:15:00.000Z"},'
        '"timestamp":"2026-06-19T09:15:00.000Z"}'
    )
    date19_lines.append(
        '{"type":"user.message","data":{"content":"Pythonの非同期処理について"},'
        '"timestamp":"2026-06-19T09:15:10.000Z"}'
    )
    date19_lines.append(
        '{"type":"assistant.turn_start","data":{"turnId":"0"},'
        '"timestamp":"2026-06-19T09:15:10.000Z"}'
    )
    date19_lines.append(
        '{"type":"assistant.message","data":{"messageId":"m001","content":"",'
        '"reasoningText":"ユーザーがPythonの非同期処理について質問しています。'
        'asyncioライブラリの基本的な使い方を説明しましょう。"},'
        '"timestamp":"2026-06-19T09:15:11.000Z"}'
    )
    date19_lines.append(
        '{"type":"assistant.message","data":{"messageId":"m002",'
        '"content":"asyncioを使います。async/awaitキーワードで非同期関数を定義します。"},'
        '"timestamp":"2026-06-19T09:15:12.000Z"}'
    )
    date19_lines.append(
        '{"type":"assistant.turn_end","data":{"turnId":"0"},"timestamp":"2026-06-19T09:15:12.000Z"}'
    )
    # セッション s002（別の会話）
    date19_lines.append(
        '{"type":"session.start","data":{"sessionId":"s002","version":1,'
        '"producer":"copilot-agent","copilotVersion":"0.53.0",'
        '"vscodeVersion":"1.125.0","startTime":"2026-06-19T11:30:00.000Z"},'
        '"timestamp":"2026-06-19T11:30:00.000Z"}'
    )
    date19_lines.append(
        '{"type":"user.message","data":{"content":"FastAPIのバリデーションについて教えて"},'
        '"timestamp":"2026-06-19T11:30:05.000Z"}'
    )
    date19_lines.append(
        '{"type":"assistant.turn_start","data":{"turnId":"0"},'
        '"timestamp":"2026-06-19T11:30:05.000Z"}'
    )
    date19_lines.append(
        '{"type":"assistant.message","data":{"messageId":"m003",'
        '"content":"Pydanticモデルを使ってリクエストボディのバリデーションができます。"'
        ',"toolRequests":[{"toolCallId":"tc001","name":"read_file",'
        '"arguments":"{\\"filePath\\":\\"/src/main.py\\"}"}]},'
        '"timestamp":"2026-06-19T11:30:10.000Z"}'
    )
    date19_lines.append(
        '{"type":"assistant.turn_end","data":{"turnId":"0"},"timestamp":"2026-06-19T11:30:12.000Z"}'
    )
    (chat_dir / "2026-06-19.jsonl").write_text("\n".join(date19_lines) + "\n", encoding="utf-8")

    # 2026-06-18 のセッション（フィルタリング対象外）
    date18_lines = [
        '{"type":"session.start","data":{"sessionId":"s003","version":1,'
        '"producer":"copilot-agent","copilotVersion":"0.53.0",'
        '"vscodeVersion":"1.125.0","startTime":"2026-06-18T22:00:00.000Z"},'
        '"timestamp":"2026-06-18T22:00:00.000Z"}',
        '{"type":"user.message","data":{"content":"TypeScriptのジェネリクス"},'
        '"timestamp":"2026-06-18T22:00:10.000Z"}',
        '{"type":"assistant.turn_start","data":{"turnId":"0"},'
        '"timestamp":"2026-06-18T22:00:10.000Z"}',
        '{"type":"assistant.message","data":{"messageId":"m004",'
        '"content":"TypeScriptでは、ジェネリクスを使って型安全なコンポーネントを作成できます。"},'
        '"timestamp":"2026-06-18T22:00:15.000Z"}',
        '{"type":"assistant.turn_end","data":{"turnId":"0"},'
        '"timestamp":"2026-06-18T22:00:16.000Z"}',
    ]
    (chat_dir / "2026-06-18.jsonl").write_text("\n".join(date18_lines) + "\n", encoding="utf-8")

    # 複数日付混在ファイル
    mixed_lines = [
        # 2026-06-19 のセッション
        '{"type":"session.start","data":{"sessionId":"s004","copilotVersion":"0.53.0",'
        '"startTime":"2026-06-19T14:00:00.000Z"},'
        '"timestamp":"2026-06-19T14:00:00.000Z"}',
        '{"type":"user.message","data":{"content":"Docker Composeで複数サービス"},'
        '"timestamp":"2026-06-19T14:00:10.000Z"}',
        '{"type":"assistant.turn_start","data":{"turnId":"0"},'
        '"timestamp":"2026-06-19T14:00:10.000Z"}',
        '{"type":"assistant.message","data":{"content":"docker-compose.ymlに各サービスを定義します。"},'
        '"timestamp":"2026-06-19T14:00:15.000Z"}',
        '{"type":"assistant.turn_end","data":{"turnId":"0"},'
        '"timestamp":"2026-06-19T14:00:16.000Z"}',
        # 2026-06-20 のセッション（フィルタリング対象外）
        '{"type":"session.start","data":{"sessionId":"s005","copilotVersion":"0.53.0",'
        '"startTime":"2026-06-20T08:00:00.000Z"},'
        '"timestamp":"2026-06-20T08:00:00.000Z"}',
        '{"type":"user.message","data":{"content":"Rustの所有権システム"},'
        '"timestamp":"2026-06-20T08:00:10.000Z"}',
        '{"type":"assistant.turn_start","data":{"turnId":"0"},'
        '"timestamp":"2026-06-20T08:00:10.000Z"}',
        '{"type":"assistant.message","data":{"content":"所有権はRustの中心的な概念です。"},'
        '"timestamp":"2026-06-20T08:00:15.000Z"}',
        '{"type":"assistant.turn_end","data":{"turnId":"0"},'
        '"timestamp":"2026-06-20T08:00:16.000Z"}',
        # 2026-06-19 の別セッション
        '{"type":"session.start","data":{"sessionId":"s006","copilotVersion":"0.53.0",'
        '"startTime":"2026-06-19T16:45:00.000Z"},'
        '"timestamp":"2026-06-19T16:45:00.000Z"}',
        '{"type":"user.message","data":{"content":"今日の開発のまとめ"},'
        '"timestamp":"2026-06-19T16:45:10.000Z"}',
        '{"type":"assistant.turn_start","data":{"turnId":"0"},'
        '"timestamp":"2026-06-19T16:45:10.000Z"}',
        '{"type":"assistant.message","data":{"content":"いくつかのタスクを進めました。"},'
        '"timestamp":"2026-06-19T16:45:15.000Z"}',
        '{"type":"assistant.turn_end","data":{"turnId":"0"},'
        '"timestamp":"2026-06-19T16:45:16.000Z"}',
    ]
    (chat_dir / "mixed.jsonl").write_text("\n".join(mixed_lines) + "\n", encoding="utf-8")

    return str(chat_dir)


@pytest.fixture
def sample_git_repo(temp_dir: str) -> str:
    """サンプルGitリポジトリを作成する（親ディレクトリを返す）.

    temp_dir 配下に複数のGitリポジトリを作成し、対象日付のコミットを含める。

    Args:
        temp_dir: テスト用一時ディレクトリ

    Returns:
        親ディレクトリの絶対パス（この配下にGitリポジトリが存在する）
    """
    # リポジトリ1: project-a
    repo_a = Path(temp_dir) / "repos" / "project-a"
    repo_a.mkdir(parents=True, exist_ok=True)
    _init_git_repo(repo_a, target_date="2026-06-19")

    # リポジトリ2: nested/project-b（ネスト構造のテスト用）
    repo_b = Path(temp_dir) / "repos" / "nested" / "project-b"
    repo_b.mkdir(parents=True, exist_ok=True)
    _init_git_repo(repo_b, target_date="2026-06-19")

    # 親ディレクトリを返す
    return str(Path(temp_dir) / "repos")


def _init_git_repo(repo_path: Path, target_date: str) -> None:
    """指定パスにGitリポジトリを初期化し、対象日付のコミットを作成する.

    Args:
        repo_path: リポジトリを作成するパス
        target_date: コミットの日付（YYYY-MM-DD）
    """
    git = ["git", "-C", str(repo_path)]

    # git init
    subprocess.run([*git, "init", "--initial-branch=main"], capture_output=True, check=True)

    # ユーザー設定（テスト用）
    subprocess.run(
        [*git, "config", "user.email", "test@example.com"], capture_output=True, check=True
    )
    subprocess.run([*git, "config", "user.name", "Test User"], capture_output=True, check=True)

    # 日付を環境変数で設定
    env = os.environ.copy()
    # 最初のコミット: 別日付（フィルタリング対象外）を最初に作成し、時系列順にする
    env_old = os.environ.copy()
    env_old["GIT_AUTHOR_DATE"] = "2026-06-18T09:00:00+09:00"
    env_old["GIT_COMMITTER_DATE"] = "2026-06-18T09:00:00+09:00"
    old_file = repo_path / "old.py"
    old_file.write_text("# old file\n")
    subprocess.run([*git, "add", "old.py"], capture_output=True, check=True)
    subprocess.run(
        [*git, "commit", "-m", "Old commit from yesterday"],
        capture_output=True,
        check=True,
        env=env_old,
    )

    # 2番目のコミット: 対象日の初期セットアップ
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = f"{target_date}T10:00:00+09:00"
    env["GIT_COMMITTER_DATE"] = f"{target_date}T10:00:00+09:00"
    readme = repo_path / "README.md"
    readme.write_text(f"# Project {repo_path.name}\n")
    subprocess.run([*git, "add", "README.md"], capture_output=True, check=True)
    subprocess.run(
        [*git, "commit", "-m", "Initial commit: project setup"],
        capture_output=True,
        check=True,
        env=env,
    )

    # 3番目のコミット（機能追加）— HEAD はこの最も新しいコミットを指す
    src_dir = repo_path / "src"
    src_dir.mkdir(exist_ok=True)
    main_py = src_dir / "main.py"
    main_py.write_text("def main():\n    print('Hello')\n")
    subprocess.run([*git, "add", "src/main.py"], capture_output=True, check=True)

    env_new = os.environ.copy()
    env_new["GIT_AUTHOR_DATE"] = f"{target_date}T14:00:00+09:00"
    env_new["GIT_COMMITTER_DATE"] = f"{target_date}T14:00:00+09:00"
    subprocess.run(
        [*git, "commit", "-m", "Add main module with hello function"],
        capture_output=True,
        check=True,
        env=env_new,
    )


@pytest.fixture
def sample_terminal_dir(temp_dir: str) -> str:
    """サンプルターミナル履歴ディレクトリを作成する.

    日付ごとのJSONLファイル（history_YYYY-MM-DD.jsonl）を作成する。

    Args:
        temp_dir: テスト用一時ディレクトリ

    Returns:
        履歴ディレクトリの絶対パス
    """
    history_dir = Path(temp_dir) / "terminal_history"
    history_dir.mkdir(parents=True, exist_ok=True)

    # 2026-06-19 の履歴
    date19_entries = [
        '{"timestamp":"2026-06-19T09:00:00+09:00","command":"cd ~/github/myproject","exit_code":0,"cwd":"/home/user","git_branch":"main"}',  # noqa: E501
        '{"timestamp":"2026-06-19T09:05:00+09:00","command":"git status","exit_code":0,"cwd":"/home/user/myproject","git_branch":"main"}',  # noqa: E501
        '{"timestamp":"2026-06-19T09:10:00+09:00","command":"git checkout -b feature/new","exit_code":0,"cwd":"/home/user/myproject","git_branch":"main"}',  # noqa: E501
        '{"timestamp":"2026-06-19T10:30:00+09:00","command":"python -m venv .venv","exit_code":0,"cwd":"/home/user/myproject","git_branch":"feature/new"}',  # noqa: E501
        '{"timestamp":"2026-06-19T10:35:00+09:00","command":"source .venv/bin/activate","exit_code":0,"cwd":"/home/user/myproject","git_branch":"feature/new"}',  # noqa: E501
        '{"timestamp":"2026-06-19T11:00:00+09:00","command":"pip install fastapi","exit_code":0,"cwd":"/home/user/myproject","git_branch":"feature/new"}',  # noqa: E501
        '{"timestamp":"2026-06-19T14:00:00+09:00","command":"docker compose up -d","exit_code":0,"cwd":"/home/user/myproject","git_branch":"feature/new"}',  # noqa: E501
        '{"timestamp":"2026-06-19T15:00:00+09:00","command":"git add .","exit_code":0,"cwd":"/home/user/myproject","git_branch":"feature/new"}',  # noqa: E501
        '{"timestamp":"2026-06-19T15:05:00+09:00","command":"git commit -m \'Add new feature\'","exit_code":0,"cwd":"/home/user/myproject","git_branch":"feature/new"}',  # noqa: E501
        '{"timestamp":"2026-06-19T16:00:00+09:00","command":"pytest tests/","exit_code":0,"cwd":"/home/user/myproject","git_branch":"feature/new"}',  # noqa: E501
    ]
    (history_dir / "history_2026-06-19.jsonl").write_text(
        "\n".join(date19_entries) + "\n", encoding="utf-8"
    )

    # 2026-06-18 の履歴（フィルタリング対象外）
    date18_entries = [
        '{"timestamp":"2026-06-18T09:00:00+09:00","command":"cd ~/github/other","exit_code":0,"cwd":"/home/user","git_branch":"main"}',  # noqa: E501
        '{"timestamp":"2026-06-18T09:30:00+09:00","command":"npm install","exit_code":0,"cwd":"/home/user/other","git_branch":"main"}',  # noqa: E501
    ]
    (history_dir / "history_2026-06-18.jsonl").write_text(
        "\n".join(date18_entries) + "\n", encoding="utf-8"
    )

    # 2026-06-20 の履歴（フィルタリング対象外）
    date20_entries = [
        '{"timestamp":"2026-06-20T09:00:00+09:00","command":"cd ~/github/devlog","exit_code":0,"cwd":"/home/user","git_branch":"main"}',  # noqa: E501
    ]
    (history_dir / "history_2026-06-20.jsonl").write_text(
        "\n".join(date20_entries) + "\n", encoding="utf-8"
    )

    return str(history_dir)


@pytest.fixture
def config_for_tools(temp_dir: str) -> dict:
    """テスト用の設定データを提供する.

    Args:
        temp_dir: テスト用一時ディレクトリ

    Returns:
        設定データの dict（AppConfig の raw 形式）
    """
    chat_dir = Path(temp_dir) / "copilot_chats"
    chat_dir.mkdir(parents=True, exist_ok=True)

    repos_dir = Path(temp_dir) / "repos"
    repos_dir.mkdir(parents=True, exist_ok=True)

    return {
        "llm": {
            "collector": {
                "model": "test-model",
                "base_url": "http://test:8080/v1",
                "api_key": "test-key",
            },
            "parser": {
                "model": "test-model",
                "base_url": "http://test:8080/v1",
                "api_key": "test-key",
            },
            "enricher": {
                "model": "test-model",
                "base_url": "http://test:8080/v1",
                "api_key": "test-key",
            },
            "reporter": {
                "model": "test-model",
                "base_url": "http://test:8080/v1",
                "api_key": "test-key",
            },
        },
        "data_sources": {
            "copilot_chat": {
                "workspace_storage_dirs": [str(chat_dir)],
                "max_workspaces": 50,
            },
            "git_root_dir": str(repos_dir),
            "terminal_history_dir": str(Path(temp_dir) / "terminal_history"),
        },
        "output": {
            "directory": temp_dir,
        },
        "timeout_seconds": 600,
    }


# ---------------------------------------------------------------------------
# workspaceStorage フィクスチャ（複数ワークスペース対応 US1/US2/US3 用）
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace_storage_base_dir(temp_dir: str) -> str:
    """workspaceStorage ベースディレクトリを作成する（3 つのワークスペース + α）.

    以下の構造を作成:
    {temp_dir}/workspaceStorage/
      {uuid-a}/
        workspace.json
        GitHub.copilot-chat/transcripts/
          chat.jsonl  ← target_date のセッション
      {uuid-b}/
        workspace.json
        chatSessions/  ← Windows パス
          chat.jsonl  ← target_date のセッション
      {uuid-c}/
        workspace.json
        GitHub.copilot-chat/transcripts/
          chat.jsonl  ← target_date のセッション
      empty-workspace/
        workspace.json
        （transcripts/ も chatSessions/ もなし → スキップ対象）

    Args:
        temp_dir: テスト用一時ディレクトリ

    Returns:
        workspaceStorage ベースディレクトリの絶対パス
    """
    import json

    base_dir = Path(temp_dir) / "workspaceStorage"
    base_dir.mkdir(parents=True, exist_ok=True)

    workspaces = {
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa": {
            "folder": "/home/user/projects/frontend",
            "platform": "linux",
        },
        "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb": {
            "folder": "/home/user/projects/backend",
            "platform": "windows",
        },
        "cccccccc-cccc-cccc-cccc-cccccccccccc": {
            "folder": "/home/user/projects/docs",
            "platform": "linux",
        },
        "empty-workspace": {
            "folder": "/home/user/projects/empty",
            "platform": "linux",
            "skip_transcripts": True,
        },
    }

    target_date = "2026-06-22"

    for uuid, info in workspaces.items():
        ws_dir = base_dir / uuid
        ws_dir.mkdir(parents=True, exist_ok=True)

        # workspace.json
        ws_json = {"workspace": {"folder": info["folder"]}}
        (ws_dir / "workspace.json").write_text(json.dumps(ws_json), encoding="utf-8")

        if info.get("skip_transcripts"):
            continue

        # プラットフォーム別のパス
        if info["platform"] == "linux":
            transcript_dir = ws_dir / "GitHub.copilot-chat" / "transcripts"
        else:
            transcript_dir = ws_dir / "chatSessions"
        transcript_dir.mkdir(parents=True, exist_ok=True)

        # サンプルセッションを作成
        session_id = f"session-{uuid[:8]}"
        lines = [
            f'{{"type":"session.start","data":{{"sessionId":"{session_id}","version":1,'
            f'"producer":"copilot-agent","copilotVersion":"0.53.0",'
            f'"vscodeVersion":"1.125.0","startTime":"{target_date}T09:00:00.000Z"}},'
            f'"timestamp":"{target_date}T09:00:00.000Z"}}',
            f'{{"type":"user.message","data":{{"content":"{info["folder"]} の質問"}},'
            f'"timestamp":"{target_date}T09:00:10.000Z"}}',
            f'{{"type":"assistant.turn_start","data":{{"turnId":"0"}},'
            f'"timestamp":"{target_date}T09:00:10.000Z"}}',
            f'{{"type":"assistant.message","data":{{"messageId":"m-{uuid[:8]}","content":"回答内容"}},'
            f'"timestamp":"{target_date}T09:00:15.000Z"}}',
            f'{{"type":"assistant.turn_end","data":{{"turnId":"0"}},'
            f'"timestamp":"{target_date}T09:00:16.000Z"}}',
        ]
        (transcript_dir / f"chat_{target_date}.jsonl").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

    return str(base_dir)


@pytest.fixture
def config_with_workspace_storage(temp_dir: str, workspace_storage_base_dir: str) -> dict:
    """workspaceStorage ベースディレクトリを使用するテスト用設定.

    Args:
        temp_dir: テスト用一時ディレクトリ
        workspace_storage_base_dir: workspaceStorage ベースディレクトリ

    Returns:
        設定データの dict
    """
    return {
        "llm": {
            "collector": {
                "model": "test-model",
                "base_url": "http://test:8080/v1",
                "api_key": "test-key",
            },
            "parser": {
                "model": "test-model",
                "base_url": "http://test:8080/v1",
                "api_key": "test-key",
            },
            "enricher": {
                "model": "test-model",
                "base_url": "http://test:8080/v1",
                "api_key": "test-key",
            },
            "reporter": {
                "model": "test-model",
                "base_url": "http://test:8080/v1",
                "api_key": "test-key",
            },
        },
        "data_sources": {
            "copilot_chat": {
                "workspace_storage_dirs": [workspace_storage_base_dir],
                "max_workspaces": 50,
            },
            "git_root_dir": str(Path(temp_dir) / "repos"),
            "terminal_history_dir": str(Path(temp_dir) / "terminal_history"),
        },
        "output": {
            "directory": temp_dir,
        },
        "timeout_seconds": 600,
    }


# ---------------------------------------------------------------------------
# workspaceStorage フィクスチャ（US3: クロスプラットフォーム対応）
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace_storage_second_base_dir(temp_dir: str) -> str:
    """2つ目の workspaceStorage ベースディレクトリ（US3 用）.

    最初のベースディレクトリと以下の関係を持つ:
    - aaaaaaaa-...: 同一 UUID（マージテスト用） — Windows パス
    - dddddddd-...: 新規 UUID（ディスジョイントテスト用）
    - aaaaaaaa-... のセッション sessionId が同一（重複排除テスト用）

    Args:
        temp_dir: テスト用一時ディレクトリ

    Returns:
        2つ目の workspaceStorage ベースディレクトリの絶対パス
    """
    import json as _json

    base_dir = Path(temp_dir) / "workspaceStorage_Windows"
    base_dir.mkdir(parents=True, exist_ok=True)

    workspaces = {
        # 同一 UUID（最初のベースディレクトリと共通）→ マージテスト用
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa": {
            "folder": "/mnt/c/Users/takumi/projects/frontend",
            "platform": "windows",
            "dedup_session": True,  # 同一 sessionId を含む
        },
        # 新規 UUID（ディスジョイント）
        "dddddddd-dddd-dddd-dddd-dddddddddddd": {
            "folder": "/home/user/projects/mobile",
            "platform": "linux",
        },
    }

    target_date = "2026-06-22"

    for uuid, info in workspaces.items():
        ws_dir = base_dir / uuid
        ws_dir.mkdir(parents=True, exist_ok=True)

        # workspace.json
        ws_json = {"workspace": {"folder": info["folder"]}}
        (ws_dir / "workspace.json").write_text(_json.dumps(ws_json), encoding="utf-8")

        # プラットフォーム別のパス
        if info["platform"] == "linux":
            transcript_dir = ws_dir / "GitHub.copilot-chat" / "transcripts"
        else:
            transcript_dir = ws_dir / "chatSessions"
        transcript_dir.mkdir(parents=True, exist_ok=True)

        # サンプルセッションを作成
        if info.get("dedup_session"):
            # 重複排除テスト用: 最初のベースディレクトリと同じ sessionId
            session_id = "session-aaaaaaaa"
            lines = [
                f'{{"type":"session.start","data":{{"sessionId":"{session_id}","version":1,'
                f'"producer":"copilot-agent","copilotVersion":"0.53.0",'
                f'"vscodeVersion":"1.125.0","startTime":"{target_date}T09:00:00.000Z"}},'
                f'"timestamp":"{target_date}T09:00:00.000Z"}}',
                f'{{"type":"user.message","data":{{"content":"{info["folder"]} の重複質問"}},'
                f'"timestamp":"{target_date}T09:00:10.000Z"}}',
                f'{{"type":"assistant.turn_start","data":{{"turnId":"0"}},'
                f'"timestamp":"{target_date}T09:00:10.000Z"}}',
                f'{{"type":"assistant.message","data":{{"messageId":"m-dup-{uuid[:8]}","content":"重複回答"}},'
                f'"timestamp":"{target_date}T09:00:15.000Z"}}',
                f'{{"type":"assistant.turn_end","data":{{"turnId":"0"}},'
                f'"timestamp":"{target_date}T09:00:16.000Z"}}',
            ]
            # 同一 sessionId のセッション + ユニークな別セッション
            other_session_id = f"session-{uuid[:8]}-other"
            lines.extend(
                [
                    f'{{"type":"session.start","data":{{"sessionId":"{other_session_id}","version":1,'
                    f'"producer":"copilot-agent","copilotVersion":"0.53.0",'
                    f'"vscodeVersion":"1.125.0","startTime":"{target_date}T10:00:00.000Z"}},'
                    f'"timestamp":"{target_date}T10:00:00.000Z"}}',
                    f'{{"type":"user.message","data":{{"content":"{info["folder"]} の別質問"}},'
                    f'"timestamp":"{target_date}T10:00:10.000Z"}}',
                    f'{{"type":"assistant.turn_start","data":{{"turnId":"0"}},'
                    f'"timestamp":"{target_date}T10:00:10.000Z"}}',
                    f'{{"type":"assistant.message","data":{{"messageId":"m-other-{uuid[:8]}","content":"別回答"}},'
                    f'"timestamp":"{target_date}T10:00:15.000Z"}}',
                    f'{{"type":"assistant.turn_end","data":{{"turnId":"0"}},'
                    f'"timestamp":"{target_date}T10:00:16.000Z"}}',
                ]
            )
        else:
            session_id = f"session-{uuid[:8]}"
            lines = [
                f'{{"type":"session.start","data":{{"sessionId":"{session_id}","version":1,'
                f'"producer":"copilot-agent","copilotVersion":"0.53.0",'
                f'"vscodeVersion":"1.125.0","startTime":"{target_date}T09:00:00.000Z"}},'
                f'"timestamp":"{target_date}T09:00:00.000Z"}}',
                f'{{"type":"user.message","data":{{"content":"{info["folder"]} の質問"}},'
                f'"timestamp":"{target_date}T09:00:10.000Z"}}',
                f'{{"type":"assistant.turn_start","data":{{"turnId":"0"}},'
                f'"timestamp":"{target_date}T09:00:10.000Z"}}',
                f'{{"type":"assistant.message","data":{{"messageId":"m-{uuid[:8]}","content":"回答内容"}},'
                f'"timestamp":"{target_date}T09:00:15.000Z"}}',
                f'{{"type":"assistant.turn_end","data":{{"turnId":"0"}},'
                f'"timestamp":"{target_date}T09:00:16.000Z"}}',
            ]
        (transcript_dir / f"chat_{target_date}.jsonl").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

    return str(base_dir)


@pytest.fixture
def config_with_dual_workspace_storage(
    temp_dir: str,
    workspace_storage_base_dir: str,
    workspace_storage_second_base_dir: str,
) -> dict:
    """2つの workspaceStorage ベースディレクトリを使用するテスト用設定（US3 用）.

    Args:
        temp_dir: テスト用一時ディレクトリ
        workspace_storage_base_dir: 1つ目のベースディレクトリ
        workspace_storage_second_base_dir: 2つ目のベースディレクトリ

    Returns:
        設定データの dict（2つのベースディレクトリを含む）
    """
    return {
        "llm": {
            "collector": {
                "model": "test-model",
                "base_url": "http://test:8080/v1",
                "api_key": "test-key",
            },
            "parser": {
                "model": "test-model",
                "base_url": "http://test:8080/v1",
                "api_key": "test-key",
            },
            "enricher": {
                "model": "test-model",
                "base_url": "http://test:8080/v1",
                "api_key": "test-key",
            },
            "reporter": {
                "model": "test-model",
                "base_url": "http://test:8080/v1",
                "api_key": "test-key",
            },
        },
        "data_sources": {
            "copilot_chat": {
                "workspace_storage_dirs": [
                    workspace_storage_base_dir,
                    workspace_storage_second_base_dir,
                ],
                "max_workspaces": 50,
            },
            "git_root_dir": str(Path(temp_dir) / "repos"),
            "terminal_history_dir": str(Path(temp_dir) / "terminal_history"),
        },
        "output": {
            "directory": temp_dir,
        },
        "timeout_seconds": 600,
    }
