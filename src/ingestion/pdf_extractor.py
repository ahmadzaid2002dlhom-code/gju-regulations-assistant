from __future__ import annotations

import re
from pathlib import Path

import fitz

from src.models import ExtractedPage


PRINTED_PAGE_PATTERN = re.compile(r"^(?:page\s+)?([0-9٠-٩]+|[ivxlcdm]+)$", re.IGNORECASE)


def _printed_page_number(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    candidates = lines[:3] + lines[-3:]
    for candidate in candidates:
        match = PRINTED_PAGE_PATTERN.fullmatch(candidate)
        if match:
            return match.group(1)
    return None


def extract_pdf_pages(pdf_path: str | Path) -> list[ExtractedPage]:
    pages: list[ExtractedPage] = []
    with fitz.open(str(pdf_path)) as document:
        if document.needs_pass:
            raise ValueError("The PDF is password-protected and cannot be extracted.")

        for index, page in enumerate(document):
            page_text = page.get_text("text", sort=True).strip()
            pages.append(
                ExtractedPage(
                    pdf_page_number=index + 1,
                    printed_page_number=_printed_page_number(page_text),
                    page_text=page_text,
                )
            )
    return pages
