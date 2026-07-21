"""トークン分割・要約統合ロジック（Map-Reduce パターン）.

データサイズがモデルのコンテキストウィンドウを超える場合:
1. テキストをトークン数ベースでチャンク分割（オーバーラップなし）
2. 各チャンクを個別に LLM で要約（中間要約 / Map）
3. 全中間要約を統合し、最終出力を生成（Reduce）
"""

from __future__ import annotations

import logging

from langchain_openai import ChatOpenAI

from .client import call_llm_with_retry

logger = logging.getLogger(__name__)

# デフォルトのチャンクサイズ設定
# モデルのコンテキストウィンドウの 80% を安全マージンとして使用
DEFAULT_CONTEXT_WINDOW = 131072  # デフォルト値（実際はモデルに応じて設定）
CHUNK_SAFETY_RATIO = 0.8


def estimate_tokens(text: str) -> int:
    """テキストのトークン数を簡易推定する.

    英字は 4 文字 ≈ 1 トークン、日本語は 2 文字 ≈ 1 トークンの近似.

    Args:
        text: 推定するテキスト

    Returns:
        推定トークン数
    """
    # 簡単な近似: 英数字・空白を英字としてカウント
    ascii_chars = sum(1 for c in text if c.isascii())
    non_ascii_chars = len(text) - ascii_chars
    return ascii_chars // 4 + non_ascii_chars // 2 + 1


def split_into_chunks(
    text: str,
    chunk_size: int | None = None,
    context_window: int = DEFAULT_CONTEXT_WINDOW,
) -> list[str]:
    """テキストをトークン数ベースでチャンク分割する（オーバーラップなし）.

    Args:
        text: 分割するテキスト
        chunk_size: チャンクあたりの最大トークン数（None の場合は context_window の 80%）
        context_window: モデルのコンテキストウィンドウサイズ

    Returns:
        分割されたチャンクのリスト
    """
    if chunk_size is None:
        chunk_size = int(context_window * CHUNK_SAFETY_RATIO)

    # チャンクサイズが小さすぎる場合のガード
    if chunk_size < 100:
        chunk_size = 100

    # 改行で分割してからチャンクを構築（文の途中での分割を避ける）
    paragraphs = text.split("\n")
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_tokens = 0

    for paragraph in paragraphs:
        para_tokens = estimate_tokens(paragraph)

        # 単一パラグラフがチャンクサイズを超える場合、強制分割
        if para_tokens > chunk_size:
            # 現在のチャンクがあれば確定
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_tokens = 0

            # 長いパラグラフを文字数ベースで強制分割
            char_limit = chunk_size * 4  # 概算: 1トークン ≈ 4文字
            for i in range(0, len(paragraph), char_limit):
                chunks.append(paragraph[i : i + char_limit])
            continue

        # 現在のチャンクに追加
        if current_tokens + para_tokens > chunk_size:
            chunks.append("\n".join(current_chunk))
            current_chunk = [paragraph]
            current_tokens = para_tokens
        else:
            current_chunk.append(paragraph)
            current_tokens += para_tokens

    # 最後のチャンクを追加
    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks if chunks else [text]


async def map_summarize(
    llm: ChatOpenAI,
    chunk: str,
    system_prompt: str,
    map_prompt_template: str,
) -> str:
    """単一チャンクを LLM で要約する（Map フェーズ）.

    Args:
        llm: ChatOpenAI インスタンス
        chunk: 要約するチャンクテキスト
        system_prompt: システムプロンプト
        map_prompt_template: Map 用プロンプトテンプレート（{text} プレースホルダを含む）

    Returns:
        チャンクの要約テキスト
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": map_prompt_template.format(text=chunk)},
    ]
    return await call_llm_with_retry(llm, messages)


async def reduce_summaries(
    llm: ChatOpenAI,
    summaries: list[str],
    system_prompt: str,
    reduce_prompt_template: str,
) -> str:
    """複数の中間要約を統合し最終出力を生成する（Reduce フェーズ）.

    Args:
        llm: ChatOpenAI インスタンス
        summaries: 中間要約のリスト
        system_prompt: システムプロンプト
        reduce_prompt_template: Reduce 用プロンプトテンプレート（{summaries} プレースホルダを含む）

    Returns:
        統合された最終要約テキスト
    """
    combined = "\n\n---\n\n".join(f"【チャンク {i + 1}】\n{s}" for i, s in enumerate(summaries))
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": reduce_prompt_template.format(summaries=combined),
        },
    ]
    return await call_llm_with_retry(llm, messages)


async def process_with_chunking(
    llm: ChatOpenAI,
    text: str,
    system_prompt: str,
    map_prompt_template: str,
    reduce_prompt_template: str,
    context_window: int = DEFAULT_CONTEXT_WINDOW,
) -> tuple[str, int]:
    """テキストを必要に応じてチャンク分割し、Map-Reduce で処理する.

    テキストがコンテキストウィンドウに収まる場合は直接 LLM に送信し、
    収まらない場合は分割 → 個別要約 → 統合のフローで処理する.

    Args:
        llm: ChatOpenAI インスタンス
        text: 処理するテキスト
        system_prompt: システムプロンプト
        map_prompt_template: Map 用プロンプトテンプレート
        reduce_prompt_template: Reduce 用プロンプトテンプレート
        context_window: モデルのコンテキストウィンドウサイズ

    Returns:
        (最終処理結果テキスト, チャンク分割数) のタプル
    """
    estimated = estimate_tokens(text)
    chunk_size = int(context_window * CHUNK_SAFETY_RATIO)

    # チャンクサイズの 80% 以下なら分割不要
    if estimated <= chunk_size:
        logger.info(
            "テキストが小さいため分割不要 (estimated=%d, limit=%d)",
            estimated,
            chunk_size,
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": map_prompt_template.format(text=text)},
        ]
        result = await call_llm_with_retry(llm, messages)
        return result, 0

    # チャンク分割して Map-Reduce
    logger.info(
        "テキストが大きいため分割処理 (estimated=%d, limit=%d)",
        estimated,
        chunk_size,
    )
    chunks = split_into_chunks(text, context_window=context_window)
    logger.info("チャンク分割完了: %d チャンク", len(chunks))

    # Map: 各チャンクを要約
    summaries: list[str] = []
    for i, chunk in enumerate(chunks):
        logger.info("チャンク %d/%d を要約中...", i + 1, len(chunks))
        summary = await map_summarize(llm, chunk, system_prompt, map_prompt_template)
        summaries.append(summary)

    # Reduce: 統合
    chunk_count = len(chunks)
    logger.info("全 %d チャンクの要約を統合中...", chunk_count)
    if len(summaries) == 1:
        return summaries[0], chunk_count

    result = await reduce_summaries(llm, summaries, system_prompt, reduce_prompt_template)
    return result, chunk_count
