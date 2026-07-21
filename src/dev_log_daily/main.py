"""CLI エントリポイント — click を使用した dev-log-daily コマンド."""

from __future__ import annotations

import asyncio
import importlib.resources
import shutil
import sys
from datetime import datetime
from pathlib import Path

import click

from dev_log_daily.utils.date import get_previous_date
from dev_log_daily.utils.logging import create_progress_logger

console = create_progress_logger("dev_log_daily")


def _get_default_date() -> str:
    """システムローカルタイムゾーン基準の前日を YYYY-MM-DD 形式で返す."""
    return get_previous_date()


def _run_pipeline(config: str, target_date: str) -> None:
    """日報生成パイプラインを実行する（デフォルト動作）.

    Args:
        config: YAML設定ファイルのパス
        target_date: 日報対象日（YYYY-MM-DD）
    """
    # 日付形式の簡易検証
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        console.error(f"日付形式が不正です: {target_date}（YYYY-MM-DD 形式で指定してください）")
        sys.exit(1)

    # ヘッダー表示
    console.info("=" * 60)
    console.info("Dev Log Daily - 日報生成パイプライン")
    console.info("=" * 60)
    console.info(f"対象日: {target_date}")
    console.info("")

    # 設定ファイル読み込み
    try:
        from dev_log_daily.config.loader import load_config

        app_config = load_config(config)
    except SystemExit:
        sys.exit(1)
    except Exception as e:
        console.error(f"設定ファイル読み込みエラー: {e}")
        sys.exit(1)

    # パイプライン実行
    try:
        from dev_log_daily.agent import run_pipeline

        result = asyncio.run(run_pipeline(app_config, target_date))
    except Exception as e:
        console.error(f"パイプライン実行エラー: {e}")
        sys.exit(2)

    # エラーチェックと終了コード決定
    errors = result.get("errors", [])
    daily_report = result.get("daily_report", "")

    exit_code = _determine_exit_code(errors, daily_report, result)

    if exit_code == 0:
        if daily_report:
            console.info("")
            console.info("✅ 日報の生成が完了しました")
        else:
            console.info("")
            console.info("ℹ️  対象データがありません")
    elif exit_code == 2:
        console.error("")
        console.error("❌ LLMエラーが発生しました")
    elif exit_code == 3:
        console.error("")
        console.error("❌ 全データソースの収集に失敗しました")

    sys.exit(exit_code)


# ---------------------------------------------------------------------------
# init サブコマンド — パッケージ内スクリプトの管理
# ---------------------------------------------------------------------------


def _get_scripts_dir() -> Path:
    """パッケージ内 scripts/ ディレクトリの絶対パスを返す.

    Returns:
        scripts/ ディレクトリの Path オブジェクト

    Raises:
        FileNotFoundError: ディレクトリが存在しない場合
    """
    scripts_dir: Path = Path(str(importlib.resources.files("dev_log_daily") / "scripts"))
    if not scripts_dir.is_dir():
        raise FileNotFoundError(f"scripts/ ディレクトリが見つかりません: {scripts_dir}")
    return scripts_dir


def _validate_flag_exclusivity(
    show_paths: bool,
    export_post_commit: str | None,
    guide: bool,
) -> None:
    """init サブコマンドの排他フラグを検証する.

    複数のフラグが同時に指定された場合、エラーメッセージを表示して終了する.
    """
    flags = sum([show_paths, export_post_commit is not None, guide])
    if flags > 1:
        click.echo(
            "エラー: --show-paths, --export-post-commit, --guide は同時に指定できません",
            err=True,
        )
        sys.exit(1)


def _cmd_show_paths(scripts_dir: Path) -> None:
    """同梱スクリプトの絶対パスを表示する."""
    scripts = [
        ("log_terminal.sh", scripts_dir / "log_terminal.sh"),
        ("post-commit.sample", scripts_dir / "post-commit.sample"),
    ]
    for name, path in scripts:
        if path.exists():
            click.echo(f"{name}:\t{path.resolve()}")
        else:
            click.echo(f"{name}:\t[ファイルが見つかりません]", err=True)


def _cmd_export_post_commit(scripts_dir: Path, dest_dir_str: str) -> None:
    """post-commit.sample を指定ディレクトリにコピーする.

    Args:
        scripts_dir: パッケージ内 scripts/ ディレクトリ
        dest_dir_str: コピー先ディレクトリのパス文字列
    """
    dest_dir = Path(dest_dir_str).resolve()
    if not dest_dir.is_dir():
        click.echo(f"エラー: 指定されたディレクトリが存在しません: {dest_dir}", err=True)
        sys.exit(1)

    src = scripts_dir / "post-commit.sample"
    dest = dest_dir / "post-commit.sample"
    shutil.copy2(str(src), str(dest))
    click.echo(f"post-commit.sample を {dest_dir} にエクスポートしました。")
    click.echo("使用するにはファイル名を post-commit にリネームし、実行権限を付与してください:")
    click.echo(f"  mv {dest} {dest_dir}/post-commit")
    click.echo(f"  chmod +x {dest_dir}/post-commit")


def _cmd_guide(scripts_dir: Path) -> None:
    """セットアップ手順を表示する."""
    guide_text = f"""# Dev Log Daily — ログ収集セットアップガイド

## 1. ターミナルログ収集

以下の行を ~/.bashrc に追記してください:

  source {scripts_dir.resolve()}/log_terminal.sh

必要に応じて、log_terminal.sh 内の LOG_ROOT を実際のログ保存先に変更してください。

設定後、シェルを再起動するか以下を実行してください:

  source ~/.bashrc

## 2. Git post-commit hook

日報に Git コミットを含めたいプロジェクトで以下を実行してください:

  dev-log-daily init --export-post-commit /path/to/project/.git/hooks/
  mv /path/to/project/.git/hooks/post-commit.sample /path/to/project/.git/hooks/post-commit
  chmod +x /path/to/project/.git/hooks/post-commit

必要に応じて、post-commit 内の LOG_ROOT を編集してください。
"""
    click.echo(guide_text)


@click.group(
    name="dev-log-daily",
    invoke_without_command=True,
    help="開発活動ログ自動収集・日報生成ツール",
)
@click.option(
    "--config",
    type=click.Path(exists=False, dir_okay=False),
    default=None,
    help="YAML設定ファイルのパス（必須: サブコマンドなしの場合のみ）",
)
@click.option(
    "--date",
    type=str,
    default=None,
    help="日報対象日（YYYY-MM-DD）。省略時は前日。",
)
@click.pass_context
def main(ctx: click.Context, config: str | None, date: str | None) -> None:
    """dev-log-daily: 開発活動ログから日報を自動生成する.

    Args:
        ctx: click コンテキスト
        config: YAML設定ファイルのパス
        date: 日報対象日（省略時は前日）
    """
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["date"] = date

    # サブコマンドなし = デフォルトの日報生成
    if ctx.invoked_subcommand is None:
        if config is None:
            console.error("エラー: --config は必須です（日報生成を実行する場合）")
            sys.exit(1)
        target_date = date or _get_default_date()
        _run_pipeline(config, target_date)


def _determine_exit_code(
    errors: list[dict],
    daily_report: str,
    state: dict,
) -> int:
    """パイプライン実行結果から終了コードを決定する.

    Returns:
        0: 正常終了（日報生成成功 or 対象データなし）
        1: 起動時エラー（本関数では返さない）
        2: LLMエラー
        3: 全データソース収集失敗
    """
    # 全データソース収集失敗
    all_failed = any(e.get("error_type") == "AllSourcesFailed" for e in errors)
    if all_failed:
        return 3

    # LLM永久エラー（Parser/Enricher/Reporter）
    from dev_log_daily.llm.client import LLMPermanentError

    llm_permanent = any(e.get("error_type") == LLMPermanentError.__name__ for e in errors)
    from dev_log_daily.llm.client import LLMTemporaryError

    llm_temporary = any(e.get("error_type") == LLMTemporaryError.__name__ for e in errors)
    if llm_permanent or llm_temporary:
        return 2

    # 正常終了
    return 0


@main.command(
    name="init",
    help="パッケージ内スクリプトの管理・セットアップガイド表示",
)
@click.option(
    "--show-paths",
    is_flag=True,
    default=False,
    help="同梱スクリプトの絶対パスを表示",
)
@click.option(
    "--export-post-commit",
    type=str,
    default=None,
    metavar="DIR",
    help="post-commit.sample を指定ディレクトリにコピー",
)
@click.option(
    "--guide",
    is_flag=True,
    default=False,
    help="セットアップ手順を表示",
)
def init(
    show_paths: bool,
    export_post_commit: str | None,
    guide: bool,
) -> None:
    """dev-log-daily init: パッケージ内スクリプトを管理する.

    Args:
        show_paths: スクリプトの絶対パスを表示
        export_post_commit: post-commit.sample のコピー先ディレクトリ
        guide: セットアップ手順を表示
    """
    # 排他フラグ検証
    _validate_flag_exclusivity(show_paths, export_post_commit, guide)

    # scripts/ ディレクトリの解決
    try:
        scripts_dir = _get_scripts_dir()
    except FileNotFoundError as e:
        console.error(str(e))
        sys.exit(1)

    # 各フラグの処理
    if show_paths:
        _cmd_show_paths(scripts_dir)
    elif export_post_commit is not None:
        _cmd_export_post_commit(scripts_dir, export_post_commit)
    elif guide:
        _cmd_guide(scripts_dir)
    else:
        # フラグなしの場合は init --help を表示
        ctx = click.Context(main.commands["init"])
        click.echo(main.commands["init"].get_help(ctx))


if __name__ == "__main__":
    main()
