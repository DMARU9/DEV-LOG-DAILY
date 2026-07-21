"""トークン分割の単体テスト.

チャンク分割、トークン数推定、Map-Reduce 統合の基本動作を検証する。
"""

from unittest.mock import AsyncMock

import pytest

from dev_log_daily.llm.chunking import estimate_tokens, process_with_chunking, split_into_chunks


class TestEstimateTokens:
    """estimate_tokens() のテスト."""

    def test_empty_string(self):
        """空文字列のトークン数が 1 と推定されること."""
        assert estimate_tokens("") == 1

    def test_short_ascii_text(self):
        """短い英字テキストのトークン数を推定できること."""
        # "hello" は 5文字 / 4 = 1 + 1 = 2
        assert estimate_tokens("hello") == 2

    def test_mixed_japanese_and_ascii(self):
        """日本語と英字が混在したテキストのトークン数を推定できること."""
        text = "hello 世界"
        # ascii: 6文字 ("hello ") → 6/4 = 1
        # non-ascii: 2文字 ("世界") → 2/2 = 1
        # 合計: 1 + 1 + 1 = 3
        assert estimate_tokens(text) == 3

    def test_long_text(self):
        """長いテキストのトークン数を推定できること."""
        text = "a" * 1000
        # 1000 / 4 = 250 + 1 = 251
        assert estimate_tokens(text) == 251


class TestSplitIntoChunks:
    """split_into_chunks() のテスト."""

    def test_small_text_no_split(self):
        """テキストがチャンクサイズ以下の場合は分割されないこと."""
        text = "小さなテキストです"
        chunks = split_into_chunks(text, chunk_size=1000)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_large_text_split_into_multiple_chunks(self):
        """テキストがチャンクサイズを超える場合は分割されること."""
        # トークン数が 100 を超えるテキストを作成
        text = "\n".join([f"パラグラフ{i}: " + "a" * 50 for i in range(20)])
        chunks = split_into_chunks(text, chunk_size=50)
        assert len(chunks) >= 2

    def test_chunk_size_floor(self):
        """チャンクサイズが 100 未満の場合は 100 に切り上げられること."""
        text = "a" * 500
        chunks = split_into_chunks(text, chunk_size=10)
        # 100トークン制限で分割されるはず
        assert len(chunks) >= 1

    def test_empty_text_returns_single_chunk(self):
        """空テキストは単一チャンクとして返されること."""
        chunks = split_into_chunks("")
        assert len(chunks) >= 1

    def test_paragraph_boundary_respected(self):
        """段落（改行）境界で分割されること."""
        text = "短い段落1\n短い段落2\n短い段落3"
        chunks = split_into_chunks(text, chunk_size=100)
        assert len(chunks) == 1  # 全部収まる


class TestProcessWithChunking:
    """process_with_chunking() のテスト."""

    @pytest.mark.asyncio
    async def test_small_text_no_chunking(self):
        """テキストが小さい場合、直接 LLM が呼ばれること."""
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=type("R", (), {"content": "要約結果"})())

        result, chunks = await process_with_chunking(
            mock_llm,
            "小さなテキスト",
            "システムプロンプト",
            "{text}を要約してください",
            "{summaries}を統合してください",
            context_window=1000,
        )
        assert result == "要約結果"
        assert chunks == 0
        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_large_text_map_reduce(self):
        """テキストが大きい場合、Map-Reduce が実行されること."""
        # 複数チャンクに分割される大きなテキスト
        large_text = "\n".join([f"内容{i}: " + "abc " * 100 for i in range(20)])

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=type("R", (), {"content": "チャンク要約"})())

        result, chunks = await process_with_chunking(
            mock_llm,
            large_text,
            "システムプロンプト",
            "以下のテキストを要約してください:\n\n{text}",
            "以下を統合してください:\n\n{summaries}",
            context_window=500,
        )
        assert result is not None
        assert chunks > 0
        # Map-Reduce の場合、複数回呼ばれる
        assert mock_llm.ainvoke.call_count >= 2

    @pytest.mark.asyncio
    async def test_single_chunk_after_split_skips_reduce(self):
        """分割後チャンクが1つだけの場合、Reduce はスキップされること."""
        text = "ある程度の長さのテキストです。" * 50

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=type("R", (), {"content": "要約"})())

        result, chunks = await process_with_chunking(
            mock_llm,
            text,
            "システムプロンプト",
            "要約: {text}",
            "統合: {summaries}",
            context_window=100000,  # 大きなウィンドウで分割不要に
        )
        assert result is not None
        assert chunks == 0
        assert mock_llm.ainvoke.call_count == 1
