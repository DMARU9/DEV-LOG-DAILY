"""init サブコマンドのユニットテスト."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from dev_log_daily.main import main


@pytest.fixture
def runner() -> CliRunner:
    """Click テストランナー."""
    return CliRunner()


@pytest.fixture
def temp_dir() -> Path:
    """テスト用一時ディレクトリ."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


class TestInitShowPaths:
    """init --show-paths のテスト."""

    def test_show_paths_success(self, runner: CliRunner) -> None:
        """--show-paths がスクリプトの絶対パスを表示することを確認."""
        result = runner.invoke(main, ["init", "--show-paths"])
        assert result.exit_code == 0
        assert "log_terminal.sh" in result.output
        assert "post-commit.sample" in result.output
        # 絶対パスが表示されていることを確認
        for line in result.output.splitlines():
            if "log_terminal.sh" in line:
                assert "/" in line

    def test_show_paths_files_exist(self, runner: CliRunner) -> None:
        """表示されたパスが実在するファイルを指していることを確認."""
        result = runner.invoke(main, ["init", "--show-paths"])
        assert result.exit_code == 0
        for line in result.output.splitlines():
            if ":" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    path_str = parts[1].strip()
                    if path_str:
                        assert Path(path_str).exists(), f"パスが存在しません: {path_str}"


class TestInitExportPostCommit:
    """init --export-post-commit のテスト."""

    def test_export_to_existing_directory(self, runner: CliRunner, temp_dir: Path) -> None:
        """存在するディレクトリに post-commit.sample をコピーできることを確認."""
        result = runner.invoke(main, ["init", "--export-post-commit", str(temp_dir)])
        assert result.exit_code == 0
        dest_file = temp_dir / "post-commit.sample"
        assert dest_file.exists(), "post-commit.sample がコピーされていません"
        assert dest_file.stat().st_size > 0, "コピーされたファイルが空です"

    def test_export_to_nonexistent_directory(self, runner: CliRunner) -> None:
        """存在しないディレクトリを指定した場合エラーになることを確認."""
        nonexistent = "/tmp/nonexistent-dir-for-test-000"
        result = runner.invoke(main, ["init", "--export-post-commit", nonexistent])
        assert result.exit_code == 1
        assert "存在しない" in result.output or "存在" in result.output

    def test_export_content_match(self, runner: CliRunner, temp_dir: Path) -> None:
        """エクスポートされたファイルの内容が元と一致することを確認."""
        # まず show-paths で元のパスを取得
        show_result = runner.invoke(main, ["init", "--show-paths"])
        assert show_result.exit_code == 0
        source_path = None
        for line in show_result.output.splitlines():
            if "post-commit.sample" in line and ":" in line:
                source_path = line.split(":", 1)[1].strip()
                break
        assert source_path, "post-commit.sample のパスが取得できません"

        # エクスポート実行
        result = runner.invoke(main, ["init", "--export-post-commit", str(temp_dir)])
        assert result.exit_code == 0

        # 内容一致確認
        original = Path(source_path).read_bytes()
        exported = (temp_dir / "post-commit.sample").read_bytes()
        assert original == exported, "エクスポートされたファイルの内容が元と一致しません"


class TestInitGuide:
    """init --guide のテスト."""

    def test_guide_output(self, runner: CliRunner) -> None:
        """--guide がセットアップ手順を表示することを確認."""
        result = runner.invoke(main, ["init", "--guide"])
        assert result.exit_code == 0
        assert "セットアップ" in result.output or "setup" in result.output.lower()
        assert "log_terminal.sh" in result.output or ".bashrc" in result.output

    def test_guide_contains_export_info(self, runner: CliRunner) -> None:
        """--guide に post-commit のエクスポート手順が含まれていることを確認."""
        result = runner.invoke(main, ["init", "--guide"])
        assert result.exit_code == 0
        assert "post-commit" in result.output.lower()


class TestInitFlagExclusivity:
    """init フラグの排他制御テスト."""

    def test_multiple_flags_show_error(self, runner: CliRunner) -> None:
        """複数のフラグを同時に指定した場合エラーになることを確認."""
        result = runner.invoke(main, ["init", "--show-paths", "--guide"])
        assert result.exit_code != 0

    def test_show_paths_and_export_conflict(self, runner: CliRunner) -> None:
        """--show-paths と --export-post-commit の同時指定でエラーになることを確認."""
        result = runner.invoke(main, ["init", "--show-paths", "--export-post-commit", "/tmp"])
        assert result.exit_code != 0

    def test_export_and_guide_conflict(self, runner: CliRunner) -> None:
        """--export-post-commit と --guide の同時指定でエラーになることを確認."""
        result = runner.invoke(main, ["init", "--export-post-commit", "/tmp", "--guide"])
        assert result.exit_code != 0


class TestInitNoFlags:
    """フラグなしで init を実行した場合のテスト."""

    def test_init_without_flags_shows_usage(self, runner: CliRunner) -> None:
        """フラグなしの init が使用方法を表示することを確認."""
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        # --show-paths, --export-post-commit, --guide のいずれかのヘルプが表示される
        assert any(
            flag in result.output for flag in ["--show-paths", "--export-post-commit", "--guide"]
        )
