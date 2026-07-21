"""LLM クライアント — langchain-openai ChatOpenAI を使用したリトライ・タイムアウト制御."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

logger = logging.getLogger(__name__)


class LLMTemporaryError(Exception):
    """一時的なLLMエラー（リトライ可能）.

    例: HTTP 429（レート制限）、5xx（サーバーエラー）、ネットワークタイムアウト
    """


class LLMPermanentError(Exception):
    """永続的なLLMエラー（即時停止）.

    例: HTTP 400（Bad Request）、401（Unauthorized）、403（Forbidden）
    """


def create_llm(
    model: str,
    base_url: str,
    api_key: str,
    temperature: float = 0.0,
    timeout: int = 600,
    max_retries: int = 0,  # 自前でリトライ制御するため本体ではリトライしない
    max_tokens: int | None = None,
) -> ChatOpenAI:
    """ChatOpenAI インスタンスを生成する.

    timeout=0 の場合はタイムアウトなし（無制限待機）となります。
    ローカルLLMのように応答が遅い環境では 0 を推奨します。

    Args:
        model: モデル名
        base_url: API ベース URL
        api_key: API キー
        temperature: 生成時の温度パラメータ（デフォルト 0 = 決定論的）
        timeout: リクエストタイムアウト（秒）。0 で無制限待機
        max_retries: 内部リトライ回数（自前制御のため 0）
        max_tokens: 生成応答の最大トークン数（None の場合はモデル既定値）

    Returns:
        設定済みの ChatOpenAI インスタンス
    """
    kwargs: dict[str, Any] = {
        "model": model,
        "base_url": base_url,
        "api_key": SecretStr(api_key),
        "temperature": temperature,
        # timeout=0 の場合、None を渡して無制限待機（ローカルLLM対策）
        "timeout": None if timeout <= 0 else timeout,
        "max_retries": max_retries,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    return ChatOpenAI(**kwargs)


def classify_llm_error(http_status: int | None, error_message: str) -> type[Exception]:
    """HTTP ステータスコードとエラーメッセージからエラー種別を判定する.

    Args:
        http_status: HTTP ステータスコード（不明な場合は None）
        error_message: エラーメッセージ文字列

    Returns:
        LLMTemporaryError または LLMPermanentError のいずれか
    """
    if http_status is None:
        # ステータスコード不明 → タイムアウト・ネットワークエラー等（一時的と判断）
        return LLMTemporaryError

    if http_status in (429,) or (500 <= http_status < 600):
        # 429: レート制限, 5xx: サーバーエラー → 一時的
        return LLMTemporaryError

    # 400, 401, 403 等 → 永続的
    return LLMPermanentError


async def call_llm_with_retry(
    llm: ChatOpenAI,
    messages: list[dict[str, Any]],
    max_retries: int = 3,
    base_delay: float = 5.0,
) -> str:
    """LLM を呼び出し、エラー時に指数バックオフリトライを実行する.

    Args:
        llm: ChatOpenAI インスタンス
        messages: 送信するメッセージリスト
        max_retries: 最大リトライ回数（デフォルト 3）
        base_delay: 初期待機時間（秒、デフォルト 5.0）

    Returns:
        LLM からの応答文字列

    Raises:
        LLMPermanentError: 永続エラー（400/401/403）の場合 → 即時停止
        LLMTemporaryError: リトライ上限到達後も失敗の場合
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            response = await llm.ainvoke(messages)
            content = response.content
            if isinstance(content, str):
                return content
            # list[str | dict] の場合は先頭の文字列要素を返す
            if isinstance(content, list):
                parts: list[str] = []
                for item in content:
                    if isinstance(item, str):
                        parts.append(item)
                    elif isinstance(item, dict):
                        parts.extend(str(v) for v in item.values() if isinstance(v, str))
                return "\n".join(parts)
            return str(content)

        except Exception as e:
            last_exception = e
            error_str = str(e).lower()

            # HTTP ステータスコードの判定を試みる
            http_status: int | None = None
            if hasattr(e, "status_code"):
                http_status = e.status_code  # type: ignore[union-attr]
            elif hasattr(e, "response") and hasattr(e.response, "status_code"):  # type: ignore[union-attr]
                http_status = e.response.status_code  # type: ignore[union-attr]

            error_type = classify_llm_error(http_status, error_str)

            if error_type == LLMPermanentError:
                logger.error(
                    "LLM永続エラー (attempt %d/%d): %s",
                    attempt + 1,
                    max_retries + 1,
                    e,
                )
                raise LLMPermanentError(
                    f"LLM呼び出しエラー (HTTP {http_status or '不明'}): {e}"
                ) from e

            # 一時的エラー → リトライ
            if attempt < max_retries:
                delay = base_delay * (2**attempt)
                logger.warning(
                    "LLM一時的エラー (attempt %d/%d, delay %.1fs): %s",
                    attempt + 1,
                    max_retries + 1,
                    delay,
                    e,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "LLMリトライ上限到達 (attempt %d/%d): %s",
                    attempt + 1,
                    max_retries + 1,
                    e,
                )
                raise LLMTemporaryError(
                    f"LLM呼び出しエラー（リトライ {max_retries}/{max_retries} 失敗）: {e}"
                ) from e

    # ここには到達しないが、型安全性のため
    raise LLMTemporaryError(f"予期しないエラー: {last_exception}")
