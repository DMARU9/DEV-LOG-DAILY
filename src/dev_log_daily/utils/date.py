"""日付ユーティリティ — タイムゾーンに基づく前日計算・日付文字列処理."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta, timezone

# YYYY-MM-DD 形式の正規表現パターン
_DATE_PATTERN = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$")

# 日本標準時（UTC+9）をデフォルトのタイムゾーンとして使用
_JST = timezone(timedelta(hours=9))


def get_system_timezone() -> timezone:
    """システムのローカルタイムゾーンを取得する.

    OS のタイムゾーン設定から UTC オフセットを動的に計算する。

    Returns:
        システムのローカルタイムゾーン
    """
    local_offset = datetime.now(UTC).astimezone().utcoffset()
    if local_offset is None:
        return _JST
    return timezone(local_offset)


def get_previous_date(tz: timezone | None = None) -> str:
    """システムローカルタイムゾーンに基づく前日の日付を YYYY-MM-DD 形式で返す.

    Args:
        tz: 基準とするタイムゾーン（None の場合はシステムローカルを使用）

    Returns:
        前日の日付文字列（YYYY-MM-DD 形式）
    """
    if tz is None:
        tz = get_system_timezone()
    today = datetime.now(tz).date()
    yesterday = today - timedelta(days=1)
    return yesterday.isoformat()


def validate_date(date_str: str) -> bool:
    """与えられた文字列が YYYY-MM-DD 形式の有効な日付か検証する.

    Args:
        date_str: 検証する日付文字列

    Returns:
        有効な日付形式の場合は True
    """
    if not _DATE_PATTERN.match(date_str):
        return False
    try:
        year, month, day = map(int, date_str.split("-"))
        date(year, month, day)
        return True
    except (ValueError, OverflowError):
        return False


def parse_date(date_str: str) -> date:
    """YYYY-MM-DD 形式の文字列を date オブジェクトに変換する.

    Args:
        date_str: 日付文字列（YYYY-MM-DD 形式）

    Returns:
        変換された date オブジェクト

    Raises:
        ValueError: 無効な日付形式の場合
    """
    if not validate_date(date_str):
        raise ValueError(f"無効な日付形式です: {date_str}（YYYY-MM-DD 形式で指定してください）")
    year, month, day = map(int, date_str.split("-"))
    return date(year, month, day)
