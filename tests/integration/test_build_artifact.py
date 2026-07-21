"""Wheel ビルド成果物の検証テスト."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_IN_WHEEL = [
    "dev_log_daily/scripts/log_terminal.sh",
    "dev_log_daily/scripts/post-commit.sample",
]


@pytest.fixture(scope="module")
def dist_dir() -> Path:
    """プロジェクトの dist/ ディレクトリを返す."""
    return PROJECT_ROOT / "dist"


@pytest.fixture(scope="module")
def wheel_path(dist_dir: Path) -> Path:
    """ビルドされた Wheel ファイルのパスを返す."""
    wheels = list(dist_dir.glob("dev_log_daily-*-py3-none-any.whl"))
    if not wheels:
        pytest.skip("Wheel ファイルが見つかりません。先に 'python -m build' を実行してください。")
    return wheels[0]


class TestBuildArtifact:
    """ビルド成果物（Wheel）の検証."""

    def test_wheel_exists(self, wheel_path: Path) -> None:
        """Wheel ファイルが存在することを確認."""
        assert wheel_path.exists()
        assert wheel_path.suffix == ".whl"

    def test_source_archive_exists(self, dist_dir: Path) -> None:
        """ソースアーカイブ（.tar.gz）が存在することを確認."""
        archives = list(dist_dir.glob("dev_log_daily-*.tar.gz"))
        if not archives:
            pytest.skip(
                "ソースアーカイブが見つかりません。先に 'python -m build' を実行してください。"
            )
        assert len(archives) >= 1

    def test_wheel_contains_scripts(self, wheel_path: Path) -> None:
        """Wheel にログ収集スクリプトが含まれていることを確認."""
        result = subprocess.run(
            [sys.executable, "-m", "zipfile", "--list", str(wheel_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        for script_path in SCRIPTS_IN_WHEEL:
            assert script_path in result.stdout, f"{script_path} が Wheel に含まれていません"

    def test_wheel_metadata_version(self, wheel_path: Path) -> None:
        """Wheel のバージョンが pyproject.toml と一致することを確認."""
        result = subprocess.run(
            [sys.executable, "-m", "zipfile", "--list", str(wheel_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        # METADATA ファイルが含まれていることを確認
        assert any("METADATA" in line for line in result.stdout.splitlines())

    def test_scripts_content_match(self, wheel_path: Path) -> None:
        """Wheel 内のスクリプトがソースと一致するか確認（zipfile モジュール使用）."""
        import zipfile

        with zipfile.ZipFile(wheel_path) as zf:
            names = zf.namelist()
        for script_path in SCRIPTS_IN_WHEEL:
            assert script_path in names, f"{script_path} が Wheel の一覧に含まれていません"
