from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

import fitz

from src.models import ExtractedPage


PRINTED_PAGE_PATTERN = re.compile(r"^(?:page\s+)?([0-9٠-٩]+|[ivxlcdm]+)$", re.IGNORECASE)
ARABIC_CHARACTER_PATTERN = re.compile(r"[\u0600-\u06ff]")
LATIN_CHARACTER_PATTERN = re.compile(r"[A-Za-z]")


class OCRProvider(Protocol):
    def extract_text(
        self,
        image_bytes: bytes,
        *,
        page_number: int,
        language: str | None,
    ) -> str: ...


def _restore_arabic_reading_order(text: str) -> str:
    restored_lines: list[str] = []
    for line in text.splitlines():
        words = line.split()
        if (
            len(words) > 1
            and len(ARABIC_CHARACTER_PATTERN.findall(line))
            > len(LATIN_CHARACTER_PATTERN.findall(line))
        ):
            words.reverse()
        restored_lines.append(" ".join(words))
    return "\n".join(restored_lines)


def _printed_page_number(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    candidates = lines[:3] + lines[-3:]
    for candidate in candidates:
        match = PRINTED_PAGE_PATTERN.fullmatch(candidate)
        if match:
            return match.group(1)
    return None


def extract_pdf_pages(
    pdf_path: str | Path,
    *,
    ocr_provider: OCRProvider | None = None,
    language: str | None = None,
) -> list[ExtractedPage]:
    pages: list[ExtractedPage] = []
    with fitz.open(str(pdf_path)) as document:
        if document.needs_pass:
            raise ValueError("The PDF is password-protected and cannot be extracted.")

        for index, page in enumerate(document):
            page_text = page.get_text("text", sort=True).strip()
            if page_text and language == "ar":
                page_text = _restore_arabic_reading_order(page_text)
            if not page_text and ocr_provider is not None:
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                page_text = ocr_provider.extract_text(
                    pixmap.tobytes("png"),
                    page_number=index + 1,
                    language=language,
                ).strip()
            pages.append(
                ExtractedPage(
                    pdf_page_number=index + 1,
                    printed_page_number=_printed_page_number(page_text),
                    page_text=page_text,
                )
            )
    return pages
