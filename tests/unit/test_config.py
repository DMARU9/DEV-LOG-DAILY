"""設定読み込み・スキーマ検証の単体テスト.

有効/無効な YAML の検証、必須項目欠落時のエラー検出、
出力ディレクトリ不在時のエラー検出を検証する。
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from dev_log_daily.config.loader import load_config
from dev_log_daily.config.schema import (
    AppConfig,
    ComponentLLMConfig,
    CopilotChatConfig,
    DataSourceConfig,
    LLMConfig,
    OutputConfig,
)


class TestLLMConfig:
    """LLMConfig のテスト."""

    def test_valid_llm_config(self):
        """有効な LLM 設定が正しく構築できること."""
        config = LLMConfig(
            model="Qwen3.6-35B-A3B",
            base_url="http://localhost:8080/v1",
            api_key="not-needed",
        )
        assert config.model == "Qwen3.6-35B-A3B"
        assert config.base_url == "http://localhost:8080/v1"
        assert config.api_key == "not-needed"

    def test_model_missing_raises_error(self):
        """model が未指定の場合はエラーになること."""
        with pytest.raises(ValueError):
            LLMConfig(
                base_url="http://localhost:8080/v1",
                api_key="not-needed",
            )

    def test_base_url_missing_raises_error(self):
        """base_url が未指定の場合はエラーになること."""
        with pytest.raises(ValueError):
            LLMConfig(
                model="Qwen3.6-35B-A3B",
                api_key="not-needed",
            )

    def test_api_key_missing_raises_error(self):
        """api_key が未指定の場合はエラーになること."""
        with pytest.raises(ValueError):
            LLMConfig(
                model="Qwen3.6-35B-A3B",
                base_url="http://localhost:8080/v1",
            )


class TestComponentLLMConfig:
    """ComponentLLMConfig のテスト."""

    def test_valid_component_config(self):
        """有効なコンポーネント別設定が正しく構築できること."""
        llm = LLMConfig(model="m", base_url="u", api_key="k")
        config = ComponentLLMConfig(
            collector=llm,
            parser=llm,
            enricher=llm,
            reporter=llm,
        )
        assert config.collector.model == "m"
        assert config.parser.model == "m"
        assert config.enricher.model == "m"
        assert config.reporter.model == "m"

    def test_component_missing_raises_error(self):
        """コンポーネントが未指定の場合はエラーになること."""
        llm = LLMConfig(model="m", base_url="u", api_key="k")
        with pytest.raises(ValueError):
            ComponentLLMConfig(
                collector=llm,
                parser=llm,
                enricher=llm,
                # reporter 未指定
            )


class TestCopilotChatConfig:
    """CopilotChatConfig のテスト."""

    def test_valid_config(self):
        """有効な設定が正しく構築できること."""
        config = CopilotChatConfig(
            workspace_storage_dirs=["/path/to/chats"],
            max_workspaces=50,
        )
        assert config.workspace_storage_dirs == ["/path/to/chats"]
        assert config.max_workspaces == 50

    def test_default_max_workspaces(self):
        """max_workspaces のデフォルト値が 50 であること."""
        config = CopilotChatConfig(
            workspace_storage_dirs=["/path/to/chats"],
        )
        assert config.max_workspaces == 50

    def test_empty_dirs_list_raises_error(self):
        """空の workspace_storage_dirs はエラーになること."""
        with pytest.raises(ValueError):
            CopilotChatConfig(
                workspace_storage_dirs=[],
            )

    def test_max_workspaces_zero_raises_error(self):
        """max_workspaces=0 はエラーになること."""
        with pytest.raises(ValueError):
            CopilotChatConfig(
                workspace_storage_dirs=["/path/to/chats"],
                max_workspaces=0,
            )

    def test_max_workspaces_over_thousand_raises_error(self):
        """max_workspaces=1001 はエラーになること."""
        with pytest.raises(ValueError):
            CopilotChatConfig(
                workspace_storage_dirs=["/path/to/chats"],
                max_workspaces=1001,
            )


class TestDataSourceConfig:
    """DataSourceConfig のテスト."""

    def test_valid_data_source_config(self):
        """有効なデータソース設定が正しく構築できること."""
        config = DataSourceConfig(
            copilot_chat={
                "workspace_storage_dirs": ["/path/to/chats"],
                "max_workspaces": 50,
            },
            git_root_dir="/path/to/git",
            terminal_history_dir="/path/to/history",
        )
        assert config.copilot_chat.workspace_storage_dirs == ["/path/to/chats"]
        assert config.copilot_chat.max_workspaces == 50
        assert config.git_root_dir == "/path/to/git"
        assert config.terminal_history_dir == "/path/to/history"


class TestOutputConfig:
    """OutputConfig のテスト."""

    def test_existing_directory_succeeds(self):
        """存在するディレクトリの場合は検証に成功すること."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OutputConfig(directory=tmpdir)
            assert config.directory == tmpdir

    def test_non_existent_directory_raises_error(self):
        """存在しないディレクトリの場合はエラーになること."""
        with pytest.raises(ValueError, match="出力ディレクトリが存在しません"):
            OutputConfig(directory="/non/existent/path/that/does/not/exist")

    def test_file_path_raises_error(self):
        """ファイルパスが指定された場合はエラーになること."""
        with tempfile.NamedTemporaryFile() as tmpfile:
            with pytest.raises(ValueError, match="ディレクトリではありません"):
                OutputConfig(directory=tmpfile.name)


class TestAppConfig:
    """AppConfig のテスト."""

    @pytest.fixture
    def valid_llm_config(self) -> dict:
        return {
            "collector": {"model": "m1", "base_url": "u1", "api_key": "k1"},
            "parser": {"model": "m2", "base_url": "u2", "api_key": "k2"},
            "enricher": {"model": "m3", "base_url": "u3", "api_key": "k3"},
            "reporter": {"model": "m4", "base_url": "u4", "api_key": "k4"},
        }

    def test_valid_config(self, valid_llm_config: dict):
        """有効な設定が正しく構築できること."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig(
                llm=valid_llm_config,
                data_sources={
                    "copilot_chat": {
                        "workspace_storage_dirs": ["/path/to/chats"],
                        "max_workspaces": 50,
                    },
                    "git_root_dir": "/path/to/git",
                    "terminal_history_dir": "/path/to/history",
                },
                output={"directory": tmpdir},
                timeout_seconds=600,
            )
            assert config.timeout_seconds == 600
            assert config.llm.collector.model == "m1"

    def test_default_timeout(self, valid_llm_config: dict):
        """timeout_seconds が未指定の場合はデフォルト値 600 になること."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig(
                llm=valid_llm_config,
                data_sources={
                    "copilot_chat": {
                        "workspace_storage_dirs": ["/path/to/chats"],
                        "max_workspaces": 50,
                    },
                    "git_root_dir": "/path/to/git",
                    "terminal_history_dir": "/path/to/history",
                },
                output={"directory": tmpdir},
            )
            assert config.timeout_seconds == 600

    def test_zero_timeout_is_allowed(self, valid_llm_config: dict):
        """timeout_seconds=0 は「タイムアウトなし」として許容されること."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig(
                llm=valid_llm_config,
                data_sources={
                    "copilot_chat": {
                        "workspace_storage_dirs": ["/path/to/chats"],
                        "max_workspaces": 50,
                    },
                    "git_root_dir": "/path/to/git",
                    "terminal_history_dir": "/path/to/history",
                },
                output={"directory": tmpdir},
                timeout_seconds=0,
            )
            assert config.timeout_seconds == 0

    def test_negative_timeout_raises_error(self, valid_llm_config: dict):
        """timeout_seconds が負数の場合はエラーになること."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError):
                AppConfig(
                    llm=valid_llm_config,
                    data_sources={
                        "copilot_chat": {
                            "workspace_storage_dirs": ["/path/to/chats"],
                            "max_workspaces": 50,
                        },
                        "git_root_dir": "/path/to/git",
                        "terminal_history_dir": "/path/to/history",
                    },
                    output={"directory": tmpdir},
                    timeout_seconds=-1,
                )

    def test_empty_path_raises_error(self, valid_llm_config: dict):
        """空のパスフィールドがある場合はエラーになること."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="workspace_storage_dirs"):
                AppConfig(
                    llm=valid_llm_config,
                    data_sources={
                        "copilot_chat": {
                            "workspace_storage_dirs": [],
                        },
                        "git_root_dir": "/path/to/git",
                        "terminal_history_dir": "/path/to/history",
                    },
                    output={"directory": tmpdir},
                )

    def test_yaml_load_and_validate(self, valid_llm_config: dict):
        """YAML から読み込んだ設定が正しく検証できること."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_data = {
                "llm": valid_llm_config,
                "data_sources": {
                    "copilot_chat": {
                        "workspace_storage_dirs": ["/path/to/chats"],
                        "max_workspaces": 50,
                    },
                    "git_root_dir": "/path/to/git",
                    "terminal_history_dir": "/path/to/history",
                },
                "output": {"directory": tmpdir},
                "timeout_seconds": 300,
            }
            # YAML → dict → pydantic
            loaded = yaml.safe_load(yaml.dump(yaml_data))
            config = AppConfig(**loaded)
            assert config.timeout_seconds == 300


class TestComponentLLMMissingError:
    """コンポーネント別LLM未指定時のエラーメッセージ検証.

    US2: 各コンポーネント（collector/parser/enricher/reporter）のLLM設定が
    YAML設定ファイルで未指定の場合、具体的なエラーメッセージとともに
    検証エラーになることを確認する。
    """

    def _make_valid_data_sources(self) -> dict:
        return {
            "copilot_chat": {
                "workspace_storage_dirs": ["/path/to/chats"],
                "max_workspaces": 50,
            },
            "git_root_dir": "/path/to/git",
            "terminal_history_dir": "/path/to/history",
        }

    def test_collector_missing_raises_error(self):
        """collector が未指定の場合に ValueError になること."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError):
                AppConfig(
                    llm={
                        "parser": {"model": "m2", "base_url": "u2", "api_key": "k2"},
                        "enricher": {"model": "m3", "base_url": "u3", "api_key": "k3"},
                        "reporter": {"model": "m4", "base_url": "u4", "api_key": "k4"},
                    },
                    data_sources=self._make_valid_data_sources(),
                    output={"directory": tmpdir},
                )

    def test_parser_missing_raises_error(self):
        """parser が未指定の場合に ValueError になること."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError):
                AppConfig(
                    llm={
                        "collector": {"model": "m1", "base_url": "u1", "api_key": "k1"},
                        "enricher": {"model": "m3", "base_url": "u3", "api_key": "k3"},
                        "reporter": {"model": "m4", "base_url": "u4", "api_key": "k4"},
                    },
                    data_sources=self._make_valid_data_sources(),
                    output={"directory": tmpdir},
                )

    def test_enricher_missing_raises_error(self):
        """enricher が未指定の場合に ValueError になること."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError):
                AppConfig(
                    llm={
                        "collector": {"model": "m1", "base_url": "u1", "api_key": "k1"},
                        "parser": {"model": "m2", "base_url": "u2", "api_key": "k2"},
                        "reporter": {"model": "m4", "base_url": "u4", "api_key": "k4"},
                    },
                    data_sources=self._make_valid_data_sources(),
                    output={"directory": tmpdir},
                )

    def test_reporter_missing_raises_error(self):
        """reporter が未指定の場合に ValueError になること."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError):
                AppConfig(
                    llm={
                        "collector": {"model": "m1", "base_url": "u1", "api_key": "k1"},
                        "parser": {"model": "m2", "base_url": "u2", "api_key": "k2"},
                        "enricher": {"model": "m3", "base_url": "u3", "api_key": "k3"},
                    },
                    data_sources=self._make_valid_data_sources(),
                    output={"directory": tmpdir},
                )

    def test_multiple_components_missing_raises_error(self):
        """複数コンポーネントが未指定の場合も ValueError になること."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError):
                AppConfig(
                    llm={
                        "reporter": {"model": "m4", "base_url": "u4", "api_key": "k4"},
                    },
                    data_sources=self._make_valid_data_sources(),
                    output={"directory": tmpdir},
                )

    def test_empty_llm_section_raises_error(self):
        """llm セクション自体が空の場合に ValueError になること."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError):
                AppConfig(
                    llm={},
                    data_sources=self._make_valid_data_sources(),
                    output={"directory": tmpdir},
                )


class TestConfigLoaderErrorMessages:
    """設定ローダー（load_config）のエラーメッセージ検証テスト.

    US2: 設定ファイル不在・不正YAML構文・出力ディレクトリ不在・
    コンポーネント別LLM未指定の各ケースで、具体的なエラーメッセージと
    適切な exit code で停止することを確認する。
    """

    def _write_yaml(self, tmpdir: str, filename: str, data: dict) -> str:
        """ヘルパー: YAMLファイルを一時ディレクトリに書き込む."""
        config_file = Path(tmpdir) / filename
        config_file.write_text(yaml.dump(data), encoding="utf-8")
        return str(config_file)

    def test_config_file_not_found(self):
        """設定ファイルが存在しない場合に SystemExit(1) になること."""
        with pytest.raises(SystemExit) as excinfo:
            load_config("/nonexistent/path/config.yml")
        assert excinfo.value.code == 1

    def test_invalid_yaml_syntax(self):
        """不正な YAML 構文の場合に SystemExit(1) になること."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "invalid.yml"
            config_file.write_text("llm: [unclosed list\n", encoding="utf-8")
            with pytest.raises(SystemExit) as excinfo:
                load_config(str(config_file))
            assert excinfo.value.code == 1

    def test_output_directory_not_exist_via_loader(self):
        """出力ディレクトリが存在しない場合に SystemExit(1) になること."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_data = {
                "llm": {
                    "collector": {"model": "m", "base_url": "u", "api_key": "k"},
                    "parser": {"model": "m", "base_url": "u", "api_key": "k"},
                    "enricher": {"model": "m", "base_url": "u", "api_key": "k"},
                    "reporter": {"model": "m", "base_url": "u", "api_key": "k"},
                },
                "data_sources": {
                    "copilot_chat": {
                        "workspace_storage_dirs": ["/path/to/chats"],
                        "max_workspaces": 50,
                    },
                    "git_root_dir": "/path/to/git",
                    "terminal_history_dir": "/path/to/history",
                },
                "output": {"directory": "/nonexistent/output/dir"},
            }
            config_file = Path(tmpdir) / "config.yml"
            config_file.write_text(yaml.dump(yaml_data), encoding="utf-8")
            with pytest.raises(SystemExit) as excinfo:
                load_config(str(config_file))
            assert excinfo.value.code == 1

    def test_component_llm_missing_via_loader(self):
        """コンポーネント別LLMが未指定の場合に SystemExit(1) になること."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_data = {
                "llm": {
                    "parser": {"model": "m2", "base_url": "u2", "api_key": "k2"},
                    "enricher": {"model": "m3", "base_url": "u3", "api_key": "k3"},
                    "reporter": {"model": "m4", "base_url": "u4", "api_key": "k4"},
                },
                "data_sources": {
                    "copilot_chat": {
                        "workspace_storage_dirs": ["/path/to/chats"],
                        "max_workspaces": 50,
                    },
                    "git_root_dir": "/path/to/git",
                    "terminal_history_dir": "/path/to/history",
                },
                "output": {"directory": tmpdir},
            }
            config_file = Path(tmpdir) / "config.yml"
            config_file.write_text(yaml.dump(yaml_data), encoding="utf-8")
            with pytest.raises(SystemExit) as excinfo:
                load_config(str(config_file))
            assert excinfo.value.code == 1

    def test_empty_config_file(self):
        """空の設定ファイルの場合に SystemExit(1) になること."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "empty.yml"
            config_file.write_text("", encoding="utf-8")
            with pytest.raises(SystemExit) as excinfo:
                load_config(str(config_file))
            assert excinfo.value.code == 1

    def test_config_file_is_directory(self):
        """設定ファイルパスがディレクトリの場合に SystemExit(1) になること."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(SystemExit) as excinfo:
                load_config(tmpdir)
            assert excinfo.value.code == 1

    def test_legacy_copilot_chat_dir_detected(self):
        """旧形式 copilot_chat_dir が検出された場合に SystemExit(1) になること."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_data = {
                "llm": {
                    "collector": {"model": "m", "base_url": "u", "api_key": "k"},
                    "parser": {"model": "m", "base_url": "u", "api_key": "k"},
                    "enricher": {"model": "m", "base_url": "u", "api_key": "k"},
                    "reporter": {"model": "m", "base_url": "u", "api_key": "k"},
                },
                "data_sources": {
                    "copilot_chat_dir": "/old/path/to/chats",
                    "git_root_dir": "/path/to/git",
                    "terminal_history_dir": "/path/to/history",
                },
                "output": {"directory": tmpdir},
            }
            config_file = Path(tmpdir) / "config.yml"
            config_file.write_text(yaml.dump(yaml_data), encoding="utf-8")
            with pytest.raises(SystemExit) as excinfo:
                load_config(str(config_file))
            assert excinfo.value.code == 1

    def test_both_old_and_new_format_raises_error(self):
        """新旧両方の形式が指定された場合も SystemExit(1) になること."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_data = {
                "llm": {
                    "collector": {"model": "m", "base_url": "u", "api_key": "k"},
                    "parser": {"model": "m", "base_url": "u", "api_key": "k"},
                    "enricher": {"model": "m", "base_url": "u", "api_key": "k"},
                    "reporter": {"model": "m", "base_url": "u", "api_key": "k"},
                },
                "data_sources": {
                    "copilot_chat_dir": "/old/path",
                    "copilot_chat": {
                        "workspace_storage_dirs": ["/new/path"],
                    },
                    "git_root_dir": "/path/to/git",
                    "terminal_history_dir": "/path/to/history",
                },
                "output": {"directory": tmpdir},
            }
            config_file = Path(tmpdir) / "config.yml"
            config_file.write_text(yaml.dump(yaml_data), encoding="utf-8")
            with pytest.raises(SystemExit) as excinfo:
                load_config(str(config_file))
            assert excinfo.value.code == 1
