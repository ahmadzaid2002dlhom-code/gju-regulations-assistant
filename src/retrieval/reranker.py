from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from src.models import RetrievalHit


def _normalize(hits: list[RetrievalHit], field: str) -> list[RetrievalHit]:
    maximum = max((getattr(hit, field) for hit in hits), default=0.0)
    if maximum <= 0:
        return hits
    return [replace(hit, **{field: getattr(hit, field) / maximum}) for hit in hits]


def merge_and_rerank(
    vector_hits: list[RetrievalHit],
    keyword_hits: list[RetrievalHit],
    section_hits: list[RetrievalHit],
) -> list[RetrievalHit]:
    normalized_groups = (
        _normalize(vector_hits, "vector_score"),
        _normalize(keyword_hits, "keyword_score"),
        _normalize(section_hits, "section_score"),
    )
    merged: dict[str, RetrievalHit] = {}
    for hit in _flatten(normalized_groups):
        if hit.chunk_id not in merged:
            merged[hit.chunk_id] = hit
            continue
        current = merged[hit.chunk_id]
        current.vector_score = max(current.vector_score, hit.vector_score)
        current.keyword_score = max(current.keyword_score, hit.keyword_score)
        current.section_score = max(current.section_score, hit.section_score)

    for hit in merged.values():
        hit.freshness_score = 1.0 if hit.document_status == "current" else 0.0
        hit.final_score = (
            0.50 * hit.vector_score
            + 0.25 * hit.keyword_score
            + 0.15 * hit.section_score
            + 0.10 * hit.freshness_score
        )
    return sorted(merged.values(), key=lambda hit: hit.final_score, reverse=True)


def _flatten(groups: Iterable[list[RetrievalHit]]) -> Iterable[RetrievalHit]:
    for group in groups:
        yield from group


def select_diverse_hits(hits: list[RetrievalHit], limit: int) -> list[RetrievalHit]:
    selected: list[RetrievalHit] = []
    per_section: dict[tuple[str, str | None], int] = {}
    for hit in hits:
        key = (hit.document_id, hit.article_number or hit.section_title)
        if per_section.get(key, 0) >= 2:
            continue
        selected.append(hit)
        per_section[key] = per_section.get(key, 0) + 1
        if len(selected) >= limit:
            break
    return selected
