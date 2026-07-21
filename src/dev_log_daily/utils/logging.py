"""ロギング設定 — 標準出力への進捗表示用ロガー・ファイル出力用詳細ロガー."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def create_progress_logger(name: str = "dev_log_daily") -> logging.Logger:
    """標準出力への進捗表示用ロガーを作成する.

    メッセージは stdout に出力される。フォーマットはシンプルで、
    各ノードの開始・終了・エラーを逐次表示する用途を想定。

    Args:
        name: ロガー名

    Returns:
        設定済みの Logger インスタンス
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # ハンドラが既に設定されている場合は追加しない
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(message)s",  # メッセージのみ（タグは呼び出し元で付与）
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # 親ロガーへの伝播を防止
    logger.propagate = False

    return logger


def create_file_logger(
    log_file: str | Path,
    name: str = "dev_log_daily_detail",
) -> logging.Logger:
    """ファイル出力用詳細ロガーを作成する.

    タイムスタンプ・ログレベルを含む詳細な形式でファイルに出力。
    デバッグ・トラブルシューティング用途を想定。

    Args:
        log_file: ログファイルのパス
        name: ロガー名

    Returns:
        設定済みの Logger インスタンス
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(
            str(log_path),
            encoding="utf-8",
            mode="a",
        )
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False

    return logger


# デフォルトの進捗ロガー
_default_progress_logger = create_progress_logger()


def get_progress_logger() -> logging.Logger:
    """デフォルトの進捗ロガーを取得する."""
    return _default_progress_logger
