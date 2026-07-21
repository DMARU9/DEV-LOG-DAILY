"""LLM クライアントの単体テスト.

リトライ戦略（一時的エラー最大3回、永続エラー即時停止）、
タイムアウト処理、エラー分類を検証する。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dev_log_daily.llm.client import (
    LLMPermanentError,
    LLMTemporaryError,
    call_llm_with_retry,
    classify_llm_error,
    create_llm,
)


class TestClassifyLLMError:
    """classify_llm_error() のテスト."""

    def test_none_status_returns_temporary(self):
        """ステータスコード None（タイムアウト等）は一時的エラーと判定されること."""
        assert classify_llm_error(None, "timeout error") == LLMTemporaryError

    def test_429_returns_temporary(self):
        """429（レート制限）は一時的エラーと判定されること."""
        assert classify_llm_error(429, "rate limit") == LLMTemporaryError

    def test_500_returns_temporary(self):
        """500（サーバーエラー）は一時的エラーと判定されること."""
        assert classify_llm_error(500, "internal server error") == LLMTemporaryError

    def test_503_returns_temporary(self):
        """503（サービス利用不可）は一時的エラーと判定されること."""
        assert classify_llm_error(503, "service unavailable") == LLMTemporaryError

    def test_400_returns_permanent(self):
        """400（Bad Request）は永続エラーと判定されること."""
        assert classify_llm_error(400, "bad request") == LLMPermanentError

    def test_401_returns_permanent(self):
        """401（Unauthorized）は永続エラーと判定されること."""
        assert classify_llm_error(401, "unauthorized") == LLMPermanentError

    def test_403_returns_permanent(self):
        """403（Forbidden）は永続エラーと判定されること."""
        assert classify_llm_error(403, "forbidden") == LLMPermanentError

    def test_404_returns_permanent(self):
        """404（Not Found）等の他4xxは永続エラーと判定されること."""
        assert classify_llm_error(404, "not found") == LLMPermanentError

    def test_422_returns_permanent(self):
        """422（Unprocessable Entity）は永続エラーと判定されること."""
        assert classify_llm_error(422, "unprocessable") == LLMPermanentError


class TestCreateLLM:
    """create_llm() のテスト."""

    def test_creates_chat_openai_instance(self):
        """create_llm() が ChatOpenAI インスタンスを返すこと."""
        with patch("dev_log_daily.llm.client.ChatOpenAI") as mock_chat:
            mock_instance = MagicMock()
            mock_chat.return_value = mock_instance

            result = create_llm(
                model="test-model",
                base_url="http://test:8080/v1",
                api_key="test-key",
                temperature=0.0,
                timeout=600,
                max_retries=0,
            )

            assert result is mock_instance
            mock_chat.assert_called_once()
            call_kwargs = mock_chat.call_args.kwargs
            assert call_kwargs["model"] == "test-model"
            assert call_kwargs["base_url"] == "http://test:8080/v1"
            assert call_kwargs["temperature"] == 0.0
            assert call_kwargs["timeout"] == 600
            assert call_kwargs["max_retries"] == 0

    def test_default_parameters(self):
        """create_llm() がデフォルトパラメータで正しく動作すること."""
        with patch("dev_log_daily.llm.client.ChatOpenAI") as mock_chat:
            mock_instance = MagicMock()
            mock_chat.return_value = mock_instance

            result = create_llm(
                model="test-model",
                base_url="http://test:8080/v1",
                api_key="test-key",
            )

            assert result is mock_instance
            mock_chat.assert_called_once()
            call_kwargs = mock_chat.call_args.kwargs
            assert call_kwargs["model"] == "test-model"
            assert call_kwargs["base_url"] == "http://test:8080/v1"
            assert call_kwargs["temperature"] == 0.0
            assert call_kwargs["timeout"] == 600
            assert call_kwargs["max_retries"] == 0


class TestCallLLMWithRetry:
    """call_llm_with_retry() のリトライ戦略テスト."""

    @pytest.fixture
    def mock_llm(self) -> MagicMock:
        """モック LLM インスタンス."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_success_on_first_try(self, mock_llm: MagicMock):
        """1回目の呼び出しで成功した場合、その結果が返されること."""
        mock_response = MagicMock()
        mock_response.content = "正常な応答"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await call_llm_with_retry(
            mock_llm,
            [{"role": "user", "content": "hello"}],
            max_retries=3,
        )

        assert result == "正常な応答"
        assert mock_llm.ainvoke.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_temporary_error_then_success(self, mock_llm: MagicMock):
        """一時的エラー（429）後にリトライが成功すること."""
        mock_response = MagicMock()
        mock_response.content = "リトライ後の応答"

        class RateLimitError(Exception):
            pass

        rate_error = RateLimitError("rate limit exceeded")
        rate_error.status_code = 429  # type: ignore[union-attr]

        mock_llm.ainvoke = AsyncMock(side_effect=[rate_error, rate_error, mock_response])

        result = await call_llm_with_retry(
            mock_llm,
            [{"role": "user", "content": "hello"}],
            max_retries=3,
        )

        assert result == "リトライ後の応答"
        assert mock_llm.ainvoke.call_count == 3

    @pytest.mark.asyncio
    async def test_exhaust_retries_raises_temporary_error(self, mock_llm: MagicMock):
        """リトライ上限到達後、LLMTemporaryError が送出されること."""

        class ServerError(Exception):
            pass

        server_error = ServerError("internal server error")
        server_error.status_code = 500  # type: ignore[union-attr]

        mock_llm.ainvoke = AsyncMock(side_effect=server_error)

        with pytest.raises(LLMTemporaryError) as exc_info:
            await call_llm_with_retry(
                mock_llm,
                [{"role": "user", "content": "hello"}],
                max_retries=2,
                base_delay=0.01,
            )

        assert "リトライ 2/2 失敗" in str(exc_info.value)
        assert mock_llm.ainvoke.call_count == 3  # 初回 + 2回リトライ

    @pytest.mark.asyncio
    async def test_permanent_error_stops_immediately(self, mock_llm: MagicMock):
        """永続エラー（400）は即座に LLMPermanentError が送出されること."""

        class BadRequestError(Exception):
            pass

        bad_request = BadRequestError("bad request")
        bad_request.status_code = 400  # type: ignore[union-attr]

        mock_llm.ainvoke = AsyncMock(side_effect=bad_request)

        with pytest.raises(LLMPermanentError) as exc_info:
            await call_llm_with_retry(
                mock_llm,
                [{"role": "user", "content": "hello"}],
                max_retries=3,
                base_delay=0.01,
            )

        assert "HTTP 400" in str(exc_info.value)
        # リトライは行われない
        assert mock_llm.ainvoke.call_count == 1

    @pytest.mark.asyncio
    async def test_unauthorized_stops_immediately(self, mock_llm: MagicMock):
        """401（Unauthorized）は即座に LLMPermanentError が送出されること."""

        class AuthError(Exception):
            pass

        auth_error = AuthError("invalid API key")
        auth_error.status_code = 401  # type: ignore[union-attr]

        mock_llm.ainvoke = AsyncMock(side_effect=auth_error)

        with pytest.raises(LLMPermanentError) as exc_info:
            await call_llm_with_retry(
                mock_llm,
                [{"role": "user", "content": "hello"}],
                max_retries=3,
                base_delay=0.01,
            )

        assert "HTTP 401" in str(exc_info.value)
        assert mock_llm.ainvoke.call_count == 1

    @pytest.mark.asyncio
    async def test_forbidden_stops_immediately(self, mock_llm: MagicMock):
        """403（Forbidden）は即座に LLMPermanentError が送出されること."""

        class ForbiddenError(Exception):
            pass

        forbidden_error = ForbiddenError("forbidden")
        forbidden_error.status_code = 403  # type: ignore[union-attr]

        mock_llm.ainvoke = AsyncMock(side_effect=forbidden_error)

        with pytest.raises(LLMPermanentError) as exc_info:
            await call_llm_with_retry(
                mock_llm,
                [{"role": "user", "content": "hello"}],
                max_retries=3,
                base_delay=0.01,
            )

        assert "HTTP 403" in str(exc_info.value)
        assert mock_llm.ainvoke.call_count == 1

    @pytest.mark.asyncio
    async def test_network_timeout_retried(self, mock_llm: MagicMock):
        """ネットワークタイムアウト（status_code None）はリトライされること."""
        mock_response = MagicMock()
        mock_response.content = "タイムアウト後復帰"

        class TimeoutError(Exception):
            pass

        timeout_error = TimeoutError("timeout")
        # status_code なし（None 扱い）

        mock_llm.ainvoke = AsyncMock(side_effect=[timeout_error, timeout_error, mock_response])

        result = await call_llm_with_retry(
            mock_llm,
            [{"role": "user", "content": "hello"}],
            max_retries=3,
            base_delay=0.01,
        )

        assert result == "タイムアウト後復帰"
        assert mock_llm.ainvoke.call_count == 3

    @pytest.mark.asyncio
    async def test_exponential_backoff_delays(self, mock_llm: MagicMock):
        """リトライ間隔が指数バックオフになっていること（base_delay * 2^attempt）."""

        class ServerError(Exception):
            pass

        server_error = ServerError("server error")
        server_error.status_code = 500  # type: ignore[union-attr]

        mock_llm.ainvoke = AsyncMock(side_effect=server_error)

        with (
            patch("dev_log_daily.llm.client.asyncio.sleep") as mock_sleep,
            pytest.raises(LLMTemporaryError),
        ):
            await call_llm_with_retry(
                mock_llm,
                [{"role": "user", "content": "hello"}],
                max_retries=3,
                base_delay=1.0,
            )

        # 指数バックオフ: 1.0, 2.0, 4.0
        assert mock_sleep.call_count == 3
        mock_sleep.assert_any_call(1.0)
        mock_sleep.assert_any_call(2.0)
        mock_sleep.assert_any_call(4.0)

    @pytest.mark.asyncio
    async def test_response_content_as_list_of_strings(self, mock_llm: MagicMock):
        """LLM 応答が文字列リスト形式でも正しく処理されること."""
        mock_response = MagicMock()
        mock_response.content = ["部分1", "部分2", "部分3"]
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await call_llm_with_retry(
            mock_llm,
            [{"role": "user", "content": "hello"}],
        )

        assert result == "部分1\n部分2\n部分3"

    @pytest.mark.asyncio
    async def test_response_content_as_list_of_dicts(self, mock_llm: MagicMock):
        """LLM 応答が dict リスト形式でも正しく処理されること."""
        mock_response = MagicMock()
        mock_response.content = [
            {"text": "応答テキスト", "type": "text"},
        ]
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await call_llm_with_retry(
            mock_llm,
            [{"role": "user", "content": "hello"}],
        )

        assert "応答テキスト" in result

    @pytest.mark.asyncio
    async def test_response_content_as_non_string(self, mock_llm: MagicMock):
        """LLM 応答が文字列以外の形式でも str() 変換されること."""
        mock_response = MagicMock()
        mock_response.content = 12345
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await call_llm_with_retry(
            mock_llm,
            [{"role": "user", "content": "hello"}],
        )

        assert result == "12345"

    @pytest.mark.asyncio
    async def test_zero_max_retries_no_retry(self, mock_llm: MagicMock):
        """max_retries=0 の場合、リトライせず即座にエラーになること."""

        class ServerError(Exception):
            pass

        server_error = ServerError("server error")
        server_error.status_code = 500  # type: ignore[union-attr]

        mock_llm.ainvoke = AsyncMock(side_effect=server_error)

        with pytest.raises(LLMTemporaryError):
            await call_llm_with_retry(
                mock_llm,
                [{"role": "user", "content": "hello"}],
                max_retries=0,
                base_delay=0.01,
            )

        assert mock_llm.ainvoke.call_count == 1
