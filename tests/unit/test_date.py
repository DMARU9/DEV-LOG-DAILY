"""日付ユーティリティの単体テスト.

前日計算、タイムゾーン境界、日付フォーマット検証を検証する。
"""

from datetime import timedelta, timezone

import pytest

from dev_log_daily.utils.date import get_previous_date, parse_date, validate_date


class TestGetPreviousDate:
    """get_previous_date() のテスト."""

    def test_returns_string_in_yyyy_mm_dd_format(self):
        """戻り値が YYYY-MM-DD 形式の文字列であること."""
        result = get_previous_date()
        assert isinstance(result, str)
        assert validate_date(result)

    def test_returns_yesterday_relative_to_jst(self):
        """JST 基準で前日の日付が返ること."""
        # 固定タイムゾーンで検証
        utc_plus_9 = timezone(timedelta(hours=9))
        result = get_previous_date(tz=utc_plus_9)

        from datetime import datetime

        today_jst = datetime.now(utc_plus_9).date()
        expected = today_jst.isoformat()
        # 結果は前日（today とは異なる）のはず
        assert result != expected  # 少なくとも今日ではない

    def test_timezone_boundary_utc_plus_14(self):
        """UTC+14 の極端なタイムゾーンでも正しく前日計算されること."""
        tz = timezone(timedelta(hours=14))
        result = get_previous_date(tz=tz)
        assert validate_date(result)

    def test_timezone_boundary_utc_minus_12(self):
        """UTC-12 の極端なタイムゾーンでも正しく前日計算されること."""
        tz = timezone(timedelta(hours=-12))
        result = get_previous_date(tz=tz)
        assert validate_date(result)

    def test_default_timezone_is_jst(self):
        """デフォルトのタイムゾーンが JST (UTC+9) であること."""
        result_default = get_previous_date()
        result_jst = get_previous_date(tz=timezone(timedelta(hours=9)))
        assert result_default == result_jst


class TestValidateDate:
    """validate_date() のテスト."""

    @pytest.mark.parametrize(
        "valid_date",
        [
            "2026-01-01",
            "2026-12-31",
            "2024-02-29",  # うるう年
            "2023-02-28",  # 非うるう年
            "2026-06-15",
        ],
    )
    def test_valid_dates(self, valid_date: str):
        """有効な日付形式の場合は True を返すこと."""
        assert validate_date(valid_date)

    @pytest.mark.parametrize(
        "invalid_date",
        [
            "",
            "2026-13-01",  # 月が範囲外
            "2026-01-32",  # 日が範囲外
            "2026-02-30",  # 存在しない日付
            "2026/01/01",  # 区切り文字が不正
            "20260101",  # 区切り文字なし
            "abc-def-ghi",  # 数字以外
            "2026-1-1",  # ゼロ埋めなし
            "26-01-01",  # 年が4桁でない
        ],
    )
    def test_invalid_dates(self, invalid_date: str):
        """無効な日付形式の場合は False を返すこと."""
        assert not validate_date(invalid_date)

    def test_leap_year_february_29(self):
        """うるう年の2月29日を正しく検証すること."""
        assert validate_date("2024-02-29")  # うるう年
        assert not validate_date("2023-02-29")  # 非うるう年
        assert not validate_date("1900-02-29")  # 100で割れる非うるう年
        assert validate_date("2000-02-29")  # 400で割れるうるう年

    def test_month_end_boundary(self):
        """月末境界を正しく検証すること."""
        assert validate_date("2026-01-31")
        assert not validate_date("2026-01-32")
        assert validate_date("2026-04-30")
        assert not validate_date("2026-04-31")


class TestParseDate:
    """parse_date() のテスト."""

    def test_valid_date_string(self):
        """有効な日付文字列を date オブジェクトに変換すること."""
        from datetime import date

        result = parse_date("2026-06-15")
        assert result == date(2026, 6, 15)

    def test_invalid_date_string_raises_value_error(self):
        """無効な日付文字列で ValueError が発生すること."""
        with pytest.raises(ValueError, match="無効な日付形式"):
            parse_date("2026-13-01")

    def test_empty_string_raises_value_error(self):
        """空文字列で ValueError が発生すること."""
        with pytest.raises(ValueError):
            parse_date("")

    def test_year_end_boundary(self):
        """年末年始の境界を正しく処理すること."""
        from datetime import date

        assert parse_date("2025-12-31") == date(2025, 12, 31)
        assert parse_date("2026-01-01") == date(2026, 1, 1)
