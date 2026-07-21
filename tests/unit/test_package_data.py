"""パッケージデータ（scripts/）アクセスのユニットテスト."""

from __future__ import annotations

import importlib.resources
from pathlib import Path


def get_scripts_dir() -> Path:
    """importlib.resources を使って scripts/ ディレクトリのパスを取得する."""
    return importlib.resources.files("dev_log_daily") / "scripts"


class TestPackageDataResolution:
    """importlib.resources によるパス解決のテスト."""

    def test_scripts_directory_exists(self) -> None:
        """scripts/ ディレクトリが存在することを確認."""
        scripts_dir = get_scripts_dir()
        assert scripts_dir.is_dir(), f"scripts/ ディレクトリが存在しません: {scripts_dir}"

    def test_log_terminal_sh_exists(self) -> None:
        """log_terminal.sh が存在することを確認."""
        script_path = get_scripts_dir() / "log_terminal.sh"
        assert script_path.exists(), f"log_terminal.sh が存在しません: {script_path}"

    def test_post_commit_sample_exists(self) -> None:
        """post-commit.sample が存在することを確認."""
        script_path = get_scripts_dir() / "post-commit.sample"
        assert script_path.exists(), f"post-commit.sample が存在しません: {script_path}"

    def test_log_terminal_sh_is_file(self) -> None:
        """log_terminal.sh がファイルであることを確認."""
        script_path = get_scripts_dir() / "log_terminal.sh"
        assert script_path.is_file()

    def test_post_commit_sample_is_file(self) -> None:
        """post-commit.sample がファイルであることを確認."""
        script_path = get_scripts_dir() / "post-commit.sample"
        assert script_path.is_file()

    def test_scripts_dir_is_absolute(self) -> None:
        """scripts/ のパスが絶対パスであることを確認."""
        scripts_dir = get_scripts_dir()
        assert scripts_dir.is_absolute(), f"scripts/ のパスが絶対パスではありません: {scripts_dir}"


class TestPackageDataContent:
    """パッケージデータの内容検証."""

    def test_log_terminal_sh_content(self) -> None:
        """log_terminal.sh の内容が空でないことを確認."""
        content = (get_scripts_dir() / "log_terminal.sh").read_text(encoding="utf-8")
        assert len(content) > 0
        assert "#!/bin/bash" in content

    def test_post_commit_sample_content(self) -> None:
        """post-commit.sample の内容が空でないことを確認."""
        content = (get_scripts_dir() / "post-commit.sample").read_text(encoding="utf-8")
        assert len(content) > 0
        assert "post-commit" in content.lower() or "#!/bin/bash" in content


class TestPackageDataReadability:
    """異なる環境でのパッケージデータ読み取り可能性のテスト."""

    def test_readable_via_importlib_resources(self) -> None:
        """importlib.resources 経由でファイルを読み取れることを確認."""
        scripts_dir = importlib.resources.files("dev_log_daily") / "scripts"
        log_terminal = scripts_dir / "log_terminal.sh"
        content = log_terminal.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_multiple_reads_consistent(self) -> None:
        """複数回読み取っても内容が一貫していることを確認."""
        path = get_scripts_dir() / "log_terminal.sh"
        content1 = path.read_text(encoding="utf-8")
        content2 = path.read_text(encoding="utf-8")
        assert content1 == content2
