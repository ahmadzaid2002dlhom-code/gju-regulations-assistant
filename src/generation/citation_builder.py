from __future__ import annotations

import re

from src.models import EvidenceSource


SOURCE_REFERENCE_PATTERN = re.compile(r"\[S\d+\]")


def page_label(source: EvidenceSource) -> str:
    hit = source.hit
    if hit.pdf_page_start == hit.pdf_page_end:
        return str(hit.pdf_page_start)
    return f"{hit.pdf_page_start}-{hit.pdf_page_end}"


def source_summary(source: EvidenceSource) -> str:
    hit = source.hit
    location = f"Article {hit.article_number}" if hit.article_number else hit.section_title
    parts = [source.source_id, hit.document_title]
    if location:
        parts.append(location)
    parts.append(f"PDF page {page_label(source)}")
    return " — ".join(parts)


def ensure_source_references(answer: str, sources: list[EvidenceSource]) -> str:
    if not sources or SOURCE_REFERENCE_PATTERN.search(answer):
        return answer.strip()
    labels = ", ".join(f"[{source.source_id}]" for source in sources)
    return answer.strip() + f"\n\nRetrieved official sources: {labels}"
