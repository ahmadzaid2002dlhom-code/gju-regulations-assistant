from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

try:
    import tiktoken
except ImportError:  # pragma: no cover - fallback supports lightweight inspection
    tiktoken = None

from src.ingestion.heading_detector import ARTICLE_PATTERN, normalize_number
from src.models import (
    ArticleBlock,
    ArticlePiece,
    DetectedSection,
    ExtractedPage,
    PreparedChunk,
)


class _TokenCodec:
    def __init__(self) -> None:
        self._encoding = None
        if tiktoken:
            try:
                self._encoding = tiktoken.get_encoding("cl100k_base")
            except Exception:
                # The first tiktoken use may need to fetch its vocabulary. PDF
                # ingestion must remain usable on restricted or offline machines.
                self._encoding = None

    def encode(self, text: str) -> list[int] | list[str]:
        if self._encoding:
            return self._encoding.encode(text)
        return re.findall(r"\S+\s*", text)

    def decode(self, tokens: Sequence[int] | Sequence[str]) -> str:
        if self._encoding:
            return self._encoding.decode(list(tokens)).strip()
        return "".join(str(token) for token in tokens).strip()


@dataclass(slots=True)
class _PageTokenSpan:
    start: int
    end: int
    page_number: int


def article_blocks(
    pages: list[ExtractedPage],
    sections: list[DetectedSection],
) -> list[ArticleBlock]:
    section_lookup = {
        (section.article_number, section.page_start): section
        for section in sections
        if section.section_type == "article"
    }
    blocks: list[ArticleBlock] = []
    current: ArticleBlock | None = None

    def append_current() -> None:
        nonlocal current
        if current and any(piece.text.strip() for piece in current.pieces):
            blocks.append(current)
        current = None

    for page in pages:
        text = page.page_text.strip()
        if not text:
            continue
        matches = list(ARTICLE_PATTERN.finditer(text))
        if not matches:
            if current is None:
                current = ArticleBlock(
                    local_section_key=None,
                    article_number=None,
                    section_title=page.section_title,
                )
            current.pieces.append(ArticlePiece(page.pdf_page_number, text))
            continue

        prefix = text[: matches[0].start()].strip()
        if prefix:
            if current is None:
                current = ArticleBlock(None, None, page.section_title)
            current.pieces.append(ArticlePiece(page.pdf_page_number, prefix))

        for match_index, match in enumerate(matches):
            append_current()
            number = normalize_number(match.group(1))
            section = section_lookup.get((number, page.pdf_page_number))
            end = matches[match_index + 1].start() if match_index + 1 < len(matches) else len(text)
            current = ArticleBlock(
                local_section_key=section.local_key if section else None,
                article_number=number,
                section_title=section.title if section else f"Article {number}",
                pieces=[ArticlePiece(page.pdf_page_number, text[match.start() : end].strip())],
            )

    append_current()
    return blocks


def _embedding_text(
    *,
    document_title: str,
    document_type: str,
    language: str,
    block: ArticleBlock,
    page_start: int,
    text: str,
) -> str:
    context = [
        f"Document: {document_title}",
        f"Category: {document_type}",
        f"Language: {language}",
    ]
    if block.section_title:
        context.append(f"Section: {block.section_title}")
    if block.article_number:
        context.append(f"Article: {block.article_number}")
    context.append(f"PDF page: {page_start}")
    return "\n".join(context) + "\n\n" + text


def create_chunks(
    *,
    pages: list[ExtractedPage],
    sections: list[DetectedSection],
    document_title: str,
    document_type: str,
    language: str,
    academic_year: str | None,
    document_status: str = "current",
    target_tokens: int = 700,
    max_tokens: int = 1000,
    overlap_tokens: int = 75,
) -> list[PreparedChunk]:
    if target_tokens <= overlap_tokens:
        raise ValueError("target_tokens must be greater than overlap_tokens")
    if max_tokens < target_tokens:
        raise ValueError("max_tokens must be at least target_tokens")

    codec = _TokenCodec()
    page_lookup = {page.pdf_page_number: page for page in pages}
    chunks: list[PreparedChunk] = []

    for block in article_blocks(pages, sections):
        all_tokens: list[int] | list[str] = []
        spans: list[_PageTokenSpan] = []
        for piece in block.pieces:
            piece_tokens = codec.encode(piece.text + "\n")
            start = len(all_tokens)
            all_tokens.extend(piece_tokens)
            spans.append(_PageTokenSpan(start, len(all_tokens), piece.page_number))

        if not all_tokens:
            continue

        window = len(all_tokens) if len(all_tokens) <= max_tokens else target_tokens
        start = 0
        while start < len(all_tokens):
            end = min(start + window, len(all_tokens))
            text = codec.decode(all_tokens[start:end])
            covered_pages = sorted(
                {
                    span.page_number
                    for span in spans
                    if span.start < end and span.end > start
                }
            )
            page_start = covered_pages[0]
            page_end = covered_pages[-1]
            chunks.append(
                PreparedChunk(
                    chunk_index=len(chunks),
                    chunk_text=text,
                    embedding_text=_embedding_text(
                        document_title=document_title,
                        document_type=document_type,
                        language=language,
                        block=block,
                        page_start=page_start,
                        text=text,
                    ),
                    pdf_page_start=page_start,
                    pdf_page_end=page_end,
                    printed_page_start=page_lookup[page_start].printed_page_number,
                    printed_page_end=page_lookup[page_end].printed_page_number,
                    section_title=block.section_title,
                    article_number=block.article_number,
                    section_local_key=block.local_section_key,
                    language=language,
                    academic_year=academic_year,
                    document_status=document_status,
                    token_count=end - start,
                )
            )
            if end == len(all_tokens):
                break
            start = end - overlap_tokens

    return chunks
